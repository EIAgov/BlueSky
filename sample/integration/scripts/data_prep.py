####################################################################################################################
####################################################################################################################
#PRE-PROCESSING
####################################################################################################################
####################################################################################################################

# TODO: ID frames that are the same for all years
# Idaytq (but not in restprep), Idaytq_orig, Idaytqset
# in restprep already: Map_EcpGroup, map_plantsteps, RampRate, Map_day, Map_ms, Hour_map, UnmetLoad_penalty, 
#                       HydroDispatchablePortion, 
# cont. RampUp_Cost, RampDown_Cost, Map, Map_hr_d, Dayweights
# TODO: ID all frames that are different in each year & have y column
# TranCost, TranLimitCan, TranCostLimit, SolWindCapFactor, SupplyPrice, Load, SupplyCurve, TranCostCan, TranLineLimitCan, 
# TranLineLimitCanSet, TranLimitCanSet, TradeSet, TradeCanSet,
# cont. StorageSet, GenSet, SupplyCurveMonths (maybe can be generalized?), BatteryChargeCap,
# SparseSet, ptiUpperSet, CapacityFactor, LoadSet, SupplyPriceSet, SupplyCurveSet, TranCostSet,  TranCostCanSet, TranLimitSet
# TODO: ID all frames above that do not have y column
# HydroCapFactor, HydroSet, M864_LF (can drop it before passed out, not used in model)
# TODO: ID dfs we won't need
# NetTrade, DPVcap, DPVgen, h2_turbine_generation, ClipCapFactor, BatteryIncrement,
# From restprep: Map_m2 (saving for quick reference), Map_mes (don't think we need), StartBatteryFrac
#

#TODO: Eventully, we will need just 1 input data set for expansion initialization

# TODO: add y column to frames which don't have it

# TODO: get_prep_data: make function which pulls in & processes restprep data (single pull first)
# TODO: get_all_years_data: make function which runs and aggregates all years' data pull
# TODO: get_year_data: make function which pulls in an individual year's data from ecpout
    
#Setup

#Import pacakges
import pandas as pd
import numpy as np
import os
import preprocessor as pp
from pyomo.common.timing import TicTocTimer
timer = TicTocTimer()


####################################################################################################################
#Read in data

# Technology Code Names (not a set) Useful here as a reference
names = [[1, 'Coal'], [2, 'Steam'], [3, 'Turbine'], [4, 'CC'], [5, 'FuelC'], [6, 'Nuclear'], [7, 'Biomass'],
        [8, 'Geother'], [9, 'MSW'], [10, 'Hydro'], [11, 'Storage'], [12, 'P2'], [13, 'Storage'], [14, 'Wind'],
        [16, 'Wind'], [17, 'Solar'], [18, 'Solar'], [19, 'Solar'], [20, 'Solar'], [22, 'OtherIn'], [23, 'DistGen']]

ti = [70, 71, 72, 73, 74, 75, 76]  # Intermittent_technology ECPtype, used to process nems data

def open_and_split_data(filename):
    #Read the text file into a string
    with open(filename) as file:
        data = file.read()

    #Split the text by semicolon (;)
    frames = data.split(';')

    return frames

#setup tables and variables for the split strings
def convert_split_data_to_tables(frame,all_frames):
    frame = frame.strip()  
    if frame == '':
        pass
    #Convert input tables to dataframes
    elif frame.split('\n')[0]=='COMPOSITE TABLE:':
        df = pd.DataFrame([[float(y) for y in x.split()] \
            for x in frame.split('\n')[2:]], columns=[x for x in frame.split('\n')[1].split()])
        #either adds or appends df to dictionary
        name = frame.split('\n')[1].split()[-1]
        if name in all_frames:
            all_frames[name] = pd.concat([all_frames[name],df])
        else:
            all_frames[name] = df

    return all_frames

def add_opened_data_to_dict(filename,all_frames):
    frames = open_and_split_data(filename)
    for frame in frames:
        all_frames = convert_split_data_to_tables(frame, all_frames)
    
    return all_frames


# duplicate initial data for all years
def get_data_initial_year(all_frames,setin):
    for name, df in all_frames.items():
        if 'y' in df.columns:
            df.drop(columns=['y'], inplace=True)
            all_frames[name] = pd.merge(df, setin.all_years_init, how='cross')

    return all_frames

def get_data_year(year, all_frames_rest2,keep_df):
    frames_rest = open_and_split_data(f'../input/initial_setup/toAIMMS/ecpout_{str(year)}.txt')  # {str(setin.y[0])}
    all_frames_rest = {}
    for frame in frames_rest:
        all_frames_rest = convert_split_data_to_tables(frame, all_frames_rest)

    # Only keep MSW and DPV capacity
    keep_index = (all_frames_rest['SupplyPrice']['pt'] == 9) | (
                (all_frames_rest['SupplyPrice']['steps'] == 2) & (all_frames_rest['SupplyPrice']['pt'] == 20))
    all_frames_rest['SupplyCurve'] = all_frames_rest['SupplyPrice'].loc[keep_index].drop(
        columns=['SupplyPrice'])

    # drop SupplyCurve column
    all_frames_rest['SupplyPrice'].drop(columns=['SupplyCurve'], inplace=True)

    # Keep load
    all_frames_rest['Load'] = all_frames_rest['NetTrade'].copy().drop(
        columns=['Group_ECP', 'Segment_ECP', 'EMMGroup', 'EMMSegment', 'NetTrade'])
    # replace df
    for name in keep_df:
        new_name = name + '_new'
        all_frames_rest[name].rename(columns={name: new_name}, inplace=True)

        all_frames_rest2[name] = pd.concat([all_frames_rest2[name],
                                            all_frames_rest[name]], ignore_index=True)
    return all_frames_rest2

#subsets the data by region
def subset_regions(all_frames,setin):
    for i in all_frames:
        if type(all_frames[i]) != str:
            if 'r' in all_frames[i].columns:
                all_frames[i] = all_frames[i].loc[all_frames[i]['r'].isin(setin.r)]
            if 'r1' in all_frames[i].columns:
                all_frames[i] = all_frames[i].loc[all_frames[i]['r1'].isin(setin.r + setin.r_can)]
    
    return all_frames

#identifying alls sets, rename a few sets in all_frames
def create_set_list(all_frames):
    set_list = []
    for name, item in all_frames.items():
        if isinstance(item,pd.DataFrame):
            all_frames[name] = item.rename(columns={'year':'y','Steps':'steps','ptc':'pt'})
            if 'y' in all_frames[name].columns:
                all_frames[name].insert(len(all_frames[name].columns)-2, 'y', all_frames[name].pop('y'))
            set_list = set_list+(list(all_frames[name].columns)[:-1])
            #print(name,all_frames[name].columns)
                    
    set_list.append('hr')
    set_list = sorted(list(set(set_list)))

    return all_frames, set_list


def read_in_data(setin):
    """Read in data, create dictionary with input tables and input variables

    Parameters
    ----------
    setin : class
        contains sets used in the model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    """

    # add restprep data to dictionary
    all_frames = {}
    filename = '../input/initial_setup/restprep.txt'
    all_frames = add_opened_data_to_dict(filename,all_frames)

    #add initial year's data to dictionary
    filename = f'../input/initial_setup/toAIMMS/ecpout_{str(setin.y0)}.txt'
    all_frames = add_opened_data_to_dict(filename,all_frames)

    all_frames = get_data_initial_year(all_frames,setin)

    # Some dataframes are read in together, splitting them here
    all_frames['Load'] = all_frames['NetTrade'].copy().drop(
        columns=['Group_ECP', 'Segment_ECP', 'EMMGroup', 'EMMSegment', 'NetTrade'])
    all_frames['NetTrade'] = all_frames['NetTrade'].drop(
        columns=['Group_ECP', 'Segment_ECP', 'EMMGroup', 'EMMSegment', 'Load'])
    all_frames['SupplyCurve'] = all_frames['SupplyPrice'].copy().drop(columns=['SupplyPrice'])
    all_frames['SupplyPrice'].drop(columns=['SupplyCurve'], inplace=True)
    
    # save first year of supply curve summer capacity for learning
    all_frames['SupplyCurve_learning'] = all_frames['SupplyCurve'][(all_frames['SupplyCurve']['y'] == setin.start_year) 
                                                                   & (all_frames['SupplyCurve']['s'] == 2)]

    #save for use in model obj
    all_frames['year_weights'] = setin.year_weights

    # only if multiyear, will update load and MSW, DPV with all year values
    if len(setin.y) > 1:
        keep_df = ['Load', 'SupplyCurve','SupplyPrice']
        # loop through rest of years to retrieve load, MSW cap, DPV cap
        # replace this in initialized data

        #initialize
        keys = keep_df
        values = [pd.DataFrame() for x in keep_df]
        all_frames_rest2 = dict(zip(keys, values))

        for year in setin.solve_range:
            all_frames_rest2 = get_data_year(year, all_frames_rest2,keep_df)

        all_frames_rest2['SupplyPrice'] = pd.merge(all_frames_rest2['SupplyPrice'],
                 all_frames['SupplyPrice'][all_frames['SupplyPrice']['y'] == all_frames['SupplyPrice']['y'].min()]\
                     .rename(columns={'y':'y_drop'}).drop(columns=['SupplyPrice']),
                 on=['r','s','pt','steps'], how='right').drop(columns=['y_drop'])

        # merge next years' data on to initial year's where appropriate
        for name in keep_df:
            new_name = name + '_new'
            cols = all_frames_rest2[name].columns
            cols_keep = list(cols[cols != new_name])

            all_frames_rest2[name].rename(columns={'y': 'y_real'}, inplace=True)
            all_frames_rest2[name] = pd.merge(all_frames_rest2[name], setin.year_map,
                                              on=['y_real']).drop(columns=['y_real'])
            all_frames_rest2[name] = all_frames_rest2[name].groupby(cols_keep).agg('mean').reset_index()
            all_frames[name] = pd.merge(all_frames[name], all_frames_rest2[name],
                                        on=cols_keep, how='outer')
            all_frames[name].loc[~all_frames[name][new_name].isna(), name] = \
                list(all_frames[name][~all_frames[name][new_name].isna()][new_name])
            all_frames[name].drop(columns=[new_name], inplace=True)
            
    # add csv input files to all frames 
    for filename in os.listdir('../input/initial_setup/csv_inputs/'):
        #print(filename[:-4])
        f = os.path.join('../input/initial_setup/csv_inputs/', filename)
        if os.path.isfile(f):
            all_frames[filename[:-4]] = pd.read_csv(f)
            #print(filename[:-4],all_frames[filename[:-4]].columns)

    # update sets based on hour and day mappings
    setin.num_hr_day = int(all_frames['Hour_map']['Hour_map'].max()) #number of periods in a day
    setin.num_days = int(all_frames['Map_day']['Map_day'].max()) #number of days
    setin.num_hr = setin.num_hr_day * setin.num_days

    setin.m = range(1, setin.num_months + 1)  # Month
    setin.day = range(1, setin.num_days + 1) #Day #model solves with specified number of days
    setin.h = range(1, setin.num_hr_day+1) #hours in a day
    setin.hr = range(1, setin.num_days*len(setin.h)+1)   #Number of hours the model solves for: days x number of periods per day
    setin.hr1 = range(1, setin.num_days*len(setin.h)+1, len(setin.h)) #First hour of the day #SubsetOf: HR;
    setin.hr23 = list(set(setin.hr) - set(setin.hr1)) #All hours that are not the first hour

    all_frames['RampUp_Cost'] = all_frames['RampDown_Cost'].copy().drop(columns=['RampDown_Cost'])
    all_frames['RampDown_Cost'] = all_frames['RampDown_Cost'].drop(columns=['RampUp_Cost'])

    all_frames = subset_regions(all_frames, setin)
    
    #Removing non-set columns  
    all_frames['M864_LF'] = all_frames['M864_LF'].drop(columns=['Map_PlantSteps'])
    all_frames, set_list = create_set_list(all_frames)

    #check naming convention for sets
    for i in set_list:
        if (len(i)>2) and (__name__ == "__main__"):
            #print('Check: Is',i,'a set? If no, remove from set list, otherwise consider shortening name.')
            pass
    #print('check sets here:',set_list)

    return all_frames

####################################################################################################################
def update_temporal_mapping(all_frames, setin):
    """Updates to all_frames: Updating the temporal resolution applied in the model

    Parameters
    ----------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    setin : class
        contains sets used in the model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    """

    all_frames['Map_day'].rename(columns={'Map_day':'day'}, inplace=True)
    # TODO: add unit test to check that no days span multiple seasons

    #Create map for seasons, months, days, and hours
    all_frames['Map'] = pd.DataFrame([(i,
                                       1+(i-1)%(setin.num_hr_day), #new hour #this is fine with any month/daytype combo
                                       1+(i-1)//(setin.num_hr_day)) #generalized daytype #this is fine with any month/daytype combo
                                      for i in setin.hr],
                                     columns=['hr', 'Hour_map', 'day'])
    #TODO: add unit test to check that max(day) = max(day) from Map_day file

    #adding d and m
    all_frames['Map'] = pd.merge(all_frames['Map'],
                                 all_frames['Map_day'],
                                 on=['day'], how='left')
    #adding season map
    all_frames['Map'] = pd.merge(all_frames['Map'],
                                 all_frames['Map_ms'],
                                 on=['m'], how='left').drop(columns=['Map_ms','d','m']).drop_duplicates().reset_index(drop=True)

    # time period mapping 
    all_frames['Map_day_s'] = all_frames['Map'].drop(columns=['Hour_map','hr']).drop_duplicates().set_index(['day'])
    all_frames['Map_hr_s'] = all_frames['Map'].drop(columns=['Hour_map','day']).set_index(['hr'])
    all_frames['Map_hr_d'] = all_frames['Map'].drop(columns=['Hour_map','s']).set_index(['hr'])
    all_frames['Map_ms'] = all_frames['Map_ms'].set_index(['m'])

    # create table with hour weights
    # TODO: unit test to make sure hours are chronological
    all_frames['Hr_weights'] = all_frames['Hour_map'].groupby(['Hour_map']).agg('count').reset_index().rename(columns={'h': 'Hr_weights'})

    # create map from hr to Hr_weights
    all_frames['Hr_weights'] = pd.merge(all_frames['Map'].drop(columns=['day', 's']),
                                      all_frames['Hr_weights'],
                                      on=['Hour_map'],how='left').drop(columns=['Hour_map']).sort_values(by=['hr']).set_index(['hr'])

    #Add peak day dayweight to the weekday dayweight in Idaytq
    all_frames['Idaytq_orig'] = pd.merge(all_frames['Idaytq'], 
                                         all_frames['Map_day'], 
                                         on=['m','d'], how='left')
    all_frames['Idaytq'] = all_frames['Idaytq_orig'].drop(columns=['d', 'm']).groupby(['day']).agg('sum').reset_index()

    #Creating Dayeighting frame
    all_frames['Dayweights'] = pd.merge(all_frames['Map'],
                                        all_frames['Idaytq'].rename(columns={'Idaytq': 'Dayweights'}),
                                        on=['day'], how='left').drop(columns=['s','Hour_map','day'])
    
    #Using the new day-type mappings to update the input data for load and solar/wind capacity factors
    # aggregating data by new days/periods
    def create_h_col(df_name, additional_groupby, method='wm'):
        df = all_frames[df_name]

        group_by_base = ['r', 'day']
        merge_on = ['m']

        if 'h' in df.columns: # if hours are in df
            merge_on += ['d']
            tmp_merge = all_frames['Idaytq_orig']
            group_by_base += ['y', 'h']
        else:
            tmp_merge = all_frames['Idaytq_orig'].drop(columns=['d']).groupby(['m', 'day']).agg('sum').reset_index()
        
        df = pd.merge(df, tmp_merge, on=merge_on, how='left')
        df.drop(columns=merge_on, inplace=True)
            
        # find weighted mean of value for each representative day    
        if method == 'wm':
            # weighted mean
            wm = lambda x: np.average(x, weights=df.loc[x.index, "Idaytq"])
            df = df.groupby(group_by_base + additional_groupby).agg(value=(df_name, wm)).reset_index()
            df.rename(columns={'value': df_name}, inplace=True)
        elif method == 'max':
            df = df.drop(columns=["Idaytq"]).groupby(group_by_base + additional_groupby).agg('max').reset_index()

        if 'h' in df.columns:
            # find sum of value aggregated over all representative hour-periods.
            # SolWindCapFactor value is later divided by number of hours in an hour-period (so it becomes an average)
            map_tmp = pd.merge(all_frames['Map'].drop(columns=['s']),
                               all_frames['Hour_map'],
                               on=['Hour_map'], how='left')

            df = pd.merge(df, map_tmp, on=['day', 'h'], how='left').drop(columns=['h', 'Hour_map', 'day'])
            
            if method == 'max':
                df = df.groupby(['r', 'y', 'hr'] + additional_groupby).agg('max').reset_index()
            else:
                df = df.groupby(['r', 'y', 'hr'] + additional_groupby).agg('sum').reset_index()

        return df

    timer.toc('temporal_mapping first bit')
    #Using the new day-type mappings to update the input data for load and solar/wind capacity factors
    all_frames['Load'] = create_h_col('Load', [])
    timer.toc('temporal_mapping Load')
    
    #Change SolWindCapFactor from 1-24 hours to 1-576 hours and remove d=3
    all_frames['SolWindCapFactor'] = pd.merge(all_frames['SolWindCapFactor'], 
                                              all_frames['Map_EcpGroup'], 
                                              on=['tech'], how='left').drop(columns='Map_EcpGroup')
    all_frames['SolWindCapFactor'] = create_h_col('SolWindCapFactor', ['tech', 'pt'])

    all_frames['SolWindCapFactor'] = pd.merge(all_frames['SolWindCapFactor'],
                                              all_frames['Hr_weights'].reset_index(),
                                              on=['hr'], how='left')
    all_frames['SolWindCapFactor']['SolWindCapFactor'] = (all_frames['SolWindCapFactor']['SolWindCapFactor'] /
                                                          all_frames['SolWindCapFactor']['Hr_weights'])
    all_frames['SolWindCapFactor'].drop(columns=['Hr_weights'], inplace=True)

    #remove PVhybrid as an option
    all_frames['SolWindCapFactor'] = all_frames['SolWindCapFactor'][all_frames['SolWindCapFactor']['pt'] != 21].reset_index(drop=True)
    timer.toc('temporal_mapping SolWindCapFactor')

    #Converting HydroCapFactor to be by day instead of month (because it could have multiple months in 1 day)
    all_frames['HydroCapFactor'] = create_h_col('HydroCapFactor', [])
    timer.toc('temporal_mapping HydroCapFactor')
    
    return all_frames

####################################################################################################################
def update_supply_data(all_frames,setin):
    """Updates to all_frames: Updating the supply curves and prices data and capacity factor data

    Parameters
    ----------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    setin : class
        contains sets used in the model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    """

    # Hard code for now. separating spring and fall for hydro can't store intra-seasonal,
    # so need to duplicate capacity for all techs
    def add_4th_season(df, s_name):
        tmp_df = df[df[s_name] == 3]
        tmp_df.loc[:, s_name] = 4
        df = pd.concat([df, tmp_df], ignore_index=True)
        return df

    all_frames['SupplyPrice'] = add_4th_season(all_frames['SupplyPrice'],'s')
    all_frames['SupplyCurve'] = add_4th_season(all_frames['SupplyCurve'],'s')
    all_frames['TranLimit'] = add_4th_season(all_frames['TranLimit'],'s')
    all_frames['TranLimitCan'] = add_4th_season(all_frames['TranLimitCan'],'loadgp')

    def create_second_step(frame):
        frame['steps'] = 2
        return frame

    #Add Hydro changes to SupplyCurve
    def add_hydro_supply_step(frame):
        frame = pd.concat([frame, create_second_step(frame[frame['pt'].isin(setin.pth)].copy())])
        return frame

    all_frames['SupplyPrice'] = add_hydro_supply_step(all_frames['SupplyPrice'])
    all_frames['SupplyCurve'] = add_hydro_supply_step(all_frames['SupplyCurve'])

    #overwrite hydro supply curves for step 1
    all_frames['SupplyCurve'] = pd.merge(all_frames['SupplyCurve'],
                                         all_frames['HydroDispatchablePortion'], 
                                         on=['r'], how='left')
    all_frames['SupplyCurve'].loc[((all_frames['SupplyCurve']['pt'].isin(setin.pth)) & (all_frames['SupplyCurve']['steps']==1)),'SupplyCurve'] \
        = all_frames['SupplyCurve']['SupplyCurve'] * all_frames['SupplyCurve']['HydroDispatchablePortion']

    #overwrite hydro supply curves for step 2
    all_frames['SupplyCurve'].loc[((all_frames['SupplyCurve']['pt'].isin(setin.pth)) & (all_frames['SupplyCurve']['steps']==2)),'SupplyCurve'] \
        = all_frames['SupplyCurve']['SupplyCurve'] * (1 - all_frames['SupplyCurve']['HydroDispatchablePortion'])
    all_frames['SupplyCurve'] = all_frames['SupplyCurve'].drop(columns=['HydroDispatchablePortion'])

    #remove PV hybrid capacity
    all_frames['SupplyCurve'] = all_frames['SupplyCurve'].loc[all_frames['SupplyCurve']['pt'] != 21]

    #Add custom changes to SupplyPrice
    def update_supplyprice(pt,step,price):
        all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==pt) & (all_frames['SupplyPrice']['steps']==step), \
                                      'SupplyPrice'] = price
        return all_frames['SupplyPrice']

    supply_price_updates = [[10, 1, 0.003], [10, 2, 0.003],[14, 1, 0.002],[15, 1, 0.002],[16, 1, 0.002],
                            [17, 1, 0.001],[18, 1, 0.001],[19, 1, 0.001],[20, 1, 0.001]]
    
    for pt_step_price in supply_price_updates: 
        update_supplyprice(pt_step_price[0], pt_step_price[1], pt_step_price[2])
        
    # set up first year capacity for learning.
    all_frames['SupplyCurve_learning'] = pd.merge(all_frames['SupplyCurve_learning'], 
                                                  all_frames['CapCost'], 
                                                  how='outer').drop(columns=['s','y','CapCost','r','steps']).rename(
                                                      columns={'SupplyCurve':'SupplyCurve_learning'}).groupby(['pt']).agg('sum').reset_index()
    
    # if cap = 0, set to minimum unit size (0.1 for now)
    all_frames['SupplyCurve_learning'].loc[all_frames['SupplyCurve_learning']['SupplyCurve_learning'] == 0.0,'SupplyCurve_learning'] = 0.01
    
    #duplicate H2curve for now #TODO: fix
    tmp = all_frames['H2Supply'].copy()
    for r in setin.r:
        if r != 7:
            tmp2 = tmp.copy()
            tmp2.loc[:,'r'] = r
            all_frames['H2Supply'] = pd.concat([all_frames['H2Supply'], 
                                               tmp2], 
                                               ignore_index=True)
    
    all_frames['H2Price'] = all_frames['H2Supply'].drop(columns=['H2Supply'])
    all_frames['H2Supply'].drop(columns=['H2Price'], inplace=True)

    return all_frames
    
####################################################################################################################
def update_builds_data(all_frames, setin):
    """Updates to all_frames: Updating the new capacity costs data

    Parameters
    ----------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    setin : class
        contains sets used in the model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    """
    # Update CapCosts to be by $/MW instead of $/kW and annualize
    # TODO: fix annualization factor
    all_frames['CapCost'].loc[:, 'CapCost'] = all_frames['CapCost']['CapCost'] * 1000

    # $/kw to $/MW
    all_frames['FOMCost'].loc[:, 'FOMCost'] = all_frames['FOMCost']['FOMCost'] * 1000


    # drop costs where builds aren't allowed
    all_frames['allowBuilds'] = all_frames['allowBuilds'][all_frames['allowBuilds']['allowBuilds'] == 1].reset_index(drop=True)
    all_frames['CapCost'] = pd.merge(all_frames['CapCost'], 
                                     all_frames['allowBuilds'],
                                     on=['pt','steps'], how='right').drop(columns=['allowBuilds'])

    all_frames['allowRet'] = all_frames['allowRet'][all_frames['allowRet']['allowRet'] == 1].reset_index(drop=True)

    # make this by region
    tmp_regs = pd.DataFrame(data = {'r':setin.r})
    all_frames['CapCost'] = pd.merge(tmp_regs, 
                                     all_frames['CapCost'],
                                     how='cross').reset_index(drop=True)

    all_frames['FOMCost'] = pd.merge(tmp_regs,
                                     all_frames['FOMCost'],
                                     how='cross').reset_index(drop=True)

    #save first year CapCost
    all_frames['CapCost_y0'] = all_frames['CapCost'].copy().rename(columns={'CapCost':'CapCost_y0'})

    # hardcode small cost decrease for now so LP isn't as degenerate
    def cost_decrease(y):
        y0 = setin.y[0]
        return 0.02 * (y - y0)

    # make this by year
    # TODO: will need to redo this when we introduce quadratic function
    tmp_y = pd.DataFrame(data = {'y':setin.y,
                                 'decrease':[cost_decrease(year) for year in setin.y]})
    all_frames['CapCost'] = pd.merge(tmp_y,
                                     all_frames['CapCost'],
                                     how='cross').reset_index(drop=True)
    # reduce cost by year so it doesn't build everything in first year
    all_frames['CapCost'].loc[:, 'CapCost'] = all_frames['CapCost']['CapCost'] * (1.0 - all_frames['CapCost']['decrease'])
    all_frames['CapCost'] = all_frames['CapCost'][['r', 'pt', 'y', 'steps', 'CapCost']]

    return all_frames
####################################################################################################################
def update_trade_data(all_frames,setin):
    """Updates to all_frames: Updating transmission and trade related data

    Parameters
    ----------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    setin : class
        contains sets used in the model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    """

    #Create sparse sets for trade subsets
    def create_master_trade_sets(name_df):
        df = pd.merge(all_frames[name_df],
                      all_frames['Map']).drop(columns=['Hour_map', 's', 'day'])
        return df

    #clean up TranLimitCan to make it by season
    all_frames['TranLimitCan'] = all_frames['TranLimitCan'][all_frames['TranLimitCan'].loadseg == 1]
    all_frames['TranLimitCan'].rename(columns={'loadgp': 's'}, inplace=True)
    all_frames['TranLimitCan'].drop(columns=['loadseg'], inplace=True)

    # split canadian transmission from US
    all_frames['TranCostCan'] = all_frames['TranCost'][(all_frames['TranCost']['r'].isin(setin.r_can_conn)) 
                                                       & (all_frames['TranCost']['r1'].isin(setin.r_can))]\
                                                           .rename(columns={'TranCost':'TranCostCan'})
                                                           
    all_frames['TranCost'] = all_frames['TranCost'][(all_frames['TranCost']['r1'].isin(setin.r)) 
                                                    & (all_frames['TranCost']['r'].isin(setin.r))
                                                    & (all_frames['TranCost']['CSteps'] == 1)].drop(columns=['CSteps'])

    all_frames['TranLineLimitCan'] = all_frames['TranLimit'][(all_frames['TranLimit']['r'].isin(setin.r_can_conn)) 
                                                             & (all_frames['TranLimit']['r1'].isin(setin.r_can))]\
                                                                 .rename(columns={'TranLimit':'TranLineLimitCan'})
                                                                 
    all_frames['TranLimit'] = all_frames['TranLimit'][(all_frames['TranLimit']['r1'].isin(setin.r)) 
                                                      & (all_frames['TranLimit']['r'].isin(setin.r))]

    # make trade parameters sparse
    all_frames['TranLineLimitCan'] = create_master_trade_sets('TranLineLimitCan')
    all_frames['TranLimitCan'] = create_master_trade_sets('TranLimitCan')

    return all_frames

####################################################################################################################
def update_opres_data(all_frames, setin):
    """Updates to all_frames: Updating operating reserve related data

    Parameters
    ----------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    setin : class
        contains sets used in the model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    """
    all_frames['ResTechUpperBound'] = pd.merge(all_frames['ResUpperBound'],
                                               all_frames['RampRateRes'],
                                               how='cross')
    all_frames['ResTechUpperBound'].loc[:, 'ResTechUpperBound'] = \
        np.minimum(1.0,
                   all_frames['ResTechUpperBound']['ResUpperBound']
        * all_frames['ResTechUpperBound']['RampRateRes'])

    all_frames['ResTechUpperBound'].drop(columns=['ResUpperBound', 'RampRateRes'], inplace=True)

    return all_frames
####################################################################################################################
def create_indexing(all_frames,setin):
    """Updates to all_frames: Updating indexing for parameters, makes them into sparse sets

    Parameters
    ----------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    setin : class
        contains sets used in the model

    Returns
    -------
    all_frames : dictionary
        dictionary of dataframes, input parameters for the model
    """

    #Create sparse sets for pt subsets 
    def create_master_pt_sets(pt_set):
        df = pd.merge(all_frames['SupplyCurve'][all_frames['SupplyCurve']['pt'].isin(pt_set)].dropna(),
                      all_frames['Map'],
                      on=['s'], how='left')
        return df

    time_drop = ['s','Hour_map','day']
    index_cols = ['pt','y','r','steps','hr']

    #apply sparse set function and drop columns and set indexes
    all_frames['RetSet'] = pd.merge(all_frames['SupplyCurve'].drop(columns=['s']),
                                    pd.merge(all_frames['allowBuilds'],
                                             all_frames['SupplyCurve'][['r','y']].drop_duplicates(), how='cross'),
                                    on = ['pt','steps','r','y'], how='outer').drop(columns = ['allowBuilds','SupplyCurve']).fillna(0)\
                                        .groupby(['r','pt','steps','y']).agg('mean').reset_index()

    all_frames['RetSet'] =  pd.merge(all_frames['RetSet'],
                                     all_frames['allowRet'],
                                     on = ['pt','steps'], how='inner').rename(columns={'allowRet':'RetSet'})
    
    all_frames['ptiUpperSet'] = create_master_pt_sets(setin.pti)
    all_frames['ptiUpperSet'] = pd.merge(all_frames['ptiUpperSet'], 
                                         all_frames['SolWindCapFactor'], 
                                         on=['r','y','pt','hr'], how='left')

    all_frames['ptiUpperSet'] = all_frames['ptiUpperSet'].drop(columns=time_drop+['tech', 'SupplyCurve']).fillna(0).set_index(index_cols)

    all_frames['RetSet'] = all_frames['RetSet'].set_index(['pt', 'y', 'r', 'steps'])
    
    def assign_paramindex(param):
        #create index list for parameter and set as df index
        index_list = list(all_frames[param].columns)
        index_list.remove(param)
        all_frames[param] = all_frames[param].set_index(index_list)
        #print(param,index_list)

    # Instantiate the Subsets class
    param_list = ['HydroCapFactor','Idaytq','Load', 'SupplyPrice','SupplyCurve','Dayweights',
                  'TranCost','TranCostCan','TranLimit','TranLineLimitCan','TranLimitCan','CapCost','CapCost_y0','FOMCost','allowBuilds','year_weights',
                  'RampUp_Cost','RampDown_Cost','RampRate','ResTechUpperBound','SupplyCurve_learning', 'H2Price', 'ReserveMargin']
    for param in param_list:
        assign_paramindex(param)

    return all_frames

####################################################################################################################
def keep_only_used_frames(all_frames):
    keep_list = ['allowBuilds',
                'SupplyCurve_learning',
                'CapCost',
                'CapCost_y0',
                'FOMCost',
                'Dayweights',
                'RetSet',
                'H2Price',
                'Hr_weights',
                'HydroCapFactor',
                'Idaytq',
                'Load',
                'Map_hr_s',
                'Map_day_s',
                'Map_hr_d',
                'year_weights',
                'ptiUpperSet',
                'ReserveMargin',
                'SupplyCurve',
                'SupplyPrice',
                'TradeCanSet',
                'TranCost',
                'TranCostCan',
                'TranLimit',
                'TranLimitCan',
                'TranLimitCanSet',
                'TranLineLimitCan',
                'RampUp_Cost',
                'RampDown_Cost',
                'RampRate',
                'ResTechUpperBound']
    
    newdict = all_frames.copy()
    for key in all_frames:
        if key not in keep_list:
            #print(key)
            del newdict[key]
    return newdict

def convert_back_to_dfs(all_frames):
    for key in all_frames:
        print(key)
        all_frames[key] = all_frames[key].reset_index()
        if all_frames[key].shape[0]==0:
            print('Check:',key, 'frame is empty') 
    return all_frames

####################################################################################################################
def preprocessor(setin):
    timer.tic('start')
    print('read_in_data')
    all_frames = read_in_data(setin)
    timer.toc('read_in_data')
    print()

    print('update_temporal_mapping')
    all_frames = update_temporal_mapping(all_frames,setin)
    timer.toc('update_temporal_mapping')
    print()

    print('everything else')
    all_frames = update_supply_data(all_frames,setin)
    all_frames = update_builds_data(all_frames, setin)
    all_frames = update_trade_data(all_frames,setin)
    all_frames = update_opres_data(all_frames,setin)
    all_frames = create_indexing(all_frames,setin)
    all_frames = keep_only_used_frames(all_frames)
    timer.toc('everything else')
    return all_frames, setin

####################################################################################################################
if __name__ == "__main__":

    #Build sets used for model
    years=list(pd.read_csv('../input/sw_year.csv')['year'])
    regions = list(pd.read_csv('../input/sw_reg.csv')['region'])

    test_years = list(pd.read_csv('../input/sw_year.csv').dropna()['year'])
    test_regions = list(pd.read_csv('../input/sw_reg.csv').dropna()['region'])

    #Test switch
    test = 0
    if test == 1:
        years = test_years
        regions = test_regions

    setA = pp.Sets(years,regions)

    #creates the initial data
    all_frames, setA = preprocessor(setA)

    #for key in all_frames:all_frames[key].to_csv('../input/cem_inputs/'+key+'.csv')
    for key in all_frames:all_frames[key].to_csv('../input/temp/'+key+'.csv')
    print('done')    

