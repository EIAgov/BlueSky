"""
A first crack at unifying the solve of both H2 and Elec

Dev Note:  This works, but needs a lot of cleanup and probably some
restructuring if it were to include the Res model as well in some format

"""

from collections import defaultdict
from logging import getLogger
from pathlib import Path
import tomllib
import pyomo.environ as pyo

from definitions import PROJECT_ROOT
from src.integrator.jacobi_elec_hyd_solver import simple_solve
from src.integrator.progress_plot import plot_it
from src.integrator.utilities import (
    HI,
    convert_h2_price_records,
    regional_annual_prices,
    poll_hydrogen_price,
)
from src.models.electricity.scripts.electricity_model import PowerModel
from src.models.electricity.scripts.runner import run_model
from src.models.hydrogen.model import actions

logger = getLogger(__name__)

HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
data_path = HYDROGEN_ROOT / 'inputs/single_region'  # has a bit of regions 7 data


def run_unified(config_path: Path):
    # some data gathering
    h2_price_records = []
    elec_price_records = []
    h2_obj_records = []
    elec_obj_records = []
    h2_demand_records = []
    elec_demand_records = []
    iter = 0

    logger.info('Starting Iterative ELEC-HYD run')
    # ------------------ 1.  get the regions & years of interest...
    with open(config_path, 'rb') as src:
        config = tomllib.load(src)
        logger.info(f'Retrieved config data: {config}')
        years = [int(year) for year in config['years']]
        regions = config['regions']

    # ------------------ 2.  H2 model
    logger.info('Making H2 Model')
    grid_data = actions.load_data(data_path, regions_of_interest=regions)
    grid = actions.build_grid(grid_data=grid_data)
    h2_model = actions.build_model(grid=grid, years=years)

    # ------------------ 4.  ELEC model
    logger.info('Doing initial solve on Elec')
    elec_model = run_model(years=years, regions=regions, solve=False)

    # ------------------ 5.  Unified Model

    meta = pyo.ConcreteModel('meta')
    meta.h2 = h2_model
    meta.elec = elec_model

    # ------------------ 6.  Update the ELEC model
    # Now, we need to augment several things
    # add the "dormant" variable demand to the ELEC model...
    # note:  This "deactivation" below will need to be re-instated when
    #        the constraint is reinstated.  For now, we don't need
    #        to worry about it or the replacement.  Both monkey
    #        with the cost capture from duals...

    # elec_model.Annual_balance.deactivate()

    # re-work the annual demand in the elec model with the variable instead of the parameter
    def Annual_balance(self: PowerModel, r, y):
        """A quick & ugly summation to balance load on an annual basis if there are
        external, annual demands for electricity
        """
        annual_demand = (
            sum(self.Load[(r, y, hr)] * self.annual_count(hr) for hr in self.hr)
            + self.var_elec_request[r, y]  # <--------------- this is the big change
        )

        annual_production = (
            sum(
                self.Generation[(tech, y, r, step, hr)] * self.annual_count(hr)
                for hr in self.hr
                for (tech, step) in self.GenSetDemandBalance[(y, r, hr)]
            )
            + sum(
                self.Storage_outflow[(tech, y, r, step, hr)] * self.annual_count(hr)
                - self.Storage_inflow[(tech, y, r, step, hr)] * self.annual_count(hr)
                for hr in self.hr
                for (tech, step) in self.StorageSetDemandBalance[(y, r, hr)]
            )
            + sum(self.unmet_Load[(r, y, hr)] * self.annual_count(hr) for hr in self.hr)
            + (
                sum(
                    (
                        self.TradeToFrom[(r, reg1, y, hr)] * (1 - self.setA.TransLoss)
                        - self.TradeToFrom[(reg1, r, y, hr)]
                    )
                    * self.annual_count(hr)
                    for hr in self.hr
                    for (reg1) in self.TradeSetDemandBalance[(y, r, hr)]
                )
                if self.sw_trade and r in self.setA.trade_regs
                else 0
            )
            + (
                sum(
                    self.TradeToFromCan[(r, r_can, y, CSteps, hr)]
                    * (1 - self.setA.TransLoss)
                    * self.annual_count(hr)
                    for hr in self.hr
                    for (r_can, CSteps) in self.TradeCanSetDemandBalance[(y, r, hr)]
                )
                if (self.sw_trade == 1 and r in self.setA.r_can_conn)
                else 0
            )
        )

        return annual_production >= annual_demand

    # elec_model.Annual_balance = pyo.Constraint(elec_model.r, elec_model.y, rule=Annual_balance)

    # ------------------ 7.  Update the ELEC model
    # hook the var_elec_demand to what the H2 model's request...

    # TODO:  Note that the below is part of linking the elec demand back to the elec model
    #        and per comment above, that is disabled for now.  This linking constraint does
    #        work, but is not needed until we feed elec demand back into the model, turn on
    #        constraint above, etc.

    # # helper... this could be moved.  We need to identify which hubs are in each region
    # regional_hubs = defaultdict(list)  # {region_1: [hub_1, hub_2, ...], region_2: ...}
    # for idx in h2_model.h2_volume:
    #     hub, _, _ = idx
    #     region = h2_model.grid.registry.hubs[hub].region
    #     regional_hubs[region].append(hub)

    # def link_elec_demand(meta, r, y):
    #     return elec_model.var_elec_request[r, y] >= sum(
    #         h2_model.h2_volume[hub, tech, y] * 1 / h2_model.efficiencies[tech]
    #         for hub in regional_hubs[r]
    #         for tech in h2_model.technology
    #     )

    # meta.link_elec_demand = pyo.Constraint(elec_model.r, elec_model.y, rule=link_elec_demand)

    # now, connect disable the demand param in the H2 model and hook up the variable demand to what the Elec wants...
    for idx in h2_model.demand:
        h2_model.demand[idx] = 0.0

    # this retrieval from the elec model could be made into just 1 function in the future....  the orig used "value()",
    # it *could* return the variable and we could get the value later in that case
    # it is borrowed from the elec model
    h2_consuming_techs = {5}  # TODO:  get rid of this hard-coding

    # gather results
    res: dict[HI, float] = defaultdict(float)
    # iterate over the Generation variable and screen out the H2 "demanders" and build a
    # summary expression for all the demands in the (region, year) index of the H2 model
    for idx in elec_model.Generation.index_set():
        tech, y, reg, _, hr = idx
        if tech in h2_consuming_techs:
            h2_demand_weighted = (
                elec_model.Generation[idx]
                * elec_model.Idaytq[elec_model.Map_hr_d[hr]]
                * elec_model.h2_conversion_eff
            )
            res[HI(region=reg, year=y)] += h2_demand_weighted

    # hook 'em up with a constraint
    def link_h2_demand(meta, r, y):
        return h2_model.var_demand[r, y] >= res[HI(r, y)]

    meta.link_h2_demand = pyo.Constraint(h2_model.regions, h2_model.year, rule=link_h2_demand)

    # ------------------ 8.  Update the objective
    h2_model.total_cost.deactivate()
    elec_model.totalCost.deactivate()
    meta.obj = pyo.Objective(expr=h2_model.total_cost + elec_model.totalCost)
    meta.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    # let's just iterate...

    done = False
    old_obj_sum = 0  # some fake old objective sum to support iteration
    tol = 0.05  # relative change
    while not done:
        logger.info('Starting iteration: %d', iter)

        simple_solve(meta)
        # meta.display()

        # ------------------ 9.  Catch Metrics...
        # catch metrics from H2 Model

        # elec_demand = h2_model.poll_electric_demand()
        # tot_e_demand = sum(elec_demand.values())
        # elec_demand_records.append((iter + 1, tot_e_demand))
        h2_obj_records.append((iter, pyo.value(h2_model.total_cost())))
        new_h2_prices = poll_hydrogen_price(meta, block=meta.h2)
        avg_hyd_price = sum(t[1] for t in new_h2_prices) / len(new_h2_prices)
        h2_price_records.append((iter + 1, avg_hyd_price))  # price for "next" iter

        # catch metrics from Elec
        tot_h2_demand = sum(elec_model.poll_h2_demand().values())
        h2_demand_records.append((iter + 1, tot_h2_demand))
        logger.debug('Tot H2 Demand for iteration %d: %0.2f', iter, tot_h2_demand)
        elec_obj_records.append((iter, pyo.value(elec_model.totalCost)))

        rap = regional_annual_prices(meta, block=meta.elec)
        grand_avg = sum(rap.values()) / len(rap)
        elec_price_records.append((iter + 1, grand_avg))

        # ------------------ 10.  Info swap
        # H2 prices
        elec_model.update_h2_prices(h2_prices=convert_h2_price_records(new_h2_prices))
        # Elec prices
        h2_model.update_exchange_params(new_electricity_price=rap)

        # ------------------ 11.  Check termination criteria
        meta_obj = pyo.value(meta.obj)
        if iter == 0:
            old_obj_sum = meta_obj
            done = False
        elif abs(meta_obj - old_obj_sum) / old_obj_sum <= tol:
            done = True
        else:
            old_obj_sum = meta_obj

        if iter > 20:
            done = True
            logger.warning('Terminating iterative solve based on iteration count > 20!')
        print(f'Finished Iteration {iter} with meta obj value: {meta_obj:0.2f}')
        iter += 1

    plot_it(
        h2_price_records=h2_price_records,
        elec_price_records=elec_price_records,
        h2_obj_records=h2_obj_records,
        elec_obj_records=elec_obj_records,
        h2_demand_records=h2_demand_records,
        elec_demand_records=elec_demand_records,
    )
