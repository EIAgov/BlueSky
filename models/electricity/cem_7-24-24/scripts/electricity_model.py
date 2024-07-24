#Electricity Dispatch Model - Based on Restore Module within NEMS

####################################################################################################################
#Setup

#Import pacakges
import os
import sys
from datetime import datetime
import numpy as np
import pandas as pd
import pyomo.environ as pyo
import gc
import highspy
from pyomo.common.timing import TicTocTimer
from pyomo.opt import SolutionStatus, SolverStatus, TerminationCondition
from pyomo.util.infeasible import log_close_to_bounds, log_infeasible_constraints, find_infeasible_constraints
import common.common as com
import common.common_debug as com_bug
import logging

#import scripts
import preprocessor as prep
import postprocessor as post

### Setup Logging

# Delete old log
log_name = 'elec_debug.log'

try:
    os.remove(log_name)
except:
    pass

# Configure Logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig( level=logging.INFO, #change this to logging.DEBUG for more details
                    format='[%(asctime)s][%(name)s]' +
                           '[%(funcName)s][%(levelname)s]  :: |%(message)s|',
                    handlers=[logging.FileHandler(log_name),
                              logging.StreamHandler()])

logger = logging.getLogger(__name__)

####################################################################################################################
#MODEL

class PowerModel(pyo.ConcreteModel):
    """A PowerModel instance"""

    def __init__(self, all_frames, setA, *args, **kwargs):
        """
        Build a PowerModel instance
        :param data: some kind of data...
        """
        super().__init__(*args, **kwargs)
        

        ####################################################################################################################
        #Switches
        # TODO: figure out why certain year/region combos are unbounded
        # TODO: add test_region and years to scedes file
        
        self.sw_trade =     setA.sw_trade
        self.sw_expansion = setA.sw_expansion
        self.sw_agg_years = setA.sw_agg_years
        self.sw_rm =        setA.sw_rm
        self.sw_ramp =      setA.sw_ramp
        self.sw_reserves =  setA.sw_reserves
        self.sw_learning =  setA.sw_learning #0 = no learning, 1= linear iterations with full expression, 2= linear iterations with taylor series, 3= nonlinear
        self.sw_h2int = 0
        
        ####################################################################################################################
        #Sets

        self.cols_dict = {}

        self.hr = pyo.Set(initialize = setA.hr) #change hours (1-48) or (1-577)?
        self.day = pyo.Set(initialize = setA.day)
        self.y = pyo.Set(initialize = setA.y)
        self.s = pyo.Set(initialize = setA.s)

        self.r = pyo.Set(initialize = range(1,26))
        self.r_can = pyo.Set(initialize = range(29,34))

        self.UnmetSet = self.r * self.y * self.hr
        self.cols_dict['UnmetSet'] = ['UnmetSet','r','y','hr']

        #Create sparse sets 

        index_list = ['pt','y','r','steps','hr'] 

        def declare_set(sname,df):
            sset = pyo.Set(initialize = df.index)
            scols = list(df.reset_index().columns)
            scols = scols[-1:] + scols[:-1]
            self.cols_dict[sname] = scols

            return sset

        def create_subsets(df,col,subset):
            df = df[df[col].isin(subset)].dropna()
            return df

        def create_hourly_sets(df):
            df = pd.merge(df,
                        all_frames['Map_hr_s'].reset_index(),
                        on=['s'], how='left').drop(columns=['s'])
            return df

        self.SupplyPriceSet = declare_set('SupplyPriceSet', all_frames['SupplyPrice'])
        self.SupplyCurveSet = declare_set('SupplyCurveSet', all_frames['SupplyCurve'])

        self.GenSet = declare_set('GenSet', create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptg)).set_index(index_list))
        
        self.ptd_upper_set = declare_set('ptd_upper_set', create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptd)).set_index(index_list))
        
        self.pth_upper_set = declare_set('pth_upper_set', create_hourly_sets(create_subsets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pth),'steps',[2])).set_index(index_list))
        
        self.Gen_ramp_set = declare_set('Gen_ramp_set', create_subsets(create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptc)),'hr',setA.hr23).set_index(index_list))
        
        self.FirstHour_gen_ramp_set = declare_set('FirstHour_gen_ramp_set', create_subsets(create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptc)),'hr',setA.hr1).set_index(index_list))
        
        self.HydroSet = declare_set('HydroSet', all_frames['HydroCapFactor'])
        self.IdaytqSet = declare_set('IdaytqSet', all_frames['Idaytq'])
        self.LoadSet = declare_set('LoadSet', all_frames['Load'])

        self.StorageSet = declare_set('StorageSet', create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pts)).set_index(index_list))
                
        self.H2GenSet = declare_set('H2GenSet', create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pth2)).set_index(index_list))
        
        self.HydroMonthsSet = declare_set('HydroMonthsSet', create_subsets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pth),'steps',[1]
            ).drop(columns=['steps']).set_index(['pt','y','r','s']))
        
        self.StorageBalance_set = declare_set('StorageBalance_set',create_subsets(create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pts)),'hr',setA.hr23).set_index(index_list))

        self.FirstHourStorageBalance_set = declare_set('FirstHourStorageBalance_set',create_subsets(create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pts)),'hr',setA.hr1).set_index(index_list))

        self.ptiUpperSet = declare_set('ptiUpperSet',all_frames['ptiUpperSet'])        
        self.H2PriceSet = declare_set('H2PriceSet',all_frames['H2Price'])

        def capacitycredit_df():
            df = create_hourly_sets(all_frames['SupplyCurve'].reset_index())
            df = pd.merge(df,all_frames['ptiUpperSet'].reset_index(),how='left',on=index_list
                          ).rename(columns={'SolWindCapFactor':'CapacityCredit'})
            df['CapacityCredit'] = df['CapacityCredit'].fillna(1)
            df2 = pd.merge(all_frames['HydroCapFactor'].reset_index(),all_frames['Map_hr_s'].reset_index(),
                        on=['s'], how='left').drop(columns=['s'])
            df2['pt'] = setA.pth[0]
            df = pd.merge(df,df2,how='left',on=['pt','r','hr'])
            df.loc[df['pt'].isin(setA.pth),'CapacityCredit'] = df['HydroCapFactor']
            df = df.drop(columns=['SupplyCurve','HydroCapFactor']).set_index(index_list)
            return df

        if self.sw_expansion:
            if self.sw_learning > 0:
                self.LearningRateSet = declare_set('LearningRateSet',all_frames['LearningRate'])
                self.CapCost0Set = declare_set('CapCost0Set',all_frames['CapCost_y0'])
                self.LearningPtSet = declare_set('LearningPtSet',all_frames['SupplyCurve_learning'])
            self.CapCostSet = declare_set('CapCostSet',all_frames['CapCost'])
            self.FOMCostSet = declare_set('FOMCostSet',all_frames['FOMCost'])
            self.allowBuildsSet = declare_set('allowBuildsSet',all_frames['allowBuilds'])
            self.RetSet = declare_set('RetSet',all_frames['RetSet'])
            self.CapacityCreditSet = declare_set('CapacityCreditSet',capacitycredit_df())

        if self.sw_trade:
            self.TranCostSet = declare_set('TranCostSet',all_frames['TranCost'])
            self.TranLimitSet = declare_set('TranLimitSet',all_frames['TranLimit'])
            self.TradeSet = declare_set('TradeSet',create_hourly_sets(
                all_frames['TranLimit'].reset_index()).set_index(['r', 'r1', 'y', 'hr']))
            
            self.TranCostCanSet = declare_set('TranCostCanSet',all_frames['TranCostCan'])

            self.TranLimitCanSet = declare_set('TranLimitCanSet',create_hourly_sets(
                all_frames['TranLimitCan'].reset_index()).set_index(['r1','CSteps','y','hr']))
            
            self.TranLineLimitCanSet = declare_set('TranLineLimitCanSet',create_hourly_sets(
                all_frames['TranLineLimitCan'].reset_index()).set_index(['r', 'r1', 'y', 'hr']))
            self.TradeCanSet = declare_set('TradeCanSet',
                pd.merge(
                    create_hourly_sets(all_frames['TranLimitCan'].reset_index()), 
                    create_hourly_sets(all_frames['TranLineLimitCan'].reset_index()), 
                    how="inner").drop(columns=['TranLimitCan']).set_index(['r', 'r1', 'y','CSteps', 'hr']))

        if self.sw_ramp:
            self.RampUp_CostSet = declare_set('RampUp_CostSet',all_frames['RampUp_Cost'])
            self.RampRateSet = declare_set('RampRateSet',all_frames['RampRate'])

            self.RampSet = declare_set('RampSet',create_hourly_sets(
                create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptc)).set_index(index_list))

        if self.sw_reserves:
            self.ProcurementSet = declare_set('ProcurementSet',
                pd.merge(create_hourly_sets(all_frames['SupplyCurve'].reset_index()),
                         pd.DataFrame({'restypes': setA.restypes}),
                         how='cross').set_index(['restypes']+index_list))
            
            self.RegReservesCostSet = declare_set('RegReservesCostSet',all_frames['RegReservesCost'])
            self.ResTechUpperBoundSet = declare_set('ResTechUpperBoundSet',all_frames['ResTechUpperBound'])

        ####################################################################################################################
        #Parameters

        self.Storagelvl_cost = pyo.Param(initialize = 0.00000001)
        self.Storagelvl_cost_col = ['Storagelvl_cost','None']
        self.cols_dict['Storagelvl_cost'] = self.Storagelvl_cost_col
        
        self.UnmetLoad_penalty = pyo.Param(initialize = 500)
        self.UnmetLoad_penalty_col = ['UnmetLoad_penalty','None']
        self.cols_dict['UnmetLoad_penalty'] = self.UnmetLoad_penalty_col
        
        def declare_param(pname,p_set,df,default=0,mutable=False):
            param = pyo.Param(p_set, initialize = df, default=default, mutable=mutable)
            pcols = list(df.reset_index().columns)
            pcols = pcols[-1:] + pcols[:-1]
            self.cols_dict[pname] = pcols

            return param

        self.Idaytq =           declare_param('Idaytq', self.IdaytqSet, all_frames['Idaytq'])
        self.Load =             declare_param('Load', self.LoadSet, all_frames['Load'])
        self.HydroCapFactor =   declare_param('HydroCapFactor', self.HydroSet, all_frames['HydroCapFactor'])
        
        self.BatteryChargeCap = declare_param('BatteryChargeCap', self.StorageSet, create_hourly_sets(
            create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pts)).set_index(index_list))
        
        self.BatteryEfficiency =declare_param('BatteryEfficiency', setA.pts, all_frames['BatteryEfficiency'])
        self.HourstoBuy =       declare_param('HourstoBuy', setA.pts, all_frames['HourstoBuy'])
        self.Dayweights =       declare_param('Dayweights',self.hr, all_frames['Dayweights'])
        self.SupplyPrice =      declare_param('SupplyPrice', self.SupplyPriceSet, all_frames['SupplyPrice'])
        self.SupplyCurve =      declare_param('SupplyCurve', self.SupplyCurveSet, all_frames['SupplyCurve'])
        self.SolWindCapFactor = declare_param('SolWindCapFactor', self.ptiUpperSet, all_frames['ptiUpperSet']) 
        self.H2Price =          declare_param('H2Price', self.H2PriceSet, all_frames['H2Price'], mutable=True) #eventually connect with H2 model

        self.year_weights =     declare_param('year_weights', self.y, all_frames['year_weights'])
        self.Map_hr_s =         declare_param('Map_hr_s', self.hr, all_frames['Map_hr_s']) #all_frames['Map_hr_s'].loc[hr]['s']
        self.Hr_weights =       declare_param('Hr_weights', self.hr, all_frames['Hr_weights']['Hr_weights']) #all_frames['Hr_weights']['Hr_weights'][hr]
        self.Map_hr_d =         declare_param('Map_hr_d', self.hr, all_frames['Map_hr_d']['day'])

        if self.sw_expansion:
            # if learning is not to be solved nonlinearly directly in the obj
            if self.sw_learning < 3:
                if self.sw_learning == 0:
                    mute = False
                else:
                    mute = True
                self.capacity_costs_learning = declare_param(
                    'capacity_costs_learning', self.CapCostSet, all_frames['CapCost'], mutable=mute)
                
            # if learning is on
            if self.sw_learning > 0:
                self.LearningRate =        declare_param('LearningRate', self.LearningRateSet, all_frames['LearningRate'])
                self.CapCost_y0 =          declare_param('CapCost_y0', self.CapCost0Set, all_frames['CapCost_y0'])
                
                self.SupplyCurve_learning =declare_param(
                    'SupplyCurve_learning', self.LearningPtSet, all_frames['SupplyCurve_learning'])
            
            self.FOMCost =          declare_param('FOMCost', self.FOMCostSet, all_frames['FOMCost'])
            self.CapacityCredit =   declare_param('CapacityCredit', self.CapacityCreditSet, capacitycredit_df())

        if self.sw_trade:
            self.TranCost =         declare_param('TranCost', self.TranCostSet, all_frames['TranCost'])
            self.TranLimit =        declare_param('TranLimit', self.TranLimitSet, all_frames['TranLimit'])
            self.TranCostCan =      declare_param('TranCostCan', self.TranCostCanSet, all_frames['TranCostCan'])
            
            self.TranLimitCan =     declare_param('TranLimitCan', self.TranLimitCanSet, create_hourly_sets(
                all_frames['TranLimitCan'].reset_index()).set_index(['r1','CSteps','y','hr']))

            self.TranLineLimitCan = declare_param('TranLineLimitCan', self.TranLineLimitCanSet, create_hourly_sets(
                all_frames['TranLineLimitCan'].reset_index()).set_index(['r', 'r1', 'y', 'hr']))
        
        if self.sw_rm:
            self.ReserveMargin =    declare_param('ReserveMargin', self.r, all_frames['ReserveMargin'])
            
        if self.sw_ramp:
            self.RampUp_Cost =      declare_param('RampUp_Cost', self.RampUp_CostSet, all_frames['RampUp_Cost'])
            self.RampDown_Cost =    declare_param('RampDown_Cost', self.RampUp_CostSet, all_frames['RampDown_Cost'])
            self.RampRate =         declare_param('RampRate', self.RampRateSet, all_frames['RampRate'])

        if self.sw_reserves:
            self.RegReservesCost =  declare_param('RegReservesCost', self.RegReservesCostSet, all_frames['RegReservesCost'])
            self.ResTechUpperBound =declare_param('ResTechUpperBound', self.ResTechUpperBoundSet, all_frames['ResTechUpperBound'])
        
        
        ####################################################################################################################
        #Variables
        
        def declare_var(vname,sname,v_set):
            var = pyo.Var(v_set, within=pyo.NonNegativeReals) 
            vcols = [vname] + self.cols_dict[sname][1:]
            self.cols_dict[vname] = vcols
            return var

        self.Storage_inflow =   declare_var('Storage_inflow','StorageSet',self.StorageSet) 
        self.Storage_outflow =  declare_var('Storage_outflow','StorageSet',self.StorageSet)
        self.Storage_level =    declare_var('Storage_level','StorageSet',self.StorageSet)
        self.Generation =       declare_var('Generation','GenSet',self.GenSet)
        self.unmet_Load =       declare_var('unmet_Load','UnmetSet',self.UnmetSet)
        self.TotalCapacity =    declare_var('TotalCapacity','SupplyCurveSet',self.SupplyCurveSet)

        if self.sw_expansion:
            self.CapacityBuilds = declare_var('CapacityBuilds','CapCostSet',self.CapCostSet)
            self.CapacityRetirements = declare_var('CapacityRetirements','RetSet',self.RetSet)

        if self.sw_trade:
            self.TradeToFromCan = declare_var('TradeToFromCan','TradeCanSet',self.TradeCanSet)
            
            #TODO: Move Trade_upper to constraints
            def Trade_upper(self, r, r1, y, hr):
                return (0, self.TranLimit[(r, r1, self.Map_hr_s[hr], y)] * self.Hr_weights[hr])

            self.TradeToFrom = pyo.Var(self.TradeSet, within=pyo.NonNegativeReals, bounds = Trade_upper)
            self.cols_dict['TradeToFrom'] = ['TradeToFrom'] + self.cols_dict['TradeSet'][1:]

        if self.sw_rm:
            self.AvailStorCap = declare_var('AvailStorCap','StorageSet',self.StorageSet)
            
        if self.sw_ramp:
            self.RampUp = declare_var('RampUp','RampSet',self.RampSet)
            self.RampDown = declare_var('RampDown','RampSet',self.RampSet)

        if self.sw_reserves:
            self.ReservesProcurement = declare_var('ReservesProcurement','ProcurementSet',self.ProcurementSet)
            

        ####################################################################################################################
        def populate_sets_rule(m1, sname, set_base_name = '', set_base2 = []):
            set_in = getattr(m1, sname)
            scols = m1.cols_dict[sname][1:]
            
            if set_base_name == '':
                scol_base =np.array( [s in set_base2 for s in scols], 
                                    dtype=bool)
                scols2 = list(np.array(scols)[scol_base])
                scol_base_order =np.array( [scols2.index(s) for s in set_base2])
                m1.set_out = {}
            else:
                set_base = getattr(m1, set_base_name)
                m1.set_out = pyo.Set(m1.hr)
                scol_base = np.array( [s == set_base_name for s in scols], 
                                    dtype=bool)
                
            for i in set_in:
                i = np.array(i)
                rest_i = tuple(i[~scol_base])
                if set_base_name == '':
                    base_i = tuple(i[scol_base][scol_base_order])
                    if base_i not in m1.set_out:
                        m1.set_out[base_i] = []  
                    m1.set_out[base_i].append(rest_i)
                else:
                    base_i = int(i[scol_base][0])

                    m1.set_out[base_i].add(rest_i)
            set_out = m1.set_out        
            m1.del_component('set_out')
            return(set_out)
        
        #Objective Function

        def populate_by_hour_sets_rule(m):
            m.StorageSetByHour = populate_sets_rule(m, 'StorageSet',set_base_name = 'hr')
            m.GenSetByHour = populate_sets_rule(m, 'GenSet', set_base_name = 'hr')
            m.H2GenSetByHour = populate_sets_rule(m, 'H2GenSet', set_base_name = 'hr')
                    
        self.populate_by_hour_sets = pyo.BuildAction(rule=populate_by_hour_sets_rule)

        #Variable Objectivefunction
        #make sure to correct all costs to multiply by year weights
        def dispatchCost(self):
            return sum(self.Dayweights[hr] * (
                        sum(self.year_weights[y] * (0.5 * self.SupplyPrice[(reg,s,tech,step,y)] \
                            * (self.Storage_inflow[(tech,y,reg,step,hr)] + self.Storage_outflow[(tech,y,reg,step,hr)]) \
                            + (self.Hr_weights[hr] * self.Storagelvl_cost) \
                            * self.Storage_level[(tech,y,reg,step,hr)]) \
                            for (tech, y, reg, step) in self.StorageSetByHour[hr]) \
                        + sum(self.year_weights[y] * self.SupplyPrice[(reg,s,tech,step,y)]
                                                      * self.Generation[(tech, y, reg, step, hr)] \
                              for (tech, y, reg, step) in self.GenSetByHour[hr]) 
                        + sum(self.year_weights[y] * self.H2Price[reg,s,tech,step,y] * setA.H2_heatrate \
                        * self.Generation[(tech, y, reg, 1, hr)] \
                      for (tech, y, reg, step) in self.H2GenSetByHour[hr])\
                ) for hr in self.hr if (s := self.Map_hr_s[hr])) 
            
        self.dispatchCost = pyo.Expression(expr=dispatchCost)

        def unmetLoadCost(self):
            return sum(self.Dayweights[hour] *
                        self.year_weights[y] * self.unmet_Load[(reg, y, hour)] * self.UnmetLoad_penalty \
                            for (reg, y, hour) in self.UnmetSet)
        self.unmetLoadCost = pyo.Expression(expr=unmetLoadCost)

        if self.sw_trade:
            def tradeCost(self):
                return sum(self.Dayweights[hour] * self.year_weights[y] * self.TradeToFrom[(reg,reg1,y,hour)] * self.TranCost[(reg,reg1,y)] \
                                  for (reg,reg1,y,hour) in self.TradeSet) \
                            + sum(self.Dayweights[hour] * self.year_weights[y] * self.TradeToFromCan[(reg, reg_can, y, CSteps, hour)] * self.TranCostCan[(reg, reg_can, CSteps, y)] \
                                  for(reg, reg_can, y, CSteps, hour) in self.TradeCanSet)
            self.tradeCost = pyo.Expression(expr=tradeCost)


        if self.sw_ramp: #ramping
            def RampCost(self):
                return sum(self.Dayweights[hour] * self.year_weights[y] * (self.RampUp[(ptc, y, reg, step, hour)] * self.RampUp_Cost[ptc]
                           + self.RampDown[(ptc, y, reg, step, hour)] * self.RampDown_Cost[ptc]) \
                           for (ptc, y, reg, step, hour) in self.RampSet)
            self.RampCost = pyo.Expression(expr=RampCost)

        if self.sw_expansion:
            
            # nonlinear expansion costs
            if self.sw_learning == 3:
                
                def capExpansionCost(self): #TODO: not sure if I need self.year_weights[y] weighting here, I don't think so but maybe?
                    return sum((self.CapCost_y0[(reg, pt, step)] \
             * (((self.SupplyCurve_learning[pt]  \
                  + 0.0001*(y - setA.start_year)
                  + sum(sum(self.CapacityBuilds[(r, pt, year, steps)] for year in setA.y if year < y) 
                        for (r, tech, steps) in self.CapCost0Set if tech == pt)) \
                  / self.SupplyCurve_learning[pt]) \
                ** (-1.0*self.LearningRate[pt])) )
                 * self.CapacityBuilds[(reg,pt,y,step)] \
                               for (reg,pt,y,step) in self.CapCostSet)
                self.capExpansionCost = pyo.Expression(expr=capExpansionCost)
            else: #linear expansion costs
            
                def capExpansionCost(self): #TODO: not sure if I need self.year_weights[y] weighting here, I don't think so but maybe?
                    return sum(self.capacity_costs_learning[(reg,pt,y,step)] * self.CapacityBuilds[(reg,pt,y,step)] \
                               for (reg,pt,y,step) in self.CapCostSet)
                self.capExpansionCost = pyo.Expression(expr=capExpansionCost)

            # choosing summer for capacity, may want to revisit this assumption
            def FOMCostObj(self):
                return sum(self.year_weights[y] * self.FOMCost[(reg, pt, steps)] \
                           * self.TotalCapacity[(reg, s, pt, steps, y)]  \
                                  for (reg,s,pt,steps,y) in self.SupplyCurveSet if s==2) #need to fix this weighting

            self.FOMCostObj = pyo.Expression(expr=FOMCostObj)

        if self.sw_reserves: # operating reserves
            def opresCost(self):
                return sum( (self.RegReservesCost[pt] if restype == 2 else 0.01)
                            * self.Dayweights[hr] * self.year_weights[y] \
                            * self.ReservesProcurement[(restype, pt, y, r, steps, hr)] \
                                    for (restype, pt, y, r, steps, hr) in self.ProcurementSet)
            self.opresCost = pyo.Expression(expr=opresCost)

        def objFunction(self):
            return (self.dispatchCost + self.unmetLoadCost
                    + (self.RampCost if self.sw_ramp else 0)
                    + (self.tradeCost if self.sw_trade else 0)
                    + (self.capExpansionCost + self.FOMCostObj if self.sw_expansion else 0)
                    + (self.opresCost if self.sw_reserves else 0)
                    )
                
        self.totalCost = pyo.Objective(rule=objFunction, sense = pyo.minimize)

        ####################################################################################################################
        #Constraints


        def populate_demand_balance_sets_rule(m):
            m.GenSetDemandBalance = populate_sets_rule(m, 'GenSet', set_base2 = ['y','r','hr'])
            m.StorageSetDemandBalance = populate_sets_rule(m, 'BatteryChargeCap', set_base2 = ['y','r','hr'])

            if m.sw_trade == 1:
                m.TradeSetDemandBalance = populate_sets_rule(m, 'TradeSet', set_base2 = ['y','r','hr'])
                m.TradeCanSetDemandBalance = populate_sets_rule(m, 'TradeCanSet', set_base2 = ['y','r','hr'])
                
        self.populate_demand_balance_sets = pyo.BuildAction(rule=populate_demand_balance_sets_rule)

        #Property: ShadowPrice
        @self.Constraint(self.LoadSet)
        def Demand_balance(self, r, y, hr):
            return self.Load[(r, y, hr)] <= \
                    sum(self.Generation[(tech, y, r, step, hr)] for (tech, step) in self.GenSetDemandBalance[(y, r, hr)]) \
                    + sum(self.Storage_outflow[(tech,y,r,step,hr)] - self.Storage_inflow[(tech,y,r,step,hr)] \
                        for (tech, step) in self.StorageSetDemandBalance[(y,r,hr)]) \
                    + self.unmet_Load[(r, y, hr)] \
                    + (sum(self.TradeToFrom[(r,reg1,y,hr)]*(1-setA.TransLoss) - self.TradeToFrom[(reg1,r,y,hr)] \
                        for (reg1) in self.TradeSetDemandBalance[(y, r, hr)]) if self.sw_trade and r in setA.trade_regs else 0) \
                    + (sum(self.TradeToFromCan[(r, r_can, y, CSteps, hr)] * (1 - setA.TransLoss) \
                        for (r_can, CSteps) in self.TradeCanSetDemandBalance[(y, r, hr)]) if (self.sw_trade == 1 and r in setA.r_can_conn) else 0)

        # #First hour
        @self.Constraint(self.FirstHourStorageBalance_set)
        def FirstHourStorageBalance(self, pts, y, r, steps, hr1):
            return self.Storage_level[(pts,y,r,steps,hr1)] == self.Storage_level[(pts,y,r,steps,hr1 + setA.num_hr_day-1)] \
                + self.BatteryEfficiency[pts] * self.Storage_inflow[(pts,y,r,steps,hr1)] - self.Storage_outflow[(pts,y,r,steps,hr1)]

        # #Not first hour
        @self.Constraint(self.StorageBalance_set)
        def StorageBalance(self, pts, y, r, steps, hr23):
            return self.Storage_level[(pts,y,r,steps,hr23)] == self.Storage_level[(pts,y,r,steps,hr23-1)] \
                + self.BatteryEfficiency[pts] * self.Storage_inflow[(pts,y,r,steps,hr23)] - self.Storage_outflow[(pts,y,r,steps,hr23)]

        self.DaySHydro = pyo.Set(self.s)
        self.HourSHydro = pyo.Set(self.s)
        
        self.SWtHydro = pyo.Param(self.s, default=0, mutable=True)
        self.SWtHydro_cols = ['SWtHydro','s']
        self.cols_dict['SWtHydro'] = self.SWtHydro_cols

        def populate_hydro_sets_rule(m):
            for (s, hr) in all_frames['Map_hr_s'].reset_index().set_index(['s', 'hr']).index:
                m.HourSHydro[s].add(hr)
                m.SWtHydro[s] = m.SWtHydro[s] + m.Hr_weights[hr] * m.Idaytq[m.Map_hr_d[hr]]
            for (s, day) in all_frames['Map_day_s'].reset_index().set_index(['s', 'day']).index:
                m.DaySHydro[s].add(day)

        self.populate_hydro_sets = pyo.BuildAction(rule=populate_hydro_sets_rule)

        @self.Constraint(self.HydroMonthsSet)
        def Hydro_Gen_Cap(self, pth, y, r, s):
            return sum(self.Generation[pth, y, r, 1, hr] * \
                    self.Idaytq[self.Map_hr_d[hr]] \
                        for hr in self.HourSHydro[s]) \
                <= self.TotalCapacity[(r, s, pth, 1, y)] \
                    * self.HydroCapFactor[r, s] * self.SWtHydro[s]


        ####################################################################################################################
        #Constraints Generation Variable Upper Bounds

        @self.Constraint(self.ptd_upper_set)
        def ptd_upper(self, ptd, y, r, steps, hr):
            return (self.Generation[(ptd,y,r,steps,hr)]
                    + (sum(self.ReservesProcurement[(restype, ptd, y, r, steps, hr)]
                          for restype in setA.restypes) if self.sw_reserves else 0) \
                    <= \
                    self.TotalCapacity[(r, self.Map_hr_s[hr], ptd, steps, y)] \
                    * self.Hr_weights[hr])

        @self.Constraint(self.pth_upper_set)
        def pth_upper(self, pth, y, r, steps, hr):
            return ((self.Generation[(pth,y,r,steps,hr)] \
                        + sum(self.ReservesProcurement[(restype, pth, y, r, steps, hr)]
                              for restype in setA.restypes) if self.sw_reserves else 0) \
                    <= \
                    self.TotalCapacity[(r, self.Map_hr_s[hr], pth, steps, y)] \
                    * self.HydroCapFactor[(r, self.Map_hr_s[hr])] \
                    * self.Hr_weights[hr])

        @self.Constraint(self.ptiUpperSet)
        def pti_upper(self, pti, y, r, steps, hr):
            return (self.Generation[(pti,y,r,steps,hr)] \
                    + (sum(self.ReservesProcurement[(restype, pti, y, r, steps, hr)]
                          for restype in setA.restypes) if self.sw_reserves else 0) \
                    <= \
                    self.TotalCapacity[(r, self.Map_hr_s[hr], pti, steps, y)] \
                    * self.SolWindCapFactor[(pti,y,r,steps,hr)] \
                    * self.Hr_weights[hr])

        @self.Constraint(self.StorageSet)
        def Storage_inflow_upper(self, pt, y, r, steps, hr):
            return (self.Storage_inflow[(pt,y,r,steps,hr)] \
                    <= \
                    self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)] \
                        * self.Hr_weights[hr])

        # TODO check if it's only able to build in regions with existing capacity?
        @self.Constraint(self.StorageSet)
        def Storage_outflow_upper(self, pt, y, r, steps, hr):
            return (self.Storage_outflow[(pt,y,r,steps,hr)] \
                    + (sum(self.ReservesProcurement[(restype, pt, y, r, steps, hr)] \
                          for restype in setA.restypes) if self.sw_reserves else 0) \
                    <= \
                    self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)] \
                        * self.Hr_weights[hr])

        @self.Constraint(self.StorageSet)
        def Storage_level_upper(self, pt, y, r, steps, hr):
            return  self.Storage_level[(pt,y,r,steps,hr)] <= \
                     self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)] \
                        * self.HourstoBuy[(pt)]

        @self.Constraint(self.SupplyCurveSet)
        def totalCapacityEq(self, r, s, pt, steps, y):
                return self.TotalCapacity[(r, s, pt, steps, y)] == \
                    self.SupplyCurve[(r, s, pt, steps, y)] \
                     + (sum(self.CapacityBuilds[(r, pt, year, steps)] for year in setA.y if year <= y) \
                            if self.sw_expansion and (pt, steps) in self.allowBuildsSet else 0) \
                     - (sum(self.CapacityRetirements[(pt, year, r, steps)] for year in setA.y if year <= y) \
                            if self.sw_expansion and (pt, y, r, steps) in self.RetSet else 0)

        if self.sw_expansion:
            @self.Constraint(self.RetSet)
            def Ret_upper(self, pt, y, r, steps):
                return self.CapacityRetirements[(pt, y, r, steps)] <= \
                    ((self.SupplyCurve[(r, 2, pt, steps, y)] if (r, 2, pt, steps, y) in self.SupplyCurveSet else 0) \
                     + (sum(self.CapacityBuilds[(r, pt, year, steps)] for year in setA.y if year < y) \
                            if (pt, steps) in self.allowBuildsSet else 0) \
                     - sum(self.CapacityRetirements[(pt, year, r, steps)] for year in setA.y if year < y) \
                     )
                        
    
        ### trade upper bound

        if self.sw_trade and all_frames['TranLineLimitCan'].size != 0:
            def populate_trade_sets_rule(m):
                m.TradeCanLineSetUpper = populate_sets_rule(m, 'TradeCanSet', set_base2 = ['r','r1','y','hr'])
                m.TradeCanSetUpper = populate_sets_rule(m, 'TradeCanSet', set_base2 = ['r1','y', 'CSteps','hr'])

            self.populate_trade_sets = pyo.BuildAction(rule=populate_trade_sets_rule)

            @self.Constraint(self.TranLineLimitCanSet)
            def tradelinecan_upper(self, r, r_can, y, hr):
                return (sum(self.TradeToFromCan[(r, r_can, y, c, hr)] for c in self.TradeCanLineSetUpper[(r, r_can, y, hr)]) \
                        <= \
                    self.TranLineLimitCan[(r, r_can, y, hr)] * self.Hr_weights[hr])

            @self.Constraint(self.TranLimitCanSet)
            def tradecan_upper(self, r_can, CSteps, y, hr):
                return (sum(self.TradeToFromCan[(r,r_can,y,CSteps,hr)] for r in self.TradeCanSetUpper[(r_can, y, CSteps, hr)]) \
                        <= \
                    self.TranLimitCan[(r_can, CSteps,y, hr)] * self.Hr_weights[hr])

        if self.sw_expansion and self.sw_rm:
            # must meet reserve margin requirement
            # apply to every hour, a fraction above the final year's load
            # ReserveMarginReq <= sum(Max capacity in that hour)

            def populate_RM_sets_rule(m):
                m.SupplyCurveRM = populate_sets_rule(m, 'SupplyCurveSet', set_base2 = ['y','r','s'])

            self.populate_RM_sets = pyo.BuildAction(rule=populate_RM_sets_rule)

            @self.Constraint(self.LoadSet)
            def ReserveMarginLower(self, r, y, hr):
                return (self.Load[(r, y, hr)] * (1 + self.ReserveMargin[r]) \
                         <= \
                            self.Hr_weights[hr] \
                            * sum(
                                (self.CapacityCredit[(pt,y,r,steps,hr)] \
                                * (self.AvailStorCap[(pt, y, r, steps, hr)] if pt in setA.pts
                                   else self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)]) ) \
                                for (pt, steps) in self.SupplyCurveRM[(y, r, self.Map_hr_s[hr])]))
            
            # ensure available capacity to meet RM for storage < power capacity
            @self.Constraint(self.StorageSet)
            def AvailCapStor1_Upper(self, pts, y, r, steps, hr):
                return self.AvailStorCap[(pts, y, r, steps, hr)] <= \
                    self.TotalCapacity[(r, self.Map_hr_s[hr], pts, steps, y)]
            
            # ensure available capacity to meet RM for storage < existing SOC
            @self.Constraint(self.StorageSet)
            def AvailCapStor2_Upper(self, pts, y, r, steps, hr):
                return self.AvailStorCap[(pts, y, r, steps, hr)] <= \
                    self.Storage_level[(pts,y,r,steps,hr)]   

        if self.sw_ramp:
            #First hour
            @self.Constraint(self.FirstHour_gen_ramp_set)
            def FirstHour_gen_ramp(self, ptc, y, r, steps, hr1):
                return (self.Generation[(ptc,y,r,steps,hr1)] \
                    == self.Generation[(ptc,y,r,steps,hr1 + setA.num_hr_day-1)]
                        + self.RampUp[(ptc,y,r,steps,hr1)]
                        - self.RampDown[(ptc,y,r,steps,hr1)])

            # NOT first hour
            @self.Constraint(self.Gen_ramp_set)
            def Gen_ramp(self, ptc, y, r, steps, hr23):
                return (self.Generation[(ptc, y, r, steps, hr23)] \
                    == self.Generation[(ptc, y, r, steps, hr23 - 1)]
                        + self.RampUp[(ptc, y, r, steps, hr23)] - \
                        self.RampDown[(ptc, y, r, steps, hr23)])

            @self.Constraint(self.RampSet)
            def RampUp_upper(self, ptc, y, r, steps, hr):
                return self.RampUp[(ptc, y, r, steps, hr)] <= \
                    self.Hr_weights[hr] * self.RampRate[ptc] \
                    * self.TotalCapacity[(r, self.Map_hr_s[hr], ptc, steps, y)]


            @self.Constraint(self.RampSet)
            def RampDown_upper(self, ptc, y, r, steps, hr):
                return self.RampDown[(ptc, y, r, steps, hr)] <= \
                    self.Hr_weights[hr] * self.RampRate[ptc] \
                    * self.TotalCapacity[(r, self.Map_hr_s[hr], ptc, steps, y)]

        if self.sw_reserves:

            #wind set
            self.WindSetReserves = {}
            #solar set
            self.SolarSetReserves = {}
            def populate_reserves_sets_rule(m):
                m.ProcurementSetReserves = populate_sets_rule(m, 'ProcurementSet', set_base2 = ['restypes','r','y','hr'])
                #
                for (pt, year, reg, step, hour) in m.ptiUpperSet:
                    if (year, reg, hour) not in m.WindSetReserves:
                        m.WindSetReserves[(year, reg, hour)] = []
                    if (year, reg, hour) not in m.SolarSetReserves:
                        m.SolarSetReserves[(year, reg, hour)] = []

                    if pt in setA.ptw:
                        m.WindSetReserves[(year, reg, hour)].append((pt, step))
                    elif pt in setA.ptsol:
                        m.SolarSetReserves[(year, reg, hour)].append((pt, step))

            self.populate_reserves_sets = pyo.BuildAction(rule=populate_reserves_sets_rule)

            # 3% of load
            @self.Constraint(self.LoadSet)
            def spinReservesRequirement(self, r, y, hr):
                return (sum(self.ReservesProcurement[(1, pt, y, r, step, hr)]
                            for (pt, step) in self.ProcurementSetReserves[(1, r, y, hr)])
                        >= 0.03 * self.Load[(r, y, hr)])

            # 1% of load + 0.5% of wind generation + 0.3% of solar capacity
            @self.Constraint(self.LoadSet)
            def regReservesRequirement(self, r, y, hr):
                return (sum(self.ReservesProcurement[(2, pt, y, r, step, hr)]
                            for (pt, step) in self.ProcurementSetReserves[(2, r, y, hr)]) \
                        >= 0.01 * self.Load[(r, y, hr)] \
                        + 0.005 * sum(self.Generation[(ptw,y,r,step,hr)] \
                                    for (ptw, step) in self.WindSetReserves[(y, r, hr)]) \
                        + 0.003 * self.Hr_weights[hr]
                                * sum(self.TotalCapacity[(r, self.Map_hr_s[hr], ptsol, step, y)] \
                                    for (ptsol, step) in self.SolarSetReserves[(y, r, hr)]))

            #  10% of wind generation + 4% of solar capacity
            @self.Constraint(self.LoadSet)
            def flexReservesRequirement(self, r, y, hr):
                return (sum(self.ReservesProcurement[(3, pt, y, r, step, hr)]
                            for (pt, step) in self.ProcurementSetReserves[(3, r, y, hr)])
                        >= \
                    + 0.1 * sum(self.Generation[(ptw, y, r, step, hr)]
                                for (ptw, step) in self.WindSetReserves[(y, r, hr)]) \
                    + 0.04 * self.Hr_weights[hr] \
                                * sum(self.TotalCapacity[(r, self.Map_hr_s[hr], ptsol, step, y)] \
                                      for (ptsol, step) in self.SolarSetReserves[(y, r, hr)]))

            @self.Constraint(self.ProcurementSet)
            def resProcurementUpper(self, restypes, pt, y, r, steps, hr):
                return self.ReservesProcurement[(restypes, pt, y, r, steps, hr)] <= \
                    self.ResTechUpperBound[(restypes, pt)] * self.Hr_weights[hr] \
                    * self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)]
                 
def run_model():

    #Measuring the run time of code
    start_time = datetime.now()
    timer = TicTocTimer(logger=logger)
    timer.tic('start')

    ####################################################################################################################
    #PRE-PROCESSING
    
    logger.info('Preprocessing')

    #Build inputs used for model
    test_years = list(pd.read_csv('../input/sw_year.csv').dropna()['year'])
    test_regions = list(pd.read_csv('../input/sw_reg.csv').dropna()['region'])
    
    all_frames, setin = prep.preprocessor(prep.Sets(test_years,test_regions))

    timer.toc('preprocessor finished')

    #####################################################################################################################
    #Solve

    # disabling garbage collection to improve runtime
    gc.disable()
    
    # Building model
    logger.info('Build Pyomo')
    instance = PowerModel(all_frames, setin)
    
    # add electricity price dual
    instance.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    
    timer.toc('build model finished')
    #instance.pprint()

    #number of variables
    nvar = pyo.value(instance.nvariables())
    logger.info('Number of variables ='+str(nvar))
    #number of constraints
    ncon = pyo.value(instance.nconstraints())
    logger.info('Number of constraints ='+str(ncon))
    
    logger.info('Solving Pyomo')
    
    if instance.sw_learning == 3: #nonlinear solver
        solver_name ="ipopt"
        opt = pyo.SolverFactory(solver_name, tee=True) #, tee=True
        #Select options. The prefix "OF_" tells pyomo to create an options file
        opt.options['OF_mu_strategy']= "adaptive"
        opt.options['OF_num_linear_variables'] = 100000
        opt.options['OF_mehrotra_algorithm'] = 'yes'
        #Ask IPOPT to print options so you can confirm that they were used by the solver
        opt.options['print_user_options'] = 'yes'
    else: #linear solver
        solver_name = "appsi_highs"
        opt = pyo.SolverFactory(solver_name)
        
    logger.info('Using Solver: ' + solver_name)

    if instance.sw_learning in [1, 2]: #run iterative learning
        # Set any high tolerance
        tol = 999
        iter_num = 0
    
        
        def init_old_cap(instance,setin):
            instance.old_cap = {}
            instance.cap_set = []
            instance.old_cap_wt = {}
            
            for (r,pt,y,steps) in instance.CapCostSet:
                if (pt,y) not in instance.old_cap:
                    instance.cap_set.append((pt,y))
                    # each pt will increase cap by 1 GW per year. reasonable starting point.
                    instance.old_cap[(pt,y)] = (y - setin.start_year) * 1
                    instance.old_cap_wt[(pt,y)] = instance.year_weights[y] * instance.old_cap[(pt,y)]
        
        def set_new_cap(instance,setin):
                instance.new_cap = {}
                instance.new_cap_wt = {}
                for (r,pt,y,steps) in instance.CapCostSet:
                    if (pt,y) not in instance.new_cap:
                        instance.new_cap[(pt,y)] = 0.0
                    instance.new_cap[(pt,y)] = instance.new_cap[(pt,y)] + sum(instance.CapacityBuilds[(r, pt, year, steps)].value for year in setin.y if year < y)
                    instance.new_cap_wt[(pt,y)] = instance.year_weights[y] * instance.new_cap[(pt,y)]
                    
        def g(instance, start_year, pt, y):
            cost = (((instance.SupplyCurve_learning[pt]  \
                  + 0.0001*(y - start_year) 
                  + instance.new_cap[pt,y])
                  / instance.SupplyCurve_learning[pt]) \
                ** (-1.0*instance.LearningRate[pt]))
            return cost
        
        def g_prime(instance, start_year, pt, y):
            cost =  -1 * instance.LearningRate[pt] * g(instance, setin.start_year, pt, y) \
                        / (instance.SupplyCurve_learning[pt]  \
                              + 0.0001*(y - start_year) 
                              + instance.new_cap[pt,y])
            return cost
        
        def linear_approx(instance, start_year, pt, y):
            return g(instance, start_year, pt, y)  \
                                        + instance.new_cap[pt,y] * g_prime(instance, start_year, pt, y)
            
        def linear_exact(instance, start_year, pt, y):
            return g(instance, start_year, pt, y)
        
        def cost_learning_func(instance, start_year, pt, y):
            if instance.sw_learning == 1:
                val = linear_exact(instance, start_year, pt, y)
            else:
                val = linear_approx(instance, start_year, pt, y)
            return val
        
        def update_cost(instance, setin):
            new_multiplier = {}
            for (pt,y) in instance.cap_set:
                new_multiplier[(pt,y)] = cost_learning_func(instance, setin.start_year, pt, y)
            
            new_cost = {}
            # Assign new learning
            for (r, pt, y, steps) in instance.CapCostSet:
                # updating learning cost
                new_cost[(r,pt,y,steps)] = instance.CapCost_y0[(r, pt, steps)] * new_multiplier[pt,y]
                instance.capacity_costs_learning[(r,pt,y,steps)].value = new_cost[(r,pt,y,steps)]
            
        
        #initialize capacity to set pricing
        init_old_cap(instance,setin)
        instance.new_cap = instance.old_cap
        update_cost(instance, setin)
        
        while tol > 0.1 and iter_num < 20:
            logger.info('Linear iteration number: ' + str(iter_num))
            
            iter_num +=1
            # solve model
            opt_success = opt.solve(instance)
            timer.toc('solve model finished')
            
            set_new_cap(instance,setin)
            print(instance.new_cap)
            
            # Update tolerance
            tol = sum([abs(instance.old_cap_wt[(pt,y)] - instance.new_cap_wt[(pt,y)]) for (pt,y) in instance.cap_set])
                
            update_cost(instance, setin)
            
            instance.old_cap = instance.new_cap
            instance.old_cap_wt = instance.new_cap_wt
            
            logger.info('Tolerance: '+ str(tol))
    else:
        opt_success = opt.solve(instance)
        timer.toc('solve model finished')
        # instance.pprint()
        
    # save electricity prices for H2 connection
    #component_objects_to_df(instance.)
    
        ### Check results and load model solutions
    # Check results for termination condition and solution status
    if com.check_results(opt_success, TerminationCondition, SolutionStatus):
        name = "noclass!"
        logger.info(f"[{name}] Solve failed")
        if opt_success is not None:
            logger.info("status=" + str(opt_success.solver.status))
            logger.info("TerminationCondition=" + str(opt_success.solver.termination_condition))

    # If model solved, load model solutions into model, else exit
    try:
        if (opt_success.solver.status == SolverStatus.ok) and (opt_success.solver.termination_condition == TerminationCondition.optimal):
            instance.solutions.load_from(opt_success)
        else:
            logger.warning('Solve Failed.')
            exit()
    except:
        logger.warning('Solve Failed.')
        exit()
    
    logger.info('Solve complete')
    
    #Check
    #Objective Value
    obj_val = pyo.value(instance.totalCost)
    #print('Objective Function Value =',obj_val)
    
    logger.info("Displaying solution...")
    logger.info(f"instance.totalCost(): {instance.totalCost()}")
    
    logger.info("Logging infeasible constraints...")
    logger.info(log_infeasible_constraints(instance))


    logger.info('dispatchCost Value ='+ str(pyo.value(instance.dispatchCost)))
    logger.info('unmetLoadCost Value ='+ str(pyo.value(instance.unmetLoadCost)))
    if instance.sw_expansion:
        logger.info('Cap expansion Value ='+ str(pyo.value(instance.capExpansionCost)))
        logger.info('FOMCostObj Value ='+ str(pyo.value(instance.FOMCostObj)))
    if instance.sw_reserves:
        logger.info('opres Value ='+ str(pyo.value(instance.opresCost)))
    if instance.sw_ramp:
        logger.info('RampCost Value ='+ str(pyo.value(instance.RampCost)))
    if instance.sw_trade:
        logger.info('tradeCost Value =' + str(pyo.value(instance.tradeCost)))
    
    logger.info('Obj complete')
    
    def get_elec_price(instance):
        # for H2 model electricity price
        for c in instance.component_objects(pyo.Constraint, active=True):
            const = str(c)
            if const=="Demand_balance":
                vars()[const] = pd.DataFrame({'Constraint':[np.nan], 'Index':[0], 'Dual':[0] })
                for index in c:
                    last_row =  pd.DataFrame({'Constraint':[const], 'Index':[index], 'Dual':[float(instance.dual[c[index]])] })
                    vars()[const] = pd.concat([vars()[const],last_row]).dropna()
          
                vars()[const].reset_index(drop=True, inplace=True)
                df = pd.DataFrame([pd.Series(x) for x in vars()[const]['Index']])
                #Note: I'd like to be able to add the names of the indices automatically, but just using this shortcut for now
                df.columns = ['i_{}'.format(x+1) for x in df.columns]
                vars()[const] = pd.concat([vars()[const], df], axis=1)
                elec_price = vars()[const]
                elec_price.rename(
                    columns={'i_1':'r', 'i_2':'y', 'i_3':'hr'},
                    inplace=True)
        return elec_price
    
    elec_price = get_elec_price(instance)

    
    if instance.sw_h2int:
        
        def map_region_names(instance,df):
            #test_regions = list(pd.read_csv('../input/sw_reg.csv').dropna()['region'])
            reg_map = pd.read_csv('../input/reg_map.csv').rename(columns={'EMMReg':'r'})
            df2 = pd.merge(df, reg_map, on=['r'],how='left')
            return df2
            
        # this is generation for H2 model to use
        
        def get_h2_generation(instance):
            # for H2 model electricity price
            Generation = pd.Series(instance.Generation.get_values()).to_frame().reset_index().rename(
                columns={'level_0':'pt', 'level_1':'y', 'level_2':'r', 'level_3':'steps', 'level_4':'hr', 0:'Generation'})
            Generation = Generation[Generation['pt'] == 15].drop(columns=['pt','steps'])
            return Generation
        
        def sum_annual(instance, df):
            daywt = pd.Series(instance.Dayweights.extract_values()).to_frame().reset_index().rename(
                columns={'index':'hr', 0:'daywt'})
            df2 = pd.merge(df, daywt, on='hr',how='outer')
            df2.loc[:,'Generation'] = df2['Generation'] * df2['daywt']
            df2.drop(columns = ['hr','daywt'], inplace=True)
            df3 = df2.groupby(['y','r']).agg('sum').reset_index()
            return df3
        
        h2gen = get_h2_generation(instance)
        h2gen_ann = map_region_names(instance,sum_annual(instance, h2gen))
        
            
        def avg_annual(instance, df):
            daywt = pd.Series(instance.Dayweights.extract_values()).to_frame().reset_index().rename(
                columns={'index':'hr', 0:'daywt'})
            df2 = pd.merge(df, daywt, on='hr',how='outer')
            
            def my_agg(x):
                names = {'weighted_ave_price': (x['daywt'] * x['Dual']).sum()/x['daywt'].sum()}
                return pd.Series(names, index=['weighted_ave_price'])
            df3 = df2.groupby(['y','r']).apply(my_agg).reset_index()
            return df3
        
        elecprice_ann = map_region_names(instance,avg_annual(instance, elec_price))
        
    timer.toc('done with checks and extracting vars')



    ####################################################################################################################
    #Post-procressor
    #post.main(instance,instance.cols_dict)
    timer.toc('postprocessing done')
    

    #final steps for measuring the run time of the code
    end_time = datetime.now()
    run_time = end_time - start_time
    file = open('run_time.txt', 'a')
    file.write('\nStart Time: ' + datetime.strftime(start_time,"%m/%d/%Y %H:%M") + ', Run Time: ' + str(round(run_time.total_seconds()/60,2)) + ' mins')
    file.close()
    timer.toc('finished')

    
    logger.info('\nStart Time: ' + datetime.strftime(start_time,"%m/%d/%Y %H:%M") + ', Run Time: ' + str(round(run_time.total_seconds()/60,2)) + ' mins')

if __name__ == '__main__':

    run_model()