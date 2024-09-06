"""
A first crack at unifying the solve of both H2 and Elec and Res

Dev Notes:

(1).  This borrows heavily from (aka is a cheap copy of) the unified_solver.py which solves
      the elec and h2 jointly
(2).  This is for demonstration purposes only, and it is presumed that an improved single
      class "unified solver" would have selectable options to join models?  Maybe?
(3).  As is the case with the original effort, this can/should be refactored a bit when the
      grand design pattern stabilizes
(4).  The "annual demand" constraint that is present and INACTIVE in the unified_solver.py
      class is omitted here for clarity.  It may likely be needed--in some form--at a later
      time.  Recall, the key linkages to share the electrical demand primary variable are:
          (a).  an annual level demand constraint (see unified_solver.py)
          (b).  an accurate price-pulling function that can consider weighted duals
                from both constraints [NOT done]
(5).  This model has a 2-solve update cycle as commented on near the termination check
      elec_prices gleaned from      cycle[n] results -> solve cycle[n+1]
      new_load gleaned from         cycle[n+1] results -> solve cycle[n+2]
      elec_pices gleaned from       cycle[n+2]
(6).  This iterative process could benefit from refactoring to use a persistent solver, after
      some decisions are made about how to handle arbitrary solvers--some may/may not have
      that capability.

"""

from collections import defaultdict, deque
from logging import getLogger
from pathlib import Path
import tomllib
import pyomo.environ as pyo

from definitions import PROJECT_ROOT
from src.integrator import config_setup
from src.integrator.progress_plot import plot_it
from src.integrator.utilities import (
    HI,
    EI,
    get_elec_price,
    convert_elec_price_to_lut,
    convert_h2_price_records,
    regional_annual_prices,
    poll_hydrogen_price,
)
from src.models.electricity.scripts.electricity_model import PowerModel
from src.models.electricity.scripts.runner import run_model, init_old_cap, update_cost, set_new_cap
from src.models.hydrogen.model import actions
from src.models.residential.scripts.residential import residentialModule

logger = getLogger(__name__)

HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
data_path = HYDROGEN_ROOT / 'inputs/single_region'  # has a bit of regions 7 data


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


def run_unified_res_elec_h2(config_path: Path):
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

    logger.info('Starting Iterative ELEC-HYD run')
    # ------------------ 1.  get the settings for the solve...
    settings = config_setup.Config_settings(config_path)
    force_10 = settings.force_10  # force at least 10 iterations
    tol = settings.tol  # relative change
    max_iter = settings.max_iter  # max number of iterations
    years = settings.years
    regions = settings.regions

    # ------------------ 2.  H2 model
    logger.info('Making H2 Model')
    grid_data = actions.load_data(data_path, regions_of_interest=regions)
    grid = actions.build_grid(grid_data=grid_data)
    h2_model = actions.build_model(grid=grid, years=years)

    # ------------------ 4.  ELEC model
    logger.info('Doing initial solve on Elec')
    elec_model = run_model(settings, solve=False)

    # ------------------ 5.  Residential Block Factory
    # TODO:  The res module *currently* produces non-reusable blocks, so we just set
    #        up the infrastructure here.  We cannot make a block until prices are
    #        known after first turn-of-the-handle with elec model
    res_block_factory = residentialModule()

    # ------------------ 6.  Unified Model

    meta = pyo.ConcreteModel('meta')
    meta.h2 = h2_model
    meta.elec = elec_model
    meta.res = pyo.Block()  # an empty placeholder to facilitate iterative syntax
    meta.elec_price = pyo.Param(elec_model.LoadSet, initialize=0, default=0, mutable=True)

    # ------------------ 6.  Update the ELEC model

    # Dev Note:  The shared primal variable for demand in the Elec model is
    #            not yet hooked up.  See notes in companion file unified_solver.py

    # ------------------ 7.  Update the H2 model
    # hook the var_elec_demand to what the H2 model's request...

    # Dev note:  same as above wrt the demand inject to the elec model.
    #            see unified_solver.py

    # ------------------ 8.  Connect the primary variable for H2 demand
    # zero out the fixed demand from original inputs
    for idx in h2_model.demand:
        h2_model.demand[idx] = 0.0

    # this retrieval from the elec model could be made into just 1 function in the future....  the orig used "value()",
    # it *could* return the variable and we could get the value later in that case
    # it is borrowed from the elec model
    h2_consuming_techs = {5}  # TODO:  get rid of this hard-coding

    # gather results
    h2_demand_equations_from_elec: dict[HI, float] = defaultdict(float)
    # iterate over the Generation variable and screen out the H2 "demanders" and build a
    # summary expression for all the demands in the (region, year) index of the H2 model

    # see note in Elec Model function for polling H2 regarding units of H2_HEATRATE
    for idx in elec_model.Generation.index_set():
        tech, y, reg, _, hr = idx
        if tech in h2_consuming_techs:
            h2_demand_weighted = (
                elec_model.Generation[idx]
                * elec_model.Idaytq[elec_model.Map_hr_d[hr]]
                / elec_model.H2_HEATRATE
            )
            h2_demand_equations_from_elec[HI(region=reg, year=y)] += h2_demand_weighted

    # hook 'em up with a constraint
    def link_h2_demand(meta, r, y):
        return h2_model.var_demand[r, y] >= h2_demand_equations_from_elec[HI(r, y)]

    meta.link_h2_demand = pyo.Constraint(h2_model.regions, h2_model.year, rule=link_h2_demand)

    # ------------------ 9.  Update the objective
    h2_model.total_cost.deactivate()
    elec_model.totalCost.deactivate()
    meta.obj = pyo.Objective(expr=h2_model.total_cost + elec_model.totalCost)
    meta.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    done = False
    meta_objs = deque([], maxlen=3)  # keep the last 3 obj values in a deque

    if meta.elec.sw_learning == 1:  # initializing iterative learning
        # initialize capacity to set pricing
        init_old_cap(meta.elec)
        meta.elec.new_cap = meta.elec.old_cap
        update_cost(meta.elec)

    while not done:
        logger.info('Starting iteration: %d', iter)

        # ------------------ 10.  Solve model
        # solve model
        simple_solve(meta)

        # meta.display()

        # solving this produces 4 things we need to propogate:
        # prices of elec -> res  (12)
        # prices of elec -> H2 (14)
        # prices of H2 -> elec (14)
        # new Load -> elec (13)

        # catch the new Load metric from res...
        if iter > 0:
            meta.elec.Load.store_values(meta.res.Load.extract_values())
            # meta.res.Load.pprint()
            # sys.exit(-1)
        # we can still poll the elec load used from the elec model in all iterations which
        # will show the value used in the next iteration with/without the 0th update above
        agg_load = sum(pyo.value(meta.elec.Load[idx]) for idx in meta.elec.Load)  # type: ignore
        load_records.append((iter + 1, agg_load))
        # dev note:  the res block is now depleted... we have extracted the new load values
        #            In the future, we should make it persistent

        # ------------------ 11.  Attach a new res block
        # Note for the 0th solve there will be no res model, as a price is needed to
        # initialize it, but for iter 1, ..., N there will be a res model in the
        # solve above

        prices = get_elec_price(meta, block=meta.elec)
        prices = prices.set_index(['r', 'y', 'hr'])['price_wt'].to_dict()
        prices = [(EI(*k), prices[k]) for k, v in prices.items()]

        # dev note:  we must use this because the Res model needs (reg, yr, hr) not just (reg, yr)!
        price_lut = convert_elec_price_to_lut(prices=prices)

        # cannot have zero prices, so a quick interim check...  Belt AND suspenders!
        for idx, price in price_lut.items():
            assert price > 0, f'found a bad apple {idx}'
        meta.elec_price.store_values(price_lut)

        # ------------------ 12.  Pass in Elec Prices to res
        res_block = res_block_factory.make_block(meta.elec_price, meta.elec_price.index_set())
        # record the price reported to Elec
        grand_av_price = sum(pyo.value(meta.elec_price[idx]) for idx in meta.elec_price) / len(
            meta.elec_price
        )
        elec_price_to_res_records.append((iter + 1, grand_av_price))
        logger.info('grand avg elec price told to res: %0.2f', grand_av_price)

        meta.del_component(h2_demand_equations_from_elec)
        meta.res = res_block

        # ------------------ 13.  Catch Metrics...
        # catch metrics from H2 Model

        # (on hold per note at top...  although we will catch Load from res, which should
        # be equivalent)
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

        # ------------------ 14.  Info swap
        # H2 prices
        elec_model.update_h2_prices(h2_prices=convert_h2_price_records(new_h2_prices))
        # Elec prices
        h2_model.update_exchange_params(new_electricity_price=rap)

        # ----------------- 14a. Update electricity capital cost learning if applicable
        if meta.elec.sw_learning == 1:  # iterative learning update
            # set new capacities
            set_new_cap(meta.elec)
            # update learning costs in model
            update_cost(meta.elec)
            # update old capacities
            meta.elec.old_cap = meta.elec.new_cap
            meta.elec.old_cap_wt = meta.elec.new_cap_wt

        # ------------------ 15  Check termination criteria
        meta_obj = round(pyo.value(meta.obj), 2)
        # Note:  We must force at least 3 iterations because ...
        #        - the new elec price is set in the 0th iter
        #        - the new load is set in the 1st iter
        #        - the new load is used in the 2nd iter to make a new price
        #        - the 3rd iteration has the updated price and can set a new load
        #
        #        so we have a 2-iteration update cycle, starting at the 3rd

        def under_tolerance() -> bool:
            max_recent = max(meta_objs)
            min_recent = min(meta_objs)
            return abs(max_recent - min_recent) / min_recent < tol

        meta_objs.append(meta_obj)
        if iter < 2:  # we must force at least 3 iterations
            # print('iter < 2')
            done = False
        elif under_tolerance() and not (force_10 and iter < 10):
            # print('under tolerance')
            done = True
        elif iter > max_iter:
            print('iter > max_iter')
            done = True
            logger.warning(f'Terminating iterative solve based on iteration count > {max_iter}!')
        else:
            # print('keep going')
            done = False
        print(f'Finished Iteration {iter} with meta obj value: {meta_obj:0.2f}')
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
