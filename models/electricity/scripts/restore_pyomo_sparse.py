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
import gc
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
#Read in data

#Read the text file into a string

with open('../input/toAIMMS/ecpout_2040.txt') as file:
    data = file.read()

#Split the text by semicolon (;)
frames = data.split(';')

with open('../input/restprep.txt') as file:
    data = file.read()

frames += data.split(';')

all_frames = {}
for frame in frames:
    if frame.strip() == '':
        continue
    frame = frame.strip()  
    if frame.split('\n')[0]=='COMPOSITE TABLE:':
        all_frames[frame.split('\n')[1].split()[-1]] = pd.DataFrame([[float(y) for y in x.split()] for x in frame.split('\n')[2:]], columns=[x for x in frame.split('\n')[1].split()])
    else:
        all_frames[frame.split(':=')[0].strip()] = frame.split(':=')[1].strip()

def testOneReg(reg):
    for i in all_frames:
        if type(all_frames[i]) != str:
            if 'r' in all_frames[i].columns:
                all_frames[i] = all_frames[i].loc[all_frames[i].r.isin([reg])]
    return reg

if test_region!=0: r = [testOneReg(test_region)]

####################################################################################################################
#Update data
#Updating the day-type mapping (this model solves for two day-types per month, input data includes three day-types per month)

#Create map for seasons, months, days, and hours
all_frames['Map'] = pd.DataFrame([(i,((i-1)//24)%2+1,((i-1)//48)+1,all_frames['Map_ms'].s[((i-1)//48)]) for i in range(1,577)], columns=['hr','d','m','s'])
all_frames['Map']['dm'] = all_frames['Map'].apply(lambda x: 1 if x.d==2 else 2, axis=1)
all_frames['Map']['h'] = (all_frames['Map'].hr + 23 ) % 48 + 1 + ((all_frames['Map'].hr-1)//48) * 48 
all_frames['MapHrIndex'] = all_frames['Map'].set_index(['hr'])
all_frames['Map_ms'] = all_frames['Map_ms'].set_index(['m'])

#Using the new day-type mappings to update the input data for load and solar/wind capacity factors
all_frames['Load'] = all_frames['Load'][all_frames['Load'].d !=3]
all_frames['Load']['hr'] = ((all_frames['Load'].d-1)%3 + (all_frames['Load'].m-1)*2)*24 + all_frames['Load'].h
#Change SolWindCapFactor from 1-24 hours to 1-576 hours and remove d=3
all_frames['SolWindCapFactor'] = all_frames['SolWindCapFactor'][all_frames['SolWindCapFactor'].d != 3]
all_frames['SolWindCapFactor'] = pd.merge(all_frames['SolWindCapFactor'],all_frames['Map_EcpGroup'].drop(columns='Map_EcpGroup'), on='tech')
all_frames['SolWindCapFactor']['hr'] = ((all_frames['SolWindCapFactor'].d-1)%3 + (all_frames['SolWindCapFactor'].m-1)*2)*24 + all_frames['SolWindCapFactor'].h
solwind = all_frames['SolWindCapFactor']
#Change ClipCapFactor from 1-24 hours to 1-576 hours and remove d=3
all_frames['ClipCapFactor'] = all_frames['ClipCapFactor'][all_frames['ClipCapFactor'].d != 3]
all_frames['ClipCapFactor']['hr'] = (((all_frames['ClipCapFactor'].d-1)%3)+(all_frames['ClipCapFactor'].m-1)*2)*24 + all_frames['ClipCapFactor'].h
#Change BatteryIncrement column 'year' to 'y' for consistency
all_frames['BatteryIncrement'] = all_frames['BatteryIncrement'].rename(columns={'year':'y'})
#Change M864_LF column 'Steps' to 'steps' for consistency
all_frames['M864_LF'] = all_frames['M864_LF'].rename(columns={'Steps': 'steps'})

all_frames['Map_EcpGroup'] = all_frames['Map_EcpGroup'].set_index('pt')


####################################################################################################################
#Update data
#Updating the supply curves data

#Add custom changes to SupplyPrice
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==10) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.003
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==10) & (all_frames['SupplyPrice']['steps']==2),'SupplyPrice'] = 0.003
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==14) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.002
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==15) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.002
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==16) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.002
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==17) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.001
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==18) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.001
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==19) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.001
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==20) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.001
all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt']==21) & (all_frames['SupplyPrice']['steps']==1),'SupplyPrice'] = 0.001

def addSupplyStep(frame):
    frame['steps'] = 2
    return frame

#Add an increment storage capacity, Now using storage steps=2 to represent the increment storage capacity and cost
all_frames['SupplyPrice'] = pd.concat([all_frames['SupplyPrice'],addSupplyStep(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice']['pt'].isin(pts)].copy().drop(columns=['SupplyCurve']))])

#Add Hydro changes to SupplyCurve
all_frames['SupplyPrice'] = pd.concat([all_frames['SupplyPrice'], addSupplyStep(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice']['pt'].isin(pth)].copy())])
all_frames['SupplyPrice']['SupplyCurve'].loc[(all_frames['SupplyPrice']['pt'].isin(pth)) & (all_frames['SupplyPrice']['steps']==1)] = \
    all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt'].isin(pth)) & (all_frames['SupplyPrice']['steps']==1)].apply(lambda row: row.SupplyCurve * all_frames['HydroDispatchablePortion']['HydroDispatchablePortion'][row.r-1], axis=1)
all_frames['SupplyPrice']['SupplyCurve'].loc[(all_frames['SupplyPrice']['pt'].isin(pth)) & (all_frames['SupplyPrice']['steps']==2)] = \
    all_frames['SupplyPrice'].loc[(all_frames['SupplyPrice']['pt'].isin(pth)) & (all_frames['SupplyPrice']['steps']==2)].apply(lambda row: row.SupplyCurve * (1-all_frames['HydroDispatchablePortion']['HydroDispatchablePortion'][row.r-1]), axis=1)

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

#Add peak day dayweight to the weekday dayweight in Idaytq
all_frames['Idaytq'].loc[all_frames['Idaytq']['d']==1,'Idaytq'] += 1
all_frames['Dayweights'] = pd.merge(all_frames['Map'],all_frames['Idaytq'].rename(columns={'d':'dm'})).drop(columns=['d','m','s','dm','h']).rename(columns={'Idaytq':'Dayweights'})

#Create DailyPeakLoad from Load
all_frames['DailyPeakLoad'] = all_frames['Load'].groupby(['r','y','m','d'], as_index=False)['Load'].max().rename(columns={'Load':'DailyPeakLoad'})
#Dailypeakload = all_frames['DailyPeakLoad']

#Create CapacityFactor
CapacityFactor = all_frames['Load'].drop(columns=['EMMGroup','EMMSegment','Group_ECP','Segment_ECP'])
CapacityFactor = pd.DataFrame.merge(CapacityFactor,all_frames['DailyPeakLoad'],how='left')
CapacityFactor = pd.DataFrame.merge(CapacityFactor,all_frames['M864_LF'],how='cross')
CapacityFactor['CapacityFactor'] = CapacityFactor['M864_LF'] + (1 - CapacityFactor['M864_LF']) * CapacityFactor['Load']/CapacityFactor['DailyPeakLoad']
CapacityFactor = pd.DataFrame.merge(CapacityFactor.drop(columns=['h']).rename(columns={'hr':'h'}), all_frames['Map'].drop(columns=['s','d']), how='left', on=['m','h'])
CapacityFactor = CapacityFactor.drop(columns=['Load','DailyPeakLoad','Map_PlantSteps','M864_LF'])

#Add in GenerationMaxTotal
all_frames['GenerationMaxTotal'] = pd.merge(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice']['pt'].isin(ptpvb)].drop(columns=['SupplyPrice']).dropna(),all_frames['Map'].drop(columns=['d','m','dm']))
all_frames['GenerationMaxTotal'] = pd.merge(all_frames['GenerationMaxTotal'],all_frames['ClipCapFactor'],how='left').fillna(0).drop(columns=['s','m','d','h','tech'])
all_frames['GenerationMaxTotal'] = pd.merge(all_frames['GenerationMaxTotal'],all_frames['SolWindCapFactor'].loc[all_frames['SolWindCapFactor'].tech==77], how='left',on=['r','y','hr','pt']).fillna(0).drop(columns=['m','d','h','tech'])
all_frames['GenerationMaxTotal']['GenerationMaxTotal'] = all_frames['GenerationMaxTotal'].SupplyCurve * (all_frames['GenerationMaxTotal'].ClipCapFactor + all_frames['GenerationMaxTotal'].SolWindCapFactor)
all_frames['GenerationMaxTotal'] = all_frames['GenerationMaxTotal'].drop(columns=['SupplyCurve','ClipCapFactor','SolWindCapFactor']).set_index(['pt','y','r','steps','hr'])

#Note: missing PVBatt_maxCF calculation here

#Add in BatteryChargeCaps with pt==21 changed from SupplyCurve
all_frames['BatteryChargeCap'] = pd.merge(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice'].pt.isin(pts)].drop(columns=['SupplyPrice']).dropna(),all_frames['Map']).rename(columns={'SupplyCurve':'BatteryChargeCap'})
all_frames['BatteryChargeCap'].loc[all_frames['BatteryChargeCap'].pt==21,'BatteryChargeCap'] /=3

#Note: MISSING
#Battery_DischargeCap = Battery_ChargeCap.copy().rename(columns={'Battery_ChargeCap':'Battery_DischargeCap'})

#H2B = {'pts': pts, 'HourstoBuy': [HourstoBuy*3, HourstoBuy, HourstoBuy/3]}
#HourstoBuy = pd.DataFrame(H2B)

#making these parameters smaller
#BatteryEfficiency =     BatteryEfficiency[BatteryEfficiency['pt'].isin(pts)].rename(columns = {'pt':'pts'})
#RampRate =              RampRate[RampRate['pt'].isin(ptc)].rename(columns = {'pt':'ptc'})

####################################################################################################################
#Indexing

#Create master set for variables to loop through some subset
all_frames['StorageSet'] = pd.merge(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice']['pt'].isin(pts)].drop(columns=['SupplyPrice']).dropna(),all_frames['Map'].drop(columns=['d','m','dm'])).set_index(['pt','y','r','steps','hr'])
all_frames['GenSet'] = pd.merge(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice']['pt'].isin(list(set(pt)-set(ptn)))].drop(columns=['SupplyPrice']).dropna(),all_frames['Map'].drop(columns=['d','m','dm'])).set_index(['pt','y','r','steps','hr'])
all_frames['RampSet'] = pd.merge(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice']['pt'].isin(ptc)].drop(columns=['SupplyPrice']).dropna(),all_frames['Map'].drop(columns=['d','m','dm'])).set_index(['pt','y','r','steps','hr'])

sparseSet = pd.merge(all_frames['SupplyPrice'].drop(columns=['SupplyPrice']).dropna(),all_frames['Map'])
sparseSet = pd.merge(sparseSet,all_frames['SolWindCapFactor'].drop(columns=['m','d','h','tech']), how='left', on=['r','y','pt','hr']).fillna(0)
sparseSet = pd.merge(sparseSet,CapacityFactor.drop(columns=['m','d','h','dm']), how='left', on=['r','y','pt','steps','hr']).fillna(0)

ptipvUpperSet = sparseSet.loc[sparseSet.pt.isin(ptipv)].set_index(['pt','y','r','steps','hr'])

CapacityFactor = CapacityFactor.set_index(['pt','y','r','steps','hr'])
all_frames['CapacityFactor'] = CapacityFactor.loc[all_frames['GenSet'].index].drop(columns=['m','d','h'])

all_frames['Load_EMMRen'] = all_frames['Load'].drop(columns=['m','d','h','EMMGroup','EMMSegment','Group_ECP','Segment_ECP'])
all_frames['Load_EMMRen'].hr = (((all_frames['Load'].d%2))%3 + (all_frames['Load'].m-1)*2)*24 + all_frames['Load'].h
all_frames['Load_EMMRen'] = all_frames['Load_EMMRen'].sort_values(by=['r','hr']).rename(columns={'Load':'Load_EMMRen'})

all_frames['SupplyCurveMonths'] = pd.merge(all_frames['SupplyPrice'].loc[all_frames['SupplyPrice']['pt'].isin(pth)].drop(columns=['SupplyPrice']).dropna(),all_frames['Map'].drop(columns=['dm'])).groupby(['pt','y','r','steps','m'])['s'].max()
# supply = all_frames['SupplyPrice']
# storageSet = all_frames['StorageSet']
Dayweight = all_frames['Dayweights']
MainMap = all_frames['Map']

def formatData(frames):
    return {None:   {
                    'HydroSet' : frames['HydroCapFactor'].set_index(['m','r']).index,
                    'IdaytqSet' : frames['Idaytq'].set_index(['m','d']).index,
                    'LoadSet' : frames['Load'].drop(columns=['m','d','h']).set_index(['r','y','hr']).index,
                    'SupplyPriceSet' : frames['SupplyPrice'].drop(columns=['SupplyCurve']).set_index(['r','s','pt','y','steps']).dropna().index,
                    'SupplyCurveSet' : frames['SupplyPrice'].drop(columns=['SupplyPrice']).set_index(['r','s','pt','y','steps']).dropna().index,
                    'M864_LFSet' : frames['M864_LF'].set_index(['pt','steps']).index,
                    'StorageSet' : frames['StorageSet'].index,
                    'RampSet' : frames['RampSet'].index,
                    'GenSet' : frames['GenSet'].index,
                    'SolWinSet' : frames['SolWindCapFactor'].set_index(['hr','r','y','tech']).index,
                    'HydroCapFactor' : frames['HydroCapFactor'].set_index(['m','r']).to_dict()['HydroCapFactor'],
                    'Idaytq' : frames['Idaytq'].set_index(['m','d']).to_dict()['Idaytq'],
                    'Load_EMMRen' : frames['Load_EMMRen'].set_index(['r','y','hr']).to_dict()['Load_EMMRen'],
                    'SupplyPrice' : frames['SupplyPrice'].drop(columns=['SupplyCurve']).set_index(['r','s','pt','y','steps']).dropna().to_dict()['SupplyPrice'],
                    'SupplyCurve' : frames['SupplyPrice'].drop(columns=['SupplyPrice']).set_index(['r','s','pt','y','steps']).dropna().to_dict()['SupplyCurve'],
                    'Dayweights' : frames['Dayweights'].set_index('hr').to_dict()['Dayweights'],
                    'M864_LF' : frames['M864_LF'].set_index(['pt','steps']).to_dict()['M864_LF'],
                    'Map_ms' : frames['Map_ms'].to_dict()['s'],
                    'BatteryEfficiency' : frames['BatteryEfficiency'].set_index(['pt']).to_dict()['BatteryEfficiency'],
                    'CapacityFactor' : frames['CapacityFactor'].to_dict()['CapacityFactor'],
                    'RampRate' : frames['RampRate'].set_index('pt').to_dict()['RampRate'],
                    'HourstoBuy' : {None : int(frames['HourstoBuy'])},
                    'Battery_ChargeCap' : pd.merge(all_frames['BatteryChargeCap'].loc[all_frames['BatteryChargeCap']['pt'].isin(pts)],all_frames['Map'].drop(columns=['d','m','dm'])).set_index(['pt','y','r','steps','hr']).to_dict()['BatteryChargeCap'],
                    'SolWinCapFactor_ER' : frames['SolWindCapFactor'].set_index(['hr','r','y','tech']).to_dict()['SolWindCapFactor'],
                    'RampUp_Cost' : frames['RampDown_Cost'].set_index(['ptc']).to_dict()['RampUp_Cost'],
                    'RampDown_Cost' : frames['RampDown_Cost'].set_index(['ptc']).to_dict()['RampDown_Cost'],
                    'r' : {None : r}
                    }
            }  

####################################################################################################################
####################################################################################################################
#MODEL
####################################################################################################################
####################################################################################################################

timer.toc('preprocessor finished')
model = pyo.AbstractModel()

####################################################################################################################
#Sets

model.hr = pyo.Set(initialize = range(1,577)) #change hours (1-48) or (1-577)?
model.r = pyo.Set(initialize = range(1,26))
model.d = pyo.Set(initialize = [1,2,3])
model.y = pyo.Set(initialize = [2040])

model.HydroSet = pyo.Set()
model.IdaytqSet = pyo.Set()
model.LoadSet = pyo.Set()
model.M864_LFSet = pyo.Set()
model.StorageSet = pyo.Set()
model.RampSet = pyo.Set()
model.UnmetSet = model.r * model.y * model.hr
model.SolWinSet = pyo.Set()
model.GenSet = pyo.Set()

model.SupplyPriceSet = pyo.Set()
model.SupplyCurveSet = pyo.Set()


####################################################################################################################
#Parameters

model.Storagelvl_cost = pyo.Param(initialize=0.00000001)
model.UnmetLoad_penalty = pyo.Param(initialize=500)

model.Idaytq = pyo.Param(model.IdaytqSet)

model.Load_EMMRen = pyo.Param(model.LoadSet)
model.SolWinCapFactor_ER = pyo.Param(model.SolWinSet)
model.HydroCapFactor = pyo.Param(model.HydroSet)
model.RampUp_Cost = pyo.Param(ptc)
model.RampDown_Cost = pyo.Param(ptc)
model.Battery_ChargeCap = pyo.Param(model.StorageSet)
#Missing Battery_DischargeCap
model.BatteryEfficiency = pyo.Param(pts)
model.HourstoBuy= pyo.Param()
model.RampRate = pyo.Param(ptc)
model.Dayweights = pyo.Param(model.hr)
model.SupplyPrice = pyo.Param(model.SupplyPriceSet)
model.SupplyCurve = pyo.Param(model.SupplyCurveSet)
model.CapacityFactor = pyo.Param(model.GenSet)
#Missing PVBatt_maxCF
#Missing GenerationMaxTotal

model.M864_LF = pyo.Param(model.M864_LFSet)

####################################################################################################################
#Upper Bounds

def RampUp_upper(model, ptc, y, r, steps, hr):
    return (0, model.RampRate[ptc] * model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],ptc,y,steps)])

def RampDown_upper(model, ptc, y, r, steps, hr):
    return (0, model.RampRate[ptc] * model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],ptc,y,steps)])

def Storage_inflow_upper(model, pt, y, r, steps, hr):
    return (0, model.Battery_ChargeCap[(pt,y,r,steps,hr)])

def Storage_outflow_upper(model, pt, y, r, steps, hr):
    return (0, model.Battery_ChargeCap[(pt,y,r,steps,hr)])

####################################################################################################################
#Variables
#Note: generation upper bounds are defined below as constraints, but best practice is to include them when the variable is initialized, need to update here. 

model.RampUp =          pyo.Var(model.RampSet, within=pyo.NonNegativeReals, bounds=RampUp_upper) #Operation increase GW of Tech T in hour h #GW
model.RampDown =        pyo.Var(model.RampSet, within=pyo.NonNegativeReals, bounds=RampDown_upper) #Operation decrease GW of Tech T in hour h #GW
model.Storage_inflow =  pyo.Var(model.StorageSet, within=pyo.NonNegativeReals, bounds=Storage_inflow_upper) #Storage inflow in hour h in GW #GW
model.Storage_outflow = pyo.Var(model.StorageSet, within=pyo.NonNegativeReals, bounds=Storage_outflow_upper) #Storage outflow in hour h in GW #GW
model.Storage_level =   pyo.Var(model.StorageSet, within=pyo.NonNegativeReals) #Energy level of storage tech T_S in hour h in GWh #GWh
model.Generation =      pyo.Var(model.GenSet, within=pyo.NonNegativeReals) #Operated capacity GW use of technology group T in hour h #GW
model.unmet_Load =      pyo.Var(model.UnmetSet, within=pyo.NonNegativeReals) #slack variable #GW

####################################################################################################################
#Objective Function

model.StorageSetByHour = pyo.Set(model.hr)
model.GenSetByHour = pyo.Set(model.hr)
model.RampSetByHour = pyo.Set(model.hr)


def populate_by_hour_sets_rule(m):
    for (tech, y, reg, step, hour) in m.StorageSet:
        m.StorageSetByHour[hour].add((tech, y, reg, step))
    for (tech, y, reg, step, hour) in m.GenSet:
        m.GenSetByHour[hour].add((tech, y, reg, step))
    for (tech, y, reg, step, hour) in m.RampSet:
        m.RampSetByHour[hour].add((tech, y, reg, step))


model.populate_by_hour_sets = pyo.BuildAction(rule=populate_by_hour_sets_rule)

#Variable Objectivefunction
#using PV pricing for PV portion of PV+battery
def objFunction(model):
    return (sum(
        model.Dayweights[hour] * model.unmet_Load[(reg, y, hour)] * model.UnmetLoad_penalty for (reg, y, hour) in
        model.UnmetSet) + \
            sum(model.Dayweights[hr] * (
                    sum(0.5 * model.SupplyPrice[(reg, s, tech, y, step)] * (
                                model.Storage_inflow[(tech, y, reg, step, hr)] + model.Storage_outflow[
                            (tech, y, reg, step, hr)]) \
                        + model.Storagelvl_cost * model.Storage_level[(tech, y, reg, step, hr)] for (tech, y, reg, step)
                        in model.StorageSetByHour[hr]) \
                    + sum(0.5 * model.SupplyPrice[(reg, s, tech, y, step)] * (
                        model.Storage_inflow[(tech, y, reg, step, hr)] + model.Storage_outflow[
                    (tech, y, reg, step, hr)]) \
                          + model.Storagelvl_cost * model.Storage_level[(tech, y, reg, step, hr)] for
                          (tech, y, reg, step) in model.StorageSetByHour[hr] if tech in ptpvb) \
                    + sum(model.SupplyPrice[(reg, s, tech, y, step)] * model.Generation[(tech, y, reg, step, hr)] for
                          (tech, y, reg, step) in model.GenSetByHour[hr]) \
                    + sum((model.RampUp_Cost[tech] * model.RampUp[(tech, y, reg, step, hr)]) + (
                        model.RampDown_Cost[tech] * model.RampDown[(tech, y, reg, step, hr)]) for (tech, y, reg, step)
                          in model.RampSetByHour[hr]) \
                ) for hr in model.hr if (s := all_frames['Map']['s'][hr - 1])))


model.totalCost = pyo.Objective(rule=objFunction, sense=pyo.minimize)

####################################################################################################################
#Constraints

model.GenSetDemandBalance = {}
model.StorageSetADemandBalance = {}
model.StorageSetBDemandBalance = {}


def populate_demand_balance_sets_rule(m):
    for (tech, year, reg, step, hour) in all_frames['GenSet'].loc(axis=0)[:, :, :, :, :].index:
        if (year, reg, hour) not in m.GenSetDemandBalance:
            m.GenSetDemandBalance[(year, reg, hour)] = []  # TBD- collapse with default key value
        m.GenSetDemandBalance[(year, reg, hour)].append((tech, step))
    for (tech, year, reg, step, hour) in all_frames['StorageSet'].loc(axis=0)[:, :, :, :, :].index:
        if tech in ptn:
            if (year, reg, hour) not in m.StorageSetADemandBalance:
                m.StorageSetADemandBalance[(year, reg, hour)] = []
            m.StorageSetADemandBalance[(year, reg, hour)].append((tech, step))
        if tech in ptpvb:
            if (year, reg, hour) not in m.StorageSetBDemandBalance:
                m.StorageSetBDemandBalance[(year, reg, hour)] = []
            m.StorageSetBDemandBalance[(year, reg, hour)].append((tech, step))

model.populate_demand_balance_sets = pyo.BuildAction(rule=populate_demand_balance_sets_rule)

# Property: ShadowPrice
@model.Constraint(model.LoadSet)
def Demand_balance(model, r, y, hr):
    return model.Load_EMMRen[(r, y, hr)] <= \
        sum(model.Generation[(tech, y, r, step, hr)] for (tech, step) in model.GenSetDemandBalance[(y, r, hr)]) \
        + sum(model.Storage_outflow[(tech, y, r, step, hr)] - model.Storage_inflow[(tech, y, r, step, hr)] for
              (tech, step) in model.StorageSetADemandBalance[(y, r, hr)]) \
        + sum(model.Storage_outflow[(tech, y, r, step, hr)] for (tech, step) in
              model.StorageSetBDemandBalance[(y, r, hr)]) \
        + model.unmet_Load[(r, y, hr)]

#First hour
@model.Constraint(all_frames['GenSet'].loc(axis=0)[[i for i in ptc if i in all_frames['GenSet'].index.get_level_values(0)],:,:,:,hr1].index)
def FirstHour_gen_ramp(model, ptc, y, r, steps, hr1):
    return model.Generation[(ptc,y,r,steps,hr1)] == \
        model.Generation[(ptc,y,r,steps,hr1+23)] + model.RampUp[(ptc,y,r,steps,hr1)] - model.RampDown[(ptc,y,r,steps,hr1)]

#NOT first hour
@model.Constraint(all_frames['GenSet'].loc(axis=0)[[i for i in ptc if i in all_frames['GenSet'].index.get_level_values(0)],:,:,:,hr23].index)
def Gen_ramp(model, ptc, y, r, steps, hr23):
    return model.Generation[(ptc,y,r,steps,hr23)] == \
        model.Generation[(ptc,y,r,steps,hr23-1)] + model.RampUp[(ptc,y,r,steps,hr23)] - model.RampDown[(ptc,y,r,steps,hr23)]

# #First hour
@model.Constraint(all_frames['StorageSet'].loc(axis=0)[:,:,:,:,hr1].index)
def FirstHourStorageBalance2(model, pts, y, r, steps, hr1):
    return model.Storage_level[(pts,y,r,steps,hr1)] == model.Storage_level[(pts,y,r,steps,hr1+23)] + \
        model.BatteryEfficiency[pts] * model.Storage_inflow[(pts,y,r,steps,hr1)] - model.Storage_outflow[(pts,y,r,steps,hr1)]

# #Not first hour
@model.Constraint(all_frames['StorageSet'].loc(axis=0)[:,:,:,:,hr23].index)
def StorageBalance(model, pts, y, r, steps, hr23):
    return model.Storage_level[(pts,y,r,steps,hr23)] == model.Storage_level[(pts,y,r,steps,hr23-1)] + \
        model.BatteryEfficiency[pts] * model.Storage_inflow[(pts,y,r,steps,hr23)] - model.Storage_outflow[(pts,y,r,steps,hr23)]

@model.Constraint(all_frames['SupplyCurveMonths'].loc(axis=0)[:,:,:,1,:].index)
def Hydro_Gen_Cap(model, pth, y, r, steps, m):
    return sum(model.Generation[pth,y,r,steps,hr] * model.Idaytq[m,all_frames['MapHrIndex'].loc[hr].dm] for hr in all_frames['Map'].loc[all_frames['Map'].m==m].hr) <= \
        (model.SupplyCurve[r,all_frames['Map_ms'].loc[m].s,pth,y,1] * model.HydroCapFactor[m,r]) * sum(model.Idaytq[m,d] for d in model.d)  * 24
#off by factor of 48 for some reason. I added in a temporary fix
        #sum(model.Map_ms[m, s] * model.SupplyCurve[pth, r, s, 1, y] * model.HydroCapFactor[m, r] for s in model.s) * sum(model.Idaytq[d, m] for d in model.d) * 24

#PVBatt_maxCF = max generation (inverter capacity)
@model.Constraint(all_frames['StorageSet'].loc(axis=0)[ptpvb,:,:,:,:].index)
def PVBattery_balance(model, ptpvb, y, r, steps, hr):
    return model.Generation[(ptpvb,y,r,steps,hr)] + model.Storage_outflow[(ptpvb,y,r,steps,hr)] <= all_frames['StorageSet'].loc(axis=0)[ptpvb,y,r,steps,hr].SupplyCurve

#kW PV to grid + kW PV to Batt <= PV available (unclipped by inverter)
@model.Constraint(all_frames['GenerationMaxTotal'].index)
def PVBattery_balance2(model, ptpvb, y, r, steps, hr):
    return model.Generation[(ptpvb,y,r,steps,hr)] + model.Storage_inflow[(ptpvb,y,r,steps,hr)] <= all_frames['GenerationMaxTotal'].loc(axis=0)[ptpvb,y,r,steps,hr].GenerationMaxTotal

####################################################################################################################
#Constraints Generation Variable Upper Bounds

@model.Constraint(all_frames['GenSet'].loc(axis=0)[[i for i in ptc if i in all_frames['GenSet'].index.get_level_values(0)],:,:,:,:].index)
def ptc_upper(model, ptc, y, r, steps, hr):
    return model.Generation[(ptc,y,r,steps,hr)] <= \
        model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],ptc,y,steps)] * model.CapacityFactor[(ptc,y,r,steps,hr)]

@model.Constraint(all_frames['GenSet'].loc(axis=0)[[i for i in ptr if i in all_frames['GenSet'].index.get_level_values(0)],:,:,:,:].index)
def ptr_upper(model, ptr, y, r, steps, hr):
    return model.Generation[(ptr,y,r,steps,hr)] <= \
        model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],ptr,y,steps)] * model.CapacityFactor[(ptr,y,r,steps,hr)]

@model.Constraint(all_frames['GenSet'].loc(axis=0)[[i for i in pth if i in all_frames['GenSet'].index.get_level_values(0)],:,:,2,:].index)
def pth_upper(model, pth, y, r, steps, hr):
    return model.Generation[(pth,y,r,steps,hr)] <= \
        model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],pth,y,steps)] * model.HydroCapFactor[(all_frames['Map']['m'][hr-1],r)]

@model.Constraint(ptipvUpperSet.loc(axis=0)[[i for i in ptipv if i in list(sparseSet.pt)],:,:,:,:].index)
def ptipv_upper(model, ptipv, y, r, steps, hr):
    return model.Generation[(ptipv,y,r,steps,hr)] <= \
        model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],ptipv,y,steps)] * ptipvUpperSet.loc(axis=0)[ptipv,y,r,steps,hr].SolWindCapFactor

@model.Constraint(all_frames['StorageSet'].loc(axis=0)[13,:,:,:,:].index)
def Storage_level_13_upper(model, pt, y, r, steps, hr):
    return model.Storage_level[(pt, y, r, steps, hr)] <= model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],pt,y,steps)] * model.HourstoBuy

@model.Constraint(all_frames['StorageSet'].loc(axis=0)[11,:,:,:,:].index)
def Storage_level_11_upper(model, pt, y, r, steps, hr):
    return model.Storage_level[(pt, y, r, steps, hr)] <= model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],pt,y,steps)] * 12

@model.Constraint(all_frames['StorageSet'].loc(axis=0)[21,:,:,:,:].index)
def Storage_level_21_upper(model, pt, y, r, steps, hr):
    return model.Storage_level[(pt, y, r, steps, hr)] <= model.SupplyCurve[(r,all_frames['Map']['s'][hr-1],pt,y,steps)] * model.HourstoBuy / 3

# #Constraint forces no generation at ptn, so the index for generation at ptn can be removed instead
#@model.Constraint(all_frames['GenSet'].loc(axis=0)[ptn,:,:,:,:].index)
#def ptn_upper(model, ptn, y, steps, hr):
#    return model.Generation[(ptn,y,r,steps,hr)] <= 0

####################################################################################################################
gc.disable()
#Solve
instance = model.create_instance(formatData(all_frames))
timer.toc('build model finished')
opt = pyo.SolverFactory("appsi_highs")
opt_success = opt.solve(instance)#.write()
timer.toc('solve model finished')
print()
#instance.pprint()

#Check
#Objective Value
obj_val = pyo.value(instance.totalCost)
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

RampUp = pd.Series(instance.RampUp.get_values()).to_frame().reset_index().rename(columns={'level_0':'ptc', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'RampUp'})
RampDown = pd.Series(instance.RampDown.get_values()).to_frame().reset_index().rename(columns={'level_0':'ptc', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'RampDown'})
Storage_inflow = pd.Series(instance.Storage_inflow.get_values()).to_frame().reset_index().rename(columns={'level_0':'pts', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Storage_inflow'})
Storage_outflow = pd.Series(instance.Storage_outflow.get_values()).to_frame().reset_index().rename(columns={'level_0':'pts', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Storage_outflow'})
Storage_level = pd.Series(instance.Storage_level.get_values()).to_frame().reset_index().rename(columns={'level_0':'pts', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Storage_level'})
Generation = pd.Series(instance.Generation.get_values()).to_frame().reset_index().rename(columns={'level_0':'pt', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Generation'})
unmet_Load = pd.Series(instance.unmet_Load.get_values()).to_frame().reset_index().rename(columns={'level_0':'r', 'level_1':'y', 'level_2':'hr', 0:'unmet_Load'})

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
file.write('\nSparse: Start Time: ' + datetime.strftime(start_time,"%m/%d/%Y %H:%M") + ', Run Time: ' + str(round(run_time.total_seconds()/60,2)) + ' mins')
file.close()
timer.toc('postprocessor finished')
print()
