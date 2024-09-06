"""This file contains the options to re-create the input files. It creates:
 - Load.csv: electricity demand for all model years (used in residential and electricity)
 - BaseElecPrice.csv: electricity prices for initial model year (used in residential only)
Uncomment out the functions at the end of this file in the "if __name__ == '__main__'" statement
in order to generate new load or base electricity prices.
"""

from pathlib import Path
import pandas as pd
import os
from datetime import datetime

# Set directories
# TODO: import structure is to support running locally, will consider changing
PROJECT_ROOT = Path(__file__).parents[4]
os.chdir(PROJECT_ROOT)
data_root = Path(PROJECT_ROOT, 'src/models/residential/input')

# Import scripts
from definitions import OUTPUT_ROOT
from src.integrator.utilities import make_output_dir, setup_logger
from src.integrator.runner import run_elec_solo


def scale_load():
    """Reads in BaseLoad.csv (load for all regions/hours for first year)
    and LoadScalar.csv (a multiplier for all model years). Merges the
    data and multiplies the load by the scalar to generate new load
    estimates for all model years.

    Returns
    -------
    pandas.core.frame.DataFrame
        dataframe that contains load for all regions/years/hours
    """
    # combine first year baseload data with scalar data for all years
    baseload = pd.read_csv(data_root / 'BaseLoad.csv')
    scalar = pd.read_csv(data_root / 'LoadScalar.csv')
    df = pd.merge(scalar, baseload, how='cross')

    # scale load in each year by scalar
    df['Load'] = round(df['Load'] * df['scalar'], 3)
    df = df.drop(columns=['scalar'])

    # reorder columns
    df = df[['r', 'y', 'hr', 'Load']]

    return df


def base_price():
    """Runs the electricity model with base price configuration settings and then
    merges the electricity prices and temporal crosswalk data produced from the run
    to generate base year electricity prices.

    Returns
    -------
    pandas.core.frame.DataFrame
        dataframe that contains base year electricity prices for all regions/hours
    """
    # run electricity model with base price config settings
    baseprice_config_path = Path(data_root / 'baseprice_config.toml')
    run_elec_solo(config_path=baseprice_config_path)

    # grab electricity model output results
    cw_temporal = pd.read_csv(OUTPUT_ROOT / 'cw_temporal.csv')
    elec_price = pd.read_csv(OUTPUT_ROOT / 'electricity' / 'prices' / 'elec_price.csv')

    # keep only the electricity price data needed
    base_year = elec_price['y'].min()
    elec_price = elec_price[elec_price['y'] == base_year]
    elec_price = elec_price[['r', 'y', 'hr', 'price_wt']].rename(columns={'hr': 'Map_hr'})

    # crosswalk the electricity prices to all hours in the base year
    cw_temporal = cw_temporal[['hr', 'Map_hr']]
    elec_price = pd.merge(elec_price, cw_temporal, how='right', on=['Map_hr'])
    elec_price = elec_price.drop(columns=['Map_hr'])
    elec_price = elec_price[['r', 'y', 'hr', 'price_wt']]
    elec_price.sort_values(['r', 'y', 'hr'], inplace=True)

    return elec_price


if __name__ == '__main__':
    OUTPUT_ROOT = make_output_dir(OUTPUT_ROOT)
    logger = setup_logger(OUTPUT_ROOT)

    # Comment on/off each function as needed
    # scale_load().to_csv(data_root / 'Load.csv', index=False)
    # base_price().to_csv(data_root / 'BaseElecPrice.csv',index=False)
