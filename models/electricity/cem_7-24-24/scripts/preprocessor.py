####################################################################################################################
####################################################################################################################
#PRE-PROCESSING
####################################################################################################################
####################################################################################################################
    
#Setup

#Import pacakges
import pandas as pd
import numpy as np
import os
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

#temp switch to load data from csvs(0) or from bd(1)
db_switch = 0

####################################################################################################################
class Sets:

    def __init__(self,years,regions):

        #Scenario Descriptor
        setup_table = pd.read_csv('../input/scedes.csv',index_col=0)

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

        #Temporal Sets
        
        #Temporal Sets - Years
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

        #Temporal Sets - Seasons and Days
        sd_file = pd.read_csv('../input/sw_s_day.csv')
        self.s = range(1, sd_file['Map_s'].max()+1) #Season
        self.num_days = sd_file['Map_day'].max() #number of days
        self.day = range(1, self.num_days + 1) #Day #model solves with specified number of days

        #Temporal Sets - Hours
        hr_file = pd.read_csv('../input/sw_hr.csv')
        self.num_hr_day = hr_file['Map_hr'].max() #number of periods in a day
        self.num_hr = self.num_hr_day * self.num_days
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
        load_and_assign_subsets('../input/pt_subsets.csv', pt_subsets)
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
#functions to read in and setup parameter data

### Load csvs
def readin_csvs(all_frames):
    csv_dir = '../input/cem_inputs/'
    for filename in os.listdir(csv_dir):
        #print(filename[:-4])
        f = os.path.join(csv_dir, filename)
        if os.path.isfile(f):
            all_frames[filename[:-4]] = pd.read_csv(f)
            #print(filename[:-4],all_frames[filename[:-4]].columns)
    
    return all_frames

### Load table from SQLite DB
def readin_sql(all_frames):
    db_dir = '../input/cem_inputs_database.db'
    engine = create_engine('sqlite:///'+db_dir)
    Session = sessionmaker(bind=engine)
    session = Session()

    Base = automap_base()
    Base.prepare(autoload_with=engine)
    metadata = MetaData()
    metadata.reflect(engine)

    for table in metadata.tables.keys():
        all_frames[table] = load_data(table,metadata,engine)
        all_frames[table] = all_frames[table].drop(columns=['id'])

    session.close()
    
    return all_frames    

def load_data(tablename,metadata,engine):
    table = Table(tablename, metadata, autoload_with = engine)
    query = select(table.c).where()
    
    with engine.connect() as connection:
        result = connection.execute(query)
        df = pd.read_sql(query, connection)

    return df

def temporal_mapping():
    df1 = pd.read_csv('../input/sw_s_day.csv')
    df4 = df1.groupby(by=['Map_day'],as_index=False).count()
    df4 = df4.rename(columns={'Index_day':'Dayweights'}).drop(columns=['Map_s'])
    df1 = pd.merge(df1,df4,how='left',on=['Map_day'])

    df2 = pd.read_csv('../input/sw_hr.csv')
    df3 = df2.groupby(by=['Map_hr'],as_index=False).count()
    df3 = df3.rename(columns={'Index_hr':'Hr_weights'})
    df2 = pd.merge(df2,df3,how='left',on=['Map_hr'])

    df = pd.merge(df1,df2,how='cross')
    df['hr'] = df.index
    df['hr'] = df['hr'] + 1
    df['Map_hr'] = (df['Map_day'] - 1) * df['Map_hr'].max() + df['Map_hr']
    #df.to_csv('../input/temporal_map.csv',index=False)
    
    return df

def subset_dfs(all_frames, setin, i):
    for key in all_frames:
        if i in all_frames[key].columns:
            all_frames[key] = all_frames[key].loc[all_frames[key][i].isin(getattr(setin,i))]
    
    return all_frames

# Function to fill in the subset values
def fill_values(row, subset_list):
    if row in subset_list:
        return row
    for i in range(len(subset_list) - 1):
        if subset_list[i] < row < subset_list[i + 1]:
            return subset_list[i+1]
    return subset_list[-1]

def avg_by_group(df,set_name,map_frame):
    map_df = map_frame.copy()
    df = df.sort_values(by=list(df[:-1]))
    #print(df.tail())
    
    #location of y column and list of cols needed for the groupby
    pos = df.columns.get_loc(set_name)
    map_name = 'Map_'+set_name
    groupby_cols = list(df.columns[:-1])+[map_name]
    groupby_cols.remove(set_name)

    #group df by year map data and update y col
    df[set_name] = df[set_name].astype(int)
    df = pd.merge(df,map_df,how='left',on=[set_name])
    df = df.groupby(by=groupby_cols,as_index=False).mean()
    df[set_name] = df[map_name].astype(int)
    df = df.drop(columns=[map_name]).reset_index(drop=True)

    #move back to original position
    y_col = df.pop(set_name)
    df.insert(pos, set_name, y_col) 
    
    #used to qa
    df = df.sort_values(by=list(df[:-1]))
    #print(df.tail())
    
    return df

def preprocessor(setin):

    #read in raw data
    all_frames = {}
    if db_switch == 0:
        # add csv input files to all frames 
        all_frames = readin_csvs(all_frames)
    elif db_switch==1:
        # add sql db tables to all frames 
        all_frames = readin_sql(all_frames)

    #reshaping load df to long format
    r_tot = len(all_frames['Load'].columns)-2
    all_frames['Load'] = pd.melt(
        all_frames['Load'], 
        id_vars=list(all_frames['Load'].columns)[:-r_tot], var_name='r', value_name='Load', 
        value_vars=map(str, ['r' + str(n) for n in list(range(1,r_tot+1))]), ignore_index=True)
    all_frames['Load']['r'] = all_frames['Load']['r'].str.replace('r','').astype(int)
    all_frames['Load'] = all_frames['Load'][['r','y','hr','Load']]
    
    #international trade sets
    r_file = all_frames['TranLineLimitCan'][['r','r1']].drop_duplicates()
    r_file = r_file[r_file['r'].isin(setin.r)]
    setin.r_can_conn = list(r_file['r'].unique())
    setin.r_can = list(r_file['r1'].unique())
    setin.r1 = setin.r + setin.r_can

    #create temporal mapping df
    temporal = temporal_mapping()
    y_map = pd.DataFrame({'y': [setin.y0]+list(setin.solve_range)})
    y_map['Map_y'] = y_map['y'].apply(lambda x: fill_values(x, setin.y))
    #print(y_map)
    
    #TODO: update year weights 
    all_frames['year_weights'] = setin.year_weights

    #subset df by region
    all_frames = subset_dfs(all_frames, setin, 'r')
    all_frames = subset_dfs(all_frames, setin, 'r1')
    
    #last year values used
    filter_list = ['CapCost']
    for key in filter_list:
        all_frames[key] = all_frames[key].loc[all_frames[key]['y'].isin(getattr(setin,'y'))]

    #average values in years/hours used
    for key in all_frames.keys():
        #print(key,all_frames[key].columns)
        if 'y' in all_frames[key].columns:
            all_frames[key] = avg_by_group(all_frames[key],'y',y_map)
            #print(all_frames[key].tail())
        if 'hr' in all_frames[key].columns:
            all_frames[key] = avg_by_group(all_frames[key],'hr',temporal[['hr','Map_hr']])
            #print(all_frames[key].tail())

    #create temporal mapping parameters
    all_frames['Map_day_s'] = temporal[['Map_day','Map_s']].rename(columns={'Map_day':'day','Map_s':'s'}).drop_duplicates()
    all_frames['Map_hr_d'] = temporal[['Map_hr','Map_day']].rename(columns={'Map_day':'day','Map_hr':'hr'}).drop_duplicates()
    all_frames['Map_hr_s'] = temporal[['Map_hr','Map_s']].rename(columns={'Map_hr':'hr','Map_s':'s'}).drop_duplicates()
    all_frames['Hr_weights'] = temporal[['Map_hr','Hr_weights']].copy().rename(columns={'Map_hr':'hr'}).drop_duplicates()
    all_frames['Dayweights'] = temporal[['Map_hr','Dayweights']].copy().rename(columns={'Map_hr':'hr'}).drop_duplicates()
    all_frames['Idaytq'] = temporal[['Map_day','Dayweights']].copy().rename(columns={'Map_day':'day','Dayweights':'Idaytq'}).drop_duplicates()

    #using same pti capacity factor for all model years and reordering columns
    all_frames['ptiUpperSet'] = pd.merge(all_frames['ptiUpperSet'],y_map[['Map_y']].drop_duplicates(),how='cross')
    all_frames['ptiUpperSet'] = all_frames['ptiUpperSet'].rename(columns={'Map_y':'y'})
    all_frames['ptiUpperSet'] = all_frames['ptiUpperSet'][['pt','y','r','steps','hr','SolWindCapFactor']]
    #print(all_frames['ptiUpperSet'].head(2))
    #print(all_frames['ptiUpperSet'].shape[0])

    #Update load to be the total demand in each time segment rather than the average
    all_frames['Load'] = pd.merge(all_frames['Load'],all_frames['Hr_weights'],how='left',on=['hr'])
    all_frames['Load']['Load'] = all_frames['Load']['Load'] * all_frames['Load']['Hr_weights']
    all_frames['Load'] = all_frames['Load'].drop(columns=['Hr_weights'])

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
    
    # Extract regions with the ability to trade
    setin.trade_regs = all_frames['TranLimit']['r'].unique()

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

    makedir('../output/inputs/')

    years = list(pd.read_csv('../input/sw_year.csv').dropna()['year'])
    regions = list(pd.read_csv('../input/sw_reg.csv').dropna()['region'])

    #Build sets used for model
    all_frames = {}
    setA = Sets(years,regions)

    #creates the initial data
    all_frames, setB = preprocessor(setA)
    for key in all_frames:
        #print(key,list(all_frames[key].reset_index().columns))
        all_frames[key].to_csv('../output/inputs/'+key+'.csv')
