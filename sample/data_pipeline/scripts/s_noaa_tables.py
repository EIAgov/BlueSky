"""NOAA-ISD Data Download and Table Generation

Summary
-------
This script constructs the NOAA weather data and county-BA crosswalk table definitions for SQL and downloads the NOAA data for each county.

The first portion of the script creates the table definitions for SQLAlchemy and are used to construct an empty 
database file. There are a set of functions defined outside of main() that only need snakemake inputs to initialize.

In main(), we construct the new database, download the raw EIA930 data, and then clean/impute data and upload these
to the database
"""

import aiohttp
import asyncio
import pandas as pd
import numpy as np
import os
import concurrent.futures
#import datetime
#import time
import re
from functools import partial
from io import StringIO
#from collections import OrderedDict
from sqlalchemy import and_, delete
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Mapped, mapped_column
from typing import Optional, List
import ast

#####
### Read inputs from snakemake 
#####
l_dbloc = snakemake.params[0]
l_years = snakemake.params[1]
l_deletedb = snakemake.params[2]
l_delobs = snakemake.params[3]

l_dbloc_full = f"{l_dbloc}noaa_db.db"

# l_dbloc = "N:/NextGen Developers/Projects/demand_profiles/"
# l_years = [x for x in range(2018, 2023)]
# l_deletedb = True
# l_delobs = False

###############################################################################################
### SQL Alchemy Table Definitions
###############################################################################################

### Create base class and define baseline tables for db
Base = declarative_base()

association_table = Table(
    "association_table",
    Base.metadata,
    Column("cnty_isd_FIPS_cnty", ForeignKey("county_isds.FIPS_cnty"), primary_key=True),
    Column("ba_cnty_FIPS_cnty", ForeignKey("ba_counties.FIPS_cnty"), primary_key=True),
)

class isd_station(Base):
    __tablename__ = "isd_stations"

    station_id: Mapped[str] = mapped_column(primary_key=True)
    station_name: Mapped[str]
    date_start = Mapped[str]
    date_end = Mapped[str]
    date_dl = Mapped[str]
    USAF: Mapped[str]
    WBAN: Mapped[str]
    CTRY: Mapped[Optional[str]]
    ST: Mapped[Optional[str]]
    CALL: Mapped[Optional[str]]
    LAT: Mapped[Optional[str]]
    LON: Mapped[Optional[str]]
    ELEV: Mapped[Optional[str]]
    county: Mapped[Optional["county_isd"]] = relationship(back_populates="stations")

class county_isd(Base):
    __tablename__ = "county_isds"

    id: Mapped[int] = mapped_column(primary_key=True)
    FIPS_cnty: Mapped[str]
    Year: Mapped[int]
    station_id: Mapped[str] = mapped_column(ForeignKey("isd_stations.station_id"))
    distance_km: Mapped[int]
    stations: Mapped[List["isd_station"]] = relationship(back_populates="county")
    ba_basr: Mapped[List["ba_county"]] = relationship(
        secondary=association_table, back_populates="cnty_isd"
    )

class ba_county(Base):
    __tablename__ = "ba_counties"

    id: Mapped[int] = mapped_column(primary_key=True)
    FIPS_cnty: Mapped[str]
    Region_Name: Mapped[str]
    BA_Code: Mapped[str]
    Year: Mapped[int]
    BASR_Code: Mapped[Optional[str]]
    FIPS_st: Mapped[str]
    BA_BASR_Code: Mapped[str]
    cnty_isd: Mapped[List["county_isd"]] = relationship(
        secondary=association_table, back_populates="ba_basr"
)

class county_noaa(Base):
    __tablename__ = "counties_noaa"

    id: Mapped[int] = mapped_column(primary_key = True)
    year: Mapped[int]
    month: Mapped[int]
    day: Mapped[int]
    hour: Mapped[int]
    tmp_air_celsius_10: Mapped[Optional[int]]
    tmp_dew_celsius_10: Mapped[Optional[int]]
    wind_dir_degrees: Mapped[Optional[int]]
    wind_spd_m_per_sec_10: Mapped[Optional[int]]
    FIPS_cnty: Mapped[str]

class county(Base):
    __tablename__ = "counties"

    id: Mapped[int] = mapped_column(primary_key=True)
    FIPS_cnty: Mapped[str]
    population: Mapped[Optional[int]]
    year: Mapped[int]

####################################################################################################
### Function Definitions
####################################################################################################

def check_db_exists(i_dbloc = l_dbloc, i_deletedb = l_deletedb):
    """check_db_exists
    Checks whether the database exists; depending on switch, may delete existing database

    Parameters
    ----------
    i_dbloc : string, optional
        Location of database file, by default sm_dbloc
    i_deletedb : boolean, optional
        Indicator to delete database, by default sm_deletedb

    Returns
    -------
    l_exist : boolean
        Indicator for whether the database exists after running the function
    """
    l_exist = os.path.isfile(f"{i_dbloc}noaa_db.db")
    if l_exist:
        if i_deletedb:
            try:
                os.remove(f"{i_dbloc}noaa_db.db")
                l_exist = False
            except Exception as e:
                print(f"Unable to delete db file; check if connection open elsewhere: {e}")
        else:
            print("noaa_db already exists. Opting to continue without deleting file.")
    else:
        print("noaa_db.db doesn't exist. Create without deleting")
    return l_exist

def load_crosswalks():
    """load_crosswalks
    Load in dataframes and collect them in a dictionary.

    Dataframes included here are...
    1) NOAA_ISD Station Details
    2) Station to County Assignment
    3) County to BA/BASR Crosswalk
    4) County Details (population)

    Returns
    -------
    d_cw : dictionary
        A dictionary of data frames that should be loaded into the database
    """
    df_stations = pd.read_csv(os.path.join("outputs", "noaa", "NOAA_ISD_Stations.csv"))

    df_station_cnty = pd.read_csv(os.path.join("outputs", "crosswalks", "EIA_County-ISD.csv"))
    df_station_cnty["FIPS_cnty"] = [str(x).rjust(5, "0") for x in df_station_cnty["FIPS_cnty"]]

    df_ba_basr_cnty = pd.read_csv(os.path.join("outputs", "crosswalks", "EIA_BA-BASR-County.csv"))
    df_ba_basr_cnty["FIPS_cnty"] = [str(x).rjust(5, "0") for x in df_ba_basr_cnty["FIPS_cnty"]]
    df_ba_basr_cnty["FIPS_st"] = [str(x).rjust(2, "0") for x in df_ba_basr_cnty["FIPS_st"]]

    df_county = pd.read_csv(os.path.join("outputs", "census", "County_Population.csv"))
    df_county["FIPS_cnty"] = [str(x).rjust(5, "0") for x in df_county["FIPS_cnty"]]

    d_cw = {"df_isd_station":df_stations,
            "df_county_isd":df_station_cnty,
            "df_ba_county":df_ba_basr_cnty,
            "df_county":df_county}
    return d_cw

def upload_crosswalks(session, tablenames, d_tables, d_cw):
    """upload_crosswalks
    Takes dictionary of dataframes and uploads them to a db file using the SQLAlchemy model classes

    Function checks if table already has data, if it does it exist, the function deletes the data and
    commits new data to the db

    Parameters
    ----------
    session : SQLAlchemy Session
        Open db session to connect/query tables
    tablenames : list
        A list of table names that corresponds to the dictionary of data frames
    d_cw : dictionary
        A dictionary of data frames that should be loaded into the database
    """
    for tablename in tablenames:
        q_all = session.query(d_tables[tablename]).all()
        if len(q_all) > 0:
            session.query(d_tables[tablename]).delete()
            session.commit()
        
        df = d_cw[f"df_{tablename}"].to_dict(orient = "records")
        session.bulk_insert_mappings(d_tables[tablename], df)
        session.commit()

def check_year_exists(i_year, session, i_dbloc = l_dbloc, i_delobs = l_delobs):
    """check_year_exists
    Check if county-level observations exist in county-weather table; depending upon
    desired outcome, return either exists or doesn't exist. Option to delete observations and
    replace.

    Parameters
    ----------
    i_year : string
        Year of interest to check in database
    session : SQLAlchemy Session
        Open db session to connect/query tables
    i_dbloc : string, optional
        Location of database file, by default sm_dbloc
    i_deletedb : boolean, optional
        Indicator to delete database, by default sm_deletedb

    Returns
    -------
    exist : boolean
        Indicator for whether the database exists after running the function
    """
    year_check = [x[0] for x in session.query(county_noaa.year).distinct()]

    if i_year in year_check:
        exist = False
    else:
        if i_delobs:
            session.query(county_noaa).filter(and_(county_noaa.year == i_year)).delete()
            session.commit()
            exist = False
        else:
            exist = True
    return exist

def check_cnty_exists(i_fips_cnty, i_year, session, i_dbloc = l_dbloc, i_delobs = l_delobs):
    """check_cnty_exists



    Parameters
    ----------
    i_fips_cnty : string
        FIPS code for county (5 digit)
    i_year : string
        Year of interest to check in database
    session : SQLAlchemy Session
        Open db session to connect/query tables
    i_dbloc : string, optional
        Location of database file, by default sm_dbloc
    i_deletedb : boolean, optional
        Indicator to delete database, by default sm_deletedb

    Returns
    -------
    exist : boolean
        Indicator for whether the database exists after running the function
    """
    cnty_check = session.query(county_noaa).filter(and_(county_noaa.year == i_year, county_noaa.FIPS_cnty == i_fips_cnty)).first()

    if cnty_check is not None:
        if i_fips_cnty in cnty_check:
            exist = False
        else:
            if i_delobs:
                session.query(county_noaa).filter(and_(county_noaa.year == i_year)).delete()
                session.commit()
                exist = False
            else:
                exist = True
        return exist
    else:
        return False

def check_cnty_exists_csv(i_fips_cnty, i_year, i_dbloc = l_dbloc, i_delobs = l_delobs):
    """check_cnty_exists_csv
    Checks whether a year-county combination is saved as a csv in the temporary folder

    Parameters
    ----------
    i_fips_cnty : string
        FIPS code for county (5 digit)
    i_year : string
        Year of interest to check in database
    i_dbloc : string, optional
        Location of database file, by default sm_dbloc
    i_deletedb : boolean, optional
        Indicator to delete database, by default sm_deletedb

    Returns
    -------
    boolean
        Indicator for whether the database exists after running the function
    """
    ### Check if csv exists
    l_path = os.path.join("raw_data", "FIPS-NOAA", f"FIPS-NOAA_{i_fips_cnty}-{i_year}.csv")
    if os.path.exists(l_path):
        if i_delobs:
            os.remove(l_path)
            print(f"Due to switch, deleted {i_fips_cnty} for {i_year}")
            return False
        else:
            print(f"{i_fips_cnty} for {i_year} already exists; switch indicates keep.")
            return True
    else:
        print(f"{i_fips_cnty} for {i_year} doesn't exist. Creating new csv")
        return False

async def download_station_data(session, year, station_id):
    """download_station_data
    Concatenates url and attempts to try/download data from link. If unsuccessful, returns empty

    Parameters
    ----------
    session : ClientSession
        Open client to download from http link
    year : string
        Year of data
    station_id : string
        NOAA-ISD station ID

    Returns
    -------
    text, year, station_id
        Returns response to GET request, the input year, and the station id
    """
    url = f"https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{station_id}.csv"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                text = await response.text()
                return text, year, station_id
            else:
                print(f"Error: Unable to download data for station {station_id} in year {year}. HTTP status: {response.status}")
                return None, year, station_id
    except Exception as e:
        print(f"Error downloading data for station {station_id} in year {year}: {e}")
        return None, year, station_id

async def process_station_group(year, station_ids, delay=0.5):
    """process_station_group
    Creates an ansynchronous download session that downloads, for a given year, all station_ids in a list

    Parameters
    ----------
    year : string
        Year of data
    station_ids : list
        NOAA-ISD station ID list
    delay : float, optional
        Delay download requests, by default 0.5

    Returns
    -------
    Asyncio.Future
        Gathered responses from all download clients
    """
    async with aiohttp.ClientSession() as a_session:
        tasks = []
        for station_id in station_ids:
            await asyncio.sleep(delay)  # Rate limiting
            task = download_station_data(a_session, year, station_id)
            tasks.append(task)
        return await asyncio.gather(*tasks)

def read_station_data(t_raw):
    """read_station_data
    Function reads data from the GET request results downloaded from the NOAA website

    Parameters
    ----------
    t_raw : tuple
        Collection of outputs from download functions

    Returns
    -------
    dict
        A dictionary indexed by station id w/ values corresponding to the station level data
    """
    if t_raw[0] is None:
        return(None)
    else:
        df = pd.read_csv(StringIO(t_raw[0]), low_memory=False)
        df["year"] = t_raw[1]
        df["station_id"] = t_raw[2]
        return {t_raw[2]:df}

def create_county_series(i_fips_cnty, i_year, i_engine_loc = l_dbloc_full):
    """create_county_series: 
    Generates county-year level weather series based on varlist of interest
    identified from NOAA metadata. Uses open connection to noaa_db to find stations to download and
    to upload cleaned county series. Writes county-level weather data to csv for upload in later functions

    Parameters
    ----------
    i_fips_cnty : string
        FIPS code for county
    i_year : string
        Year of interest
    i_engine_loc : string, optional
        Location of database file, constructed with snakemake input

    Returns
    -------
    """
    print(f"Starting session for {i_fips_cnty} and {i_year}")
    ### Create Session for specific process
    engine = create_engine(f"sqlite:///{i_engine_loc}")
    Session = sessionmaker(bind=engine)
    session_func = Session()

    ### Query db for stations for county/year; pull IDs
    stations = session_func.query(county_isd).filter(and_(county_isd.FIPS_cnty == i_fips_cnty, county_isd.Year == i_year)).all()
    d_items = [[t for t in s.__dict__.items()] for s in stations]
    df_station_id = [{k: v for k,v in t} for t in d_items]
    df_station_id = pd.DataFrame(df_station_id)
    station_ids = df_station_id["station_id"]

    ### Check if county data exists; option to delete observations and overwrite
    data_exist = check_cnty_exists_csv(i_fips_cnty, i_year)
    if not data_exist:
        ### Download station data in loop
        try:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(process_station_group(i_year, station_ids))
                loop.close()
            except Exception as e:
                print(f"Error downloading stations via asyncio for {i_fips_cnty}: {e}")
            finally:
                loop.close()
        
            ### Cleaning each downloaded station dataset
            l_df_stations_raw = [x for x in map(read_station_data, results)]
            l_df_stations_raw = [x for x in l_df_stations_raw if x is not None]
            d_df_stations_raw = {k: v for d in l_df_stations_raw for k, v in d.items()}
            d_varlist = {"WND":["wind_dir_degrees", "wind_dir_qual", "wind_type", "wind_spd_m_per_sec_10", "wind_spd_qual"],
                        "TMP":["tmp_air_celsius_10", "tmp_air_qual"],
                        "DEW":["tmp_dew_celsius_10", "tmp_dew_qual"],
                        "AA1":["lprec_period_hrs", "lprec_depth_mm", "lprec_cond", "lprec_qual"],
                        "AL1":["snow_period_hrs", "snow_dim_cm", "snow_cond", "snow_qual"]}
            
            def clean_vars(i_varname, i_d_df = d_df_stations_raw, i_d_varlist = d_varlist):
                """For each variable, find in station data stored in dictionary and split concatenated
                column into corresponding variables that compose the main variable (e.g. wind). Need to include
                in d_varlist the column names composing the main variable.

                Parameters
                ----------
                i_varname : string
                    Main variable of interest (e.g. wind, temperature). Included in codebook
                i_d_df : dict
                    Dictionary that stores dataframes with raw station data. Defaults to d_df_stations_raw.
                i_d_varlist : list
                    List of variables 

                Returns
                -------
                dict_varsplit : dict
                    Dictionary of variables split from original raw columns from NOAA data
                """
                try:
                    if i_varname in i_d_varlist.keys():
                        dict_varsplit = {}
                        for key in i_d_df.keys():
                            df  = i_d_df[key]
                            try:
                                if i_varname in df.columns:
                                    var = [str(x).split(",") for x in df[i_varname]]
                                    var = [list(x) for x in zip(*var)]
                                    dict_df = {d_varlist[i_varname][i]: var[i] for i in range(len(var))}
                                    dict_varsplit[key] = dict_df
                                else:
                                    dict_varsplit[key] = ""
                            except Exception as e:
                                print(f"{key} is causing issues w/ collapsing {i_varname}: {e}")
                    else:
                        print(f"{i_varname} not assigned variables in varlist. Check d_varlist for splits")
                        dict_varsplit = {}
                    return dict_varsplit
                except Exception as e:
                    return print(f"{i_varname} doesn't work: {e}")
            
            d_clean_vars = [x for x in map(clean_vars, d_varlist.keys()) if x is not False]
            #d_clean_vars = [x for x in d_clean_vars if x != False]

            ### Create dataframes of station data with slected variables
            def clean_to_df_dict(i_station_id, l_dict = d_clean_vars, i_d_df_stations_raw = d_df_stations_raw):
                """clean_to_df_dict
                Creates a dataframe of station data (for each station id) from the processed raw data

                Parameters
                ----------
                i_station_id : string
                    Station ID
                l_dict : list, optional
                    List of dictionaries of variables split by delimiters in raw data (see clean_vars), by default d_clean_vars
                i_d_df_stations_raw : dict, optional
                    Dictionary of raw station data, by default d_df_stations_raw

                Returns
                -------
                df_full : dataframe
                    Dataframe of processed station data for station_id
                """
                ### Merge together into single data frame
                df = i_d_df_stations_raw[i_station_id]
                df_base = df[["station_id", "year", "DATE"]]
                l_df = [x[i_station_id] for x in l_dict]
                l_df = [pd.DataFrame.from_dict(x) for x in l_df if x != '']
                df_concat = pd.concat(l_df, axis = 1)
                df_full = pd.concat([df_base, df_concat], axis = 1)              
                return df_full
            
            l_df_full = [x for x in map(clean_to_df_dict, d_df_stations_raw.keys())]

            def clean_full_stations(l_df, i_df_station_id = df_station_id, i_d_varlist = d_varlist, year = i_year, fips_cnty = i_fips_cnty):
                """clean_full_stations
                Merges all dataframes from each station into a single dataframe and cleans the variables included in the downloads.
                Returns a single cleaned dataframe that can be collapsed into a county weather series

                Parameters
                ----------
                l_df : list
                    List of dataframes of station data for each station mapped to FIPS_cnty
                i_df_station_id : dataframe, optional
                    Dataframe describing station characteristics, by default df_station_id
                i_d_varlist : dict, optional
                    Dictionary describing variables included in dataframe, by default d_varlist
                year : string, optional
                    Year of the data, by default i_year
                fips_cnty : string, optional
                    FIPS code for county, by default i_fips_cnty

                Returns
                -------
                df_full : dataframe
                    Dataframe with all stations assigned to fips_cnty
                """
                ### Collapse into full data frame
                df_full = pd.concat(l_df, axis = 0)

                ### Clean Station Data
                df_full = df_full.merge(i_df_station_id[["station_id", "distance_km"]], on = ["station_id"], how = "left")
                df_full["invDist"] = round(1/df_full["distance_km"], 5)

                ### Time and date/set index
                l_time = ["year", "month", "day", "hour"]
                df_full['DATE'] = pd.to_datetime(df_full['DATE'])
                df_full['year'] = df_full['DATE'].dt.year
                df_full['month'] = df_full['DATE'].dt.month
                df_full['day'] = df_full['DATE'].dt.day
                df_full['hour'] = df_full['DATE'].dt.hour
                df_full.set_index(keys = l_time, inplace = True)

                ### For each variable, check if in columns, if so, cleaning steps
                l_qualfail = [2,3, 6, 7]

                ### Air Temperature
                try:
                    df_full["tmp_air_celsius_10"] = [int(x) for x in df_full["tmp_air_celsius_10"]]
                    df_full.loc[(df_full["tmp_air_celsius_10"] == 9999), "tmp_air_celsius_10"] = np.nan
                    df_full.loc[(df_full["tmp_air_qual"].isin(l_qualfail)), "tmp_air_celsius_10"] = np.nan
                except Exception as e:
                    print(f"Error cleaning variables in {fips_cnty} for tmp_air_celsius in year {year}: {e}")

                ### Dew point temperature
                try:
                    df_full["tmp_dew_celsius_10"] = [int(x) for x in df_full["tmp_dew_celsius_10"]]
                    df_full.loc[(df_full["tmp_dew_celsius_10"] == 9999), "tmp_dew_celsius_10"] = np.nan
                    df_full.loc[(df_full["tmp_dew_qual"].isin(l_qualfail)), "tmp_dew_celsius_10"] = np.nan
                except Exception as e:
                    print(f"Error cleaning variables in {fips_cnty} for tmp_dew_celsius in year {year}: {e}")

                ### Wind Speed
                try:
                    df_full["wind_spd_m_per_sec_10"] = [int(x) for x in df_full["wind_spd_m_per_sec_10"]]
                    df_full.loc[(df_full["wind_spd_m_per_sec_10"] == 9999), "wind_spd_m_per_sec_10"] = np.nan
                    df_full.loc[(df_full["wind_spd_qual"].isin(l_qualfail)), "wind_spd_m_per_sec_10"] = np.nan
                except Exception as e:
                    print(f"Error cleaning variables in {fips_cnty} for wind_spd_m_per_sec in year {year}: {e}")
                
                ### Wind Direction
                try:
                    df_full["wind_dir_degrees"] = [int(x) for x in df_full["wind_dir_degrees"]]
                    df_full.loc[(df_full["wind_dir_degrees"] == 999), "wind_dir_degrees"] = np.nan
                    df_full.loc[(df_full["wind_dir_qual"].isin(l_qualfail)), "wind_dir_degrees"] = np.nan
                except Exception as e:
                    print(f"Error cleaning variables in {fips_cnty} for wind_dir_degrees in year {year}: {e}")

                ### Liquid Precip (CLEAN LATER WHEN NEEDED)
                try:
                    df_full["lprec_period_hrs"] = [float(x) for x in df_full["lprec_period_hrs"]]
                    df_full["lprec_depth_mm"] = [float(x)/10 for x in df_full["lprec_depth_mm"]]
                except Exception as e:
                    print(f"Error cleaning variables in {fips_cnty} for lprec in year {year}: {e}")
                
                ### Snow Precip (CLEAN LATER WHEN NEEDED)
                try:
                    df_full["snow_period_hrs"] = [float(x) for x in df_full["snow_period_hrs"]]
                    df_full["snow_dim_cm"] = [float(x) for x in df_full["snow_dim_cm"]]
                except Exception as e:
                    print(f"Error cleaning variables in {fips_cnty} for snow in year {year}: {e}")
                
                return df_full
            
            df_station_full = clean_full_stations(l_df_full)

            ### Create county data from the full stations data frame
            l_time = ["year", "month", "day", "hour"]
            w_col = ["tmp_air_celsius_10", "tmp_dew_celsius_10", "wind_dir_degrees", "wind_spd_m_per_sec_10"]
            def countyCollapse(varname):
                """countyCollapse
                Collapse stations into county-level weather data by averaging within timesteps and weighting by distance to county centroid

                _extended_summary_

                Parameters
                ----------
                varname : string
                    Name of the variable averaged over stations

                Returns
                -------
                dataframe
                    Dataframe indexed by time that contains collapsed weather variable at county scale
                """
                ### Filter if data isn't missing
                df_collapse = df_station_full[~np.isnan(df_station_full[varname])]

                ### Sum total inverse distance by timestep
                df_sum = df_collapse.groupby(by = l_time)["invDist"].sum()
                df_sum.name = "invDist_sum"

                ### Join sum to collapsed dataframe to create weights
                df_collapse = df_collapse.join(df_sum, on = l_time)

                ### Divide distance by sum to create weight for specific timestep for station
                df_collapse["weight"] = df_collapse["invDist"]/df_collapse["invDist_sum"]
                df_collapse["var_contribution"] = df_collapse["weight"]*df_collapse[varname]

                ### Sum "contributions" to weighted sum. Replace missing values
                df_var = df_collapse.groupby(by = l_time)["var_contribution"].sum().round(0)
                df_var.loc[pd.isna(df_var)] = 9999
                df_var = df_var.astype(int)
                df_var.name = varname
                return pd.DataFrame(df_var)
            
            ### Concat variables together 
            l_out = pd.concat([x for x in map(countyCollapse, w_col)], axis = 1)
            l_out["FIPS_cnty"] = i_fips_cnty
            l_out.reset_index(drop = False, inplace=True)
            
            ### Write to csv
            l_out.to_csv(os.path.join("raw_data", "FIPS-NOAA", f"FIPS-NOAA_{i_fips_cnty}-{i_year}.csv"))
            return print(f"Download for {i_fips_cnty} in {i_year} completed. Written to csv.")
        except Exception as e:
            return print(f"Download for {i_fips_cnty} in {i_year} failed. Check session/url for issues: {e}")
    else:
        return print(f"Data for county {i_fips_cnty} in {i_year} already exists. Set exists to false if desired download/overwrite")

def upload_county_series(i_year, Session, l_dbloc = l_dbloc):
    """upload_county_series
    Uploads csv files written in create_county_series to database

    Parameters
    ----------
    i_year : string
        Year of data
    session : SQLAlchemy Session
        Open db session to connect/query tables
    l_dbloc : string, optional
        Location of database file, by default l_dbloc

    Returns
    -------
    """
    ### Create Session for specific process
    session_func = Session()

    ### Find all files saved for input year
    l_files_year = [x for x in os.listdir(os.path.join("raw_data", "FIPS-NOAA")) if re.search(f"-{i_year}", x) is not None]

    ### Append all files into single dataframe
    df_year = pd.concat([pd.read_csv(os.path.join("raw_data", "FIPS-NOAA", x)) for x in l_files_year])
    df_year["FIPS_cnty"] = [str(x).rjust(5, "0") for x in df_year["FIPS_cnty"]]

    ### Check if year uploaded
    data_exist = check_year_exists(i_year, session_func)

    ### Load each csv and impute
    def upload_csv(i_fips_cnty, i_year = i_year, session_func = session_func, df_year = df_year):
        """upload_csv
        Filters df_year for input county and uploads weather data to the db file at db_loc
        
        Parameters
        ----------
        i_fips_cnty : string
            FIPS code
        i_year : string, optional
            Year of data, by default i_year
        session_func : SQLAlchemy Session
            Open db session to connect/query tables
        df_year : dataframe, optional
            dataframe containing all counties in year, by default df_year

        Returns
        -------
        string, int
            FIPS code and indicator for successful upload
        """
        df_year_fil = df_year[df_year["FIPS_cnty"] == i_fips_cnty]            
        try:
            session_func.bulk_insert_mappings(county_noaa, df_year_fil.to_dict(orient = "records"))
            session_func.commit()
            print(f"Writing {i_fips_cnty} for {i_year} to db file successful")
            return (i_fips_cnty, 0)
        except Exception as e:
            print(f"Writing {i_fips_cnty} for {i_year} to db file failed; likely collision issue: {e}")
            return (i_fips_cnty, 1)
    results_cnty = [x for x in map(upload_csv, df_year.FIPS_cnty.drop_duplicates())]


### Prepare connect to raw noaa data
def main():

    #####
    ### Step 1: Setting up reference tables
    #####

    ### Check whether db exists; delete if necessary or prompt w/ existence 
    db_exist = check_db_exists()

    ### Create engine and session
    engine = create_engine(f'sqlite:///{l_dbloc}noaa_db.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    l_tablenames = ["isd_station", "county_isd", "ba_county", "county"]
    dict_tables = {"isd_station":isd_station,
                   "county_isd":county_isd,
                   "ba_county":ba_county,
                   "county":county}

    ### Create tables if db doesn't exist
    if not db_exist:
        Base.metadata.create_all(engine)
        dict_cw = load_crosswalks()
        upload_crosswalks(session, l_tablenames, dict_tables, dict_cw)

    #####
    ### Step 2: Create county series from downloaded station data
    #####
    if not os.path.exists(os.path.join("raw_data", "FIPS-NOAA")):
        os.mkdir(os.path.join("raw_data", "FIPS-NOAA"))
    
    ### Create input dataframe (e.g. county/year combinations)
    l_inp = [list(x) for x in zip(*session.query(county_isd.FIPS_cnty, county_isd.Year).all())]
    df_inp = pd.DataFrame({"FIPS_cnty":l_inp[0],
                           "Year":l_inp[1]}).drop_duplicates()

    ### Create county series
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [x for x in executor.map(create_county_series, df_inp["FIPS_cnty"], df_inp["Year"])]

    ### Upload all data
    upload_county_series_p = partial(upload_county_series, Session = Session)
    results_upload = [x for x in map(upload_county_series_p, l_years)]

if __name__ == "__main__":
    main()
      
