"""This file creates the enduse profiles used to create estimates of future electric demand"""

# Import python packages
import pandas as pd
import sqlite3
import enduse_db as enduse_db
from pathlib import Path
import os

# Set directories
# TODO: import structure is to support running locally, will consider changing
PROJECT_ROOT = Path(__file__).parents[4]
os.chdir(PROJECT_ROOT)
input_path = Path(PROJECT_ROOT / 'src/models/residential/input/preprocessor_inputs')

# set to True if you want to run a test version to see if the code is working
test = False

# Set db_dir to directory where stock database will live
if test:
    db_dir = Path(input_path / 'stock_database_test.db')
else:
    db_dir = enduse_db.db_dir


##################################################################################################################
# Functions used to downscale the data


# Subsets the dataframe to only the columns needed for analysis
def subset_elec_columns(df, id_cols):
    """grabs only the enduse equipment names that consume electricity

    Parameters
    ----------
    df : dataframe
        sector tables of energy consumption by enduse equipment
    id_cols : list
        list of the columns we want to keep in addition to what we will append in this function

    Returns
    -------
    dataframe
        contains sector enduse equipment consumption for electricity
    """
    # print(df.columns)
    # Adds elecrticity data related columns to the ID columns needed for analysis
    keep_cols = id_cols.copy()
    for col in df.columns:
        if 'electricity' in col:
            keep_cols.append(col)
    # for col in keep_cols: print(col)
    df = df[keep_cols]
    return df


# Groups all building stock data together
def stocks_aggregation(stock_list, stock_type_col, db_dir, assignments_fn):
    """sum enduse equipment up to enduse categories kwh

    Parameters
    ----------
    stock_list : list
        list of building stocks
    stock_type_col : str
        column name 'in.comstock_building_type' or 'in.geometry_building_type_recs'
    db_dir : path
        location where the enduse database is saved
    assignments_fn : str
        file name 'comstock_assignments' or 'resstock_assignments'

    Returns
    -------
    dataframe
        df containing kwh by stock and enduse category
    """
    # Initialize an empty dataframe to store data
    df_all = None

    # Connection to the SQLite database
    with sqlite3.connect(db_dir) as conn:
        # Read in end-use assignments
        assign = pd.read_csv(Path(input_path / f'{assignments_fn}.csv'))

        # Loop through the building stock types
        for stock in stock_list:
            print(stock)

            # Read in the building stock data
            query = "SELECT * FROM '" + stock + "';"
            df = pd.read_sql_query(query, conn)

            # Keep only columns needed for analysis
            id_cols = ['in.state', stock_type_col, 'timestamp']
            df = subset_elec_columns(df, id_cols)

            # unpivot dataframe
            value_cols = list(set(df.columns) - set(id_cols))
            df = pd.melt(
                df,
                id_vars=id_cols,
                value_vars=value_cols,
                var_name='equipment_type',
                value_name='Electricity (kWh)',
            )
            df[stock_type_col] = df[stock_type_col].str.lower()

            # merge in assignments
            df = pd.merge(df, assign, how='left', on=[stock_type_col, 'equipment_type'])

            # If this is not the first building stock in the list, it adds the data to the previous set
            if df_all is not None:
                # Combines data
                df_all = pd.concat([df, df_all])

                # Groups building stock data together
                # Comment out this line of code below if you want to examine data by building stock
                df_all = (
                    df_all.groupby(by=['in.state', 'timestamp', 'enduse_cat'], as_index=False)
                    .sum()
                    .drop(columns=[stock_type_col, 'equipment_type'])
                )

            # If this is the first building stock in the list, it creates the set
            else:
                df_all = df
            # print(df.shape)

    df_all = df_all.reset_index(drop=True)
    print(df_all.shape)
    print()

    return df_all


# Groups data up to the 8760 hours local time
def hourly_aggregation(df):
    """sum data up to hourly local time kwh.
     - sums the kwh data up from 15 min intervals into hours
     - converts from EST for each state to local standard time for each state
     - adjusts time to account for daylight savings in all states except AZ


    Parameters
    ----------
    df : dataframe
        df from stock aggregations

    Returns
    -------
    dataframe
        df containing kwh by local time hourly
    """
    # Setting time interval to the start time rather than the end time
    df['timestamp_original'] = df['timestamp']
    df['timestamp'] = pd.to_datetime(df['timestamp']) - pd.Timedelta(hours=0, minutes=15, seconds=0)

    # Reading in time zone assignments by state
    tz = (
        pd.read_csv(Path(input_path / 'timezone_assignments.csv'))
        .drop(columns=['Other_TimeZone'])
        .rename(columns={'State': 'in.state'})
    )
    df = pd.merge(df, tz, on=['in.state'], how='inner')

    # Updating the hour based on time zone assignment
    def shift_timezone_hours(df, TZ, hr):
        df.loc[(df['Primary_TimeZone'] == TZ), 'timestamp'] = pd.to_datetime(
            df['timestamp']
        ) - pd.Timedelta(hours=hr, minutes=0, seconds=0)
        return df

    df = shift_timezone_hours(df, 'CST', 1)
    df = shift_timezone_hours(df, 'MST', 2)
    df = shift_timezone_hours(df, 'PST', 3)

    # Shifting the first hours of the year in some TZs to last hours of the year in 2018
    df['Date'] = pd.to_datetime(df['timestamp']).dt.date.astype(str)
    df['Month'] = pd.to_datetime(df['timestamp']).dt.month.astype(int)
    df['Hour'] = pd.to_datetime(df['timestamp']).dt.hour.astype(int)
    df.loc[(df['Date'] == '2017-12-31'), 'Date'] = '2018-12-31'
    # df.loc[(df['Date']=='2019-01-01'), 'Date'] = '2018-01-01'

    # Grouping data by hour
    df = df.drop(columns=['timestamp', 'timestamp_original', 'Primary_TimeZone'])
    df = df.groupby(by=['in.state', 'Date', 'Month', 'Hour'], as_index=False).sum()

    # Updating timezone assignment for daylight savings
    tz_update_months = [3, 4, 5, 6, 7, 8, 9, 10]
    df.loc[(df['in.state'] != 'AZ') & (df['Month'].isin(tz_update_months)), 'Hour'] = df['Hour'] + 1
    df.loc[(df['Hour'] == 24), 'Hour'] = 0

    return df


def national_aggregations(df):
    """sum up data to national hourly kwh

    Parameters
    ----------
    df : dataframe
        df from hourly aggregations

    Returns
    -------
    _type_
        df containing kwh for the nation
    """
    df = df.groupby(by=['Month', 'Date', 'Hour'], as_index=False).sum().drop(columns=['in.state'])
    df['in.state'] = 'national'

    # print(df.shape)
    return df


# Calculates in each time segment of each end-use and each region the percent of annual electricity
def calculate_percent_cols(df, regionality):
    """_summary_

    Parameters
    ----------
    df : dataframe
        df from hourly aggregations or national aggregations
    regionality : str
        name of the regional column

    Returns
    -------
    dataframe
        df containing percent of kwh demand for each hour for each enduse category
    """
    # identify the columns we plan to calculate percentages on
    df['Count'] = 1
    enduse_cols = list(set(df.columns) - set([regionality, 'Month', 'Date', 'Hour', 'Count']))
    # print(enduse_cols)
    # calculate total electricity in each end-use and region
    totals = (
        df.groupby(by=[regionality], as_index=False)
        .sum()
        .drop(columns=['Month', 'Date', 'Hour', 'Count'])
    )

    # for each column
    for col in enduse_cols:
        # print(col)
        totals = totals.rename(columns={col: col + '_total'})
        df = pd.merge(df, totals[[regionality, col + '_total']], on=[regionality], how='left')
        df[col] = df[col] / df[col + '_total'] / df['Count']
        df = df.drop(columns=[col + '_total'])
    df = df.drop(columns=['Count'])

    print(df.shape)
    return df


def run_sector_processes(sector_name, stock_list, type_col, db_dir, regionality):
    """runs all of the processes needed to process the sector data.
    Processes include stock, hourly, and regional aggregations,
    as well as converting from kwh demand to percent demand.

    Parameters
    ----------
    sector_name : str
        sector name 'comstock' or 'resstock'
    stock_list : list
        list of building stocks
    stock_type_col : str
        column name 'in.comstock_building_type' or 'in.geometry_building_type_recs'
    db_dir : path
        location where the enduse database is saved
    regionality : str
        name of the regional column

    Returns
    -------
    dataframe
        final hourly df for the given sector
    """
    print(f'Load data for {sector_name}')
    df = stocks_aggregation(stock_list, type_col, db_dir, f'{sector_name}_assignments')

    print(f'Generate hourly profiles for {sector_name}')
    df = df.pivot(
        index=[regionality, 'timestamp'], columns='enduse_cat', values='Electricity (kWh)'
    ).reset_index()

    df = hourly_aggregation(df)
    df = national_aggregations(df)
    df = calculate_percent_cols(df, regionality)
    # df.to_csv(Path( input_path / f'{com_sector_name}_hr.csv'),index=False)

    return df


##################################################################################################################
# Main Project Execution


def main(db_dir):
    """main execution for enduse_db. runs the sector processes for both
    the residential and commercial sector data

    Parameters
    ----------
    db_dir : path
        location where the enduse database is saved

    Returns
    -------
    dataframe
        enduse_shapes data containing national, hourly, enduse category percentage profiles
    """
    # Pull in raw data from db for project
    # Note: this block of code takes ~20 minutes to run

    # Define regional column
    regionality = 'in.state'

    # Commercial data setup
    com_sector_name = 'comstock'
    com_type_col = 'in.comstock_building_type'
    com_list = enduse_db.stock_list('com', com_type_col)
    com_df = run_sector_processes(com_sector_name, com_list, com_type_col, db_dir, regionality)

    print()

    # Residential data setup
    res_sector_name = 'resstock'
    res_type_col = 'in.geometry_building_type_recs'
    res_list = enduse_db.stock_list('res', res_type_col)
    res_df = run_sector_processes(res_sector_name, res_list, res_type_col, db_dir, regionality)

    # Merge data
    final = pd.merge(com_df, res_df, how='outer', on=[regionality, 'Date', 'Month', 'Hour'])
    final = final.drop(columns=['in.state'])
    final['everything_else'] = 1 / 8760
    print('Final')
    print(final.shape)
    # print(final.shape[0]/8760, 'hourly profiles per enduse')

    # long format
    final['hr'] = final.index + 1
    final = final.drop(columns=['Month', 'Date', 'Hour'])
    final = pd.melt(final, id_vars=['hr'], var_name='enduse_cat', value_name='share')

    return final


if __name__ == '__main__':
    # Specify the output directory where the raw data is stored, run create_db.py to build the stock database
    enduse_shapes = main(db_dir)
    if test is True:
        enduse_shapes.to_csv(Path(input_path / 'enduse_shapes_test.csv'), index=False)
    else:
        enduse_shapes.to_csv(Path(input_path / 'enduse_shapes.csv'), index=False)