import numpy as np

# from pyomo.environ import *
import highspy as hp
import pandas as pd
import time
import os


class Data:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.paths_in = pd.read_csv(self.base_dir + '\paths_in.csv', index_col=0, header=0)

        # load operational dataframes:

        self.base_FixedOM_Electrolyzer = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_FixedOM_Electrolyzer', 'path']
        )
        self.base_FixedOM_NonElectrolyzer = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_FixedOM_NonElectrolyzer', 'path']
        )
        self.base_PUC_nonElectrolyzer = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_PUC_nonElectrolyzer', 'path']
        )
        self.base_PUCCostElectrolyzer = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_PUCCostElectrolyzer', 'path']
        )
        self.base_VarOM_Electrolyzer = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_VarOM_Electrolyzer', 'path']
        )
        self.base_VarOM_NonElectrolyzer = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_VarOM_NonElectrolyzer', 'path']
        )
        self.CO2CaptureRate = pd.read_csv(
            self.base_dir + self.paths_in.loc['CO2CaptureRate', 'path']
        )
        self.ElectrolyzerFuelConsumption = pd.read_csv(
            self.base_dir + self.paths_in.loc['ElectrolyzerFuelConsumption', 'path']
        )
        self.FeedstockConsumption = pd.read_csv(
            self.base_dir + self.paths_in.loc['FeedstockConsumption', 'path']
        )
        self.HPConsumption = pd.read_csv(self.base_dir + self.paths_in.loc['HPConsumption', 'path'])

        # load history dataframes:

        self.electrolyzer_learning_cap = pd.read_csv(
            self.base_dir + self.paths_in.loc['electrolyzer_learning_cap', 'path']
        )
        self.hist_prod_cap = pd.read_csv(self.base_dir + self.paths_in.loc['hist_prod_cap', 'path'])
        self.hist_storage_cap = pd.read_csv(
            self.base_dir + self.paths_in.loc['hist_storage_cap', 'path']
        )
        self.planned_cap = pd.read_csv(self.base_dir + self.paths_in.loc['planned_cap', 'path'])

        # load Transportation and Storage dataframes (TandS):

        self.base_StorageINJCost = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_StorageINJCost', 'path']
        )
        self.base_StorageWTHCost = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_StorageWTHCost', 'path']
        )
        self.base_SUCCost = pd.read_csv(self.base_dir + self.paths_in.loc['base_SUCCost', 'path'])
        self.base_TUCCost = pd.read_csv(self.base_dir + self.paths_in.loc['base_TUCCost', 'path'])
        self.base_TransportationCost = pd.read_csv(
            self.base_dir + self.paths_in.loc['base_TransportationCost', 'path']
        )
        self.pipeline_costs = pd.read_csv(
            self.base_dir + self.paths_in.loc['pipeline_costs', 'path']
        )
        self.TransportationArcs = [
            (row['regCen'], row['regCen_j'])
            for index, row in pd.read_csv(
                self.base_dir + self.paths_in.loc['regCENarcs', 'path']
            ).iterrows()
        ]

        # load other data:

        self.EMMRegion = pd.read_csv(
            self.base_dir + self.paths_in.loc['regions.NERCRegions_', 'path']
        )
        self.CensusRegion = pd.read_csv(
            self.base_dir + self.paths_in.loc['regions.CensusRegions_', 'path']
        ).CensusRegions_.tolist()
        self.smr_ng_feedstock_prc = pd.read_csv(
            self.base_dir + self.paths_in.loc['smr_ng_feedstock_prc', 'path']
        )

        # initialize general sets:

        self.CapacityVintageYear = range(2022, 2034)
        self.FuelType = ['NG', 'electricity']
        self.hour = np.arange(1, 25).tolist()
        self.PlanningPeriod = np.arange(1, 4).tolist()
        self.ProductionStep = np.arange(1, 4).tolist()
        self.DemandNode = self.CensusRegion
        self.SupplyNode = self.CensusRegion
        self.StorageNode = []
        self.Hub = self.CensusRegion
        # self.EMMRegion = pd.read_csv(self.base_dir + self.paths_in.loc['regions.NERCRegions_','path'])
        # ['TRE', 'FRCC', 'MISW', 'MISC', 'MISE', 'MISS', 'ISNE', 'NYCW', 'NYUP', 'PJME', 'PJMW', 'PJMC', 'PJMD',
        #       'SRCA', 'SRSE', 'SRCE', 'SPPS', 'SPPC', 'SPPN', 'SRSG', 'CANO', 'CASO', 'NWPP', 'RMRG', 'BASN']
        self.Season = np.arange(1, 5).tolist()
        self.StorageStep = np.arange(1, 4).tolist()
        self.StorageTechnologyType = self.base_SUCCost['storageTech'].unique().tolist()
        self.ProdTechnologyType = ['SMR', 'SMR_CCS', 'SMR_CCS_OFF', 'PEM']
        self.ProdTechnologyType_gasification = ['SMR', 'SMR_CCS', 'SMR_CCS_OFF']
        self.ProdTechnologyType_electrolysis = ['PEM']
        self.TransportationStep = np.arange(1, 4).tolist()

        # given a census region, tells you the the NERC regions inside it
        self.CensusToNERC = {
            'WSCentral': ['TRE', 'SPPS'],
            'SAtlantic': ['FRCC', 'SRCA', 'PJMD'],
            'ESCentral': ['MISC', 'MISS', 'SRSE', 'SRCE'],
            'ENCentral': ['MISC', 'MISE', 'PJMW', 'PJMC'],
            'NewEngland': ['ISNE'],
            'MidAtlantic': ['NYCW', 'NYUP', 'PJME'],
            'WNCentral': ['SPPC', 'SPPN'],
            'Mountain': ['SRSG', 'RMRG', 'BASN'],
            'Pacific': ['CANO', 'CASO', 'NWPP'],
        }

        # given a hub, tells you supply nodes that supply it
        self.SupplyNodesToHub = {hub: [hub] for hub in self.Hub}

        # given a supply node, tells you which hubs it supplies
        self.HubsFromSupplyNode = {hub: [hub] for hub in self.Hub}

        # given a hub, tells you which demand nodes it supplies
        self.DemandNodesFromHub = {hub: [hub] for hub in self.Hub}

        # given a demand node, tells you which hubs supply it
        self.HubsToDemandNode = {hub: [hub] for hub in self.Hub}

    # Functional parameter values:

    def FixedOM_Electrolyzer_f(self, model, hr, Seas, regNERC, tech, pp):
        value = self.base_FixedOM_Electrolyzer.set_index(['seas', 'regNERC', 'prodTech']).loc[
            (Seas, regNERC, tech), 'base_FixedOM_Electrolyzer'
        ]

        return value

    def FixedOM_NonElectrolyzer_f(self, model, Season, CensusRegion, tech, PlanningPeriod):
        value = self.base_FixedOM_NonElectrolyzer.set_index(['seas', 'regCen', 'prodTech']).loc[
            (Season, CensusRegion, tech), 'base_FixedOM_NonElectrolyzer'
        ]

        return value

    def PUC_nonElectrolyzer_f(self, model, CensusRegion, ProductionTechnologyType, PlanningPeriod):
        value = self.base_PUC_nonElectrolyzer.set_index(['regCen', 'prodTech']).loc[
            (CensusRegion, ProductionTechnologyType), 'base_PUCCostNonElectrolyzer'
        ]

        return value

    def PUCCostElectrolyzer_f(self, model, EMMRegion, ProductionTechnologyType, PlanningPeriod):
        value = self.base_PUCCostElectrolyzer.set_index(['regNERC', 'prodTech']).loc[
            (EMMRegion, ProductionTechnologyType), 'base_PUCCostElectrolyzer'
        ]

        return value

    def VarOM_Electrolyzer_f(
        self, model, hr, Season, regNERC, ProductionTechnologyType, PlanningPeriod
    ):
        value = self.base_VarOM_Electrolyzer.set_index(['seas', 'regNERC', 'prodTech']).loc[
            (Season, regNERC, ProductionTechnologyType), 'base_VarOM_Electrolyzer'
        ]

        return value

    def VarOM_NonElectrolyzer_f(self, model, Season, CensusRegion, tech, planningperiod):
        value = self.base_VarOM_NonElectrolyzer.set_index(['seas', 'regCen', 'prodTech']).loc[
            (Season, CensusRegion, tech), 'base_VarOM_NonElectrolyzer'
        ]
        return value

    def CO2CaptureRate_f(self, model, tech):
        value = self.CO2CaptureRate.set_index(['prodTech']).loc[tech, 'CO2CaptureRate']

        return value

    def ElectrolyzerFuelConsumption_f(self, model, fuel, tech):
        value = self.ElectrolyzerFuelConsumption.set_index(['prodTech', 'fuel']).loc[
            (tech, fuel), 'ElectrolyzerFuelConsumption'
        ]

        return value

    def FeedstockConsumption_f(self, model, prodtech, fuel):
        value = self.FeedstockConsumption.set_index(['prodTech', 'fuel']).loc[
            (prodtech, fuel), 'FeedstockConsumption'
        ]
        return value

    def HPConsumption_f(self, model, fuel, prodtech):
        value = self.HPConsumption.set_index(['prodTech', 'fuel']).loc[
            (prodtech, fuel), 'HPConsumption'
        ]

        return value

    def StorageINJCost_f(self, model, regcen, stortech):
        value = self.base_StorageINJCost.set_index(['regCen', 'storageTech']).loc[
            (regcen, stortech), 'base_StorageINJCost'
        ]

        return value

    def StorageWTHCost_f(self, model, regcen, stortech):
        value = self.base_StorageWTHCost.set_index(['regCen', 'storageTech']).loc[
            (regcen, stortech), 'base_StorageWTHCost'
        ]
        return

    def SUCCost_f(self, model, CensusRegion, StorageTechnology, PlanningPeriod):
        value = self.base_SUCCost.set_index(['regCen', 'storageTech']).loc[
            (CensusRegion, StorageTechnology), 'base_SUCCost'
        ]
        return value

    def TUCCost_f(self, model, regCen, regCen_j, PlanningPerioderiod):
        value = self.base_TUCCost.set_index(['regCen', 'regCen_j']).loc[
            (regCen, regCen_j), 'base_TUCCost'
        ]
        return value

    def TransportationCost_f(self, model, regCen, regCen_j, PlanningPeriod):
        value = self.base_TransportationCost.set_index(['regCen', 'regCen_j']).loc[
            (regCen, regCen_j), 'base_TransportationCost'
        ]
        return value

    def pipeline_costs_f(self, model, TransportationArc, PlanningPeriod):
        value = self.pipeline_costs.set_index(['regCen', 'regCen_j']).loc[
            TransportationArc, 'pipe_tcc'
        ]
        return value

    def SeasonalFraction_f(self, model, season):
        value = 0.25
        return value

    def HourlyFraction_f(self, model, hour):
        return 1 / 24

    def TaxCreditV_f(self, model, hr, season, EMMRegion, pp, cap_year):
        TaxCredit = 0

        return TaxCredit

    def CO2Value_f(self, model, census_region, pp, cap_year):
        return 0

    def FuelCost_f(self, model, Season, CensusRegion, FuelType, PlanningPeriod):
        return 2

    def OMCostElectrolyzer_f(self, model, hr, season, EMMRegion, prodtech, PlanningPeriod):
        value = self.FixedOM_Electrolyzer_f(
            model, hr, season, EMMRegion, prodtech, PlanningPeriod
        ) + self.VarOM_Electrolyzer_f(model, hr, season, EMMRegion, prodtech, PlanningPeriod)
        return value

    def OMCostNonElectrolyzer_f(
        self, model, Season, CensusRegion, ProductionTechnologyType, PlanningPeriod
    ):
        value = self.FixedOM_NonElectrolyzer_f(
            model, Season, CensusRegion, ProductionTechnologyType, PlanningPeriod
        ) + self.VarOM_NonElectrolyzer_f(
            model, Season, CensusRegion, ProductionTechnologyType, PlanningPeriod
        )

        return value

    def HourlyFuelCost_f(self, model, hour, season, EMMRegion, FuelType, pp):
        return 3

    def H2Demand_f(self, model, Season, DemandNode, PlanningPeriod):
        return 700000


"""
    def operational_process(self):
        
        # process the operational data
        
        # CO2CaptureRate
        
        self.CO2CaptureRate_dict = {row['prodTech']:row['CO2CaptureRate'] for index,row in self.CO2CaptureRate.iterrows()}
        
        # ElectrolyzerFuelConsumption
        
        self.electrolyzer_fuel_con_dict = {(row['prodTech'], row['fuel']):row['ElectrolyzerFuelConsumption'] for index, row in self.ElectrolyzerFuelConsumption.iterrows()}
        
        #
        
        self.HPConsumption_dict = {(row['prodTech'], row['fuel']):row['HPConsumption'] for index, row in self.HPConsumption.iterrows()}
        
        
        return
        

"""
