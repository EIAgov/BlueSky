"""This file contains Config_settings class. It establishes the main settings used when running
the model. It takes these settings from the run_config.toml file. It contains universal configurations
(e.g., configs that cut across modules and/or solve options) and module specific configs."""

###################################################################################################
# Setup

# Import packages
from logging import getLogger
import pandas as pd
import numpy as np
import tomllib
from pathlib import Path

# Import scripts
from definitions import PROJECT_ROOT
from definitions import OUTPUT_ROOT
from src.integrator.utilities import create_temporal_mapping

# Establish logger
logger = getLogger(__name__)


###################################################################################################
# Configuration Class


class Config_settings:
    """Generates the model settings that are used to solve. Settings include:
    - Iterative Solve Config Settings
    - Spatial Config Settings
    - Temporal Config Settings
    - Electricity Config Settings
    - Other
    """

    def __init__(self, config_path, test=False, years_ow=[], regions_ow=[]):
        with open(config_path, 'rb') as src:
            config = tomllib.load(src)
        logger.info(f'Retrieved config data: {config}')

        ############################################################################################
        # Universal Configs

        # Iterative Solve Configs
        self.tol = config['tol']
        self.force_10 = config['force_10']
        self.max_iter = config['max_iter']

        # Spatial Configs
        if not test or len(regions_ow) == 0:
            self.regions = list(pd.read_csv(config['regions']).dropna()['region'])
        else:
            self.regions = regions_ow
        logger.info(f'Regions: {self.regions}')

        # Temporal Configs
        self.sw_temporal = config['sw_temporal']
        self.cw_temporal = create_temporal_mapping(self.sw_temporal)

        if not test:
            self.cw_temporal.to_csv(OUTPUT_ROOT / 'cw_temporal.csv', index=False)

        # Temporal Configs - Years
        self.sw_agg_years = config['sw_agg_years']
        year_frame = pd.read_csv(config['years'])
        if not test or len(years_ow) == 0:
            self.years = list(year_frame.dropna()['year'])
        else:
            self.years = years_ow
        logger.info(f'Years: {self.years}')

        if self.sw_agg_years and len(self.years) > 1:
            self.start_year = year_frame['year'][0]
            all_years_list = list(range(self.start_year, self.years[-1] + 1))
        else:
            self.start_year = self.years[0]
            all_years_list = self.years

        solve_array = np.array(self.years)
        mapped_list = [solve_array[solve_array >= year].min() for year in all_years_list]
        self.year_map = pd.DataFrame({'y': all_years_list, 'Map_y': mapped_list})
        self.year_weights = (
            self.year_map.groupby(['Map_y'])
            .agg('count')
            .reset_index()
            .rename(columns={'Map_y': 'y', 'y': 'year_weights'})
        )

        ############################################################################################
        # Electricity Configs
        self.sw_trade = config['sw_trade']
        self.sw_expansion = config['sw_expansion']
        self.sw_rm = config['sw_rm']
        self.sw_ramp = config['sw_ramp']
        self.sw_reserves = config['sw_reserves']
        self.sw_learning = config['sw_learning']

        # throwing errors if certain combinations of switches
        if self.sw_expansion == 0:  # expansion off
            if self.sw_rm == 1:
                raise ValueError('Must turn RM switch off if no expansion')
            if self.sw_learning == 1:
                raise ValueError('Must turn learning switch off if no expansion')
