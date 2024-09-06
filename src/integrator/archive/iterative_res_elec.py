"""
A quick iterative approach to res-elec iteration

NOTE:  this is an early effort at unified model - iterative solve
       The unified solver is the mature version of this and should

       This is currently maintained as an example
"""

from matplotlib import pyplot as plt
import pyomo.environ as pyo
from src.integrator import utilities
from src.integrator.jacobi_elec_hyd_solver import simple_solve
from src.integrator.utilities import EI
from src.models.electricity.scripts.runner import run_model
from src.models.residential.scripts.residential import residentialModule

# TODO:  this needs a fair bit of logging added
# TODO:  should make the plotter include aggregate load and some aggregate avg price value


def run_jacobi(years=[2030, 2031, 2040], regions=[2, 3, 7, 8]):
    # recordkeeping
    obj_values = []

    # just load the model... don't solve, we need to extract stuff before solve
    elec_model = run_model(years=years, regions=regions, solve=False)

    # currently we need a "meta" model -- basically a pass-through
    meta = pyo.ConcreteModel()
    meta.elec_price = pyo.Param(elec_model.LoadSet, initialize=0, default=0, mutable=True)

    # solve to get first prices
    simple_solve(elec_model)
    first_obj = pyo.value(elec_model.totalCost)
    obj_values.append(first_obj)

    prices = utilities.get_elec_price(elec_model)
    prices = prices.set_index(['r', 'y', 'hr'])['price_wt'].to_dict()
    prices = [(EI(*k), prices[k]) for k, v in prices.items()]
    price_lut = utilities.convert_elec_price_to_lut(prices=prices)

    # cannot have zero prices, so a quick interim check...
    for idx, price in price_lut.items():
        assert price > 0, f'found a bad apple {idx}'
    meta.elec_price.store_values(price_lut)

    for iter in range(19):
        # now we can make a residential model from data in elec...
        res_model = residentialModule()
        blk = res_model.make_block(meta.elec_price, meta.elec_price.index_set())

        # now we have a single constraint in the block, properly constraining the Load var
        # add this block to the meta model so that we can "solve it"
        # TODO:  this is going to cause warnings in pyomo by replacing a named component
        #        need to modify to not make a new residential block, just mod what we have
        meta.blk = blk

        # Neet to solve to enforce the constraint and set the variable...
        meta.obj = pyo.Objective(expr=0)  # nonsense
        simple_solve(meta)

        # now the meta.blk variable "Load" contains new load requests that can be inspected...
        # put them in the elec model parameter (update the mutable param)
        elec_model.Load.store_values(meta.blk.Load.extract_values())
        # elec_model.Load.pprint()

        simple_solve(elec_model)
        new_obj = pyo.value(elec_model.totalCost)
        obj_values.append(new_obj)

        # repeat the price gathering process
        prices = utilities.get_elec_price(elec_model)
        prices = prices.set_index(['r', 'y', 'hr'])['price_wt'].to_dict()
        prices = [(EI(*k), prices[k]) for k, v in prices.items()]
        price_lut = utilities.convert_elec_price_to_lut(prices=prices)

        # cannot have zero prices, so a quick interim check...
        for idx, price in price_lut.items():
            assert price > 0, f'found a bad apple {idx}'
        meta.elec_price.store_values(price_lut)

    print(obj_values)

    plt.plot(list(range(20)), obj_values, label='ELEC Objective')
    plt.grid(visible=True)
    plt.title('Iterative Solve Residential -- Electric')
    plt.xlabel('Iteration')
    plt.ylabel('Elec Model OBJ')
    plt.xticks(ticks=range(0, 21))
    plt.legend()
    plt.show()
