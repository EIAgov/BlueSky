#Electricity Dispatch Model - Based on Restore Module within NEMS

####################################################################################################################
#Setup

#Import pacakges
from datetime import datetime
import numpy as np
import pandas as pd
import pyomo.environ as pyo
import gc
import highspy
from pyomo.common.timing import TicTocTimer

#import scripts
import preprocessor as prep
import postprocessor as post

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
        self.sw_learning =  setA.sw_learning
        self.sw_h2int = 0
        
        ####################################################################################################################
        #Sets

        self.hr = pyo.Set(initialize = setA.hr) #change hours (1-48) or (1-577)?
        self.day = pyo.Set(initialize = setA.day)
        self.y = pyo.Set(initialize = setA.y)
        self.s = pyo.Set(initialize = setA.s)

        self.r = pyo.Set(initialize = range(1,26))
        self.r_can = pyo.Set(initialize = range(29,34))

        self.SupplyPriceSet = pyo.Set(initialize = all_frames['SupplyPrice'].index)
        self.SupplyCurveSet = pyo.Set(initialize = all_frames['SupplyCurve'].index)

        #Create sparse sets 
        def create_subsets(df,col,subset):
            df = df[df[col].isin(subset)].dropna()
            return df

        def create_hourly_sets(df):
            df = pd.merge(df,
                        all_frames['Map_hr_s'].reset_index(),
                        on=['s'], how='left').drop(columns=['s'])
            return df

        index_list = ['pt','y','r','steps','hr'] 

        self.GenSet = pyo.Set(
            initialize = create_hourly_sets(
                create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptg))
            .set_index(index_list).index
            )
        
        self.ptd_upper_set = pyo.Set(
            initialize = create_hourly_sets(
                create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptd))
            .set_index(index_list).index
            )
        
        self.pth_upper_set = pyo.Set(
            initialize = create_hourly_sets(
                create_subsets(
                    create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pth),
                    'steps',[2]))
            .set_index(index_list).index
            )
        
        self.Gen_ramp_set = pyo.Set(
            initialize = create_subsets(
                create_hourly_sets(
                    create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptc)),
                    'hr',setA.hr23)
            .set_index(index_list).index
            )
        
        self.FirstHour_gen_ramp_set = pyo.Set(
            initialize = create_subsets(
                create_hourly_sets(
                    create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptc)),
                    'hr',setA.hr1)
            .set_index(index_list).index
            )
        
        self.HydroSet = pyo.Set(initialize = all_frames['HydroCapFactor'].index)
        self.IdaytqSet = pyo.Set(initialize = all_frames['Idaytq'].index)
        self.LoadSet = pyo.Set(initialize = all_frames['Load'].index)

        self.StorageSet = pyo.Set(
            initialize = create_hourly_sets(
                create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pts))
            .set_index(index_list).index
            )
                
        self.H2GenSet = pyo.Set(
            initialize = create_hourly_sets(
                create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pth2))
            .set_index(index_list).index
            )
        
        self.UnmetSet = self.r * self.y * self.hr
        self.HydroMonthsSet = pyo.Set(
            initialize = create_subsets(
                create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pth),'steps',[1]
                ).drop(columns=['steps']).set_index(['pt','y','r','s']).index
            )
        
        #TODO: move ptd to pt set list

        self.StorageBalance_set = pyo.Set(
            initialize = create_subsets(
                create_hourly_sets(
                    create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pts)),
                    'hr',setA.hr23)
            .set_index(index_list).index
            )

        self.FirstHourStorageBalance_set = pyo.Set(
            initialize = create_subsets(
                create_hourly_sets(
                    create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.pts)),
                    'hr',setA.hr1)
            .set_index(index_list).index
            )

        self.ptiUpperSet = pyo.Set(initialize = all_frames['ptiUpperSet'].index)        
        self.H2PriceSet = pyo.Set(initialize = all_frames['H2Price'].index)

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
                self.LearningRateSet = pyo.Set(initialize = all_frames['LearningRate'].index)
                self.CapCost0Set = pyo.Set(initialize = all_frames['CapCost_y0'].index)
                self.LearningPtSet = pyo.Set(initialize = all_frames['SupplyCurve_learning'].index)
            self.CapCostSet = pyo.Set(initialize = all_frames['CapCost'].index)
            self.FOMCostSet = pyo.Set(initialize=all_frames['FOMCost'].index)
            self.allowBuildsSet = pyo.Set(initialize=all_frames['allowBuilds'].index)
            self.RetSet = pyo.Set(initialize=all_frames['RetSet'].index)
            self.CapacityCreditSet = pyo.Set(initialize=capacitycredit_df().index)

        if self.sw_trade:
            self.TranCostSet = pyo.Set(initialize = all_frames['TranCost'].index)
            self.TranLimitSet = pyo.Set(initialize = all_frames['TranLimit'].index)
            self.TradeSet = pyo.Set(
                initialize = create_hourly_sets(
                    all_frames['TranLimit'].reset_index()
                    ).set_index(['r', 'r1', 'y', 'hr']).index
                )
            
            self.TranCostCanSet = pyo.Set(initialize=all_frames['TranCostCan'].index)

            self.TranLimitCanSet = pyo.Set(
                initialize = create_hourly_sets(
                    all_frames['TranLimitCan'].reset_index()
                    ).set_index(['r1','CSteps','y','hr']).index
                )
            self.TranLineLimitCanSet = pyo.Set(
                initialize = create_hourly_sets(
                    all_frames['TranLineLimitCan'].reset_index()
                    ).set_index(['r', 'r1', 'y', 'hr']).index
                )
            self.TradeCanSet = pyo.Set(
                initialize = pd.merge(
                    create_hourly_sets(all_frames['TranLimitCan'].reset_index()), 
                    create_hourly_sets(all_frames['TranLineLimitCan'].reset_index()), 
                    how="inner").drop(columns=['TranLimitCan']).set_index(['r', 'r1', 'y','CSteps', 'hr']).index
                )

        if self.sw_ramp:
            self.RampUp_CostSet = pyo.Set(initialize=all_frames['RampUp_Cost'].index)
            self.RampRateSet = pyo.Set(initialize=all_frames['RampRate'].index)

            self.RampSet = pyo.Set(
                initialize = create_hourly_sets(
                    create_subsets(all_frames['SupplyCurve'].reset_index(),'pt',setA.ptc))
                .set_index(index_list).index
                )        

        if self.sw_reserves:
            self.ProcurementSet = pyo.Set(initialize=
                pd.merge(create_hourly_sets(all_frames['SupplyCurve'].reset_index()),
                         pd.DataFrame({'restypes': setA.restypes}),
                         how='cross').set_index(['restypes']+index_list).index
            )
            
            self.RegReservesCostSet = pyo.Set(initialize=all_frames['RegReservesCost'].index)
            self.ResTechUpperBoundSet = pyo.Set(initialize=all_frames['ResTechUpperBound'].index)

        ####################################################################################################################
        #Parameters

        self.Storagelvl_cost = pyo.Param(initialize=0.00000001)
        self.UnmetLoad_penalty = pyo.Param(initialize=500)
        self.Idaytq = pyo.Param(self.IdaytqSet, initialize = all_frames['Idaytq'], default = 0)
        self.Load = pyo.Param(self.LoadSet, initialize = all_frames['Load'], default = 0)
        self.HydroCapFactor = pyo.Param(self.HydroSet, initialize = all_frames['HydroCapFactor'], default = 0)
        
        self.BatteryChargeCap = pyo.Param(
            self.StorageSet, 
            initialize = create_hourly_sets(
                create_subsets(
                    all_frames['SupplyCurve'].reset_index(),'pt',setA.pts
                    )
                ).set_index(index_list), 
            default = 0
            )
        
        self.BatteryEfficiency = pyo.Param(setA.pts, initialize = all_frames['BatteryEfficiency'], default = 0)
        self.HourstoBuy= pyo.Param(setA.pts, initialize = all_frames['HourstoBuy'], default = 0)
        self.Dayweights = pyo.Param(self.hr, initialize = all_frames['Dayweights'], default = 0)
        self.SupplyPrice = pyo.Param(self.SupplyPriceSet, initialize = all_frames['SupplyPrice'], default = 0)
        self.SupplyCurve = pyo.Param(self.SupplyCurveSet, initialize = all_frames['SupplyCurve'], default = 0)
        self.SolWindCapFactor = pyo.Param(self.ptiUpperSet, initialize=all_frames['ptiUpperSet'], default = 0) 
        self.H2Price = pyo.Param(self.H2PriceSet, initialize=all_frames['H2Price'], default = 0) #eventually connect with H2 model

        self.year_weights = pyo.Param(self.y, initialize = all_frames['year_weights'], default = 0)
        self.Map_hr_s = pyo.Param(self.hr, initialize = all_frames['Map_hr_s'], default = 0) #all_frames['Map_hr_s'].loc[hr]['s']
        self.Hr_weights = pyo.Param(self.hr, initialize=all_frames['Hr_weights']['Hr_weights'], default=0) #all_frames['Hr_weights']['Hr_weights'][hr]
        self.Map_hr_d = pyo.Param(self.hr, initialize = all_frames['Map_hr_d']['day'], default=0)

        if self.sw_expansion:
            # if learning is not to be solved nonlinearly directly in the obj
            if self.sw_learning < 2:
                if self.sw_learning == 0:
                    mute = False
                else:
                    mute = True
                self.capacity_costs_learning = pyo.Param(self.CapCostSet, initialize = all_frames['CapCost'], default = 0, mutable=mute)
            # if learning is non-linear
            if self.sw_learning > 0:
                self.LearningRate = pyo.Param(self.LearningRateSet, initialize = all_frames['LearningRate'], default = 0)
                self.CapCost_y0 = pyo.Param(self.CapCost0Set, initialize = all_frames['CapCost_y0'], default = 0)
                self.SupplyCurve_learning = pyo.Param(self.LearningPtSet, initialize = all_frames['SupplyCurve_learning'], default = 0)
            
            self.FOMCost = pyo.Param(self.FOMCostSet, initialize=all_frames['FOMCost'], default=0)
            self.CapacityCredit = pyo.Param(self.CapacityCreditSet, initialize=capacitycredit_df(), default=0)

        if self.sw_trade:
            self.TranCost = pyo.Param(self.TranCostSet, initialize = all_frames['TranCost'], default = 0)
            self.TranLimit = pyo.Param(self.TranLimitSet, initialize = all_frames['TranLimit'], default = 0)

            self.TranCostCan = pyo.Param(self.TranCostCanSet, initialize=all_frames['TranCostCan'], default=0)
            self.TranLimitCan = pyo.Param(
                self.TranLimitCanSet, initialize = create_hourly_sets(
                    all_frames['TranLimitCan'].reset_index()
                    ).set_index(['r1','CSteps','y','hr']), default=0
                )

            self.TranLineLimitCan = pyo.Param(
                self.TranLineLimitCanSet, initialize = create_hourly_sets(
                    all_frames['TranLineLimitCan'].reset_index()
                    ).set_index(['r', 'r1', 'y', 'hr']), default = 0
                )
        
        if self.sw_rm:
            self.ReserveMargin = pyo.Param(self.r, initialize=all_frames['ReserveMargin'], default=0)
            
        if self.sw_ramp:
            self.RampUp_Cost = pyo.Param(self.RampUp_CostSet, initialize=all_frames['RampUp_Cost'], default=0)
            self.RampDown_Cost = pyo.Param(self.RampUp_CostSet, initialize=all_frames['RampDown_Cost'], default=0)
            self.RampRate = pyo.Param(self.RampRateSet, initialize=all_frames['RampRate'], default=0)

        if self.sw_reserves:
            self.RegReservesCost = pyo.Param(self.RegReservesCostSet, initialize=all_frames['RegReservesCost'], default=0)
            self.ResTechUpperBound = pyo.Param(self.ResTechUpperBoundSet, initialize=all_frames['ResTechUpperBound'], default=0)
        
        

        ####################################################################################################################
        #Upper Bounds

        if self.sw_trade:
            def Trade_upper(self, r, r1, y, hr):
                return (0, self.TranLimit[(r, r1,
                                           self.Map_hr_s[hr], y)] * self.Hr_weights[hr])

        ####################################################################################################################
        #Variables

        self.Storage_inflow = pyo.Var(self.StorageSet, within=pyo.NonNegativeReals) #Storage inflow in hour h #GW
        self.Storage_outflow = pyo.Var(self.StorageSet, within=pyo.NonNegativeReals) #Storage outflow in hour h #GW
        self.Storage_level = pyo.Var(self.StorageSet, within=pyo.NonNegativeReals) #storage energy level in hour h #GWh
        self.Generation = pyo.Var(self.GenSet, within=pyo.NonNegativeReals) #Operated capacity GW use of technology group T in hour h #GW
        self.unmet_Load = pyo.Var(self.UnmetSet, within=pyo.NonNegativeReals) #slack variable #GW

        self.TotalCapacity = pyo.Var(self.SupplyCurveSet, within=pyo.NonNegativeReals) #Total capacity (existing + new - retirements) #GW

        if self.sw_expansion:
            self.CapacityBuilds = pyo.Var(self.CapCostSet, within=pyo.NonNegativeReals) #GW
            self.CapacityRetirements = pyo.Var(self.RetSet, within=pyo.NonNegativeReals) #GW

        if self.sw_trade:
            self.TradeToFrom = pyo.Var(self.TradeSet, within=pyo.NonNegativeReals, bounds = Trade_upper) # Trade to region r from r1 #GW
            self.TradeToFromCan = pyo.Var(self.TradeCanSet, within=pyo.NonNegativeReals) # Trade to region r from r1 with canada #GW

        if self.sw_rm:
            self.AvailStorCap = pyo.Var(self.StorageSet, within=pyo.NonNegativeReals) #Available storage capacity #GW
            
        if self.sw_ramp:
            self.RampUp = pyo.Var(self.RampSet, within=pyo.NonNegativeReals)
            self.RampDown = pyo.Var(self.RampSet, within=pyo.NonNegativeReals)

        if self.sw_reserves:
            self.ReservesProcurement = pyo.Var(self.ProcurementSet, within=pyo.NonNegativeReals)
            

        ####################################################################################################################
        #Objective Function
        self.StorageSetByHour = pyo.Set(self.hr)
        self.GenSetByHour = pyo.Set(self.hr)
        #self.H2GenSetByHour = {}

        def populate_by_hour_sets_rule(m):
            for (tech, y, reg, step, hour) in m.StorageSet:
                m.StorageSetByHour[hour].add((tech, y, reg, step))
            for (tech, y, reg, step, hour) in m.GenSet:
                m.GenSetByHour[hour].add((tech, y, reg, step))
            #for (tech, y, reg, step, hour) in m.H2GenSet:
            #    if (hour) not in m.H2GenSetByHour:
            #        m.H2GenSetByHour[hour] = []  # TBD- collapse with default key value
            #    m.H2GenSetByHour[hour].append((tech, y, reg, step))
                    
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
                              for (tech, y, reg, step) in self.GenSetByHour[hr]) \
                ) for hr in self.hr if (s := self.Map_hr_s[hr])) \
                    + sum(self.Dayweights[hr] * 
                          self.year_weights[y] * self.H2Price[reg,s,tech,step,y] * setA.H2_heatrate \
                          * self.Generation[(tech, y, reg, 1, hr)] \
                        for (tech, y, reg, step, hr) in self.H2GenSet if (s := self.Map_hr_s[hr]))
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
            if self.sw_learning == 2:
                
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

        self.GenSetDemandBalance = {}
        self.StorageSetDemandBalance = {}
        self.TradeSetDemandBalance = {}
        self.TradeCanSetDemandBalance = {}
        def populate_demand_balance_sets_rule(m):
            for (tech, year, reg, step, hour) in m.GenSet:
                if (year, reg, hour) not in m.GenSetDemandBalance:
                    m.GenSetDemandBalance[(year, reg, hour)] = []  # TBD- collapse with default key value
                m.GenSetDemandBalance[(year, reg, hour)].append((tech, step))
            for (tech, year, reg, step, hour) in m.BatteryChargeCap:
                if (year, reg, hour) not in m.StorageSetDemandBalance:
                    m.StorageSetDemandBalance[(year, reg, hour)] = []
                m.StorageSetDemandBalance[(year, reg, hour)].append((tech, step))
            if m.sw_trade == 1:
                for (reg, reg1, year, hour) in m.TradeSet:
                    if (year, reg, hour) not in m.TradeSetDemandBalance:
                        m.TradeSetDemandBalance[(year, reg, hour)] = []
                    m.TradeSetDemandBalance[(year, reg, hour)].append(reg1)
                for (reg, reg1, year, CSteps, hour) in m.TradeCanSet:
                    if (year, reg, hour) not in m.TradeCanSetDemandBalance:
                        m.TradeCanSetDemandBalance[(year, reg, hour)] = []
                    m.TradeCanSetDemandBalance[(year, reg, hour)].append((reg1, CSteps))
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
                        for (reg1) in self.TradeSetDemandBalance[(y, r, hr)]) if self.sw_trade else 0) \
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
            # run time seems worth it to create trade sets rule if there are , adds 9 sec (29 to 23 sec) build time if trade on with all regions

            # this may have made it run slightly slower with only 3 regions
            self.TradeCanSetUpper = {}
            self.TradeCanLineSetUpper = {}
            def populate_trade_sets_rule(m):
                for (reg, reg1, year, CSteps, hour) in m.TradeCanSet:
                    if (reg, reg1, year, hour) not in m.TradeCanLineSetUpper:
                        m.TradeCanLineSetUpper[(reg, reg1, year, hour)] = []
                    m.TradeCanLineSetUpper[(reg, reg1, year, hour)].append((CSteps))
                    if (reg1, year, CSteps, hour) not in m.TradeCanSetUpper:
                        m.TradeCanSetUpper[(reg1, year, CSteps, hour)] = []
                    m.TradeCanSetUpper[(reg1, year, CSteps, hour)].append((reg))

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

            self.SupplyCurveRM = {}

            def populate_RM_sets_rule(m):
                for (reg,s,tech,step,year) in m.SupplyCurveSet:
                    if (year, reg, s) not in m.SupplyCurveRM:
                        m.SupplyCurveRM[(year, reg, s)] = []  # TBD- collapse with default key value
                    m.SupplyCurveRM[(year, reg, s)].append((tech, step))

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

            self.ProcurementSetReserves = {}
            #wind set
            self.WindSetReserves = {}
            #solar set
            self.SolarSetReserves = {}
            def populate_reserves_sets_rule(m):
                for (restype, pt, year, reg, step, hour) in m.ProcurementSet:
                    if (restype, reg, year, hour) not in m.ProcurementSetReserves:
                        m.ProcurementSetReserves[(restype, reg, year, hour)] = []
                    m.ProcurementSetReserves[(restype, reg, year, hour)].append((pt, step))
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
    timer = TicTocTimer()
    timer.tic('start')

    ####################################################################################################################
    #PRE-PROCESSING

    #Build inputs used for model
    test_years = list(pd.read_csv('../input/sw_year.csv').dropna()['year'])
    test_regions = list(pd.read_csv('../input/sw_reg.csv').dropna()['region'])
    
    all_frames, setin = prep.preprocessor(prep.Sets(test_years,test_regions),'../input/cem_inputs/')

    timer.toc('preprocessor finished')

    #####################################################################################################################
    #Solve
    gc.disable()
    
    instance = PowerModel(all_frames, setin)
    
    if instance.sw_h2int:
        #add electricity price dual
        instance.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    
    timer.toc('build model finished')
    #instance.pprint()

    #number of variables
    nvar = pyo.value(instance.nvariables())
    print('Number of variables =',nvar)
    #number of constraints
    ncon = pyo.value(instance.nconstraints())
    print('Number of constraints =',ncon)
    print()
    
    if instance.sw_learning == 2: #nonlinear solver
        opt = pyo.SolverFactory("ipopt") #, tee=True
        opt.options['mu_strategy']= "adaptive"
        opt.options['print_user_options'] = 'yes'
    else: #linear solver
        opt = pyo.SolverFactory("appsi_highs")

    if instance.sw_learning == 1: #run iterative learning
        # Set any high tolerance
        tol = 1
        iter_num = 0

        while tol > 0.1 and iter_num < 20:
            print(iter_num)
            
            iter_num +=1
            # solve model
            opt_success = opt.solve(instance)
            timer.toc('solve model finished')
            #instance.pprint()
            print()
            
            # updating learning cost
            new_cost = [instance.CapCost_y0[(r, pt, steps)] \
             * (((instance.SupplyCurve_learning[pt]  \
                  + 0.0001*(y - setin.start_year) 
                  + sum(sum(instance.CapacityBuilds[(r, pt, year, steps)].value for year in setin.y if year < y) 
                        for (r, tech, steps) in instance.CapCost0Set if tech == pt)) \
                  / instance.SupplyCurve_learning[pt]) \
                ** (-1.0*instance.LearningRate[pt])) for (r,pt,y,steps) in instance.CapCostSet]
            
            # this is weighted by year weights for tolerance
            new_cost_wt = [instance.year_weights[y] * instance.CapCost_y0[(r, pt, steps)] \
             * (((instance.SupplyCurve_learning[pt]  \
                  + 0.0001*(y - setin.start_year) 
                  + sum(sum(instance.CapacityBuilds[(r, pt, year, steps)].value for year in setin.y if year < y) 
                        for (r, tech, steps) in instance.CapCost0Set if tech == pt)) \
                  / instance.SupplyCurve_learning[pt]) \
                ** (-1.0*instance.LearningRate[pt])) for (r,pt,y,steps) in instance.CapCostSet]

            # existing costs
            old_cost_wt = [instance.year_weights[y] * instance.capacity_costs_learning[(r,pt,y,steps)].value for (r,pt,y,steps) in instance.CapCostSet]
            
            # Update tolerance
            tol = sum([abs(old_cost_wt[i] - new_cost_wt[i]) for i in range(len(new_cost))])

            i = 0
            # Assign new learning
            for (r, pt, y, steps) in instance.CapCostSet:
                new_val = new_cost[i]
                instance.capacity_costs_learning[(r,pt,y,steps)].value = new_val
                i += 1
            print(tol)
    else:
        opt_success = opt.solve(instance)
        timer.toc('solve model finished')
        # instance.pprint()
        print()
        
    # save electricity prices for H2 connection
    #component_objects_to_df(instance.)
    
    
    #Check
    #Objective Value
    obj_val = pyo.value(instance.totalCost)
    print('Objective Function Value =',obj_val)

    print()

    print('dispatchCost Value =', pyo.value(instance.dispatchCost))
    print('unmetLoadCost Value =', pyo.value(instance.unmetLoadCost))
    if instance.sw_expansion:
        print('Cap expansion Value =', pyo.value(instance.capExpansionCost))
        print('FOMCostObj Value =', pyo.value(instance.FOMCostObj))
    if instance.sw_reserves:
        print('opres Value =', pyo.value(instance.opresCost))
    if instance.sw_ramp:
        print('RampCost Value =', pyo.value(instance.RampCost))
    if instance.sw_trade:
        print('tradeCost Value =', pyo.value(instance.tradeCost))
    print()
    
    if instance.sw_h2int:
        # for H2 model electricity price
        for c in instance.component_objects(pyo.Constraint, active=True):
            const = str(c)
            if const=="Demand_balance":
                print("Constraint", const)
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



    ####################################################################################################################
    #Post-procressor
    post.main(instance)

    #final steps for measuring the run time of the code
    end_time = datetime.now()
    run_time = end_time - start_time
    file = open('run_time.txt', 'a')
    file.write('\nStart Time: ' + datetime.strftime(start_time,"%m/%d/%Y %H:%M") + ', Run Time: ' + str(round(run_time.total_seconds()/60,2)) + ' mins')
    file.close()
    timer.toc('finished')
    print()

if __name__ == '__main__':

    run_model()