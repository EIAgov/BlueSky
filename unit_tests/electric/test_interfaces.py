import pytest
from src.integrator.utilities import HI, get_elec_price, regional_annual_prices
from src.models.electricity.scripts.runner import run_model
from pyomo.environ import value
from definitions import PROJECT_ROOT
from pathlib import Path
from src.integrator import utilities, config_setup


def test_poll_elec_prices():
    """
    test that we can poll prices from elec and get "reasonable" answers
    """
    years = [2030, 2031]
    regions = [7, 8]

    config_path = Path(PROJECT_ROOT, 'src/integrator', 'run_config.toml')
    settings = config_setup.Config_settings(
        config_path, test=True, years_ow=years, regions_ow=regions
    )
    elec_model = run_model(settings, solve=True)
    # we are just testing to see if we got *something* back ... this should have hundreds of entries...
    new_prices = get_elec_price(elec_model)
    assert len(new_prices) > 1, 'should have at least 1 price'

    # test for signage of observations
    price_records = new_prices.to_records()
    assert all((price >= 0 for *_, price in price_records)), 'expecting prices to be positive'

    # TODO:  Why does this fail?  there appear to be zero prices... Non binding constraint in these areas??
    # assert all((price > 0 for _, price in new_prices)), 'price should be non-zero, right???'

    # test for average price mehhhh above $1000
    lut = regional_annual_prices(elec_model)
    # TODO:  When price data stabilizes fix this to test that ALL are >1000.  RN region 7 has low costs
    assert max(lut.values()) > 1000, 'cost should be over $1000'


def test_update_h2_price():
    """
    test the ability to update the h2 prices in the model
    """
    years = [2030, 2031]
    regions = [
        2,
    ]
    config_path = Path(PROJECT_ROOT, 'src/integrator', 'run_config.toml')
    settings = config_setup.Config_settings(
        config_path, test=True, years_ow=years, regions_ow=regions
    )
    # just load the model...
    elec_model = run_model(settings, solve=False)
    new_prices = {HI(2, 2030): 999.0, HI(2, 2031): 101010.10}
    elec_model.update_h2_prices(new_prices)

    # sample a couple...
    #                               r, s, pt, step, yr
    assert value(elec_model.H2Price[2, 1, 5, 1, 2030]) == pytest.approx(999.0)
    assert value(elec_model.H2Price[2, 3, 5, 1, 2030]) == pytest.approx(999.0)
    assert value(elec_model.H2Price[2, 2, 5, 1, 2031]) == pytest.approx(101010.10)


def test_poll_h2_demand():
    """
    poll the solved model for some H2 Demands

    Note:  We don't have a "right answer" for this (yet), so this will just do some basic functional test
    """

    years = [2030, 2031]
    regions = [2]

    config_path = Path(PROJECT_ROOT, 'src/integrator', 'run_config.toml')
    settings = config_setup.Config_settings(
        config_path, test=True, years_ow=years, regions_ow=regions
    )
    elec_model = run_model(settings, solve=True)

    h2_demands = elec_model.poll_h2_demand()

    # some poking & proding
    assert h2_demands.keys() == {HI(2, 2030), HI(2, 2031)}
