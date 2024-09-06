# this will likely be refactored later, but it is a first cut at integrating

from logging import getLogger
from pathlib import Path
import tomllib
from pyomo.environ import value
from matplotlib import pyplot as plt

from definitions import OUTPUT_ROOT
from src.integrator import config_setup
from src.integrator import utilities
from src.models.electricity.scripts.electricity_model import PowerModel
from src.models.electricity.scripts.runner import run_model
from src.models.hydrogen.model import actions

logger = getLogger(__name__)


def run_elec_solo(config_path: Path | None = None):
    # engage the Electricity Model...
    logger.info('Running Elec model')
    if config_path:
        settings = config_setup.Config_settings(config_path)
    instance = run_model(settings)
    print(f'Objective value: {value(instance.totalCost)}')

    # write out prices and plot them
    elec_price = utilities.get_elec_price(instance)
    price_records = utilities.get_annual_wt_avg(elec_price)
    elec_price.to_csv(instance.dir / 'prices' / 'elec_price.csv')
    plot_price_distro(instance, list(elec_price.price_wt))


def run_h2_solo(data_path: Path, config_path: Path | None = None):
    if config_path:
        settings = config_setup.Config_settings(config_path)
        years = settings.years
        regions = settings.regions
    else:
        years = None
        regions = None

    grid_data = actions.load_data(data_path, regions_of_interest=regions)
    grid = actions.build_grid(grid_data=grid_data)
    model = actions.build_model(grid=grid, years=years)
    model.pprint()
    sol = actions.solve_it(model)

    model.display()


def plot_price_distro(instance: PowerModel, price_records: list[float]):
    """cheap/quick analyisis and plot of the price records"""
    # convert $/GWh to $/MWh
    plt.hist(list(t / 1000 for t in price_records), bins=100, label='Price')
    plt.xlabel('Electricity price ($/MWh)')
    plt.ylabel('Number of representative hours')
    plt.savefig(Path(OUTPUT_ROOT, 'histogram.png'), format='png')
    # plt.show()
