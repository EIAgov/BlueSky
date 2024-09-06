from logging import getLogger

# from src.models.electricity.scripts.electricity_model import PowerModel
from src.models.electricity.scripts.runner import run_model
from definitions import PROJECT_ROOT
from pathlib import Path
from src.integrator import utilities, config_setup
import src.models.electricity.scripts.preprocessor as prep
import pandas as pd

logger = getLogger(__name__)


def test_years_set():
    """test to ensure the years set is injested properly"""
    years = [2030, 2031, 2042]
    regions = [7, 8]

    config_path = Path(PROJECT_ROOT, 'src/integrator', 'run_config.toml')
    settings = config_setup.Config_settings(
        config_path, test=True, years_ow=years, regions_ow=regions
    )

    elec_model = run_model(settings, solve=False)

    # the xor of the sets should be empty...
    assert len(elec_model.y ^ set(years)) == 0, 'some diff in expected sets'


def test_hours_set():
    """test to ensure the hours set is injested properly"""
    years = [2030]
    regions = [7]

    def get_tot_load(toml_name, years, regions):
        """sum total load using hours and dayweights"""
        # first temporal set, 4 days 1 hour per day
        config_path1 = Path(PROJECT_ROOT, 'unit_tests', 'electric', toml_name)
        settings1 = config_setup.Config_settings(
            config_path1, test=True, years_ow=years, regions_ow=regions
        )
        all_frames1, setin1 = prep.preprocessor(prep.Sets(settings1))
        tot_load1 = pd.merge(
            pd.merge(
                all_frames1['Load'].reset_index(), all_frames1['Map_hr_d'].reset_index(), on='hr'
            ),
            all_frames1['Idaytq'],
            on='day',
        )
        tot_load1.loc[:, 'tot_load'] = tot_load1['Load'] * tot_load1['Idaytq']
        return sum(tot_load1.tot_load)

    # total load for 4 days, 1 hour per day
    tot_load_d4h1 = get_tot_load('run_config_test_d4h1.toml', years, regions)
    # total load for 8 days, 12 hours per day
    tot_load_d8h12 = get_tot_load('run_config_test_d8h12.toml', years, regions)

    # check that sum of load matches regardless of hours per day
    assert tot_load_d4h1 == tot_load_d8h12, 'some diff in hours sets'
