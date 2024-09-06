"""
A simple 2-step test of load updating.

We will:
1.  Make an simple ELEC model and solve it
2.  Make a Residential model using the load index
3.  call the update function in the residential model to calculate new loads
4.  pass those to the ELEC model
5.  Run it again and look for a change in OBJ (higher or lower)

"""

import pytest
from definitions import PROJECT_ROOT
from pathlib import Path
from src.integrator import utilities, config_setup
from src.integrator.unified_elec_hyd_res import simple_solve
from src.integrator.utilities import EI
from src.models.electricity.scripts.runner import run_model
from src.models.residential.residential_block import ResidentialBlock

import pyomo.environ as pyo

from src.models.residential.scripts.residential import residentialModule


def test_load_updating():
    """A simple 2-step process to make sure we have a means to update the load in the elec
    from prices generated in res from load in elec .... hahah.
    """
    years = [2030, 2031]
    regions = [
        2,
    ]
    # get settings
    config_path = Path(PROJECT_ROOT, 'src/integrator', 'run_config.toml')
    settings = config_setup.Config_settings(
        config_path, test=True, years_ow=years, regions_ow=regions
    )
    # just load the model...
    elec_model = run_model(settings, solve=False)

    # basically a pass-through
    meta = pyo.ConcreteModel()
    meta.elec_price = pyo.Param(elec_model.LoadSet, initialize=0, default=0, mutable=True)

    # solve to get first prices
    simple_solve(elec_model)
    old_obj = pyo.value(elec_model.totalCost)

    prices = utilities.get_elec_price(elec_model)
    prices = prices.set_index(['r', 'y', 'hr'])['price_wt'].to_dict()
    prices = [(EI(*k), prices[k]) for k, v in prices.items()]

    price_lut = utilities.convert_elec_price_to_lut(prices=prices)
    for idx, price in price_lut.items():
        assert price > 0, f'found a bad apple {idx}'
    meta.elec_price.store_values(price_lut)

    # now we can make a residential model from data in elec...
    res_model = residentialModule()
    blk = res_model.make_block(meta.elec_price, meta.elec_price.index_set())

    # find average prices for test
    avg_baseprice = sum(blk.updated_load.AvgBasePrice) / len(blk.updated_load.AvgBasePrice)
    avg_newprice = sum(blk.updated_load.newPrice) / len(blk.updated_load.newPrice)

    # make sure new prices are on the same order of magnitude as base prices
    # TODO: make this a weighted annual average?
    assert blk.updated_load.AvgBasePrice.min() >= 1.0, 'check min base electricity prices'
    assert blk.updated_load.AvgBasePrice.max() <= 500000.0, 'check max base electricity prices'
    assert blk.updated_load.newPrice.min() >= 1.0, 'check min new electricity prices'
    assert blk.updated_load.newPrice.max() <= 500000.0, 'check max new electricity prices'
    assert (
        avg_baseprice / 2 < avg_newprice and avg_baseprice * 2 > avg_newprice
    ), 'base price data should be on same order of magnitude'

    # now we have a single constraint in the block, properly constraining the Load var
    meta.blk = blk

    # we can simple_solve meta to make the var take on the new values...
    meta.obj = pyo.Objective(expr=0)
    simple_solve(meta)
    # meta.elec_price.pprint()

    elec_model.Load.store_values(meta.blk.Load.extract_values())
    elec_model.Load.pprint()
    simple_solve(elec_model)
    new_obj = pyo.value(elec_model.totalCost)
    assert new_obj < 0.9 * old_obj, 'new objective value should decrease with this data'
