"""EIA930 Data Download and Table Generation

Summary
-------
This script constructs the EIA930 table definitions for SQL and downloads the EIA930 data, cleaning and uploading
the data to a newly generated database file.

The first portion of the script creates the table definitions for SQLAlchemy and are used to construct an empty 
database file. There are a set of functions defined outside of main() that only need snakemake inputs to initialize.

In main(), we construct the new database, download the raw EIA930 data, and then clean/impute data and upload these
to the database
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from time import time
import datetime
import os
import scripts.support_functions as support_functions
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

#####
### Read in snakemake inputs
#####

# sm_years = [2018, 2019, 2020, 2021, 2022]
# sm_dbloc = "N:/NextGen Developers/Projects/demand_profiles/"
# sm_deletedb = True
sm_dbloc = snakemake.params["db_loc"]
sm_years = snakemake.params["years_sm"]
sm_deletedb = snakemake.params["deletedb"]

#####
### SQLAlchemy setup for constructing SQLite dataset
#####

# Create base class
Base = declarative_base()

# ORM class definitions -- Balancing Authorities
class EIA930Balance(Base):
    __tablename__ = 'eia930_balance_raw'
    id = Column(String, primary_key=True)
    balancing_authority = Column(String)
    utc_time_at_end_of_hour = Column(DateTime)
    demand = Column(Integer)
    hour = Column(Integer)
    date = Column(String)
    local_time = Column(DateTime)
    # Add other columns as needed

# ORM class definitions -- Balancing Authority Subregions
class EIA930Subregion(Base):
    __tablename__ = 'eia930_subregion_raw'
    id = Column(String, primary_key=True)
    balancing_authority = Column(String)
    sub_region = Column(String)
    demand = Column(Integer)
    utc_time_at_end_of_hour = Column(DateTime)
    hour = Column(Integer)
    date = Column(String)
    local_time = Column(DateTime)
    # Add other columns as needed

#####
### Initialized functions (don't need to be in main() script)
#####

def create_database(engine):
    """create_database
    
    Creates a database using the Base class with the table definitions defined at top of script

    Parameters
    ----------
    engine : _type_
        SQLAlchemy engine object connected to a db location
    """
    Base.metadata.create_all(engine)

def convert_to_datetime(df, column_name):
    """convert_to_datetime
    
    Creates a date-time column from a column in a dataframe

    Parameters
    ----------
    df : dataframe
        A dataframe with desired column to change
    column_name : string
        Name of column to manipulate

    Returns
    -------
    df : dataframe
        Same dataframe as inputs, but with column converted to datetime
    """
    df[column_name] = pd.to_datetime(df[column_name])
    return df

def check_data_exists(session, model, id_list, batch_size=500):
    """check_data_exists

    Check if data with specific id's exist in table, in batches to avoid SQL limits

    Parameters
    ----------
    session : SQLAlchemy Session
        A dataframe with desired column to change
    model : DeclarativeMeta
        Table class for database
    id_list : list
        List of IDs to check in DB

    Returns
    -------
    existing_ids_set : set
        Set of ids already in database
    """
    existing_ids_set = set()
    for i in range(0, len(id_list), batch_size):
        batch = id_list[i:i + batch_size]
        existing_ids = session.query(model.id).filter(model.id.in_(batch)).all()
        existing_ids_set.update(id[0] for id in existing_ids)
    return existing_ids_set

def check_db_exists(i_dbloc = sm_dbloc, i_deletedb = sm_deletedb):
    """check_db_exists
    Checks whether the database exists; depending on switch, may delete existing database

    Parameters
    ----------
    i_dbloc : _type_, optional
        _description_, by default sm_dbloc
    i_deletedb : _type_, optional
        _description_, by default sm_deletedb

    Returns
    -------
    l_exist : boolean
        Indicator for whether the database exists after running the function
    """
    l_exist = os.path.isfile(f"{i_dbloc}EIA930_database.db")
    if l_exist:
        if i_deletedb:
            try:
                os.remove(f"{i_dbloc}EIA930_database.db")
                l_exist = False
            except Exception as e:
                print(f"Unable to delete db file; check if connection open elsewhere:{e}")
        else:
            print("eia_db already exists. Opting to continue without deleting file.")
    else:
        print("eia_db.db doesn't exist. Create without deleting")
    return l_exist

def EIA930_download(years, session, regionality,eia_class):
    """EIA930_download
    Download EIA data from url; clean and upload to database

    Parameters
    ----------
    years : list
        List of years to download data for
    session : SQLAlchemy Session
        A dataframe with desired column to change
    regionality : string
        Regionality for download (e.g. sub-region or balancing authorities)
    eia_class : DeclarativeMeta
        Table class for database
    """
    
    desired_columns = {
        'Balancing Authority': 'balancing_authority',
        'Sub-Region': 'sub_region',
        'UTC Time at End of Hour': 'utc_time_at_end_of_hour',
        'Demand (MW)': 'demand',
        'Hour Number': 'hour',
        'Data Date': 'date',
        'Local Time at End of Hour': 'local_time'
    }
    
    if regionality == 'Balance':
        desired_columns.pop('Sub-Region')

    url_reg = regionality.upper().replace('_', '')
    for year in years:
        urls = [
            f'https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_{url_reg}_{year}_Jul_Dec.csv',
            f'https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_{url_reg}_{year}_Jan_Jun.csv'
        ]

        for url in urls:
            try:
                df = pd.read_csv(url, usecols=desired_columns.keys(), encoding='utf-8', low_memory=False)
                df = convert_to_datetime(df, 'UTC Time at End of Hour')
                df = convert_to_datetime(df, 'Local Time at End of Hour')
                
                #renaming columns and creating id col
                df.rename(columns=desired_columns, inplace=True)
                col_reg = list(filter(lambda x: regionality[:3].lower() in x, list(df.columns)))[0]
                df['id'] = df[col_reg] + '_' + df['utc_time_at_end_of_hour'].astype(str)

                #remove commas and nans in demand data
                df['demand'] = df['demand'].replace(',', '', regex=True)
                df['demand'] = pd.to_numeric(df['demand'], errors='coerce').fillna(0).astype(int)
                
                # #inspection
                # print("data preview: ", df.head())

                # Check and remove existing data
                existing_ids = check_data_exists(session, eia_class, df['id'].tolist())
                df = df[~df['id'].isin(existing_ids)]

                # Perform bulk insert
                if not df.empty:
                    session.bulk_insert_mappings(eia_class, df.to_dict(orient='records'))
                    session.commit()
                else:
                    print(f"No new data to insert for {year} from {url}")

            except Exception as e:
                print(f"Error downloading or processing data for year {year} from {url}: {e}")
                session.rollback()
                raise

def generate_QA_graphs(df,regionality):
    """generate_QA_graphs
    
    generates monthly subplots (4x3) for each region, 
    with imputed demand on the y-axis scaled from 0-1 and hours on the x-axis.
    Writes them to a pdf, each region to a page, with low resolution for ease of viewing.

        Parameters
    ----------
    df : dataframe
        A dataframe to generate QA graphs
    regionality : string
        Regionality for download (e.g. sub-region or balancing authorities)
    """
    #graph
    filename = 'outputs/'+regionality+'_demand_by_month_hour.pdf'
    try:
        pdf = PdfPages(filename)

        for region in df[regionality].unique():
            
            dfr = df[df[regionality]==region].copy()

            # Initialise the subplot function using number of rows and columns 
            figure, axis = plt.subplots(3, 4) 
            figure.suptitle(region)
            figure.tight_layout()
            figure.set_rasterized(True)
            
            x_axis = 'hour'
            y_axis = 'imputed_demand'
            
            reg_y_max = dfr[y_axis].max()
            reg_x_min = dfr[x_axis].min()
            reg_x_max = dfr[x_axis].max()
            
            for m in range(1,13):
                #print(m)
                
                dfrm = dfr[dfr['month']==m].copy()
                dfrm['y_axis'] = dfrm[y_axis] / reg_y_max
                
                #set subplot location
                if m <= 4:
                    y = m - 1
                    x = 0
                elif m <= 8:
                    y = m - 5
                    x = 1
                else:
                    y = m - 9
                    x = 2

                #generate subplot
                axis[x, y].scatter(dfrm[x_axis], dfrm['y_axis'], s=2, alpha=0.2) 
                axis[x, y].set_title('month ' + str(m),fontsize=8) 
                axis[x, y].set_ylim([0, 1])
                axis[x, y].set_xlim([reg_x_min, reg_x_max])
                axis[x, y].set_xticks(np.arange(0, 25, 6)) 

            # Combine all the subplots and display 
            #plt.show() 
            #figure.savefig('outputs/plots/'+key+'.png')

            pdf.savefig(figure,dpi=72)
            plt.close()
    finally:
        pdf.close()

def demand_imputation(df,regionality):
    """ 
    Performs the following imputation logic for regional data:
    
    If a full month of data is missing, keep as empty, otherwise:
    1.) change poorly reported numbers
        a.) sets to nan hours with very low and very high demand
        b.) sets to nan hours with very large absolute changes in demand
        c.) overwrites demand based on a lower and/or upper demand threshold
    2.) fill in missing values
        a.) interpolates demand for days with only a few missing hours
        b.) uses demand from the day before and/or after
        c.) interpolates again for days with some more missing hours
        d.) uses median values for each region/month/hour

    Parameters
    ----------
    df : dataframe
        eia930subregion dataframe 

    Returns
    -------
    dataframe
        eia930subregion dataframe with imputed demand 
    """

    # clean up column data
    df['demand'] = df['demand'].apply(pd.to_numeric, errors='coerce')
    df = df[df['hour']<=24].copy()
    df['year'] = pd.DatetimeIndex(df['date']).year
    df['month'] = pd.DatetimeIndex(df['date']).month

    # remove regions with no data for all years
    empty_reg = df[[regionality,'demand']].groupby(by=[regionality],as_index=False).sum()
    empty_reg = empty_reg[empty_reg['demand']==0].drop(columns=['demand'])
    empty_reg['Missing_Region_Flag'] = 1
    df = pd.merge(df,empty_reg,on=[regionality],how='left')
    df = df[df['Missing_Region_Flag'].isna()].drop(columns=['Missing_Region_Flag'])
    #print(empty_reg)

    # flag regions/months with an entire month of missing data
    empty_mon = df[[regionality,'month','year','demand']].groupby(by=[regionality,'month','year'],as_index=False).sum()
    empty_mon = empty_mon[empty_mon['demand']==0].drop(columns=['demand'])
    empty_mon['Missing_Month_Flag'] = 1
    df = pd.merge(df,empty_mon,on=[regionality,'month','year'],how='left')
    #print(empty_mon)
    
    # create imputed demand column
    df['imputed_demand'] = df['demand']
    
    # set to nan hours with very low demands
    df.loc[df['imputed_demand'] <= 0, 'Lower_Error_Flag'] = 1
    df.loc[df['imputed_demand'] <= 0, 'imputed_demand'] = np.nan

    # set to nan hours with very high demands
    high_limt = df.groupby(by=[regionality,'month','hour'])['imputed_demand'].agg(['median']).reset_index()
    high_limt['Upper_Error'] = high_limt['median'] * 3
    high_limt = high_limt[[regionality,'month','hour','Upper_Error']]
    df = pd.merge(df,high_limt, on=[regionality,'month','hour'], how='left')
    df.loc[df['imputed_demand'] > df['Upper_Error'], 'Upper_Error_Flag'] = 1
    df.loc[df['imputed_demand'] > df['Upper_Error'], 'imputed_demand'] = np.nan

    # calculate the change in demand from one hour to the next by region
    df = df.reset_index(drop=True)
    for _, group in df.groupby(regionality):
        group_index = group.index
        df.loc[group_index, 'demand_increment'] = abs(group['imputed_demand'] - group['imputed_demand'].shift(-1))

    # calculate threshold for very large changes in incremental demand
    increment = df.groupby(by=[regionality])['demand_increment'].agg(['count','median','mean','std']).reset_index()
    increment['increment_threshold'] = increment['median'] + 4 *  increment['std']
    #increment.to_csv('outputs/increment_'+regionality+'.csv',index=False)
    df = pd.merge(df,increment.drop(columns=['count','median','mean','std']),how='left',on=[regionality])

    # identify and set to nan values with very large changes in incremental demand 
    df.loc[df['demand_increment'] > df['increment_threshold'], 'Increment_Flag'] = 1
    df['demand_increment'] = df['demand_increment'].shift(1)
    df.loc[df['demand_increment'] > df['increment_threshold'], 'Increment_Flag'] += 1
    df.loc[df['Increment_Flag'] == 2, 'imputed_demand'] = np.nan
    df.loc[df['Increment_Flag'] == 1, 'Increment_Flag'] = np.nan
    df.loc[df['Increment_Flag'] == 2, 'Increment_Flag'] = 1

    # calculate high and low demand hour thresholds by region, month, and hour
    thresholds = df.groupby(by=[regionality,'month','hour'])['imputed_demand'].agg(['count','median','mean','std']).reset_index()
    thresholds['Upper_Threshold'] = thresholds['median'] + 4 * thresholds['std']
    thresholds['Lower_Threshold'] = thresholds['median'] - 4 * thresholds['std']
    thresholds.loc[thresholds['Lower_Threshold']<0, 'Lower_Threshold'] = 0
    #thresholds.to_csv('outputs/thresholds_'+regionality+'.csv',index=False)
    thresholds = thresholds[[regionality,'month','hour','median','Upper_Threshold','Lower_Threshold']]
    df = pd.merge(df,thresholds, on=[regionality,'month','hour'], how='left')
    
    # replace high and low demand numbers with threshold values
    df.loc[df['imputed_demand'] < df['Lower_Threshold'], 'Lower_Threshold_Flag'] = 1
    df.loc[df['imputed_demand'] > df['Upper_Threshold'], 'Upper_Threshold_Flag'] = 1
    df.loc[df['imputed_demand'] < df['Lower_Threshold'], 'imputed_demand'] = df['Lower_Threshold']
    df.loc[df['imputed_demand'] > df['Upper_Threshold'], 'imputed_demand'] = df['Upper_Threshold']
    #df = df.drop(columns=['month'])
    
    # interpolate nan values for days with only a few missing hours
    df.loc[df['imputed_demand'].isna(), 'daily_nan_sum'] = 1
    interpo_set = df[[regionality,'date','daily_nan_sum']].groupby(by=[regionality,'date'],as_index=False).sum()
    df = df.drop(columns=['daily_nan_sum'])
    df = pd.merge(df,interpo_set,how='left',on=[regionality,'date'])
    interpo_set = df[df['daily_nan_sum']<=4].copy()
    interpo_set.loc[interpo_set['imputed_demand'].isna(), 'Interpolate_Flag'] = 1
    interpo_set['imputed_demand'] = interpo_set['imputed_demand'].interpolate()
    noninterp_set = df[df['daily_nan_sum']>4].copy()
    df = pd.concat([interpo_set,noninterp_set])
    df.sort_values(by=[regionality, 'local_time'], inplace=True)

    # Group by BA and calculate hours values for the day before and/or after 
    for _, group in df.groupby(regionality):
        group_index = group.index
        df.loc[group_index, 'shift_demand_d'] = (group['imputed_demand'].shift(24) + group['imputed_demand'].shift(-24)) / 2
        df.loc[group_index, 'shift_demand_db'] = group['imputed_demand'].shift(24)
        df.loc[group_index, 'shift_demand_da'] = group['imputed_demand'].shift(-24)

    # fill in missing values with hours from the day before and/or after 
    df.loc[((df['imputed_demand'].isna()) & (~df['shift_demand_d'].isna())), 'Shift_Day_Flag'] = 1
    df.loc[((df['imputed_demand'].isna()) & (~df['shift_demand_d'].isna())), 'imputed_demand'] = df['shift_demand_d']
    df.loc[((df['imputed_demand'].isna()) & (~df['shift_demand_db'].isna())), 'Shift_Day_Flag'] = 1
    df.loc[((df['imputed_demand'].isna()) & (~df['shift_demand_db'].isna())), 'imputed_demand'] = df['shift_demand_db']
    df.loc[((df['imputed_demand'].isna()) & (~df['shift_demand_da'].isna())), 'Shift_Day_Flag'] = 1
    df.loc[((df['imputed_demand'].isna()) & (~df['shift_demand_da'].isna())), 'imputed_demand'] = df['shift_demand_da']

    # interpolate again!
    df.loc[df['imputed_demand'].isna(), 'daily_nan_sum_2'] = 1
    interpo_set = df[[regionality,'date','daily_nan_sum_2']].groupby(by=[regionality,'date'],as_index=False).sum()
    df = df.drop(columns=['daily_nan_sum_2'])
    df = pd.merge(df,interpo_set,how='left',on=[regionality,'date'])
    interpo_set = df[df['daily_nan_sum_2']<=8].copy()
    interpo_set.loc[interpo_set['imputed_demand'].isna(), 'Interpolate_Flag'] = 1
    interpo_set['imputed_demand'] = interpo_set['imputed_demand'].interpolate()
    noninterp_set = df[df['daily_nan_sum_2']>8].copy()
    df = pd.concat([interpo_set,noninterp_set])
    df.sort_values(by=[regionality, 'local_time'], inplace=True)

    # Fill remaining NaNs with month/hour mean
    df.loc[df['imputed_demand'].isna(), 'Median_Flag'] = 1
    df.loc[df['imputed_demand'].isna(), 'imputed_demand'] = df['median']
    
    #set back to zero region/months where entire month was missing
    df.loc[df['Missing_Month_Flag']==1, 'imputed_demand'] = 0
    df.loc[df['Missing_Month_Flag']==1, 'Median_Flag'] = np.nan
    df['imputed_demand'] = df['imputed_demand'].astype(int)
    
    # Flags summary
    flag_cols = [regionality,'Missing_Month_Flag','Lower_Error_Flag','Upper_Error_Flag','Increment_Flag',
                 'Lower_Threshold_Flag','Upper_Threshold_Flag','Interpolate_Flag','Shift_Day_Flag','Median_Flag']
    flag = df[flag_cols].groupby(by=[regionality],as_index=False).sum()
    #flag.to_csv('outputs/flag_'+regionality+'.csv',index=False)
    
    # export data from a few difficult regions to spot check results
    check = ['OVEC','BANC','SEC','PSEI','Jica','RECO','VEA','CYGA']
    #df[df[regionality].isin(check)].to_csv('outputs/sample_'+regionality+'.csv',index=False)

    #generate_QA_graphs(df,regionality)

    # remove extra columns develop for QA
    final_table_columns = ['id','balancing_authority','sub_region','utc_time_at_end_of_hour','demand',
                           'imputed_demand','hour','date','local_time']
    df = df.drop(columns=[col for col in df if col not in final_table_columns])    

    return df

def create_clean_data(regionality,eia_class):
    """create_clean_data 
    Connects to the EIA930 database using ORM reads in dataframe, 
    runs data imputation function, writes dataframe with imputed data 

    Parameters
    ----------
    regionality : string
        Regionality for download (e.g. sub-region or balancing authorities)
    eia_class : DeclarativeMeta
        Table class for database
    """

    # database connection
    engine = create_engine(f'sqlite:///{sm_dbloc}EIA930_database.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    df_in = pd.read_sql((session.query(eia_class)).statement, engine)
    df_in.sort_values(by=[regionality, 'local_time'], inplace=True)

    df_imp = demand_imputation(df_in,regionality)

    if regionality == 'balancing_authority':
        sql_reg = 'balance'
    else:
        sql_reg = 'subregion'
    
    try:
        df_imp.to_sql(f'eia930_{sql_reg}_clean', con=engine, if_exists='replace', index=False)
        session.commit()
        print('Finished data imputation')
    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()
        pass

def main():
    ### Check whether db exists; delete if necessary or prompt w/ existence 
    db_exist = check_db_exists()

    ### Set-up SQLAlchemy engine
    engine = create_engine(f'sqlite:///{sm_dbloc}EIA930_database.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    if not db_exist:
        create_database(engine)

    ### Check if create directories
    if not os.path.exists("outputs/download_logs/eia930"):
        os.mkdir("outputs/download_logs/eia930")

    log_file = support_functions.log_output("outputs/download_logs/eia930/")
    try:
        t0 = time()

        ### Filter to make sure years available in raw data
        ba_years = [x for x in sm_years if x > 2017]
        subregion_years = [x for x in sm_years if x > 2018]

        ### Run download functions
        EIA930_download(ba_years, session, 'Balance',EIA930Balance)
        EIA930_download(subregion_years, session,'Subregion',EIA930Subregion)

        t1 = time()
        print("Time taken:", str(datetime.timedelta(seconds=round(t1 - t0))))

        session.close()

    finally:
        log_file.close()
        pass

    ### Data Imputation section (combined previous scripts)

        ### Check if create directories
    if not os.path.exists("outputs/download_logs/eia930/ba"):
        os.mkdir("outputs/download_logs/eia930/ba")

    log_file = support_functions.log_output("outputs/download_logs/eia930/ba/")
    try:
        t0 = time()

        #### Run imputation function to create cleaned data
        create_clean_data('balancing_authority',EIA930Balance)
        t1 = time()
        print("Time taken:", str(datetime.timedelta(seconds=round(t1 - t0))))
    finally:
        log_file.close()
        pass

    if not os.path.exists("outputs/download_logs/eia930/subreg"):
        os.mkdir("outputs/download_logs/eia930/subreg")

    log_file = support_functions.log_output("outputs/download_logs/eia930/subreg/")
    try:
        t0 = time()

        ### Run imputation function to create cleaned data
        create_clean_data('sub_region',EIA930Subregion)
        t1 = time()
        print("Time taken:", str(datetime.timedelta(seconds=round(t1 - t0))))
    finally:
        log_file.close()
        pass

if __name__ == "__main__":
    main()
