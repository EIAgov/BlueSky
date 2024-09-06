"""NOAA-ISD weather data merge to EIA930 electricity operating data and creation of BA-level demand/weather data series

Summary
-------
This script constructs a dataset of Balancing Authority (BA) level electricity demand with weather-related predictors at hourly timesteps

The script relies on previously constructed crosswalks that assign counties to BAs; the script loads these crosswalks to identify which county weather data to load.
Once this data is loaded, the data is collapsed to a BA-level weather series using weighted averages of county variables, with the weights determined by county population.
EIA-930 data is loaded to memory for the BA and merged to this weather data. The resulting dataset is saved as a csv.

Snakemake
---------

l_dbloc
    Snakemake-originated string pointing to database file locations

l_years
    Snakemake-originated list of years to use to construct final dataset
"""

import pandas as pd
import numpy as np
import os
import re
import concurrent.futures
from time import time
import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.automap import automap_base

#####
### Read Snakemake inputs
#####
l_dbloc = snakemake.params["db_loc"]
l_years = snakemake.params["years_sm"]

# l_dbloc = "N:/NextGen Developers/Projects/demand_profiles/"
# l_years = [2018, 2019, 2020, 2021, 2022]
l_var = ["tmp_air_celsius_10", "tmp_dew_celsius_10", "wind_dir_degrees", "wind_spd_m_per_sec_10"]

def ba_basr_list():
    """ba_basr_list
    Load crosswalk between BAs and Counties to obtain list of all BAs and BASRs
    
    Returns
    -------
    l_ba_basr : list
        List of BAs and BASRs
    """
    ### Load Crosswalks and Merge Balancing AUthorites
    df_walk = pd.read_csv(os.path.join("outputs", "crosswalks", "EIA_BA-BASR-County.csv"))
    l_ba_basr = df_walk["BA_BASR_Code"].drop_duplicates().tolist()
    return l_ba_basr

### Prepare connect to raw noaa data
def main():

    #####
    ### Step 1: Setting up EIA930 and NOAA tables (currently assuming existence)
    #####
    db_930_Base = automap_base()
    db_930_engine = create_engine(f"sqlite:///{l_dbloc}EIA930_Database.db")
    db_930_metadata = MetaData()
    db_930_metadata.reflect(bind=db_930_engine)
    db_930_Base.prepare(autoload_with=db_930_engine)
    db_930_sessionmaker = sessionmaker(bind = db_930_engine)

    db_noaa_Base = automap_base()
    db_noaa_engine = create_engine(f'sqlite:///{l_dbloc}noaa_db.db')
    db_noaa_metadata = MetaData()
    db_noaa_metadata.reflect(bind = db_noaa_engine)
    db_noaa_Base.prepare(autoload_with=db_noaa_engine)
    db_noaa_sessionmaker = sessionmaker(bind = db_noaa_engine)

    #####
    ### Step 2: Load lists of unique ba/basr to run through merging functions; define and run
    #####

    l_ba_basr = ba_basr_list()

    def f_loadmerge_ba(i_ba_basr,
                       l_var = l_var, 
                       l_dbloc = l_dbloc,
                       md_noaa = db_noaa_metadata, 
                       md_930 = db_930_metadata,
                       b_noaa = db_noaa_Base,
                       b_930 = db_930_Base,
                       eg_noaa =  db_noaa_engine,
                       eg_930 = db_930_engine,
                       s_noaa=db_noaa_sessionmaker, 
                       s_930=db_930_sessionmaker):
        """f_loadmerge_ba
        Loads NOAA data at county scale, creates weighted average of weather outcomes at BA/BASR scale, and merges
        data to EIA930 electricity operating data

        Parameters
        ----------
        i_ba_basr : string
            BA and/or BASR code
        l_var : list, optional
            List of variables from NOAA to load, by default l_var
        l_dbloc : string, optional
            Location of database file, by default l_dbloc
        md_noaa : SQLAlchemy Metadata Object, optional
            NOAA db metadata object, by default db_noaa_metadata
        md_930 : SQLAlchemy Metadata Object, optional
            EIA930 db metadata object, by default db_930_metadata
        b_noaa : SQLAlchemy Base Class, optional
            Base class for NOAA db, by default db_noaa_Base
        b_930 : SQLAlchemy Base Class, optional
            Base class for EIA930 db, by default db_930_Base
        eg_noaa : SQLAlchemy Engine Object, optional
            Engine object for NOAA db, by default db_noaa_engine
        eg_930 SQLAlchemy Engine Object, optional
            Engine object for EIA930 db, by default db_930_engine
        s_noaa : SQLAlchemy Sessionmaker Object, optional
            Sessionmaker object for NOAA db, by default db_noaa_sessionmaker
        s_930 : SQLAlchemy Sessionmaker Object, optional
            Sessionmaker object for EIA930 db, by default db_930_sessionmaker

        Returns
        -------
        message : string
            String indicating success or failure of merge
        """
        try:
            ### Pull BA and BASR from code
            str_ba = i_ba_basr[0:i_ba_basr.find("-")]
            str_basr = i_ba_basr[(i_ba_basr.find("-")+1):len(i_ba_basr)]

            ### If BASR is NA, indicate that the BA/BASR is a BA, else BASR
            if str_basr == "NA":
                str_ba_basr_ind = "BA"
                l_ba_basr_cw = [str_basr]
            else:
                str_ba_basr_ind = "BASR"
                l_ba_basr_cw = pd.read_csv(os.path.join("outputs", "crosswalks", "EIA_BASR-Details.csv"))
                l_ba_basr_cw = l_ba_basr_cw[l_ba_basr_cw.BASR_Code == str_basr]
                l_ba_basr_cw = l_ba_basr_cw.BASR_Original.tolist()
            
            ### Create sessions for querying tables within function scope
            session_noaa = s_noaa()
            session_930 = s_930()

            ### Capture models from automapped base for noaa db
            ba_county = b_noaa.classes.ba_counties
            county_noaa = b_noaa.classes.counties_noaa
            county = b_noaa.classes.counties

            #####
            ### Filter counties needed for ba by year; load counties from session
            #####
            df_fips_fil = session_noaa.query(ba_county).filter(ba_county.BA_BASR_Code == i_ba_basr).all()
            df_fips_fil = [[t for t in s.__dict__.items()] for s in df_fips_fil]
            df_fips_fil = [{k: v for k,v in t} for t in df_fips_fil]
            df_fips_fil = pd.DataFrame(df_fips_fil).drop(["_sa_instance_state"], axis = 1)

            l_fips_fil = df_fips_fil["FIPS_cnty"].drop_duplicates().to_list()
            df_county = session_noaa.query(county).filter(county.FIPS_cnty.in_(l_fips_fil)).all()
            df_county = [[t for t in s.__dict__.items()] for s in df_county]
            df_county = [{k: v for k,v in t} for t in df_county]
            df_county = pd.DataFrame(df_county).drop(["_sa_instance_state"], axis = 1)

            ### TEMPORARY: Load csvs of each county needed for weather data; sql pulls taking too long
            l_fips_join = "|".join(l_fips_fil)
            l_files_year = [x for x in os.listdir(os.path.join("raw_data", "FIPS-NOAA")) if re.search(f"({l_fips_join})", x) is not None]
            df_weather = pd.concat([pd.read_csv(os.path.join("raw_data", "FIPS-NOAA", x)) for x in l_files_year])
            df_weather["FIPS_cnty"] = [str(x).rjust(5, "0") for x in df_weather["FIPS_cnty"]]
            df_weather_pop = df_weather.merge(df_county[["population", "year", "FIPS_cnty"]],
                                how = "left",
                                on = ["FIPS_cnty", "year"]).reset_index(drop = True)

            # ### Load Weather Data for Relevant Counties/years
            # def load_county(i_fips_cnty,
            #     l_dbloc = l_dbloc,
            #     df_county = df_county):
                
            #     ### Create Sessionmaker within function (to serialize)
            #     engine = create_engine(f"sqlite:///{l_dbloc}noaa_db.db")
            #     Session = sessionmaker(bind=engine)
            #     session_func = Session()

            #     df_weather = session_func.query(county_noaa).filter(county_noaa.FIPS_cnty == i_fips_cnty).all()
            #     df_weather = [[t for t in s.__dict__.items()] for s in df_weather]
            #     df_weather = [{k: v for k,v in t} for t in df_weather]
            #     df_weather = pd.DataFrame(df_weather).drop(["_sa_instance_state"], axis = 1)
            #     df_weather_pop = df_weather.merge(df_county[["population", "year", "FIPS_cnty"]],
            #                                     how = "left",
            #                                     on = ["FIPS_cnty", "year"]).reset_index(drop = True)
            #     return df_weather_pop

            # with concurrent.futures.ThreadPoolExecutor() as executor:
            #     results = [x for x in executor.map(load_county, l_fips_fil)]  
            # df_weather = pd.concat(results)
                
            ### Create weights based on population per year
            df_weather_pop = df_weather_pop.merge(right = df_weather_pop.groupby(by=["year", "month", "day", "hour"])["population"].sum().reset_index(),
                                                how = "left",
                                                on = ["year", "month", "day", "hour"],
                                                suffixes=["", "_sum"])
            df_weather_pop["weight"] = np.round(df_weather_pop["population"]/df_weather_pop["population_sum"],3)

            ### Generate Weighted Variable for timesteps in data
            for i_var in l_var:
                try:
                    df_weather_pop[f"{i_var}_"] = round(df_weather_pop["weight"]*df_weather_pop[i_var], 3)
                    df_weather_pop = df_weather_pop.merge(df_weather_pop.groupby(["year", "month", "day", "hour"])[f"{i_var}_"].sum().reset_index(),
                                                        how = "left",
                                                        on = ["year", "month", "day", "hour"],
                                                        suffixes=["", "weighted"])
                except Exception as e:
                    print(f"Error collapsing county observations for {i_ba_basr} for variable {i_var}: {e}")
                    df_weather_pop[f"{i_var}_weighted"] = None

            l_keepvar = [f"{x}_weighted" for x in l_var] + ["year", "month", "day", "hour"]
            df_weather_pop = df_weather_pop[l_keepvar]
            df_weather_pop.drop_duplicates(inplace = True)
            df_weather_pop.set_index(["year", "month", "day", "hour"], inplace=True)
                      
            ### Load EIA 930 Data and Merge
            if str_ba_basr_ind == "BA":
                s_tablename = "eia930_balance_clean"
                table = Table(s_tablename, md_930, autoload_with=eg_930)
                query = select(table.c).where(table.c.balancing_authority.in_([str_ba]))
            else:
                s_tablename = "eia930_subregion_clean"
                table = Table(s_tablename, md_930, autoload_with=eg_930)
                query = select(table.c).where(table.c.sub_region.in_(l_ba_basr_cw))

            ### Read eia930 data from cleaned tables based on BA-BASR Code value
            with eg_930.connect() as connection:
                result = connection.execute(query)
                df_eia930 = pd.read_sql(query, connection)

            ### Redeclare time steps and set index
            df_eia930["utc_time"] = pd.to_datetime(df_eia930['utc_time_at_end_of_hour'])
            df_eia930['year'] = df_eia930['utc_time'].dt.year
            df_eia930['month'] = df_eia930['utc_time'].dt.month
            df_eia930['day'] = df_eia930['utc_time'].dt.day
            df_eia930['hour'] = df_eia930['utc_time'].dt.hour
            df_eia930.set_index(["year", "month", "day", "hour"], inplace=True)

            if str_ba_basr_ind == "BA":
                df_eia930['sub_region'] = "NA"

            ### If BASR, aggregate to ensure basr codes with multiple original basr's are collapsed into single file
            if len(l_ba_basr_cw) > 1 and str_ba_basr_ind == "BASR":
                df_eia930_sum = df_eia930.groupby(["year", "month", "day", "hour"]).agg({"imputed_demand": ['sum']})
                df_eia930_sum.columns = ["imputed_demand"]
                df_eia930_sum["balancing_authority"] = str_ba
                df_eia930_sum["sub_region"] = str_basr
                df_eia930 = df_eia930[["utc_time"]]
                df_eia930 = df_eia930.merge(df_eia930_sum, left_index = True, right_index = True).drop_duplicates()
            
            ### Merge weighted variables from weather data to eia930 data
            l_keepvar = [f"{x}_weighted" for x in l_var]
            l_keepvar = ["balancing_authority", "sub_region", "utc_time", 
                        "imputed_demand"] + l_keepvar
                
            df_eia930_merged = df_eia930.merge(df_weather_pop, left_index = True, right_index = True).drop_duplicates()
            df_eia930_merged = df_eia930_merged[l_keepvar].reset_index(drop = False)

            ### Write to csv at db location directory TEMP
            df_eia930_merged.to_csv(os.path.join(f"{l_dbloc}BA-NOAA/BA-NOAA_{i_ba_basr}_Merged.csv"))

            ### Return message; print
            message = f"County collapse for {i_ba_basr} completed. Written temporarily to csv."
            print(message)
            return message
        except Exception as e:
            message = f"County collapse for {i_ba_basr} failed. Check for errors: {e}"
            print(message)
            return message
    results = [x for x in map(f_loadmerge_ba, l_ba_basr)]

    #####
    ### Create csv file that indicate runs for temporary snakemake purposes
    #####
    df_run_summary = pd.DataFrame({"BA_BASR_Code":l_ba_basr,
                                   "RunMessage": results})
    df_run_summary.to_csv(os.path.join(f"{l_dbloc}BA-NOAA/BA-NOAA_SnakemakeTrack_{l_years[0]}-{l_years[len(l_years)-1]}.csv"))

if __name__ == "__main__":
    main()
            


