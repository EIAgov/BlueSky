# -*- coding: utf-8 -*-
"""
Created on Tue Feb 20 14:42:32 2024

@author: JNI
"""

import numpy as np
from pyomo.environ import *
import highspy as hp
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import time
import data_processing

# load data from preprocessor

data = data_processing.Data()





# Build model

HMM = ConcreteModel()

#Define Index Sets

# Temporal Sets
HMM.hour = Set(initialize = data.hour)
HMM.PlanningPeriod = Set(initialize = data.PlanningPeriod)
HMM.Season = Set(initialize = data.Season)



# Spatial Sets:

HMM.CensusRegion = Set(initialize = data.CensusRegion)
HMM.DemandNode = Set(initialize = data.DemandNode)
HMM.SupplyNode = Set(initialize = data.SupplyNode)
HMM.Hub = Set(initialize = data.Hub)
HMM.EMMRegion = Set(initialize = data.EMMRegion['NERCRegions_'].tolist())

# Fuel and Technology Sets:
HMM.StorageTechnologyType = Set(initialize = data.StorageTechnologyType)
HMM.ProductionTechnologyType = Set(initialize = data.ProdTechnologyType)
HMM.ProdTechTypeGas = Set(initialize = data.ProdTechnologyType_gasification)
HMM.ProdTechTypeElec = Set(initialize = data.ProdTechnologyType_electrolysis)
HMM.FuelType = Set(initialize = data.FuelType)

# Transportation Sets:
HMM.TransportationArcs = Set(within = HMM.Hub*HMM.Hub, initialize = data.TransportationArcs)
    
HMM.ArcsByDest = {dest: [] for dest in HMM.Hub}
for (s,d) in HMM.TransportationArcs:
    HMM.ArcsByDest[d].append((s,d))
    
# misc sets
HMM.CapacityVintageYear = Set(initialize = data.CapacityVintageYear)
HMM.ProductionStep = Set(initialize = data.ProductionStep)
HMM.StorageStep = Set(initialize = data.StorageStep)
HMM.TransportationStep = Set(initialize = data.TransportationStep)

# Define parameters and their index sets, initialize to the whatever the functions say they should be:

HMM.TaxCreditV = Param(HMM.hour,HMM.Season, HMM.EMMRegion, HMM.PlanningPeriod,HMM.CapacityVintageYear, initialize = data.TaxCreditV_f)
HMM.CO2CaptureRate = Param(HMM.ProdTechTypeGas, initialize = data.CO2CaptureRate_f)
HMM.CO2Value = Param(HMM.CensusRegion, HMM.PlanningPeriod,HMM.CapacityVintageYear, initialize = data.CO2Value_f)
HMM.ElectrolyzerFuelConsumption = Param(HMM.FuelType, HMM.ProdTechTypeElec, initialize = data.ElectrolyzerFuelConsumption_f)
HMM.ExistingCapacityElectrolyzer = Param(HMM.EMMRegion, HMM.PlanningPeriod,HMM.CapacityVintageYear)
HMM.ExistingCapacityNonElectrolyzer = Param(HMM.CensusRegion,HMM.PlanningPeriod,HMM.CapacityVintageYear)
HMM.ExistingStorageCapacity = Param(HMM.CensusRegion,HMM.PlanningPeriod)
HMM.ExistingTransportationCapacity = Param(HMM.TransportationArcs, HMM.PlanningPeriod)
HMM.FeedstockConsumption = Param(HMM.ProdTechTypeGas, HMM.FuelType, initialize = data.FeedstockConsumption_f)
HMM.FuelCost = Param(HMM.Season, HMM.CensusRegion,HMM.FuelType,HMM.PlanningPeriod, initialize = data.FuelCost_f)
HMM.H2Demand = Param(HMM.Season,HMM.CensusRegion,HMM.PlanningPeriod, initialize = data.H2Demand_f)
HMM.HourlyFraction = Param(HMM.hour, initialize = data.HourlyFraction_f)
HMM.HourlyFuelCost = Param(HMM.hour,HMM.Season,HMM.EMMRegion,HMM.FuelType,HMM.PlanningPeriod, initialize = data.HourlyFuelCost_f)
HMM.HPConsumption = Param(HMM.FuelType,HMM.ProdTechTypeGas, initialize = data.HPConsumption_f)
HMM.LoadRatioLimit = Param(HMM.hour,HMM.Season,HMM.EMMRegion)
HMM.OMCostElectrolyzer = Param(HMM.hour,HMM.Season,HMM.EMMRegion,HMM.ProdTechTypeElec,HMM.PlanningPeriod, initialize = data.OMCostElectrolyzer_f)
HMM.OMCostNonElectrolyzer = Param(HMM.Season,HMM.CensusRegion,HMM.ProdTechTypeGas,HMM.PlanningPeriod, initialize = data.OMCostNonElectrolyzer_f)
HMM.ProductionStepCostMultiplier = Param(HMM.ProductionStep)
HMM.PUCCostElectrolyzer = Param(HMM.EMMRegion,HMM.ProdTechTypeElec,HMM.PlanningPeriod, initialize = data.PUCCostElectrolyzer_f)
HMM.PUCCostNonElectrolyzer = Param(HMM.CensusRegion,HMM.ProdTechTypeGas,HMM.PlanningPeriod, initialize = data.PUC_nonElectrolyzer_f)
HMM.SeasonalFraction = Param(HMM.Season, initialize = data.SeasonalFraction_f)
HMM.SUCCost = Param(HMM.CensusRegion,HMM.StorageTechnologyType,HMM.PlanningPeriod,initialize = data.SUCCost_f)
HMM.StorageINJCost = Param(HMM.CensusRegion, HMM.StorageTechnologyType, initialize = data.StorageINJCost_f)
HMM.StorageStepCostMultiplier = Param(HMM.StorageStep)
HMM.StorageWTHCost = Param(HMM.CensusRegion,HMM.StorageTechnologyType, initialize = data.StorageWTHCost_f)
HMM.TotalElectricityGen = Param(HMM.hour,HMM.Season,HMM.EMMRegion,HMM.PlanningPeriod)
HMM.TransportationCost = Param(HMM.TransportationArcs,HMM.PlanningPeriod, initialize = data.TransportationCost_f)
HMM.TransportationStepCostMultiplier = Param(HMM.TransportationStep)
HMM.TUCCost = Param(HMM.TransportationArcs,HMM.PlanningPeriod, initialize = data.TUCCost_f)


# Define variables over their index sets


#production variables:
HMM.H2ProdElectrolyzer = Var(HMM.hour,HMM.Season,HMM.EMMRegion,HMM.ProdTechTypeElec,HMM.PlanningPeriod,HMM.CapacityVintageYear, within = NonNegativeReals)
HMM.H2ProdNonElectrolyzer = Var(HMM.Season,HMM.CensusRegion,HMM.ProdTechTypeGas,HMM.PlanningPeriod,HMM.CapacityVintageYear, within = NonNegativeReals)

#Hub transportation variables:
HMM.FlowHubToDemand = Var(HMM.Season,HMM.Hub,HMM.DemandNode,HMM.PlanningPeriod, within= NonNegativeReals)
HMM.FlowSupplyToHub = Var(HMM.Season, HMM.SupplyNode, HMM.Hub,HMM.ProductionTechnologyType,HMM.PlanningPeriod, within = NonNegativeReals)  


HMM.NetStorageToHub = Var(HMM.Season,HMM.CensusRegion,HMM.StorageTechnologyType,HMM.PlanningPeriod,within = NonNegativeReals)
HMM.PUCByStepElectrolyzer = Var(HMM.ProductionStep, HMM.EMMRegion,HMM.ProductionTechnologyType,HMM.PlanningPeriod,within = NonNegativeReals)
HMM.PUCByStepNonElectrolyzer = Var(HMM.ProductionStep, HMM.CensusRegion,HMM.ProductionTechnologyType,HMM.PlanningPeriod,within = NonNegativeReals)
HMM.StorageInj = Var(HMM.Season, HMM.CensusRegion, HMM.StorageTechnologyType,HMM.PlanningPeriod,within = NonNegativeReals)
HMM.StorageWth = Var(HMM.Season, HMM.CensusRegion,HMM.StorageTechnologyType, HMM.PlanningPeriod,within = NonNegativeReals)
HMM.SUCByStep = Var(HMM.StorageStep,HMM.CensusRegion,HMM.StorageTechnologyType,HMM.PlanningPeriod, within = NonNegativeReals)

HMM.TUCByStep = Var(HMM.TransportationStep,HMM.TransportationArcs,HMM.PlanningPeriod, domain = NonNegativeReals)




def electrolyzer_cost(model):
    return sum(model.H2ProdElectrolyzer[hr,seas,regNERC,prodTech,pp,capyear] for hr in model.hour for seas in model.Season for regNERC in model.EMMRegion for prodTech in model.ProdTechTypeElec for pp in model.PlanningPeriod for capyear in model.CapacityVintageYear)
'''   
    return (sum(
        
        (
        
        
        sum(
            model.HourlyFuelCost[hr,seas,regNERC,fuel,pp]*model.ElectrolyzerFuelConsumption[fuel,prodTech] 
                   for fuel in model.FuelType) + 
                   model.OMCostElectrolyzer[hr,seas,regNERC,prodTech,pp] - 
                   model.TaxCreditV[hr,seas,regNERC,pp,capYear])* 
                   model.H2ProdElectrolyzer[hr,seas,regNERC,prodTech,pp,capYear] 
                   for hr in model.hour for seas in model.Season for  prodTech in model.ProdTechTypeElec for regNERC in model.EMMRegion for 
                   pp in model.PlanningPeriod for capYear in model.CapacityVintageYear) 
            )
'''


def nonelectrolyzer_cost(model):
    return (sum(
                (
                sum(
                    model.FuelCost[seas,regCEN,fuel,pp]*(model.FeedstockConsumption[prodTech,fuel] + model.HPConsumption[fuel,prodTech]) 
                    for fuel in model.FuelType
                    )
                    + model.OMCostNonElectrolyzer[seas,regCEN,prodTech,pp]
                    - (model.CO2CaptureRate[prodTech]*model.CO2Value[regCEN,pp,capYear])
                    ) * model.H2ProdNonElectrolyzer[seas,regCEN,prodTech,pp,capYear] 
                    for seas in model.Season for regCEN in model.CensusRegion
                    for prodTech in model.ProdTechTypeGas for pp in model.PlanningPeriod for capYear in model.CapacityVintageYear
                    ))

                                                                                
def total_cost(model):

    
    return electrolyzer_cost(model) + nonelectrolyzer_cost(model) 
                                                                              
def transportation_constraint():
    return

# The demand from DemandNode must match the 
def demand_balance_constraint(model, Season,DemandNode,PlanningPeriod):
    return sum(model.FlowHubToDemand[Season,Hub,DemandNode,PlanningPeriod] for Hub in data.HubsToDemandNode[DemandNode]) == model.H2Demand[Season,DemandNode,PlanningPeriod]



def supply_mass_balance_constraint(model,Season,Hub,PlanningPeriod):

    return ( sum(sum(model.H2ProdElectrolyzer[hr,seas,regNERC,prodTech,pp,capYear] for hr in model.hour for 
                seas in model.Season for regNERC in data.CensusToNERC[CensusRegion] for prodTech in model.ProdTechTypeElec 
                for capYear in model.CapacityVintageYear for pp in model.PlanningPeriod) for CensusRegion in data.SupplyNodesToHub[Hub])
                + 
                sum(model.H2ProdNonElectrolyzer[seas,regCEN,prodTech,pp,capYear] 
                for seas in model.Season for regCEN in model.CensusRegion for 
                prodTech in model.ProdTechTypeGas for pp in model.PlanningPeriod for capYear in model.CapacityVintageYear) 
                == 
                sum(model.FlowSupplyToHub[seas,Hub, regCEN, prodtech, pp] for seas in model.Season for regCEN in model.CensusRegion for prodtech in model.ProductionTechnologyType for pp in model.PlanningPeriod))

#def check_constraint(model,Season,Hub):
#    return Constraint.Feasible
 
HMM.cost = Objective(rule = total_cost, sense = minimize)
HMM.DemandBalanceConstraint = Constraint(HMM.Season,HMM.DemandNode, HMM.PlanningPeriod, rule = demand_balance_constraint)
HMM.SupplyMassBalanceConstraint = Constraint(HMM.Season,HMM.Hub,HMM.PlanningPeriod, rule = supply_mass_balance_constraint)
#HMM.Check = Constraint(HMM.Season,HMM.Hub, rule = check_constraint)
solver = SolverFactory('glpk')
solver.solve(HMM).write()