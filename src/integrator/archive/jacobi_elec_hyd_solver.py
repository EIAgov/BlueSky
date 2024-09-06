"""
Iteratively solve 2 models with Jacobi (like) method

Gameplan:
1.  Use a config file to control the regions & years to sync
2.  Make a fake set of demands for the H2 model to kick-start it and get a non-zero H2 price
3.  Make an H2 model
4.  Make an ELEC model
4 1/2.  Solve each model
5.  Catch metrics
6.  INFO SWAP

    H2 MODEL                    ELEC MODEL
        |                           |
        |------ H2 Prices ------->>>|       (from duals, reset cost Param for Prodcution?  (missing multiplier here))
        |                           |
        |<<<--- ELEC Prices --------|       (from duals, reset cost Param)
        |                           |
        |------ ELEC Demand ----->>>|       (via an annual demand PARAMETER)
        |                           |
        |<<<--- H2 Demand ----------|       (via model input)

7.  re-solve each model
8.  Calculate prev_value - |H2.obj| + |ELEC.obj| < tolerance
9.  No?:  goto 5


"""

from logging import getLogger
from pathlib import Path
import tomllib
import pyomo.environ as pyo

from definitions import PROJECT_ROOT
from src.integrator.progress_plot import plot_it
from src.integrator.utilities import (
    convert_h2_price_records,
    regional_annual_prices,
    poll_h2_prices_from_elec,
    poll_hydrogen_price,
)
from src.models.electricity.scripts.runner import run_model
from src.models.hydrogen.model import actions

logger = getLogger(__name__)

HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
data_path = HYDROGEN_ROOT / 'inputs/single_region'  # has a bit of regions 7 data

# settings....  In "the future" these should be some params from a setup/config file
update_h2_price = True
update_elec_price = True
update_h2_demand = True

# vvvvvvvvvvvvvvvv   note this will require turning on the annual demand constraint in elec and adjusting the dual-to-price function
update_elec_demand = False

# basically force 20 solves.... helpful when OBJ functions are wayyy off in orders of magnitude to prevent early stops
force_20 = True


def run_iterative(config_path: Path):
    """run the iterative process...

    Parameters
    ----------
    config_path : Path
        path to config file with years & region data
    """
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

    # ------------------ 2.  starting demands for H2 should be included in selected region data for now...

    # ------------------ 3.  H2 model
    logger.info('Doing initial solve on H2')
    grid_data = actions.load_data(data_path, regions_of_interest=regions)
    grid = actions.build_grid(grid_data=grid_data)
    h2_model = actions.build_model(grid=grid, years=years)
    sol = actions.solve_it(h2_model)

    # ------------------ 4.  ELEC model
    logger.info('Doing initial solve on Elec')
    elec_model = run_model(years=years, regions=regions, solve=False)

    done = False
    tol = 0.05  # relative tolerance
    old_obj_sum = 0
    while not done:
        # ------------------ 4 1/2.  Solve the models
        simple_solve(h2_model)
        simple_solve(elec_model)

        # some logging of the iteration...
        h2_obj = pyo.value(h2_model.total_cost)
        e_obj = pyo.value(elec_model.totalCost)
        logger.info('Iter %d Elec Obj: %0.2f', iter, e_obj)
        logger.info('Iter %d H2 Obj: %0.2f', iter, h2_obj)
        h2_consumption_data = elec_model.poll_h2_demand()
        logger.debug('h2 consumption: %s', h2_consumption_data)
        logger.debug(
            'Actual h2 prices used in last iteration:\n %s',
            poll_h2_prices_from_elec(model=elec_model, tech=5, regions=(7,)),
        )

        # ------------------ 5.  Catch Metrics...
        # catch metrics from H2 Model
        elec_demand = h2_model.poll_electric_demand()

        if update_elec_demand:
            tot_e_demand_from_h2_model = sum(elec_demand.values())
            # demand is presented in *next* iteration. so + 1 for alignment
            elec_demand_records.append((iter + 1, tot_e_demand_from_h2_model))
        else:
            tot_e_demand_from_h2_model = 0

        if update_h2_price:
            new_h2_prices = poll_hydrogen_price(h2_model)
            avg_hyd_price = sum(t[1] for t in new_h2_prices) / len(new_h2_prices)
            h2_price_records.append((iter + 1, avg_hyd_price))
        else:
            new_h2_prices = None

        h2_obj_records.append((iter, h2_obj))

        # catch metrics from Elec
        if update_h2_demand:
            h2_demand = elec_model.poll_h2_demand()
            tot_h2_demand = sum(elec_model.poll_h2_demand().values())
            h2_demand_records.append((iter + 1, tot_h2_demand))
        else:
            h2_demand = None

        if update_elec_price:
            rap = regional_annual_prices(elec_model)
            grand_avg = sum(rap.values()) / len(rap)
            elec_price_records.append((iter + 1, grand_avg))
        else:
            rap = None

        elec_obj_records.append((iter, e_obj))

        # ------------------ 6a.  Info swap: Prices
        # H2 prices
        if new_h2_prices:
            elec_model.update_h2_prices(h2_prices=convert_h2_price_records(new_h2_prices))
        # Elec prices
        if rap:
            h2_model.update_exchange_params(new_electricity_price=rap)

        # ------------------ 6b.  Info swap: Cross-demands

        # Elec demand
        # TODO:  Temporarily disabling the passing of demand from H2 --> ELEC
        #        and the annual constraint in ELEC is turned off to avoid
        #        contaminating the duals for price.
        # elec_model.update_elec_demand(elec_demand=elec_demand)

        # H2 demand
        if h2_demand:
            h2_model.update_exchange_params(new_demand=h2_demand)

        # ------------------ 7.  Check termination criteria

        # TODO:  probably should split the relative change to look at EACH of the
        # suboordinate OBJ's to handle case where they are wildly different in order
        # of magnitude.
        net_obj = abs(h2_obj) + abs(e_obj)
        if iter == 0:
            old_obj_sum = net_obj
            done = False
        elif abs((net_obj - old_obj_sum) / old_obj_sum) < tol and not force_20:
            done = True
        else:
            old_obj_sum = net_obj
        print(f'{iter}:  Current net objective: {net_obj}')
        logger.info('Comleted iteration %d with net obj: %0.2f', iter, net_obj)

        if iter > 20:
            done = True
            logger.warning('Terminating iterative solve based on iteration count > 20!')

        iter += 1

    plot_it(
        h2_price_records=h2_price_records,
        elec_price_records=elec_price_records,
        h2_obj_records=h2_obj_records,
        elec_obj_records=elec_obj_records,
        h2_demand_records=h2_demand_records,
        elec_demand_records=elec_demand_records,
    )


opt = pyo.SolverFactory('appsi_highs')


# TODO:  This might be a good use case for a persistent solver (1-each) for both the elec & hyd...  hmm
def simple_solve(m: pyo.ConcreteModel):
    """a simple solve routine"""

    # Note:  this is a prime candidate to split into 2 persistent solvers!!
    # TODO:  experiment with pyomo's persistent solver interface, one for each ELEC, H2
    res = opt.solve(m)
    if pyo.check_optimal_termination(res):
        return
    raise RuntimeError('failed solve in iterator')
