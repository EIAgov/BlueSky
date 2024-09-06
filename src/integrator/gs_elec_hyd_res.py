"""
Iteratively solve 3 models with GS methodology

Gameplan:
1.  Use a config file to control the regions & years to sync
2.  Make a fake set of demands for the H2 model to kick-start it and get a non-zero H2 price
3.  Make an ELEC model
4.  Make an H2 model
5.  Solve the ELEC model
5b.  Catch metrics from ELEC
6.  Update the H2 model
    a.  pass in Elec Price (GS!!)
    b.  pass in H2 demand (GS!!)
7.  Solve H2 model
8.  Make Res Model
9.  Pass ELEC Prices in (GS!! ~kinda right now)
10.  Solve Res Model
11.  Update the Elec model
    a.  new Load
    b.  new H2 Price
    c.  Future:  Elec demand from H2 (ON HOLD!)
12.  Evaluate termination conditions
13.  Loop to 5
14.  Process output

                       ~~~~~~ INFO SWAP PLAN ~~~~~
                   [ solve points annotated with =S= ]

    H2 MODEL                    ELEC MODEL                  RES/DEMAND
        |                           |                           |
        |                          =S=                          |
        |                           |                           |
        |<<<--- ELEC Prices --------|                           |
        |<<<--- H2 Demand ----------|                           |
        |                           |                           |
       =S=                          |                           |
        |                           |                           |
        |                           |------- ELEC Prices ---->>>|
        |                           |                           |
        |                           |                          =S=
        |------ H2 Prices ------->>>|                           |
        |                           |<<<--- New Load -----------|
        |                           |                           |

7.  re-solve each model
8.  Calculate prev_value - |H2.obj| + |ELEC.obj| < tolerance
9.  No?:  goto 5


"""

from logging import getLogger
from pathlib import Path
import tomllib
import pyomo.environ as pyo
import pandas as pd
from collections import namedtuple

from definitions import PROJECT_ROOT
from src.integrator import config_setup
from src.integrator.progress_plot import plot_it
from src.integrator.utilities import (
    EI,
    convert_elec_price_to_lut,
    convert_h2_price_records,
    regional_annual_prices,
    poll_h2_prices_from_elec,
    poll_hydrogen_price,
    get_elec_price,
)
from src.models.electricity.scripts.runner import run_model, init_old_cap, update_cost, set_new_cap
from src.models.hydrogen.model import actions
from src.models.residential.scripts.residential import residentialModule

logger = getLogger(__name__)

HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
data_path = HYDROGEN_ROOT / 'inputs/single_region'  # has a bit of regions 7 data

# settings....  In "the future" these should be some params from a setup/config file
update_h2_price = True
update_elec_price = True
update_h2_demand = True
update_load = True

# vvvvvvvvvvvvvvvv   note this will require turning on the annual demand constraint in elec and adjusting the dual-to-price function
update_elec_demand = False


def run_gs_combo(config_path: Path):
    """Start the iterative GS process

    Parameters
    ----------
    config_path : Path
        Path to config file
    """
    # some data gathering
    h2_price_records = []
    elec_price_records = []
    h2_obj_records = []
    elec_obj_records = []
    h2_demand_records = []
    elec_demand_records = []
    load_records = []
    elec_price_to_res_records = []
    iter = 0

    logger.info('Starting Iterative ELEC-HYD-RES run')
    # ------------------ 1.  get the settings for the solve...
    settings = config_setup.Config_settings(config_path)
    force_10 = settings.force_10  # basically force 10 solves
    tol = settings.tol  # relative tolerance
    max_iter = settings.max_iter  # max number of iterations
    years = settings.years
    regions = settings.regions

    # ------------------ 2.  starting demands for H2 should be included in selected region data for now...

    # ------------------ 3.  ELEC model
    logger.info('Making ELEC Model')
    elec_model = run_model(settings, solve=False)

    # let's sneak a peek at the "original" load
    agg_load = sum(pyo.value(elec_model.Load[idx]) for idx in elec_model.Load)  # type: ignore
    load_records.append((0, agg_load))

    if elec_model.sw_learning == 1:  # initializing iterative learning
        # initialize capacity to set pricing
        init_old_cap(elec_model)
        elec_model.new_cap = elec_model.old_cap
        update_cost(elec_model)

    # ------------------ 4.  H2 model
    logger.info('Making/loading H2 model')
    grid_data = actions.load_data(data_path, regions_of_interest=regions)
    grid = actions.build_grid(grid_data=grid_data)
    h2_model = actions.build_model(grid=grid, years=years)

    done = False
    old_obj_sum = 0
    while not done:
        # ------------------ 5.  ELEC model solve
        simple_solve(elec_model)

        e_obj = pyo.value(elec_model.totalCost)
        logger.info('Iter %d Elec Obj: %0.2f', iter, e_obj)
        elec_obj_records.append((iter, e_obj))

        # ------------------ 5b.  ELEC metrics
        if update_h2_demand:
            h2_demand = elec_model.poll_h2_demand()
            tot_h2_demand = sum(elec_model.poll_h2_demand().values())
            h2_demand_records.append((iter + 1, tot_h2_demand))
        else:
            h2_demand = None

        if update_elec_price:
            rap = regional_annual_prices(elec_model)
            annual_avg = sum(rap.values()) / len(rap)
            # avg_elec_price = sum(t[1] for t in new_elec_prices) / len(new_elec_prices)
            grand_avg = sum(rap.values()) / len(rap)
            elec_price_records.append((iter + 1, grand_avg))
        else:
            rap = None

        # ------------------ 6.  Update H2 model

        if rap:
            h2_model.update_exchange_params(new_electricity_price=rap)
        if h2_demand:
            h2_model.update_exchange_params(new_demand=h2_demand)

        # ------------------ 7.  Solve H2 model
        simple_solve(h2_model)
        h2_obj = pyo.value(h2_model.total_cost)
        h2_obj_records.append((iter, h2_obj))
        logger.info('Iter %d H2 Obj: %0.2f', iter, h2_obj)

        # some logging of the iteration...
        h2_consumption_data = elec_model.poll_h2_demand()
        logger.debug('h2 consumption: %s', h2_consumption_data)
        logger.debug(
            'Actual h2 prices used in last iteration:\n %s',
            poll_h2_prices_from_elec(model=elec_model, tech=5, regions=(7,)),
        )
        # ------------------ 8.  Make Res Model
        # currently we need a "meta" model -- basically a pass-through
        meta = pyo.ConcreteModel()
        meta.elec_price = pyo.Param(elec_model.LoadSet, initialize=0, default=0, mutable=True)

        prices = get_elec_price(elec_model)
        prices = prices.set_index(['r', 'y', 'hr'])['price_wt'].to_dict()
        prices = [(EI(*k), prices[k]) for k, v in prices.items()]

        # dev note:  we must use this because the Res model needs (reg, yr, hr) not just (reg, yr)!
        price_lut = convert_elec_price_to_lut(prices=prices)

        # cannot have zero prices, so a quick interim check...  Belt AND suspenders!
        for idx, price in price_lut.items():
            assert price > 0, f'found a bad apple {idx}'
        meta.elec_price.store_values(price_lut)

        res_model = residentialModule()

        # ------------------ 9.  Pass in Elec Prices
        blk = res_model.make_block(meta.elec_price, meta.elec_price.index_set())
        # record the price reported to Elec
        grand_av_price = sum(pyo.value(meta.elec_price[idx]) for idx in meta.elec_price) / len(
            meta.elec_price
        )
        elec_price_to_res_records.append((iter + 1, grand_av_price))
        logger.info('grand avg elec price told to res: %0.2f', grand_av_price)

        # ------------------ 10.  Solve Res Model
        # now we have a single constraint in the block, properly constraining the Load var
        # add this block to the meta model so that we can "solve it"
        # TODO:  this is going to cause warnings in pyomo by replacing a named component
        #        need to modify to not make a new residential block, just mod what we have
        meta.blk = blk

        # Neet to solve to enforce the constraint and set the variable...
        meta.obj = pyo.Objective(expr=0)  # nonsense... a constant to avoid solver warning

        simple_solve(meta)
        # ------------------ 11.  Update the Elec Model

        # ------------------ 11a.  Update the Elec Model Load

        # now the meta.blk variable "Load" contains new load requests that can be inspected...
        # put them in the elec model parameter (update the mutable param)
        if update_load:
            elec_model.Load.store_values(meta.blk.Load.extract_values())
        agg_load = sum(pyo.value(elec_model.Load[idx]) for idx in elec_model.Load)  # type: ignore
        load_records.append((iter + 1, agg_load))

        # ------------------ 11b.  Update the Elec Model H2 Prices
        if update_h2_price:
            new_h2_prices = poll_hydrogen_price(h2_model)
            avg_hyd_price = sum(t[1] for t in new_h2_prices) / len(new_h2_prices)
            h2_price_records.append((iter + 1, avg_hyd_price))
        else:
            new_h2_prices = None
        if new_h2_prices:
            elec_model.update_h2_prices(h2_prices=convert_h2_price_records(new_h2_prices))

        # ------------------ 11c.  Update Elec demand from H2
        #  BROKEN CODE FOR FUTURE WORK
        # catch metrics from H2 Model
        # elec_demand = h2_model.poll_electric_demand()

        # if update_elec_demand:
        #     tot_e_demand_from_h2_model = sum(elec_demand.values())
        #     # demand is presented in *next* iteration. so + 1 for alignment
        #     elec_demand_records.append((iter + 1, tot_e_demand_from_h2_model))
        # else:
        #     tot_e_demand_from_h2_model = 0

        # ------------------ 11d.  Update Elec capital cost learning
        if elec_model.sw_learning == 1:  # iterative learning update
            # set new capacities
            set_new_cap(elec_model)
            # update learning costs in model
            update_cost(elec_model)
            # update old capacities
            elec_model.old_cap = elec_model.new_cap
            elec_model.old_cap_wt = elec_model.new_cap_wt

        # ------------------ 12.  Check termination criteria

        # TODO:  probably should split the relative change to look at EACH of the
        # suboordinate OBJ's to handle case where they are wildly different in order
        # of magnitude.
        net_obj = round(abs(h2_obj) + abs(e_obj), 2)

        if iter == 0:
            old_obj_sum = net_obj
            done = False
        elif abs((net_obj - old_obj_sum) / old_obj_sum) < tol and not (force_10 and iter < 10):
            # print('under tolerance')
            done = True
        elif iter > max_iter:
            print('iter > max_iter')
            done = True
            logger.warning(f'Terminating iterative solve based on iteration count > {max_iter}!')
        else:
            # print('keep going')
            old_obj_sum = net_obj
        print(f'Finished Iteration {iter} with net obj value: {net_obj:0.2f}')
        logger.info('Completed iteration %d with net obj: %0.2f', iter, net_obj)

        iter += 1

    plot_it(
        h2_price_records=h2_price_records,
        elec_price_records=elec_price_records,
        h2_obj_records=h2_obj_records,
        elec_obj_records=elec_obj_records,
        h2_demand_records=h2_demand_records,
        elec_demand_records=elec_demand_records,
        load_records=load_records,
        elec_price_to_res_records=elec_price_to_res_records,
    )


# TODO:  This might be a good use case for a persistent solver (1-each) for both the elec & hyd...  hmm
def simple_solve(m: pyo.ConcreteModel):
    """a simple solve routine"""

    # Note:  this is a prime candidate to split into 2 persistent solvers!!
    # TODO:  experiment with pyomo's persistent solver interface, one for each ELEC, H2
    opt = pyo.SolverFactory('appsi_highs')
    res = opt.solve(m)
    if pyo.check_optimal_termination(res):
        return
    raise RuntimeError('failed solve in iterator')
