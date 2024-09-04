import pandas as pd
import sympy as sp
import pyomo.environ as pyo

class residentialModule:
    prices = {}
    loads = {}
    hr_to_s = pd.DataFrame()
    baseYear = 2023

    def __init__(self):
        self.year = sp.Idx('year')
        self.reg = sp.Idx('region')
        self.fuel = sp.Idx('fuel')
        self.LastHYr, self.LastMYr, self.BaseYr = sp.symbols(('LastHYr','LastMYr','base'))

        self.income = sp.IndexedBase('Income')
        self.incomeIndex = sp.IndexedBase('IncomeIndex')
        self.i_elas = sp.IndexedBase('IncomeElasticity')
        self.i_lag = sp.IndexedBase('IncomeLagParameter')

        self.price = sp.IndexedBase('Price')
        self.priceIndex = sp.IndexedBase('PriceIndex')
        self.p_elas = sp.IndexedBase('PriceElasticity')
        self.p_lag = sp.IndexedBase('PriceLagParameter')
        
        self.trendGR = sp.IndexedBase('TrendGR')

        self.consumption = sp.IndexedBase('Consumption')

        self.incomeEQ = (self.incomeIndex[self.year-1,self.reg,self.fuel] ** self.i_lag[self.reg,self.fuel]) * (self.income[self.year,self.reg,self.fuel]/self.income[self.BaseYr,self.reg,self.fuel]) ** self.i_elas[self.reg,self.fuel]
        self.priceEQ = (self.priceIndex[self.year-1,self.reg,self.fuel] ** self.p_lag[self.reg,self.fuel]) * (self.price[self.year,self.reg,self.fuel]/self.price[self.BaseYr,self.reg,self.fuel]) ** self.p_elas[self.reg,self.fuel]
        self.growthEQ = 1 + ((self.year - self.LastHYr)/(self.LastMYr - self.LastHYr)) * (((1 + self.trendGR[self.reg,self.fuel]) ** (self.LastMYr - self.LastHYr)) - 1)

        self.QIndex = self.incomeEQ * self.priceEQ * self.growthEQ

        self.demand = self.consumption[self.BaseYr,self.reg,self.fuel] * self.QIndex

        self.lambdifiedDemand = sp.lambdify([self.incomeIndex[self.year-1,self.reg,self.fuel],
                                    self.i_lag[self.reg,self.fuel],
                                    self.income[self.year,self.reg,self.fuel],
                                    self.income[self.BaseYr,self.reg,self.fuel],
                                    self.i_elas[self.reg,self.fuel],
                                    self.priceIndex[self.year-1,self.reg,self.fuel],
                                    self.p_lag[self.reg,self.fuel],
                                    self.price[self.year,self.reg,self.fuel],
                                    self.price[self.BaseYr,self.reg,self.fuel],
                                    self.p_elas[self.reg,self.fuel],
                                    self.year,
                                    self.LastHYr,
                                    self.LastMYr,
                                    self.trendGR[self.reg,self.fuel],
                                    self.consumption[self.BaseYr,self.reg,self.fuel]],
                                    self.demand)
        
        if not self.prices:
            priceData = pd.read_excel('../input/cem_elec_prices.xlsx').set_index(['r','y','hr'],drop=False)
            temploadData = pd.read_csv('../input/cem_inputs/Load.csv')
            temploadData = temploadData.loc[temploadData.y == 2023].set_index(['y','hr'],drop=False)
            cols = {f'r{i}':i for i in range(1,26)}
            temploadData = temploadData.rename(columns=cols)
            loadData = temploadData.loc[:,range(1,26)].stack().reset_index().rename(columns={'level_2':'r',0:'Load'}).set_index(['r','y','hr'],drop=False)
            self.set_base_values(priceData,loadData)
        
        self.demandF = lambda price, load, year, basePrice = 1, p_elas = -0.10, baseYear = self.baseYear, baseIncome = 1, income = 1, i_elas = 1, priceIndex = 1, incomeIndex = 1, p_lag = 1, i_lag = 1, trend = 0 : \
            self.lambdifiedDemand(incomeIndex, i_lag, income, baseIncome, i_elas, priceIndex, p_lag, price, basePrice, p_elas, year, baseYear, 2050, trend, load)
        
        pass
    
    #Sets up base values
    def set_base_values(self, p, load):
        self.prices['BasePrices'] = p
        self.baseYear = p.y.unique()
        self.loads['BaseLoads'] = load.Load
        return
    
    def update_load(self, p):
        hours = p.hr.unique()
        n = len(hours)
        newLoad = p.copy()
        hourMap = {}
        #hard-coded for the 4 seasons from 8760 data
        hourMap[1] = list(range(1,2161)) + list(range(8017,8761))
        hourMap[3] = range(2161,3625)
        hourMap[2] = range(3625,6553)
        hourMap[4] = range(6553,8017)
        newLoad['BasePrice'] = newLoad.apply(lambda row: sum(self.prices['BasePrices'].loc[(row.r,2023,hr),'Dual'] for hr in hourMap[row.hr])/(len(hourMap[row.hr])),axis=1)
        newLoad['Load'] = newLoad.apply(lambda row: self.demandF(row.Dual,self.loads['BaseLoads'].loc[(row.r,2023,row.hr)],row.y,row.BasePrice)[0],axis=1)
        return newLoad.Load
    
    #Creates a block that can be given to another pyomo model
    #The constraint is essentially just updating the load parameter
    def make_block(self, prices):
        loadIndex = []
        for i in prices.index:
            loadIndex.append((i[0],2023,i[2]))
        mod = pyo.ConcreteModel()
        mod.block = pyo.Block()

        mod.block.price_set = pyo.Set(initialize=prices.index)
        mod.block.load_set = pyo.Set(initialize=loadIndex)

        mod.block.prices = pyo.Param(mod.block.price_set, initialize=prices.Dual, mutable=True)
        mod.block.base_load = pyo.Param(mod.block.load_set, initialize=self.loads['BaseLoads'].loc[loadIndex], mutable=True)
        updated_load = self.update_load(prices)

        mod.block.Load = pyo.Var(mod.block.price_set, within=pyo.NonNegativeReals)

        @mod.block.Constraint(mod.block.price_set)
        def create_load(block,r,y,hr):
            return block.Load[r,y,hr] == updated_load.loc[(r,y,hr)]
        
        return mod.block
        
    #This is a standalone pyomo model
    #The objective function doesn't have much meaning
    #The real purpose is to have the load parameter changed into a variable that gets updated by the new prices
    def make_pyomo_model(self, prices):
        loadIndex = []
        for i in prices.index:
            loadIndex.append((i[0],2023,i[2]))
        mod = pyo.ConcreteModel()

        mod.price_set = pyo.Set(initialize=prices.index)
        mod.load_set = pyo.Set(initialize=loadIndex)
        
        mod.prices = pyo.Param(mod.price_set, initialize=prices.Dual, mutable=True)
        mod.base_load = pyo.Param(mod.load_set, initialize=self.loads['BaseLoads'].loc[loadIndex], mutable=True)
        updated_load = self.update_load(prices)
        
        mod.Load = pyo.Var(mod.price_set, within=pyo.NonNegativeReals)

        mod.obj = pyo.Objective(rule = sum(mod.Load[r,y,hr] for [r,y,hr] in mod.price_set))

        @mod.Constraint(mod.price_set)
        def create_new_load(mod,r,y,hr):
            return mod.Load[r,y,hr] == updated_load.loc[(r,y,hr)]
        
        return mod