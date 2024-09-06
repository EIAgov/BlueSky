"""
A gathering of utility functions for dealing with model interconnectivity

Dev Note:  At some review point, some decisions may move these back & forth with parent
models after it is decided if it is a utility job to do .... or a class method.

Additionally, there is probably some renaming due here for consistency
"""

# for easier/accurate indexing
from collections import defaultdict, namedtuple
from logging import getLogger
import typing
from pyomo.environ import ConcreteModel, value
import pandas as pd
from pathlib import Path
from definitions import PROJECT_ROOT
import logging
from datetime import datetime
import os

if typing.TYPE_CHECKING:
    from src.models.electricity.scripts.electricity_model import PowerModel
    from src.models.hydrogen.model.h2_model import H2Model

logger = getLogger(__name__)


def make_output_dir(dir):
    """generates an output directory to write model results, output directory is the date/time
    at the time this function executes. It includes subdirs for vars, params, constraints.

    Returns
    -------
    string
        the name of the output directory
    """
    if not os.path.exists(dir):
        os.makedirs(dir)
    # TODO: write warning if you are over writting directory
    return dir


# Logger Setup
def setup_logger(output_dir):
    # set up root logger
    log_path = Path(output_dir)
    if not Path.is_dir(log_path):
        Path.mkdir(log_path)
    logging.basicConfig(
        filename=output_dir / 'run.log',
        encoding='utf-8',
        filemode='w',
        # format='[%(asctime)s][%(name)s]' + '[%(funcName)s][%(levelname)s]  :: |%(message)s|',
        format='%(asctime)s | %(name)s | %(levelname)s :: %(message)s',
        datefmt='%d-%b-%y %H:%M:%S',
        level=logging.DEBUG,
    )
    logging.getLogger('pyomo').setLevel(logging.WARNING)
    logging.getLogger('pandas').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)


# a named tuple for common electric model index structure (EI=Electrical Index)
EI = namedtuple('EI', ['region', 'year', 'hour'])
"""(region, year, hour)"""
HI = namedtuple('HI', ['region', 'year'])
"""(region, year)"""


def get_elec_price(instance: typing.Union['PowerModel', ConcreteModel], block=None) -> pd.DataFrame:
    """pulls hourly electricity prices from completed PowerModel and weights correctly

    Parameters
    ----------
    instance : PowerModel
        solved electricity model

    Returns
    -------
    pd.DataFrame
        df full of electricity prices
    """
    # for H2 model electricity price

    if block:
        c = block.Demand_balance
        model = block
    else:
        c = instance.Demand_balance
        model = instance

    records = []
    for index in c:
        record = (index, float(instance.dual[c[index]]))
        records.append(record)
    elec_price = pd.DataFrame(records)
    elec_price.columns = ['Index', 'Dual']
    df = pd.DataFrame([pd.Series(x) for x in elec_price['Index']])
    # Note: I'd like to be able to add the names of the indices automatically, but just using this shortcut for now
    df.columns = ['i_{}'.format(x + 1) for x in df.columns]
    elec_price = pd.concat([elec_price, df], axis=1)
    elec_price.rename(columns={'i_1': 'r', 'i_2': 'y', 'i_3': 'hr'}, inplace=True)
    elec_price = pd.merge(elec_price, model.df_year_weights, on=['y'])
    elec_price = pd.merge(
        elec_price, pd.merge(model.df_Idaytq, model.df_Map_hr_d, on=['day']), on=['hr']
    )

    # correct for dayweights and year weights, convert $/MW -> $/GW
    elec_price.loc[:, 'price_wt'] = elec_price.Dual / (elec_price.Idaytq * elec_price.year_weights)
    return elec_price


def get_annual_wt_avg(elec_price: pd.DataFrame) -> dict[HI, float]:
    """takes annual weighted average of hourly electricity prices

    Parameters
    ----------
    elec_price : pd.DataFrame
        hourly electricity prices

    Returns
    -------
    dict[HI, float]
        annual weighted average electricity prices
    """

    def my_agg(x):
        names = {'weighted_ave_price': (x['Idaytq'] * x['price_wt']).sum() / x['Idaytq'].sum()}
        return pd.Series(names, index=['weighted_ave_price'])

    # find annual weighted average, weight by day weights
    elec_price_ann = elec_price.groupby(['r', 'y']).apply(my_agg)

    return elec_price_ann


def regional_annual_prices(
    m: typing.Union['PowerModel', ConcreteModel], block=None
) -> dict[HI, float]:
    """pulls all regional annual weighted electricity prices

    Parameters
    ----------
    m : typing.Union['PowerModel', ConcreteModel]
        solved PowerModel
    block :  optional
        solved block model if applicable, by default None

    Returns
    -------
    dict[HI, float]
        dict with regional annual electricity prices
    """
    ep = get_elec_price(m, block)
    ap = get_annual_wt_avg(ep)

    # convert from dataframe to dictionary
    lut = {}
    for r in ap.to_records():
        region, year, price = r
        lut[HI(region=region, year=year)] = price

    return lut


def convert_elec_price_to_lut(prices: list[tuple[EI, float]]) -> dict[EI, float]:
    """convert electricity prices to dictionary, look up table

    Parameters
    ----------
    prices : list[tuple[EI, float]]
        list of prices

    Returns
    -------
    dict[EI, float]
        dict of prices
    """
    res = {}
    for row in prices:
        ei, price = row
        res[ei] = price
    return res


def poll_hydrogen_price(
    model: typing.Union['H2Model', ConcreteModel], block=None
) -> list[tuple[HI, float]]:
    """Retrieve the price of H2 from the H2 model

    Parameters
    ----------
    model : H2Model
        the model to poll
    block: optional
        block model to poll

    Returns
    -------
    list[tuple[HI, float]]
        list of H2 Index, price tuples
    """
    # ensure valid class
    if not isinstance(model, ConcreteModel):
        raise ValueError('invalid input')

    # TODO:  what should happen if there is no entry for a particular region (no hubs)?
    if block:
        demand_constraint = block.demand_constraint
    else:
        demand_constraint = model.demand_constraint
    # print('************************************\n')
    # print(list(demand_constraint.index_set()))
    # print(list(model.dual.keys()))

    rows = [(HI(*k), model.dual[demand_constraint[k]]) for k, v in demand_constraint.iteritems()]  # type: ignore
    return rows  # type: ignore


def convert_h2_price_records(records: list[tuple[HI, float]]) -> dict[HI, float]:
    """simple coversion from list of records to a dictionary LUT
    repeat entries should not occur and will generate an error"""
    res = {}
    for hi, price in records:
        if hi in res:
            logger.error('Duplicate index for h2 price received in coversion: %s', hi)
            raise ValueError('duplicate index received see log file.')
        res[hi] = price

    return res


def poll_year_avg_elec_price(price_list: list[tuple[EI, float]]) -> dict[HI, float]:
    """retrieve a REPRESENTATIVE price at the annual level from a listing of prices

    This function computes the AVERAGE elec price for each region-year combo

    Parameters
    ----------
    price_list : list[tuple[EI, float]]
        input price list

    Returns
    -------
    dict[HI, float]
        a dictionary of (region, year): price
    """
    year_region_records = defaultdict(list)
    res = {}
    for ei, price in price_list:
        year_region_records[HI(region=ei.region, year=ei.year)].append(price)

    # now gather the averages...
    for hi in year_region_records:
        res[hi] = sum(year_region_records[hi]) / len(year_region_records[hi])

    logger.debug('Computed these region-year averages for elec price: \n\t %s', res)
    return res


def poll_h2_prices_from_elec(
    model: 'PowerModel', tech, regions: typing.Iterable
) -> dict[typing.Any, float]:
    """poll the step-1 H2 price currently in the model for region/year, averaged over any steps"""
    res = {}
    for idx in model.H2Price:
        reg, s, t, step, y = idx
        if t == tech and reg in regions and step == 1:  # TODO:  remove hard coding
            res[reg, s, y] = value(model.H2Price[idx])

    return res


def create_temporal_mapping(sw_temporal):
    """Combines the input mapping files within the electricity model to create a master temporal
    mapping dataframe. The df is used to build multiple temporal parameters used within the  model.
    It creates a single dataframe that has 8760 rows for each hour in the year.
    Each hour in the year is assigned a season type, day type, and hour type used in the model.
    This defines the number of time periods the model will use based on cw_s_day and cw_hr inputs.

    Returns
    -------
    dataframe
        a dataframe with 8760 rows that include each hour, hour type, day, day type, and season.
        It also includes the weights for each day type and hour type.
    """

    # Temporal Sets - read data
    # SD = season/day; hr = hour
    data_root = Path(PROJECT_ROOT, 'src/integrator/input')
    if sw_temporal == 'default':
        sd_file = pd.read_csv(data_root / 'cw_s_day.csv')
        hr_file = pd.read_csv(data_root / 'cw_hr.csv')
    else:
        cw_s_day = 'cw_s_day_' + sw_temporal + '.csv'
        cw_hr = 'cw_hr_' + sw_temporal + '.csv'
        sd_file = pd.read_csv(data_root / 'temporal_mapping' / cw_s_day)
        hr_file = pd.read_csv(data_root / 'temporal_mapping' / cw_hr)

    # set up mapping for seasons and days
    df1 = sd_file
    df4 = df1.groupby(by=['Map_day'], as_index=False).count()
    df4 = df4.rename(columns={'Index_day': 'Dayweights'}).drop(columns=['Map_s'])
    df1 = pd.merge(df1, df4, how='left', on=['Map_day'])

    # set up mapping for hours
    df2 = hr_file
    df3 = df2.groupby(by=['Map_hr'], as_index=False).count()
    df3 = df3.rename(columns={'Index_hr': 'Hr_weights'})
    df2 = pd.merge(df2, df3, how='left', on=['Map_hr'])

    # combine season, day, and hour mapping
    df = pd.merge(df1, df2, how='cross')
    df['hr'] = df.index
    df['hr'] = df['hr'] + 1
    df['Map_hr'] = (df['Map_day'] - 1) * df['Map_hr'].max() + df['Map_hr']
    # df.to_csv(data_root/'temporal_map.csv',index=False)

    return df
