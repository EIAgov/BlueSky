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

        # initialize general sets:

        self.CapacityVintageYear = range(2022, 2033)
        self.FuelType = ['NG', 'electricity']
        self.hour = np.arange(1, 25).tolist()
        self.PlanningPeriod = np.arange(1, 4).tolist()
        self.ProductionStep = np.arange(1, 4).tolist()
        self.CensusRegion = [
            'NewEngland',
            'MidAtlantic',
            'ENCentral',
            'WNCentral',
            'SAtlantic',
            'ESCentral',
            'WSCentral',
            'Mountain',
            'Pacific',
        ]
        self.DemandNode = self.CensusRegion
        self.SupplyNode = self.CensusRegion
        self.StorageNode = []
        self.EMMRegion = pd.read_csv(
            self.base_dir + self.paths_in.loc['regions.NERCRegions_', 'path']
        )
        # ['TRE', 'FRCC', 'MISW', 'MISC', 'MISE', 'MISS', 'ISNE', 'NYCW', 'NYUP', 'PJME', 'PJMW', 'PJMC', 'PJMD',
        #       'SRCA', 'SRSE', 'SRCE', 'SPPS', 'SPPC', 'SPPN', 'SRSG', 'CANO', 'CASO', 'NWPP', 'RMRG', 'BASN']
        self.Season = ['1', '2', '3', '4']
        self.StorageStep = np.arange(1, 4).tolist()


data = Data()
