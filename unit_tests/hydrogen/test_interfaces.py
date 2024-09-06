"""sequence of tests to prove out the price-demand interface"""

import pyomo.environ as pyo
from logging import getLogger

import pytest

from definitions import PROJECT_ROOT
from src.integrator.utilities import HI, poll_hydrogen_price
from src.models.hydrogen.model import actions


logger = getLogger(__name__)


def test_price_drop():
    """use a drop in price in electricity to test that the price of H2 drops
    This is mostly to test out the price interfacing
    """
    logger.info('Starting test of price drop')

    # run the model
    HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
    data_path = HYDROGEN_ROOT / 'inputs/single_region'

    grid_data = actions.load_data(data_path)
    grid = actions.build_grid(grid_data=grid_data)
    model = actions.build_model(grid=grid)
    sol = actions.solve_it(model)
    old_obj = pyo.value(model.cost_expression)
    # let's try a 20% discount...
    new_prices = {HI(k[0], k[1]): v * 0.8 for k, v in model.electricity_price.items()}
    model.update_exchange_params(new_electricity_price=new_prices)

    # re-solve
    sol_2 = actions.solve_it(model)
    new_obj = pyo.value(model.cost_expression)
    assert new_obj < old_obj * 0.95


def test_poll_h2_price():
    """
    A test of ability to retrieve H2 prices from the H2 model
    """
    logger.info('Starting test of polling H2 price')

    # run the model
    HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
    data_path = HYDROGEN_ROOT / 'inputs/single_region'

    grid_data = actions.load_data(data_path)
    grid = actions.build_grid(grid_data=grid_data)
    model = actions.build_model(grid=grid)
    sol = actions.solve_it(model)

    # we should be able to retrieve new prices for 2 years and 1 region
    # (the dimensionality we started with)
    h2_prices = poll_hydrogen_price(model=model)
    assert len(h2_prices) == 2, 'should have 2 observations'

    assert (price > 0 for idx, price in h2_prices), 'prices should be positive in value'


def test_poll_elec_demand():
    """
    Test the retrieval of the electricity demand request from a solved H2 model
    """

    HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
    data_path = HYDROGEN_ROOT / 'inputs/single_region'

    grid_data = actions.load_data(data_path)
    grid = actions.build_grid(grid_data=grid_data)
    model = actions.build_model(grid=grid)
    sol = actions.solve_it(model)

    elec_demand = model.poll_electric_demand()

    # this model has 1 region and 2 years, so keyset should have 2 entries
    assert len(elec_demand) == 2, 'should have 2 entries for region 7'

    # a crude capture of the value
    # TODO:  This will change after changing efficiencies...
    assert sum(elec_demand.values()) == pytest.approx(
        11.13, rel=0.25
    ), 'tot demand is 100K * 2 years, so elec used should be ~11.0 with efficiency of 5.4e-5'
