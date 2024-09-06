####################################################################################################################
####################################################################################################################
#PRE-PROCESSING
####################################################################################################################
####################################################################################################################

# TODO: ID frames that are the same for all years
# Idaytq (but not in restprep), Idaytq_orig, Idaytqset
# in restprep already: Map_EcpGroup, map_plantsteps, RampRate, Map_day, Map_ms, Hour_map, UnmetLoad_penalty, 
#                       HydroDispatchablePortion, HourstoBuy, BatteryEfficiency,
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

from datetime import datetime
import numpy as np
import pandas as pd
import pyomo.environ as pyo
import gc
import highspy
from pyomo.common.timing import TicTocTimer
import os
from pathlib import Path
from definitions import PROJECT_ROOT
data_root = Path(PROJECT_ROOT, 'src/models')
#from sqlalchemy import create_engine, MetaData, Table, select
#from sqlalchemy.ext.automap import automap_base
#from sqlalchemy.orm import sessionmaker

#temp switch to load data from csvs(0) or from bd(1)
db_switch = 0
#os.chdir('') 

####################################################################################################################
class Sets:

    def __init__(self,years,regions):

        #Scenario Descriptor
        #(PROJECT_ROOT / 'src/models/electricity/input/cem_inputs/SupplyPrice.csv')
        setup_table = pd.read_csv(PROJECT_ROOT / 'electricity/input/scedes.csv',index_col=0)

        #Switches Sets
        self.sw_trade =     int(setup_table.at['sw_trade', 'value'])
        self.sw_expansion = int(setup_table.at['sw_expansion', 'value'])
        self.sw_agg_years = int(setup_table.at['sw_agg_years', 'value'])
        self.sw_rm =        int(setup_table.at['sw_rm', 'value'])
        self.sw_ramp =      int(setup_table.at['sw_ramp', 'value'])
        self.sw_reserves =  int(setup_table.at['sw_reserves', 'value'])
        self.sw_learning =  int(setup_table.at['sw_learning', 'value'])
        
        #Regional Sets
        self.r = regions
        self.n_regions = len(self.r)
        r_file = pd.read_csv(PROJECT_ROOT / 'electricity/input/r_can_line.csv')
        r_file = r_file[r_file['r'].isin(self.r)]
        self.r_can_conn = list(r_file['r'].unique())
        self.r_can = list(r_file['r_can'].unique())
        self.r1 = self.r + self.r_can

        #Temporal Sets
        self.y = years
        self.start_year = self.y[0]
        self.all_years_init = pd.DataFrame({'y': self.y})
        if self.sw_agg_years and len(self.y) > 1:
            self.y0 = self.start_year
            self.solve_range = range(self.start_year+1, self.y[-1]+1)
            self.all_years = pd.DataFrame({'y': [self.y0]+list(self.solve_range)})
        else:
            self.y0 = self.y[0]
            self.solve_range = self.y[1:]
            self.all_years = self.all_years_init

        all_years_list = [self.start_year]+list(self.solve_range)
        solve_array = np.array(self.y)
        mapped_list = [solve_array[solve_array >= year].min() for year in all_years_list]
        self.year_map = pd.DataFrame({'y_real': all_years_list, 'y': mapped_list})
        self.year_weights = self.year_map.groupby(['y']).agg('count').reset_index().rename(columns={'y_real': 'year_weights'})

        #TODO: HARDCODING VALUES NEED TO UDPATE
        self.s = range(1, 5) #Season
        self.num_months = 12 #number of months
        self.num_hr_day = 4 #number of periods in a day
        self.num_days = 24 #number of days
        self.num_hr = self.num_hr_day * self.num_days

        self.m = range(1, self.num_months + 1)  # Month
        self.day = range(1, self.num_days + 1) #Day #model solves with specified number of days
        self.h = range(1, self.num_hr_day+1) #hours in a day
        self.hr = range(1, self.num_days*len(self.h)+1)   #Number of hours the model solves for: days x number of periods per day
        self.hr1 = range(1, self.num_days*len(self.h)+1, len(self.h)) #First hour of the day #SubsetOf: HR;
        self.hr23 = list(set(self.hr) - set(self.hr1)) #All hours that are not the first hour

        # Technology Sets
        class Subsets:
            pass

        def load_and_assign_subsets(filename, container):
            # read in subset dataframe from inputs
            df = pd.read_csv(filename)

            # set attributes for the master list
            master = list(df.columns)[0]
            setattr(container, master, list(df[master]))

            # Iterate through each unique subset
            for subset in df.columns:
                setattr(container, subset, list(df[df[subset].notna()][master]))

        pt_subsets = Subsets()
        load_and_assign_subsets(PROJECT_ROOT / 'electricity/input/pt_subsets.csv', pt_subsets)
        self.pt = getattr(pt_subsets, 'pt')
        self.ptc = getattr(pt_subsets, 'ptc')
        self.ptr = getattr(pt_subsets, 'ptr')
        self.pth = getattr(pt_subsets, 'pth')
        self.pth2 = getattr(pt_subsets, 'pth2')
        self.pts = getattr(pt_subsets, 'pts')
        self.pti = getattr(pt_subsets, 'pti')
        self.ptw = getattr(pt_subsets, 'ptw')
        self.ptsol = getattr(pt_subsets, 'ptsol')
        self.ptg = getattr(pt_subsets, 'ptg')
        self.ptd = getattr(pt_subsets, 'ptd')

        #Other Sets
        self.steps = range(1, 4)  # Steps within the supply curves #Note: number of steps varies by technology
        self.CSteps = range(1, 5)
        self.TransLoss = 0.02
        self.restypes = [1,2,3] # reserve types, 1=spinning, 2=regulation, 3=flex
        self.H2_heatrate = 13.84 #13.84 kwh/kg, for kwh/kg H2 -> 54.3 


####################################################################################################################
#subsets the data by region
def readin_csvs(dir,all_frames):
    for filename in os.listdir(dir):
        #print(filename[:-4])
        f = os.path.join(dir, filename)
        if os.path.isfile(f):
            all_frames[filename[:-4]] = pd.read_csv(f)
            #print(filename[:-4],all_frames[filename[:-4]].columns)
    
    return all_frames

def subset_dfs(all_frames, setin, i):
    for key in all_frames:
        if i in all_frames[key].columns:
            all_frames[key] = all_frames[key].loc[all_frames[key][i].isin(getattr(setin,i))]
    
    return all_frames

### Load table from SQLite DB
def load_data(tablename,metadata,engine):
    table = Table(tablename, metadata, autoload_with = engine)
    query = select(table.c).where()
    
    with engine.connect() as connection:
        result = connection.execute(query)
        df = pd.read_sql(query, connection)

    return df

def preprocessor(setin,dir):
    all_frames = {}

    if db_switch == 0:
        # add csv input files to all frames 
        all_frames = readin_csvs(dir, all_frames)
    elif db_switch==1:
        db_dir = 'src/models/electricity/input/cem_inputs_database.db'
        engine = create_engine('sqlite:///'+db_dir)
        Session = sessionmaker(bind=engine)
        session = Session()

        Base = automap_base()
        Base.prepare(autoload_with=engine)
        metadata = MetaData()
        metadata.reflect(engine)

        all_frames = {}
        for table in metadata.tables.keys():
            all_frames[table] = load_data(table,metadata,engine)
            all_frames[table] = all_frames[table].drop(columns=['id'])

        session.close()

    #subset df by region
    all_frames = subset_dfs(all_frames, setin, 'r')
    all_frames = subset_dfs(all_frames, setin, 'r1')
    
    #year mapping

    #last year values used
    filter_list = ['CapCost']
    for key in filter_list:
        all_frames[key] = all_frames[key].loc[all_frames[key]['y'].isin(getattr(setin,'y'))]

    # Function to fill in the subset values
    def fill_values(row, subset_list):
        if row in subset_list:
            return row
        for i in range(len(subset_list) - 1):
            if subset_list[i] < row < subset_list[i + 1]:
                return subset_list[i+1]
        return subset_list[-1]

    #create the y_map df
    y_map = pd.DataFrame({'y': [setin.y0]+list(setin.solve_range)})
    y_map['y_map'] = y_map['y'].apply(lambda x: fill_values(x, setin.y))
    #print(y_map)
    all_frames['year_weights'] = pd.merge(all_frames['year_weights'],y_map,how='left',on=['y'])
    all_frames['year_weights'] = all_frames['year_weights'].groupby(by='y_map',as_index=False).sum()
    all_frames['year_weights']['y'] = all_frames['year_weights']['y_map']
    all_frames['year_weights'] = all_frames['year_weights'].drop(columns=['y_map']).reset_index(drop=True)

    #average values in years used
    for key in all_frames:
        if 'y' in all_frames[key].columns:
            #used to qa
            all_frames[key] = all_frames[key].sort_values(by=list(all_frames[key][:-1]))
            #print(all_frames[key].tail())
            
            #location of y column and list of cols needed for the groupby
            y_pos = all_frames[key].columns.get_loc('y')
            groupby_cols = list(all_frames[key].columns[:-1])+['y_map']
            groupby_cols.remove('y')

            #group df by year map data and update y col
            all_frames[key] = pd.merge(all_frames[key],y_map,how='left',on=['y'])
            all_frames[key] = all_frames[key].groupby(by=groupby_cols,as_index=False).mean()
            all_frames[key]['y'] = all_frames[key]['y_map']
            all_frames[key] = all_frames[key].drop(columns=['y_map']).reset_index(drop=True)

            #move back to original position
            y_col = all_frames[key].pop('y')
            all_frames[key].insert(y_pos, 'y', y_col) 
            
            #used to qa
            all_frames[key] = all_frames[key].sort_values(by=list(all_frames[key][:-1]))
            #print(all_frames[key].tail())

    #Recalculate Supply Curve Learning

    # save first year of supply curve summer capacity for learning
    all_frames['SupplyCurve_learning'] = all_frames['SupplyCurve'][(all_frames['SupplyCurve']['y'] == setin.start_year) 
                                                                   & (all_frames['SupplyCurve']['s'] == 2)]
    
    # set up first year capacity for learning.
    all_frames['SupplyCurve_learning'] = pd.merge(all_frames['SupplyCurve_learning'], 
                                                  all_frames['CapCost'], 
                                                  how='outer').drop(columns=['s','y','CapCost','r','steps']).rename(
                                                      columns={'SupplyCurve':'SupplyCurve_learning'}).groupby(['pt']).agg('sum').reset_index()
    
    # if cap = 0, set to minimum unit size (0.1 for now)
    all_frames['SupplyCurve_learning'].loc[all_frames['SupplyCurve_learning']['SupplyCurve_learning'] == 0.0,'SupplyCurve_learning'] = 0.01

    #
    for key in all_frames:
        index = list(all_frames[key].columns[:-1]) 
        all_frames[key] = all_frames[key].set_index(index)

    return all_frames, setin

####################################################################################################################
if __name__ == "__main__":
    
    def makedir(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    makedir(PROJECT_ROOT / 'electricity/output/inputs/')
    makedir(PROJECT_ROOT / 'electricity/output/temp/')    

    years = list(pd.read_csv(PROJECT_ROOT / 'electricity/input/sw_year.csv').dropna()['year'])
    regions = list(pd.read_csv(PROJECT_ROOT / 'electricity/input/sw_reg.csv').dropna()['region'])

    #Build sets used for model
    all_frames = {}
    setA = Sets(years,regions)

    #creates the initial data
    all_frames, setB = preprocessor(setA,PROJECT_ROOT / 'electricity/input/cem_inputs/')
    for key in all_frames:
        all_frames[key].to_csv(PROJECT_ROOT / 'electricity/input'+key+'.csv')

    #reviews current test data
    all_frames = {}
    all_frames, setC = preprocessor(setA,PROJECT_ROOT / 'electricity/input/temp/')
    for key in all_frames:
        all_frames[key].to_csv(PROJECT_ROOT / 'electricity/output/temp/'+key+'.csv')

    new = {}
    for filename in os.listdir(PROJECT_ROOT / 'electricity/output/temp/'):
        #print(filename[:-4])
        f = os.path.join(PROJECT_ROOT / 'electricity/output/temp/', filename)
        if os.path.isfile(f):
            new[filename[:-4]] = pd.read_csv(f)

    old = {}
    for filename in os.listdir(PROJECT_ROOT / 'electricity/output/inputs/'):
        #print(filename[:-4])
        f = os.path.join(PROJECT_ROOT / 'electricity/output/inputs/', filename)
        if os.path.isfile(f):
            old[filename[:-4]] = pd.read_csv(f)
            #print(filename[:-4],all_frames[filename[:-4]].columns)

    for key in new.keys():
        col_name = (new[key].columns[-1])
        new[key] = new[key].rename(columns={col_name:col_name+'_2'})
        old[key] = pd.merge(old[key],new[key],how='left')
        n=3
        old[key] = old[key].round({col_name: n, col_name+'_2': n})
        old[key]['check'] = old[key][col_name] - old[key][col_name+'_2']
        old[key] = old[key][old[key]['check']!=0]
        if old[key].shape[0]!=0:
            print(key,old[key].shape[0],'out of',new[key].shape[0])
            print(old[key])
            #print(old[key]['pt'].unique())