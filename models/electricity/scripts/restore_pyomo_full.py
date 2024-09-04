#Electricity Dispatch Model - Based on Restore Module within NEMS

####################################################################################################################
#Setup

#Measuring the run time of code
from datetime import datetime
start_time = datetime.now()

#Import pacakges
import numpy as np
import pandas as pd
import re
import pyomo.environ as pyo
import highspy
#import ipopt
from itertools import product
import os
from pyomo.common.timing import report_timing
from pyomo.common.timing import TicTocTimer

cwd = os.getcwd()
#print(cwd)

#Tic Toc Timer
timer = TicTocTimer()
timer.tic('start')

#Test switch
#when set to zero model solves for all regions, else set to number region you want to examine (between 1 to 25)
test_region = 0

#Print switch
#set this to one if you want to export to CSV some variables results
print_switch = 0

#Note: updated the code to use pyo. for all pyomo related functions, but something is still not working in my print statements, I will fix later
if print_switch == 1: from pyomo.environ import *

####################################################################################################################
####################################################################################################################
#PRE-PROCESSING
####################################################################################################################
####################################################################################################################

#Sets

#Region #Note: there is a switch at the start of this code for test_region, set to zero to solve for all regions
if test_region == 0: r = range(1,26) 
else: r = [test_region]

#Temporal Related Sets
y = [int(open('../input/ECPYEAR.txt', 'r').read())] #Year
s = range(1,4)                          #Season
m = range(1,13)                         #Month 
dm = range(1,3)                         #DayPerMon #Number of days per month to solve the problem (weekend/weekday)
d = range(1,4)                          #DayType #Note: there are two days/month used in this model, but some inputs include three days/month (weekend/weekday/peak)
hr = range(1,577)                       #Number of hours the model solves for: 12 months x 2 day types x 24 hours
hr1 = range(1, 577, 24)                 #First hour of the day #SubsetOf: HR;
hr23 = list(set(hr) - set(hr1))         #All hours that are not the first hour, Note: this is not apart of the original AIMMS code
h = range(1,25)                         #hours in a day

#Technology Related Sets
pt = range(1,24)                        #technology type 
pts = [11, 13, 21]                      #Storage_Group #SubsetOf: PT; #Note: 11 = Pumped Hydro; 13 = Battery; 21 = PV+Battery Hybrid
ptn = [11, 13]                          #Storage_noPV_Group #SubsetOf: Storage_Group;
ptpvb = [21]                            #PVBatt_Group #SubsetOf: Storage_Group;
ptc = [1, 2, 3, 4, 5, 6, 23]            #Conventional_Group #SubsetOf: PT;
ptr = [7, 8, 9, 10, 12, 22]             #Renewable_Group #SubsetOf: PT;
ptipv = [14, 15, 16, 17, 18, 19, 20, 21] #Intermittent_PVBatt_Group #SubsetOf: PT;
pti = [14, 15, 16, 17, 18, 19, 20]      #Intermittent_Group #SubsetOf: Intermittent_PVBatt_Group;
pth = [10]                              #Hydro_Group #SubsetOf: Renewable_Group;
ti = [70, 71, 72, 73, 74, 75, 76, 77]   #Intermittent_technology #SubsetOf: ECPtype; these are the technology codes from the NEMS model
steps = range(1,4)                      #Steps within the supply curves #Note: number of steps varies by technology

#Technology Code Names (not a set, but used in post-processing) Useful here as a reference
names =[[1, 'Coal'],    [2, 'Steam'],   [3, 'Turbine'], [4, 'CC'],      [5, 'FuelC'],   [6, 'Nuclear'], [7, 'Biomass'], 
        [8, 'Geother'], [9, 'MSW'],     [10, 'Hydro'],  [11, 'Storage'],[12, 'P2'],     [13, 'Storage'],[14, 'Wind'],   [15, 'Wind'],   
        [16, 'Wind'],   [17, 'Solar'],  [18, 'Solar'],  [19, 'Solar'],  [20, 'Solar'],  [21, 'Solar'],  [22, 'OtherIn'],[23, 'DistGen'] ]
names = pd.DataFrame(names, columns=['pt', 'technology'])

####################################################################################################################
#Function to read in data

#Read the text file into a string
def read_inputs(file_path):
    with open(file_path, 'r') as file:
        data = file.read()

    #Split the text by semicolon (;)
    sections = data.split(';')

    #Initialize a list to store DataFrames
    dataframes = []
    index_set = set()
    param_df_list = []
    param_single_list = []

    #Loop through the sections and create DataFrames
    for section in sections:
        section = section.strip()
        if section:
            #Check if it's a composite table or single parameter assignment
            if 'COMPOSITE TABLE' in section:
                table_lines = section.strip().split('\n')

                #Create a list of lines that contain the table data
                table_data_lines = [line.strip() for line in table_lines[1:] if line.strip()]

                #Create a DataFrame directly from the list of lines
                df = pd.DataFrame([line.split() for line in table_data_lines])

                #Set the column names
                df.columns = df.iloc[0].tolist()
                df = df.iloc[1:].apply(pd.to_numeric)

                #Rename some columns
                if 'year' in df.columns: df.rename(columns={'year':'y'}, inplace=True)
                if 'Steps' in df.columns: df.rename(columns={'Steps':'steps'}, inplace=True)
                if 'tech' in df.columns: df.rename(columns={'tech':'ti'}, inplace=True)

                #Set the table name
                table_name = df.columns[-1]

                #Append the DataFrame to the list
                dataframes.append((table_name, df))

                #creates lists of all the parameters and sets that are read in
                param_df_list.extend([df.columns[-1]])
                index_set.update(df.columns[0:-1])
                
            else:
                #If it's a single parameter assignment, split by ':=' to extract the parameter name and value
                param_name, param_value = [part.strip() for part in section.split(':=')]
                param_df = pd.DataFrame({param_name: [param_value]})
                dataframes.append((param_name, param_df))
                param_single_list.extend([param_name])

    return dataframes, index_set, param_df_list, param_single_list

####################################################################################################################
#Read in data

#read in input/restprep using read_inputs function; this input doesn't change over time
i_set = set()
p_list = []
file_path = '../input/restprep.txt'
restprep, i_set, p_list, p1_list = read_inputs(file_path)

#read in toAIMMS/ecpout using read_inputs function; this input is updated each year
i_set2 = set()
p_list2 = []
file_path = '../input/toAIMMS/ecpout_' + str(y[0]) + '.txt'
ecpout, i_set2, p_list2, p1_list2 = read_inputs(file_path)

#Manual updates to i and  p lists
i_set.update(i_set2)
i_set = i_set - {'RampUp_Cost','Segment_ECP', 'SupplyCurve', 'Map_PlantSteps', 'Group_ECP', 'EMMSegment', 'EMMGroup'}
#print(i_set)

p_list.extend(p_list2)
#print(p_list)

p1_list.extend(p1_list2)
#print(p1_list)

all_tables = dict(restprep + ecpout)

#creates parameters from input data (tables), loops through the data that were read in from the files
#Note: in this loop I create a full index, this seems to be an area where sparse indexing could be applied?
for param in p_list: 
    vars()[param] = all_tables[param]
    temp = pd.DataFrame([[1]], columns=['key'])

    #creates full index for the read in data to merge on to 
    for index in sorted(list(i_set & set(vars()[param].columns))):
        #print(len(vars()[index]))
        temp1 = (pd.DataFrame(vars()[index])).rename(columns={0:index})
        temp = pd.merge(temp,temp1,how='cross')
    vars()[param] = pd.merge(temp,vars()[param],how='left').drop(columns='key').fillna(0)
    #vars()[param].to_csv('../output/parameters/'+param+'.csv',index=False)

    #print(param, vars()[param].columns)
    #print(len(vars()[param]))
    #print()

#creates parameters from input data (single values), loops through the data that were read in from the files
for param in p1_list: 
    globals()[param] =  float(all_tables[param].iloc[0,0])
    #print(param,"=",globals()[param])
#print()

#these were in one dataframe, making them into separate frames here 
RampUp_Cost = RampDown_Cost.drop(columns=['RampDown_Cost']).copy()
RampDown_Cost = RampDown_Cost.drop(columns=['RampUp_Cost'])

Map_PlantSteps = M864_LF.drop(columns=['M864_LF']).copy()
M864_LF = M864_LF.drop(columns=['Map_PlantSteps'])

SupplyCurve = SupplyPrice.drop(columns=['SupplyPrice']).copy()
SupplyPrice = SupplyPrice.drop(columns=['SupplyCurve'])

EMMGroup = Load.copy().drop(columns=['EMMSegment', 'Group_ECP', 'Segment_ECP', 'Load'])
EMMSegment = Load.copy().drop(columns=['EMMGroup', 'Group_ECP', 'Segment_ECP', 'Load'])
Group_ECP = Load.copy().drop(columns=['EMMGroup', 'EMMSegment', 'Segment_ECP', 'Load'])
Segment_ECP = Load.copy().drop(columns=['EMMGroup', 'EMMSegment', 'Group_ECP', 'Load'])
Load = Load.copy().drop(columns=['EMMGroup', 'EMMSegment', 'Group_ECP', 'Segment_ECP'])

####################################################################################################################
#Update data
#Updating the day-type mapping (this model solves for two day-types per month, input data includes three day-types per month)

#creating the new day-type mapping frame for month, day, and hour
d_dm_list = [(1,2),(2,1)]
Map_Daypattern = pd.DataFrame(list(product(m, d_dm_list)), columns=['m', 'd,dm'])
Map_Daypattern[['d', 'dm']] = pd.DataFrame(Map_Daypattern["d,dm"].to_list(), columns=['d', 'dm'])
Map_Daypattern = Map_Daypattern.drop(columns=['d,dm'])
Map_Daypattern['Map_Daypattern'] = 1
#print(Map_Daypattern)

Map_mdmh = pd.DataFrame(list(product(m, dm, h)), columns = ['m', 'dm', 'h'])
Map_mdmh['hr'] = Map_mdmh.index + 1
Map_mdmh = pd.merge(Map_mdmh,Map_Daypattern,on=['m', 'dm'],how='left').drop(columns=['Map_Daypattern'])

#More temporal mapping frames, different combinations of season, month, day, and hour
Map_MonthHour = Map_mdmh[['m','hr']].copy()
Map_MonthHour['Map_MonthHour'] = 1
temp = pd.DataFrame(list(product(m, hr)), columns = ['m', 'hr'])
Map_MonthHour = pd.merge(temp,Map_MonthHour,on=['m','hr'],how='left').fillna(0)

Map_Daytype_Hour = Map_mdmh[['d','hr']].copy()
Map_Daytype_Hour['Map_Daytype_Hour'] = 1
temp = pd.DataFrame(list(product(d, hr)), columns = ['d', 'hr'])
Map_Daytype_Hour = pd.merge(temp,Map_Daytype_Hour,on=['d','hr'],how='left').fillna(0)

Map_SeasonHour = pd.merge(Map_mdmh[['m','hr']],Map_ms,on=['m'],how='left').rename(columns={'Map_ms':'Map_SeasonHour'}).drop(columns=['m'])

#Using the new day-type mappings to update the input data for load and solar/wind capacity factors
Load_EMMRen = pd.merge(Map_mdmh,Load,on=['m','d','h'],how='left').drop(columns=['m','d','h','dm']).sort_values(by=['r','hr']).rename(columns={'Load':'Load_EMMRen'})

SolWinCapFactor_ER = pd.merge(Map_mdmh,SolWindCapFactor,on=['m','d','h'],how='left').drop(columns=['m','d','dm','h']).sort_values(by=['r','ti','hr'])
SolWinCapFactor_ER = SolWinCapFactor_ER.rename(columns={'SolWindCapFactor':'SolWinCapFactor_ER'})

ClipCapFactor_ER = pd.merge(Map_mdmh,ClipCapFactor,on=['m','d','h'],how='left').drop(columns=['m','d','dm','h']).sort_values(by=['r','ti','hr'])
ClipCapFactor_ER = ClipCapFactor_ER.rename(columns={'ClipCapFactor':'ClipCapFactor_ER'})

####################################################################################################################
#Update data
#Updating the supply curves data

#Add a small variable cost for solar, hydro and wind, which is used for the curtialment sequence.
SupplyPrice.loc[(SupplyPrice['pt']==10) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.003
SupplyPrice.loc[(SupplyPrice['pt']==10) & (SupplyPrice['steps']==2),'SupplyPrice'] = 0.003
SupplyPrice.loc[(SupplyPrice['pt']==14) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.002
SupplyPrice.loc[(SupplyPrice['pt']==15) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.002
SupplyPrice.loc[(SupplyPrice['pt']==16) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.002
SupplyPrice.loc[(SupplyPrice['pt']==17) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.001
SupplyPrice.loc[(SupplyPrice['pt']==18) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.001
SupplyPrice.loc[(SupplyPrice['pt']==19) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.001
SupplyPrice.loc[(SupplyPrice['pt']==20) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.001
SupplyPrice.loc[(SupplyPrice['pt']==21) & (SupplyPrice['steps']==1),'SupplyPrice'] = 0.001

Storagelvl_cost = 0.00000001

#Add one more steps for hydro supply curve for flat dispatch
pth_supply = SupplyCurve[SupplyCurve['pt'].isin(pth)].copy()
pth_supply = pth_supply[pth_supply['steps']==1].copy().rename(columns={'SupplyCurve':'SupplyCurve2'})
pth_supply['steps'] = 2
SupplyCurve = pd.merge(SupplyCurve,pth_supply, on=['pt','r','s','steps','y'], how='left')

SupplyCurve = pd.merge(SupplyCurve,HydroDispatchablePortion, on=['r'], how='left')
SupplyCurve.loc[((SupplyCurve['pt'].isin(pth)) & (SupplyCurve['steps']==1)),'SupplyCurve'] = SupplyCurve['SupplyCurve'] * SupplyCurve['HydroDispatchablePortion']
SupplyCurve['SupplyCurve2'] = SupplyCurve['SupplyCurve2'] * (1 - SupplyCurve['HydroDispatchablePortion'])
SupplyCurve.loc[((SupplyCurve['pt'].isin(pth)) & (SupplyCurve['steps']==2)),'SupplyCurve'] = SupplyCurve['SupplyCurve2'] 
SupplyCurve = SupplyCurve.drop(columns=['HydroDispatchablePortion','SupplyCurve2'])

#Solving model without increment storage(switchsolve(k)=0)
#Note: I'm just setting this up to run only one of these cases at the moment. The second case is included in the commented out code below.
SupplyCurve.loc[(SupplyCurve['pt'].isin(pts)) & (SupplyCurve['steps']==2),'SupplyCurve'] = 0.0

"""
#Solving model with increment storage(switchsolve(k)=1)
SupplyCurve = pd.merge(SupplyCurve,BatteryIncrement,on=['y', 'r', 'pt'],how='outer')
SupplyCurve.loc[(SupplyCurve['pt'].isin(pts)) & (SupplyCurve['steps']==2),'SupplyCurve'] = SupplyCurve['BatteryIncrement']
SupplyCurve = SupplyCurve.drop(columns=['BatteryIncrement'])

#Add an increment storage capacity, Now using storage steps=2 to represent the increment storage capacity and cost
temp = SupplyPrice.copy()
temp = temp[((temp['pt'].isin(pts)) & (temp['steps'] == 1))]
temp = temp.rename(columns={'SupplyPrice':'temp'}).copy()
temp['steps'] = 2
SupplyPrice = pd.merge(SupplyPrice,temp,on=['r', 's', 'pt', 'y', 'steps'],how='left')
SupplyPrice.loc[SupplyPrice['temp'].notnull(),'SupplyPrice'] = SupplyPrice['temp']
SupplyPrice = SupplyPrice.drop(columns=['temp'])
"""

####################################################################################################################
#Update data
#Updating technology performance related parameters and misc

#Moving peak day dayweight to the weekday dayweight
Idaytq_orig = Idaytq.copy().rename(columns={'Idaytq':'Idaytq_orig'})
Idaytq.loc[Idaytq['d']==1,'Idaytq'] = Idaytq['Idaytq'] + 1
Idaytq.loc[Idaytq['d']==3,'Idaytq'] = 0

Dayweights = pd.merge(Map_mdmh[['m','d','hr']],Idaytq,on=['m','d'],how='left').rename(columns={'Idaytq':'Dayweights'}).drop(columns=['m','d'])

#Daily conventional plants generation capacity factor
DailyPeakLoad = Load.groupby(['r', 'y', 'm', 'd'], as_index=False)['Load'].max().rename(columns={'Load':'DailyPeakLoad'})

CapacityFactor = pd.merge(Load, Map_mdmh, on=['m', 'd', 'h'], how='outer')
CapacityFactor = pd.merge(CapacityFactor, DailyPeakLoad, on=['r', 'y', 'm', 'd'], how='outer')
CapacityFactor = pd.merge(CapacityFactor, M864_LF, how='cross').dropna().drop(columns=['m', 'd', 'h','dm'])
CapacityFactor = pd.merge(CapacityFactor, Map_PlantSteps, on=['pt','steps'],how='left')
CapacityFactor['CapacityFactor'] = (CapacityFactor['M864_LF'] + (1 - CapacityFactor['M864_LF']) * \
                                       CapacityFactor['Load'] / CapacityFactor['DailyPeakLoad']) * CapacityFactor['Map_PlantSteps']
CapacityFactor = CapacityFactor.sort_values(by=['r','hr','pt']).reset_index(drop=True).drop(columns=['M864_LF','Load','DailyPeakLoad','Map_PlantSteps'])
#CapacityFactor.to_csv('../output/parameters/CapacityFactor.csv',index=False)

#this is the unclipped by the inverter CF ... GenerationMaxTotal, adding clipped back in
GenerationMaxTotal = pd.merge(ClipCapFactor_ER,SolWinCapFactor_ER,on=['hr', 'r', 'y', 'ti'],how='outer').fillna(0)
GenerationMaxTotal = GenerationMaxTotal[GenerationMaxTotal['ti'] == 77]
GenerationMaxTotal = pd.merge((Map_EcpGroup[Map_EcpGroup['pt'] == 21]),GenerationMaxTotal,on=['ti'],how='right')
GenerationMaxTotal = pd.merge(GenerationMaxTotal,Map_SeasonHour,on=['hr'],how='left')
GenerationMaxTotal = pd.merge(GenerationMaxTotal,SupplyCurve,on=['r', 'y','pt','s'],how='left').sort_values(by=['r','hr'])
GenerationMaxTotal['GenerationMaxTotal'] = GenerationMaxTotal['ClipCapFactor_ER'] + GenerationMaxTotal['SolWinCapFactor_ER']
GenerationMaxTotal['GenerationMaxTotal'] = GenerationMaxTotal['GenerationMaxTotal'] * GenerationMaxTotal['SupplyCurve'] * GenerationMaxTotal['Map_SeasonHour']
GenerationMaxTotal = GenerationMaxTotal.drop(columns=['ti', 'Map_EcpGroup', 'ClipCapFactor_ER', 'SolWinCapFactor_ER', 'SupplyCurve', 'Map_SeasonHour']).fillna(0)
GenerationMaxTotal = GenerationMaxTotal.groupby(['pt', 'hr', 'r', 'y', 'steps'], as_index=False).sum().drop(columns=['s'])

PVBatt_maxCF = pd.merge(SupplyCurve[SupplyCurve['pt'] == 21], Map_SeasonHour,on=['s'],how='left')\
    .drop(columns=['pt','s','Map_SeasonHour']).fillna(0).rename(columns={'SupplyCurve':'PVBatt_maxCF'})
#PVBatt_maxCF.to_csv('../output/parameters/PVBatt_maxCF.csv')

#creating battery charge and discharge caps and battery hours to buy
Battery_ChargeCap = pd.merge(SupplyCurve[SupplyCurve['pt'].isin(pts)], Map_SeasonHour, on=['s'], how='left').rename(columns={'SupplyCurve':'Battery_ChargeCap'})
Battery_ChargeCap = Battery_ChargeCap[Battery_ChargeCap['Map_SeasonHour']==1].drop(columns=['s','Map_SeasonHour'])
Battery_ChargeCap['temp'] = Battery_ChargeCap['Battery_ChargeCap'] / 3.0 #3 is storage cap fraction of inverter
Battery_ChargeCap.loc[(Battery_ChargeCap['pt']==21),'Battery_ChargeCap'] = Battery_ChargeCap['temp']
Battery_ChargeCap = Battery_ChargeCap.drop(columns=['temp'])

Battery_DischargeCap = Battery_ChargeCap.copy().rename(columns={'Battery_ChargeCap':'Battery_DischargeCap'})

H2B = {'pts': pts, 'HourstoBuy': [HourstoBuy*3, HourstoBuy, HourstoBuy/3]}
HourstoBuy = pd.DataFrame(H2B)

#making these parameters smaller
BatteryEfficiency =     BatteryEfficiency[BatteryEfficiency['pt'].isin(pts)].rename(columns = {'pt':'pts'})
RampRate =              RampRate[RampRate['pt'].isin(ptc)].rename(columns = {'pt':'ptc'})

####################################################################################################################
####################################################################################################################
#MODEL
####################################################################################################################
####################################################################################################################

#Note: I would like to run this model twice, which is how the AIMMS model is setup. One thought is to change this to an abstract model?
#I have it setup for the first solve, with the baseline values of storage. The second solve in the AIMMS model adds an increment of storage.
timer.toc('preprocessor finished')
model = pyo.ConcreteModel()
model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

####################################################################################################################
#Sets

#Note: this feels silly to have to initialize these sets here when I already created them earlier. One thought I had was to make this a function/loop, but
#I am having trouble initializing sets in pyomo through loops. Maybe this is a waste of time? Is there a better way to do this? Something like:
#set_list = ['hr', 'hr1', 'hr23', 'dm', 'pts', 'ptn', 'ptpvb', 'ptr', 'pti', 'ptipv', 'pth', 'd', 'h', 'm', 'pt', 'ptc', 'r', 's', 'steps', 'ti', 'y']
#for i in set_list: model.vars()[i] = Set(initialize=vars()[i])

model.hr =    pyo.Set(initialize=hr)
model.hr1 =   pyo.Set(initialize=hr1)
model.hr23 =  pyo.Set(initialize=hr23)
model.h =     pyo.Set(initialize=h)
model.y =     pyo.Set(initialize=y)
model.s =     pyo.Set(initialize=s)
model.m =     pyo.Set(initialize=m)
model.dm =    pyo.Set(initialize=dm)
model.d =     pyo.Set(initialize=d)
model.r =     pyo.Set(initialize=r)
model.steps = pyo.Set(initialize=steps)
model.pt =    pyo.Set(initialize=pt)
model.pts =   pyo.Set(initialize=pts)
model.ptn =   pyo.Set(initialize=ptn)
model.ptpvb = pyo.Set(initialize=ptpvb)
model.ptc =   pyo.Set(initialize=ptc)
model.ptr =   pyo.Set(initialize=ptr)
model.ptipv = pyo.Set(initialize=ptipv)
model.pti =   pyo.Set(initialize=pti)
model.pth =   pyo.Set(initialize=pth)
model.ti =    pyo.Set(initialize=ti)

####################################################################################################################
#Parameters

param_list = ['Map_ms', 'Map_MonthHour', 'Map_SeasonHour', 'Map_Daytype_Hour', 'Map_EcpGroup', 'Map_PlantSteps', 'Idaytq', 'Load_EMMRen',  
              'SolWinCapFactor_ER', 'HydroCapFactor', 'RampUp_Cost', 'RampDown_Cost', 'Battery_ChargeCap', 'Battery_DischargeCap', 'BatteryEfficiency',  
              'HourstoBuy', 'RampRate', 'Dayweights', 'SupplyPrice', 'SupplyCurve', 'CapacityFactor', 'PVBatt_maxCF', 'GenerationMaxTotal']

for parameter in param_list:
    #print(parameter)
    index_list = list(vars()[parameter].columns)
    index_list.remove(parameter)
    index_list.sort()
    vars()[parameter] = vars()[parameter].fillna(0).set_index(index_list)[parameter].to_dict()
    #print(index_list)
    
    #Note: Couldn't figure out how to include the parameter functions below in the loop above? (Maybe I don't need to?) Something like:
    #model.vars()[parameter] = pyo.Param(vars()[parameter].keys(), initialize = vars()[parameter])

#Temporal parameters
#Note: many of these parameters are mapping parameters, with a 0/1 switch, this seems like something that could be converted into a tuple
model.Map_ms =             pyo.Param(Map_ms.keys(), initialize = Map_ms, default = 0)
model.Map_MonthHour =      pyo.Param(Map_MonthHour.keys(), initialize = Map_MonthHour, default = 0)
model.Map_SeasonHour =     pyo.Param(Map_SeasonHour.keys(), initialize = Map_SeasonHour, default = 0)
model.Map_Daytype_Hour =   pyo.Param(Map_Daytype_Hour.keys(), initialize = Map_Daytype_Hour, default = 0)
model.Map_EcpGroup =       pyo.Param(Map_EcpGroup.keys(), initialize = Map_EcpGroup, default = 0)
model.Map_PlantSteps =     pyo.Param(Map_PlantSteps.keys(), initialize = Map_PlantSteps, default = 0)
model.Idaytq =             pyo.Param(Idaytq.keys(), initialize = Idaytq, default = 0)

#Technology-related parameters
model.Load_EMMRen =        pyo.Param(Load_EMMRen.keys(), initialize = Load_EMMRen, default = 0)
model.SolWinCapFactor_ER = pyo.Param(SolWinCapFactor_ER.keys(), initialize = SolWinCapFactor_ER, default = 0)
model.HydroCapFactor =     pyo.Param(HydroCapFactor.keys(), initialize = HydroCapFactor, default = 0)
model.RampUp_Cost =        pyo.Param(RampUp_Cost.keys(), initialize = RampUp_Cost, default = 0)
model.RampDown_Cost =      pyo.Param(RampDown_Cost.keys(), initialize = RampDown_Cost, default = 0)
model.Battery_ChargeCap =  pyo.Param(Battery_ChargeCap.keys(), initialize = Battery_ChargeCap, default = 0)
model.Battery_DischargeCap=pyo.Param(Battery_DischargeCap.keys(), initialize = Battery_DischargeCap, default = 0)
model.BatteryEfficiency =  pyo.Param(BatteryEfficiency.keys(), initialize = BatteryEfficiency, default = 0)
model.HourstoBuy =         pyo.Param(HourstoBuy.keys(), initialize = HourstoBuy, default = 0)
model.RampRate =           pyo.Param(RampRate.keys(), initialize = RampRate, default = 0)
model.Dayweights =         pyo.Param(Dayweights.keys(), initialize = Dayweights, default = 0)
model.SupplyPrice =        pyo.Param(SupplyPrice.keys(), initialize = SupplyPrice, default = 0)
model.SupplyCurve  =       pyo.Param(SupplyCurve.keys(), initialize = SupplyCurve, default = 0)
model.CapacityFactor =     pyo.Param(CapacityFactor.keys(),initialize = CapacityFactor, default = 0)
model.PVBatt_maxCF =       pyo.Param(PVBatt_maxCF.keys(), initialize = PVBatt_maxCF, default = 0)
model.GenerationMaxTotal = pyo.Param(GenerationMaxTotal.keys(), initialize = GenerationMaxTotal, default = 0)

####################################################################################################################
#Upper Bounds

def RampUp_upper(model, ptc, y, r, steps, hr):
    return (0, model.RampRate[ptc] * sum(model.Map_SeasonHour[hr, s] * model.SupplyCurve[ptc, r, s, steps, y] for s in model.s))

def RampDown_upper(model, ptc, y, r, steps, hr):
    return (0, model.RampRate[ptc] * sum(model.Map_SeasonHour[hr, s] * model.SupplyCurve[ptc, r, s, steps, y] for s in model.s))

def Storage_inflow_upper(model, pts, y, r, steps, hr):
    return (0, model.Battery_ChargeCap[hr, pts, r, steps, y])

def Storage_outflow_upper(model, pts, y, r, steps, hr):
    return (0, model.Battery_DischargeCap[hr, pts, r, steps, y])

def Storage_level_upper(model, pts, y, r, steps, hr):
    return (0, sum(model.Map_SeasonHour[hr, s] * model.SupplyCurve[pts, r, s, steps, y]  for s in model.s) * model.HourstoBuy[pts])

####################################################################################################################
#Variables
#Note: generation upper bounds are defined below as constraints, but best practice is to include them when the variable is initialized, need to update here. 

model.RampUp =          pyo.Var(model.ptc,model.y,model.r,model.steps,model.hr, within=pyo.NonNegativeReals, bounds=RampUp_upper) #Operation increase GW of Tech T in hour h #GW
model.RampDown =        pyo.Var(model.ptc,model.y,model.r,model.steps,model.hr, within=pyo.NonNegativeReals, bounds=RampDown_upper) #Operation decrease GW of Tech T in hour h #GW
model.Storage_inflow =  pyo.Var(model.pts,model.y,model.r,model.steps,model.hr, within=pyo.NonNegativeReals, bounds=Storage_inflow_upper) #Storage inflow in hour h in GW #GW
model.Storage_outflow = pyo.Var(model.pts,model.y,model.r,model.steps,model.hr, within=pyo.NonNegativeReals, bounds=Storage_outflow_upper) #Storage outflow in hour h in GW #GW
model.Storage_level =   pyo.Var(model.pts,model.y,model.r,model.steps,model.hr, within=pyo.NonNegativeReals, bounds=Storage_level_upper) #Energy level of storage tech T_S in hour h in GWh #GWh
model.Generation =      pyo.Var(model.pt,model.y,model.r,model.steps,model.hr, within=pyo.NonNegativeReals)  #Operated capacity GW use of technology group T in hour h #GW
model.unmet_Load =      pyo.Var(model.r,model.y,model.hr, within=pyo.NonNegativeReals)                   #slack variable #GW

####################################################################################################################
#Objective Function

#Variable Objectivefunction
#using PV pricing for PV portion of PV+battery
model.Objectivefunction = pyo.Objective(expr = \
    sum( \
        (sum(0.5 * sum(model.Map_SeasonHour[hr, s] * model.SupplyPrice[ptn, r, s, steps, y] for s in model.s) \
             * (model.Storage_inflow[  ptn, y, r, steps, hr] + model.Storage_outflow[ptn, y, r, steps, hr]) \
             + Storagelvl_cost * model.Storage_level[ptn, y, r, steps, hr] for steps in model.steps for y in model.y for ptn in model.ptn) \
            
        + sum(sum(model.Map_SeasonHour[hr, s] * model.SupplyPrice[ptpvb, r, s, steps, y] for s in model.s) \
              * (model.Storage_inflow[ptpvb, y, r, steps, hr] + model.Storage_outflow[ptpvb, y, r, steps, hr]) \
              + Storagelvl_cost * model.Storage_level[ptpvb, y, r, steps, hr] for steps in model.steps for y in model.y for ptpvb in model.ptpvb) \
            
        + sum(sum(model.Map_SeasonHour[hr, s] * model.SupplyPrice[ptc, r, s, steps, y] for s in model.s) \
              * model.Generation[ptc, y, r, steps, hr] for steps in model.steps for y in model.y for ptc in model.ptc)  \
                      
        + sum(sum(model.Map_SeasonHour[hr, s] * model.SupplyPrice[ptr, r, s, steps, y] for s in model.s) \
              * model.Generation[ptr, y, r, steps, hr] for steps in model.steps for y in model.y for ptr in model.ptr)  \
                      
        + sum(sum(model.Map_SeasonHour[hr, s] * model.SupplyPrice[ptipv, r, s, steps, y] for s in model.s) \
              * model.Generation[ptipv, y, r, steps, hr] for steps in model.steps for y in model.y for ptipv in model.ptipv)\
                      
        + sum(model.RampUp_Cost[ptc] * model.RampUp[ptc, y, r, steps, hr] \
              + model.RampDown_Cost[ptc] * model.RampDown[ptc, y, r, steps, hr] for steps in model.steps for y in model.y for ptc in model.ptc)  \
                      
        + sum(model.unmet_Load[r, y, hr] * UnmetLoad_penalty for y in model.y))
        
        * model.Dayweights[hr] for r in model.r for hr in model.hr),
    
    sense = pyo.minimize)

####################################################################################################################
#Constraints

#Property: ShadowPrice
@model.Constraint(model.r, model.y, model.hr)
def Demand_balance(model, r, y, hr):
    return model.Load_EMMRen[hr, r, y] <= \
        sum(model.Map_PlantSteps[ptc, steps] * model.Generation[ptc, y, r, steps, hr] for ptc in model.ptc for steps in model.steps) \
        + sum(model.Map_PlantSteps[ptr, steps] * model.Generation[ptr, y, r, steps, hr] for ptr in model.ptr for steps in model.steps) \
        + sum(model.Map_PlantSteps[pti, steps] * model.Generation[pti, y, r, steps, hr] for pti in model.pti for steps in model.steps) \
        + sum(model.Map_PlantSteps[ptn, steps] * (model.Storage_outflow[ptn, y, r, steps, hr] - model.Storage_inflow[ptn, y, r, steps, hr]) \
              for ptn in model.ptn for steps in model.steps) \
        + sum(model.Map_PlantSteps[ptpvb, steps] * (model.Generation[ptpvb, y, r, steps, hr] + model.Storage_outflow[ptpvb, y, r, steps, hr]) \
              for ptpvb in model.ptpvb for steps in model.steps) \
        + model.unmet_Load[r, y, hr]

#First hour 
@model.Constraint(model.ptc, model.y, model.r, model.steps, model.hr1)
def FirstHour_gen_ramp(model, ptc, y, r, steps, hr1): 
    return model.Generation[ptc, y, r, steps, hr1] == \
        model.Generation[ptc, y, r, steps, hr1+23] + model.RampUp[ptc, y, r, steps, hr1] - model.RampDown[ptc, y, r, steps, hr1]

#NOT first hour
@model.Constraint(model.ptc, model.y, model.r, model.steps, model.hr23)
def Gen_ramp(model, ptc, y, r, steps, hr23): 
    return model.Generation[ptc, y, r, steps, hr23] == \
        model.Generation[ptc, y, r, steps, hr23-1] + model.RampUp[ptc, y, r, steps, hr23] - model.RampDown[ptc, y, r, steps, hr23]

#First hour
@model.Constraint(model.pts, model.y, model.r, model.steps, model.hr1)
def FirstHourStorageBalance2(model, pts, y, r, steps, hr1):
    return model.Storage_level[pts, y, r, steps, hr1] == model.Storage_level[pts, y, r, steps, hr1+23] + \
        model.BatteryEfficiency[pts] * model.Storage_inflow[pts, y, r, steps, hr1] - model.Storage_outflow[pts, y, r, steps, hr1]

#NOT first hour
@model.Constraint(model.pts, model.y, model.r, model.steps, model.hr23)
def StorageBalance(model, pts, y, r, steps, hr23): 
    return model.Storage_level[pts, y, r, steps, hr23] == model.Storage_level[pts, y, r, steps, hr23-1] + \
        model.BatteryEfficiency[pts] * model.Storage_inflow[pts, y, r, steps, hr23] - model.Storage_outflow[pts, y, r, steps, hr23]

@model.Constraint(model.pth, model.y, model.r, model.m)
def Hydro_Gen_Cap(model, pth, y, r, m):
    return sum(model.Map_MonthHour[hr, m] * model.Map_Daytype_Hour[dm, hr] * model.Generation[pth, y, r, 1, hr] * model.Idaytq[dm, m] for hr in model.hr for dm in model.dm) <= \
        sum(model.Map_ms[m, s] * model.SupplyCurve[pth, r, s, 1, y] * model.HydroCapFactor[m, r] for s in model.s) * sum(model.Idaytq[dm, m] for dm in model.d) * 24

#PVBatt_maxCF = max generation (inverter capacity)
@model.Constraint(model.ptpvb, model.y, model.r, model.steps, model.hr)
def PVBattery_balance(model, ptpvb, y, r, steps, hr):
    return model.Generation[ptpvb, y, r, steps, hr] + model.Storage_outflow[ptpvb, y, r, steps, hr] <= model.PVBatt_maxCF[hr, r, steps, y] 

#kW PV to grid + kW PV to Batt <= PV available (unclipped by inverter)
@model.Constraint(model.ptpvb, model.y, model.r, model.steps, model.hr)
def PVBattery_balance2(model, ptpvb, y, r, steps, hr):
    return model.Generation[ptpvb, y, r, steps, hr] + model.Storage_inflow[ptpvb, y, r, steps, hr] <= model.GenerationMaxTotal[hr, ptpvb, r, steps, y]

####################################################################################################################
#Constraints Generation Variable Upper Bounds

@model.Constraint(model.ptc, model.y, model.r, model.steps, model.hr)
def ptc_upper(model, ptc, y, r, steps, hr):
    return model.Generation[ptc, y, r, steps, hr] <= \
        sum(model.Map_SeasonHour[hr, s] * model.SupplyCurve[ptc, r, s, steps, y] * model.CapacityFactor[hr, ptc, r, steps, y] for s in model.s)

@model.Constraint(model.ptr, model.y, model.r, model.steps, model.hr)
def ptr_upper(model, ptr, y, r, steps, hr):
    return model.Generation[ptr, y, r, steps, hr] <= \
        sum(model.Map_SeasonHour[hr, s] * model.SupplyCurve[ptr, r, s, steps, y] * model.CapacityFactor[hr, ptr, r, steps, y] for s in model.s)

@model.Constraint(model.pth, model.y, model.r, model.hr)
def pth_upper(model, pth, y, r, hr):
    return model.Generation[pth, y, r, 2, hr] <= \
        sum(model.Map_SeasonHour[hr, s] * model.Map_MonthHour[hr, m] * model.SupplyCurve[pth, r, s, 2, y] * model.HydroCapFactor[m, r] for m in model.m for s in model.s)

@model.Constraint(model.ptipv, model.y, model.r, model.steps, model.hr)
def ptipv_upper(model, ptipv, y, r, steps, hr):
    return model.Generation[ptipv, y, r, steps, hr] <= \
        sum(model.Map_SeasonHour[hr, s] * model.Map_EcpGroup[ptipv, ti] * model.SupplyCurve[ptipv, r, s, steps, y] * model.SolWinCapFactor_ER[hr, r, ti, y] \
            for s in model.s for ti in model.ti)

@model.Constraint(model.ptn, model.y, model.r, model.steps, model.hr)
def ptn_upper(model, ptn, y, r, steps, hr):
    return model.Generation[ptn, y, r, steps, hr] <= 0

####################################################################################################################
#Solve

#model.pprint()
#Note: tried testing with the ipopt solver, but it results in slower runtimes
timer.toc('build model finished')
opt = pyo.SolverFactory("appsi_highs")
opt_success = opt.solve(model)#.write()
timer.toc('solve model finished')
print()
#model.pprint()

#Check
#Objective Value
obj_val = pyo.value(model.Objectivefunction)
print('Resulting Objective Function Value From Pyomo =',obj_val)
if y[0] == 2040:
    if test_region == 0:
        print('Target Objective Function Value From AIMMS =    17378163.66')
    elif test_region == 22:
        print('Target Objective Function value (for r = 22) =  254216.83')
print()

####################################################################################################################
#Review

#Variables

#Export variable dataframes

RampUp = pd.Series(model.RampUp.get_values()).to_frame().reset_index().rename(columns={'level_0':'ptc', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'RampUp'})
RampDown = pd.Series(model.RampDown.get_values()).to_frame().reset_index().rename(columns={'level_0':'ptc', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'RampDown'})
Storage_inflow = pd.Series(model.Storage_inflow.get_values()).to_frame().reset_index().rename(columns={'level_0':'pts', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Storage_inflow'})
Storage_outflow = pd.Series(model.Storage_outflow.get_values()).to_frame().reset_index().rename(columns={'level_0':'pts', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Storage_outflow'})
Storage_level = pd.Series(model.Storage_level.get_values()).to_frame().reset_index().rename(columns={'level_0':'pts', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Storage_level'})
Generation = pd.Series(model.Generation.get_values()).to_frame().reset_index().rename(columns={'level_0':'pt', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Generation'})
unmet_Load = pd.Series(model.unmet_Load.get_values()).to_frame().reset_index().rename(columns={'level_0':'r', 'level_1':'y', 'level_2':'hr', 0:'unmet_Load'})

if print_switch==1:
    RampUp.to_csv('../output/variables/RampUp.csv',index=False)
    RampDown.to_csv('../output/variables/RampDown.csv',index=False)
    Storage_inflow.to_csv('../output/variables/Storage_inflow.csv',index=False)
    Storage_outflow.to_csv('../output/variables/Storage_outflow.csv',index=False)
    Storage_level.to_csv('../output/variables/Storage_level.csv',index=False)
    Generation.to_csv('../output/variables/Generation.csv',index=False)
    unmet_Load.to_csv('../output/variables/unmet_Load.csv',index=False)

print('unmet_Load')
unmet_Load = unmet_Load[unmet_Load['unmet_Load']!=0]
print(len(unmet_Load), 'rows with unmet load')
print()

####################################################################################################################
#final steps for measuring the run time of the code
end_time = datetime.now()
run_time = end_time - start_time

#appending runtime data to txt file to measure performance improvements over time
#if test_region == 0: print(report_timing())
file = open('run_time.txt', 'a')
file.write('\nFull: Start Time: ' + datetime.strftime(start_time,"%m/%d/%Y %H:%M") + ', Run Time: ' + str(round(run_time.total_seconds()/60,2)) + ' mins')
file.close()
timer.toc('postprocessor finished')
print()
