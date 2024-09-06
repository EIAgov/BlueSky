"""This file is the main preprocessor for the electricity model. It established the parameters
and sets that will be used in the model. It contains:
 - A class that contains all sets used in the model
 - A collection of support functions to read in and setup parameter data
 - The preprocessor function, which produces an instance of the Set class and a dict of params
 - A collection of support functions to write out the inputs to the output directory

"""

###################################################################################################
# Setup

# Import pacakges
from pathlib import Path
import pandas as pd
import numpy as np
import os

# Import scripts
from definitions import PROJECT_ROOT
from definitions import OUTPUT_ROOT
from src.integrator import config_setup

# switch to load data from csvs(0) or from db(1)
# note: this is a future feature, currently not available
db_switch = 0

if db_switch == 1:
    from sqlalchemy import create_engine, MetaData, Table, select
    from sqlalchemy.ext.automap import automap_base
    from sqlalchemy.orm import sessionmaker

# establish paths
data_root = Path(PROJECT_ROOT, 'src/models/electricity/input')


###################################################################################################
class Sets:
    """Generates an initial batch of sets that are used to solve electricity model. Sets include:
    - Scenario descriptor and model switches
    - Regional sets
    - Temporal sets
    - Technology type sets
    - Supply curve step sets
    - Other
    """

    def __init__(self, settings):
        # Switches
        self.sw_trade = settings.sw_trade
        self.sw_expansion = settings.sw_expansion
        self.sw_agg_years = settings.sw_agg_years
        self.sw_rm = settings.sw_rm
        self.sw_ramp = settings.sw_ramp
        self.sw_learning = settings.sw_learning
        self.sw_reserves = settings.sw_reserves

        self.restypes = [1, 2, 3]  # reserve types, 1=spinning, 2=regulation, 3=flex
        self.sw_ptbuilds = pd.read_csv(data_root / 'sw_ptbuilds.csv')
        self.sw_ptretires = pd.read_csv(data_root / 'sw_ptretires.csv')

        # Regional Sets
        self.r = settings.regions

        # Temporal Sets
        self.sw_temporal = settings.sw_temporal
        self.cw_temporal = settings.cw_temporal

        # Temporal Sets - Years
        self.years = settings.years
        self.y = settings.years
        self.start_year = settings.start_year
        self.year_map = settings.year_map
        self.year_weights = settings.year_weights

        # Temporal Sets - Seasons and Days
        self.s = range(1, self.cw_temporal['Map_s'].max() + 1)
        self.num_days = self.cw_temporal['Map_day'].max()
        self.day = range(1, self.num_days + 1)

        # Temporal Sets - Hours
        # number of time periods in a day
        self.num_hr_day = int(self.cw_temporal['Map_hr'].max() / self.cw_temporal['Map_day'].max())
        self.h = range(1, self.num_hr_day + 1)
        # Number of time periods the model solves for: days x number of periods per day
        self.num_hr = self.num_hr_day * self.num_days
        self.hr = range(1, self.num_days * len(self.h) + 1)
        # First time period of the day and all time periods that are not the first hour
        self.hr1 = range(1, self.num_days * len(self.h) + 1, len(self.h))
        self.hr23 = list(set(self.hr) - set(self.hr1))

        # Technology Sets
        def load_and_assign_subsets(df, col):
            # set attributes for the master list
            master = list(df.columns)[0]
            df = df.set_index(df[master])

            # return subset of list based on col assignments
            subset_list = list(df[df[col].notna()].index)
            # print(col,subset_list)

            return subset_list

        # read in subset dataframe from inputs
        pt_subsets = pd.read_csv(data_root / 'pt_subsets.csv')

        # create the technology subsets based on the pt_subsets input
        self.pt = load_and_assign_subsets(pt_subsets, 'pt')
        self.ptc = load_and_assign_subsets(pt_subsets, 'ptc')
        self.ptr = load_and_assign_subsets(pt_subsets, 'ptr')
        self.pth = load_and_assign_subsets(pt_subsets, 'pth')
        self.pth2 = load_and_assign_subsets(pt_subsets, 'pth2')
        self.pts = load_and_assign_subsets(pt_subsets, 'pts')
        self.pti = load_and_assign_subsets(pt_subsets, 'pti')
        self.ptw = load_and_assign_subsets(pt_subsets, 'ptw')
        self.ptsol = load_and_assign_subsets(pt_subsets, 'ptsol')
        self.ptg = load_and_assign_subsets(pt_subsets, 'ptg')
        self.ptd = load_and_assign_subsets(pt_subsets, 'ptd')

        # Step Sets - supply curve and int'l trade
        self.steps = range(1, 4)
        self.CSteps = range(1, 5)

        # Misc Inputs
        self.TransLoss = 0.02  # Transmission losses %
        self.H2_heatrate = (
            13.84 / 1000000
        )  # 13.84 kwh/kg, for kwh/kg H2 -> 54.3, #conversion kwh/kg to GWh/kg


###################################################################################################
# functions to read in and setup parameter data


### Load csvs
def readin_csvs(all_frames):
    """Reads in all of the CSV files from the input dir and returns a dictionary of dataframes,
    where the key is the file name and the value is the table data.

    Parameters
    ----------
    all_frames : dictionary
        empty dictionary to be filled with dataframes

    Returns
    -------
    dictionary
        completed dictionary filled with dataframes from the input directory
    """

    csv_dir = data_root / 'cem_inputs/'
    for filename in os.listdir(csv_dir):
        f = os.path.join(csv_dir, filename)
        if os.path.isfile(f):
            all_frames[filename[:-4]] = pd.read_csv(f)
            # print(filename[:-4],all_frames[filename[:-4]].columns)

    return all_frames


### Load table from SQLite DB
def readin_sql(all_frames):
    """Reads in all of the tables from a SQL databased and returns a dictionary of dataframes,
    where the key is the table name and the value is the table data.

    Parameters
    ----------
    all_frames : dictionary
        empty dictionary to be filled with dataframes

    Returns
    -------
    dictionary
        completed dictionary filled with dataframes from the input directory
    """
    db_dir = data_root / 'cem_inputs_database.db'
    engine = create_engine('sqlite:///' + db_dir)
    Session = sessionmaker(bind=engine)
    session = Session()

    Base = automap_base()
    Base.prepare(autoload_with=engine)
    metadata = MetaData()
    metadata.reflect(engine)

    for table in metadata.tables.keys():
        all_frames[table] = load_data(table, metadata, engine)
        all_frames[table] = all_frames[table].drop(columns=['id'])

    session.close()

    return all_frames


def load_data(tablename, metadata, engine):
    """loads the data from the SQL database; used in readin_sql function.

    Parameters
    ----------
    tablename : string
        table name
    metadata : SQL metadata
        SQL metadata
    engine : SQL engine
        SQL engine

    Returns
    -------
    dataframe
        table from SQL db as a dataframe
    """
    table = Table(tablename, metadata, autoload_with=engine)
    query = select(table.c).where()

    with engine.connect() as connection:
        result = connection.execute(query)
        df = pd.read_sql(query, connection)

    return df


def subset_dfs(all_frames, setin, i):
    """filters dataframes based on the values within the set

    Parameters
    ----------
    all_frames : dictionary
        dictionary of dataframes where the key is the file name and the value is the table data
    setin : class
        contains an initial batch of sets that are used to solve electricity model
    i : string
        name of the set contained within the setin class that the df will be filtered based on.

    Returns
    -------
    dictionary
        completed dictionary filled with dataframes filtered based on set inputs specified
    """
    for key in all_frames:
        if i in all_frames[key].columns:
            all_frames[key] = all_frames[key].loc[all_frames[key][i].isin(getattr(setin, i))]

    return all_frames


def fill_values(row, subset_list):
    """Function to fill in the subset values, is used to assign all years within the year
    solve range to each year the model will solve for.

    Parameters
    ----------
    row : int
        row number in df
    subset_list : list
        list of values to map

    Returns
    -------
    int
        value from subset_list
    """
    if row in subset_list:
        return row
    for i in range(len(subset_list) - 1):
        if subset_list[i] < row < subset_list[i + 1]:
            return subset_list[i + 1]
    return subset_list[-1]


def avg_by_group(df, set_name, map_frame):
    """takes in a dataframe and groups it by the set specified and then averages the data.

    Parameters
    ----------
    df : dataframe
        parameter data to be modified
    set_name : str
        name of the column/set to average the data by
    map_frame : dataframe
        data that maps the set name to the new grouping for that set

    Returns
    -------
    dataframe
        parameter data that is averaged by specified set mapping
    """
    map_df = map_frame.copy()
    df = df.sort_values(by=list(df[:-1]))
    # print(df.tail())

    # location of y column and list of cols needed for the groupby
    pos = df.columns.get_loc(set_name)
    map_name = 'Map_' + set_name
    groupby_cols = list(df.columns[:-1]) + [map_name]
    groupby_cols.remove(set_name)

    # group df by year map data and update y col
    df[set_name] = df[set_name].astype(int)
    df = pd.merge(df, map_df, how='left', on=[set_name])
    df = df.groupby(by=groupby_cols, as_index=False).mean()
    df[set_name] = df[map_name].astype(int)
    df = df.drop(columns=[map_name]).reset_index(drop=True)

    # move back to original position
    y_col = df.pop(set_name)
    df.insert(pos, set_name, y_col)

    # used to qa
    df = df.sort_values(by=list(df[:-1]))
    # print(df.tail())

    return df


# add seasons to data without seasons
def add_season_index(cw_temporal, df, pos):
    """adds a season index to the input dataframe

    Parameters
    ----------
    cw_temporal : dataframe
        dataframe that includes the season index
    df : dataframe
        parameter data to be modified
    pos : int
        column position for the seasonal set

    Returns
    -------
    dataframe
        modified parameter data now indexed by season
    """
    df_s = cw_temporal[['Map_s']].copy().rename(columns={'Map_s': 's'}).drop_duplicates()
    df = pd.merge(df, df_s, how='cross')
    s_col = df.pop('s')
    df.insert(pos, 's', s_col)

    return df


###################################################################################################
def preprocessor(setin):
    """master preprocessor function that generates the final dataframes and sets sent over to the
    electricity model. This function reads in the input data, modifies it based on the temporal
    and regional mapping specified in the inputs, and gets it into the final formatting needed.
    Also adds some additional regional sets to the set class based on parameter inputs.

    Parameters
    ----------
    setin : class
        an initial batch of sets that are used to solve electricity model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes where the key is the file name and the value is the table data
    setin : class
        an initial batch of sets that are used to solve electricity model
    """

    # read in raw data
    all_frames = {}
    if db_switch == 0:
        # add csv input files to all frames
        all_frames = readin_csvs(all_frames)
    elif db_switch == 1:
        # add sql db tables to all frames
        all_frames = readin_sql(all_frames)

    # read in load data from residential model
    load_file = Path(PROJECT_ROOT, 'src/models/residential/input/Load.csv')
    all_frames['Load'] = pd.read_csv(load_file)

    # international trade sets
    r_file = all_frames['TranLineLimitCan'][['r', 'r1']].drop_duplicates()
    r_file = r_file[r_file['r'].isin(setin.r)]
    setin.r_can_conn = list(r_file['r'].unique())
    setin.r_can = list(r_file['r1'].unique())
    setin.r1 = setin.r + setin.r_can

    # create temporal mapping df
    cw_temporal = setin.cw_temporal

    # year weights
    all_frames['year_weights'] = setin.year_weights

    # subset df by region
    all_frames = subset_dfs(all_frames, setin, 'r')
    all_frames = subset_dfs(all_frames, setin, 'r1')

    setin.trade_regs = all_frames['TranLimit']['r'].unique()

    # last year values used
    filter_list = ['CapCost']
    for key in filter_list:
        all_frames[key] = all_frames[key].loc[all_frames[key]['y'].isin(getattr(setin, 'years'))]

    # average values in years/hours used
    for key in all_frames.keys():
        if 'y' in all_frames[key].columns:
            all_frames[key] = avg_by_group(all_frames[key], 'y', setin.year_map)
        if 'hr' in all_frames[key].columns:
            all_frames[key] = avg_by_group(all_frames[key], 'hr', cw_temporal[['hr', 'Map_hr']])

    # create temporal mapping parameters
    def temporal_map(cols, rename_cols):
        df = cw_temporal[cols].rename(columns=rename_cols).drop_duplicates()
        return df

    all_frames['Map_day_s'] = temporal_map(['Map_day', 'Map_s'], {'Map_day': 'day', 'Map_s': 's'})
    all_frames['Map_hr_d'] = temporal_map(['Map_hr', 'Map_day'], {'Map_day': 'day', 'Map_hr': 'hr'})
    all_frames['Map_hr_s'] = temporal_map(['Map_hr', 'Map_s'], {'Map_hr': 'hr', 'Map_s': 's'})
    all_frames['Hr_weights'] = temporal_map(['Map_hr', 'Hr_weights'], {'Map_hr': 'hr'})
    all_frames['Idaytq'] = temporal_map(
        ['Map_day', 'Dayweights'], {'Map_day': 'day', 'Dayweights': 'Idaytq'}
    )

    # using same pti capacity factor for all model years and reordering columns
    all_frames['ptiUpperSet'] = pd.merge(
        all_frames['ptiUpperSet'], pd.DataFrame({'y': setin.years}), how='cross'
    )
    all_frames['ptiUpperSet'] = all_frames['ptiUpperSet'][
        ['pt', 'y', 'r', 'steps', 'hr', 'SolWindCapFactor']
    ]

    # Update load to be the total demand in each time segment rather than the average
    all_frames['Load'] = pd.merge(
        all_frames['Load'], all_frames['Hr_weights'], how='left', on=['hr']
    )
    all_frames['Load']['Load'] = all_frames['Load']['Load'] * all_frames['Load']['Hr_weights']
    all_frames['Load'] = all_frames['Load'].drop(columns=['Hr_weights'])

    # add seasons to data without seasons
    all_frames['SupplyCurve'] = add_season_index(cw_temporal, all_frames['SupplyCurve'], 1)

    # changing units of prices to all be in $/GWh so obj is $
    def price_MWh_to_GWh(dic, names: list[str]):
        for name in names:
            dic[name].loc[:, name] = dic[name][name] * 1000
        return dic

    all_frames = price_MWh_to_GWh(
        all_frames,
        [
            'SupplyPrice',
            'TranCost',
            'TranCostCan',
            'RegReservesCost',
            'RampUp_Cost',
            'RampDown_Cost',
            'CapCost',
            'CapCost_y0',
        ],
    )

    # Recalculate Supply Curve Learning

    # save first year of supply curve summer capacity for learning
    all_frames['SupplyCurve_learning'] = all_frames['SupplyCurve'][
        (all_frames['SupplyCurve']['y'] == setin.start_year) & (all_frames['SupplyCurve']['s'] == 2)
    ]

    # set up first year capacity for learning.
    all_frames['SupplyCurve_learning'] = (
        pd.merge(all_frames['SupplyCurve_learning'], all_frames['CapCost'], how='outer')
        .drop(columns=['s', 'y', 'CapCost', 'r', 'steps'])
        .rename(columns={'SupplyCurve': 'SupplyCurve_learning'})
        .groupby(['pt'])
        .agg('sum')
        .reset_index()
    )

    # if cap = 0, set to minimum unit size (0.1 for now)
    all_frames['SupplyCurve_learning'].loc[
        all_frames['SupplyCurve_learning']['SupplyCurve_learning'] == 0.0, 'SupplyCurve_learning'
    ] = 0.01

    # builds the capacity credit dataframe
    def capacitycredit_df():
        df = pd.merge(all_frames['SupplyCurve'], all_frames['Map_hr_s'], on=['s'], how='left').drop(
            columns=['s']
        )

        # capacity credit is hourly capacity factor for vre technologies
        df = pd.merge(
            df, all_frames['ptiUpperSet'], how='left', on=['pt', 'y', 'r', 'steps', 'hr']
        ).rename(columns={'SolWindCapFactor': 'CapacityCredit'})

        # capacity credit = 1 for dispatchable technologies
        df['CapacityCredit'] = df['CapacityCredit'].fillna(1)

        # capacity credit is seasonal limit for hydro
        df2 = pd.merge(
            all_frames['HydroCapFactor'],
            all_frames['Map_hr_s'],
            on=['s'],
            how='left',
        ).drop(columns=['s'])
        df2['pt'] = setin.pth[0]
        df = pd.merge(df, df2, how='left', on=['pt', 'r', 'hr'])
        df.loc[df['pt'].isin(setin.pth), 'CapacityCredit'] = df['HydroCapFactor']
        df = df.drop(columns=['SupplyCurve', 'HydroCapFactor'])
        df = df[['pt', 'y', 'r', 'steps', 'hr', 'CapacityCredit']]
        return df

    all_frames['CapacityCredit'] = capacitycredit_df()

    # Expands params that are indexed by season to be indexed by hour
    def create_hourly_params(df, cols):
        df = pd.merge(df, all_frames['Map_hr_s'], on=['s'], how='left').drop(columns=['s'])
        df = df[cols]
        return df

    # expand a few parameters to be hourly

    all_frames['TranLineLimitCan'] = create_hourly_params(
        all_frames['TranLineLimitCan'], ['r', 'r1', 'y', 'hr', 'TranLineLimitCan']
    )

    all_frames['TranLimitCan'] = create_hourly_params(
        all_frames['TranLimitCan'], ['r1', 'CSteps', 'y', 'hr', 'TranLimitCan']
    )

    # sets the index for all df in dict
    for key in all_frames:
        index = list(all_frames[key].columns[:-1])
        all_frames[key] = all_frames[key].set_index(index)

    ###############################################################################################
    # creates sets

    # Create subsets off of full sets
    def create_subsets(df, col, subset):
        df = df[df[col].isin(subset)].dropna()
        return df

    # Expands sets that are indexed by season to be indexed by hour
    def create_hourly_sets(df):
        df = pd.merge(df, all_frames['Map_hr_s'].reset_index(), on=['s'], how='left').drop(
            columns=['s']
        )
        return df

    index_list = ['pt', 'y', 'r', 'steps', 'hr']

    # sets that are related to the supply curve
    setin.GenSet = create_hourly_sets(
        create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.ptg)
    ).set_index(index_list)

    setin.ptd_upper_set = create_hourly_sets(
        create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.ptd)
    ).set_index(index_list)

    setin.StorageSet = create_hourly_sets(
        create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.pts)
    ).set_index(index_list)

    setin.H2GenSet = create_hourly_sets(
        create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.pth2)
    ).set_index(index_list)

    setin.RampSet = create_hourly_sets(
        create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.ptc)
    ).set_index(index_list)

    setin.pth_upper_set = create_hourly_sets(
        create_subsets(
            create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.pth),
            'steps',
            [2],
        )
    ).set_index(index_list)

    setin.Gen_ramp_set = create_subsets(
        create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.ptc)
        ),
        'hr',
        setin.hr23,
    ).set_index(index_list)

    setin.FirstHour_gen_ramp_set = create_subsets(
        create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.ptc)
        ),
        'hr',
        setin.hr1,
    ).set_index(index_list)

    setin.StorageBalance_set = create_subsets(
        create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.pts)
        ),
        'hr',
        setin.hr23,
    ).set_index(index_list)

    setin.FirstHourStorageBalance_set = create_subsets(
        create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.pts)
        ),
        'hr',
        setin.hr1,
    ).set_index(index_list)

    setin.HydroMonthsSet = (
        create_subsets(
            create_subsets(all_frames['SupplyCurve'].reset_index(), 'pt', setin.pth),
            'steps',
            [1],
        )
        .drop(columns=['steps'])
        .set_index(['pt', 'y', 'r', 's'])
    )

    setin.BuildSet = setin.sw_ptbuilds[setin.sw_ptbuilds['builds'] == 1].set_index(['pt', 'steps'])

    setin.RetSet = pd.merge(
        all_frames['SupplyCurve']
        .reset_index()
        .drop(columns=['s', 'SupplyCurve'])
        .drop_duplicates(),
        setin.sw_ptretires[setin.sw_ptretires['retires'] == 1],
        on=['pt', 'steps'],
        how='right',
    ).set_index(['pt', 'y', 'r', 'steps'])

    # other sets

    setin.TradeCanSet = (
        pd.merge(
            all_frames['TranLimitCan'].reset_index(),
            all_frames['TranLineLimitCan'].reset_index(),
            how='inner',
        )
        .drop(columns=['TranLimitCan'])
        .set_index(['r', 'r1', 'y', 'CSteps', 'hr'])
    )

    setin.TradeSet = create_hourly_sets(all_frames['TranLimit'].reset_index()).set_index(
        ['r', 'r1', 'y', 'hr']
    )

    setin.ProcurementSet = pd.merge(
        create_hourly_sets(all_frames['SupplyCurve'].reset_index()),
        pd.DataFrame({'restypes': setin.restypes}),
        how='cross',
    ).set_index(['restypes'] + index_list)

    return all_frames, setin


###################################################################################################
# Review Inputs


def makedir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def output_inputs():
    output_path = Path(OUTPUT_ROOT, 'electricity_inputs/')
    makedir(output_path)

    years = list(pd.read_csv(PROJECT_ROOT / 'src/integrator/input/sw_year.csv').dropna()['year'])
    regions = list(pd.read_csv(PROJECT_ROOT / 'src/integrator/input/sw_reg.csv').dropna()['region'])

    # Build sets used for model
    all_frames = {}
    setA = Sets(years, regions)

    # creates the initial data
    all_frames, setB = preprocessor(setA)
    for key in all_frames:
        # print(key, list(all_frames[key].reset_index().columns))
        fname = key + '.csv'
        all_frames[key].to_csv(output_path / fname)

    return all_frames, setB


def print_sets(setin):
    set_list = dir(setin)
    set_list = sorted([x for x in set_list if '__' not in x])
    for item in set_list:
        if isinstance(getattr(setin, item), pd.DataFrame):
            print(item, ':', getattr(setin, item).reset_index().columns)
        else:
            print(item, ':', getattr(setin, item))


# all_frames, setB = output_inputs()
# print_sets(setB)
