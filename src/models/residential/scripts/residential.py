"""Residential Model.
This file contains the residentialModule class which contains a representation of residential
electricity prices and demands.
"""

###################################################################################################
# Setup

# Import packages
from pathlib import Path
import pandas as pd
from src.integrator.config_setup import Config_settings
import sympy as sp
import pyomo.environ as pyo
import sys
import matplotlib.pyplot as plt
from logging import getLogger
import numpy as np

# Import scripts
from definitions import PROJECT_ROOT
from src.integrator.utilities import get_output_root

# Establish Logger
logger = getLogger(__name__)

###################################################################################################
# MODEL


class residentialModule:
    """
    This contains the Residential model and its associated functions. Once an object is instantiated, it can calculate new Load values for updated prices.
    It can also calculate estimated changes to the Load if one of the input variables is changed by a specified percent.
    The model will be created in a symbolic form to be easily manipulated, and then values can be filled in for calculations.
    """

    prices = {}
    loads = {}
    hr_map = pd.DataFrame()
    baseYear = int()

    def __init__(
        self,
        settings: Config_settings | None = None,
        loadFile: str | None = None,
        load_df: pd.DataFrame | None = None,
        calibrate: bool | None = False,
    ):
        """Sets up the sympy version of the residential module. This includes
        the 3 updating indexes, the combined full equation, and the equation converted to a python lambda function.
        It also loads in the base values for Load if they haven't been established yet.


        Parameters
        ----------
        loadFile : str, optional
            An optional filepath if a different or new baseline Load fileis needed, by default 'input/Load.csv'
        """
        # if none, create a settings object
        if not settings:
            config_path = Path(PROJECT_ROOT, 'src/integrator', 'run_config.toml')
            settings = Config_settings(config_path=config_path, test=True)
        # Create indexes
        self.year = sp.Idx('year')
        self.reg = sp.Idx('region')
        self.fuel = sp.Idx('fuel')
        self.LastHYr, self.LastMYr, self.BaseYr = sp.symbols(('LastHYr', 'LastMYr', 'base'))

        # Create income related Indexed variables
        self.income = sp.IndexedBase('Income')
        self.incomeIndex = sp.IndexedBase('IncomeIndex')
        self.i_elas = sp.IndexedBase('IncomeElasticity')
        self.i_lag = sp.IndexedBase('IncomeLagParameter')

        # Create price related Indexed variables
        self.price = sp.IndexedBase('Price')
        self.priceIndex = sp.IndexedBase('PriceIndex')
        self.p_elas = sp.IndexedBase('PriceElasticity')
        self.p_lag = sp.IndexedBase('PriceLagParameter')

        # Create indexed Trend variable
        self.trendGR = sp.IndexedBase('TrendGR')

        self.consumption = sp.IndexedBase('Consumption')

        # Create the 3 updating indexes for income, price, and trend
        self.incomeEQ = (
            self.incomeIndex[self.year - 1, self.reg, self.fuel] ** self.i_lag[self.reg, self.fuel]
        ) * (
            self.income[self.year, self.reg, self.fuel]
            / self.income[self.BaseYr, self.reg, self.fuel]
        ) ** self.i_elas[self.reg, self.fuel]
        self.priceEQ = (
            self.priceIndex[self.year - 1, self.reg, self.fuel] ** self.p_lag[self.reg, self.fuel]
        ) * (
            self.price[self.year, self.reg, self.fuel]
            / self.price[self.BaseYr, self.reg, self.fuel]
        ) ** self.p_elas[self.reg, self.fuel]
        self.growthEQ = 1 + ((self.year - self.LastHYr) / (self.LastMYr - self.LastHYr)) * (
            ((1 + self.trendGR[self.reg, self.fuel]) ** (self.LastMYr - self.LastHYr)) - 1
        )

        # Combine the indexes and calculate new demand by updating the base Load
        self.QIndex = self.incomeEQ * self.priceEQ * self.growthEQ
        self.demand = self.consumption[self.BaseYr, self.reg, self.fuel] * self.QIndex

        # Convert equation into lambda function for use in python
        self.lambdifiedDemand = sp.lambdify(
            [
                self.incomeIndex[self.year - 1, self.reg, self.fuel],
                self.i_lag[self.reg, self.fuel],
                self.income[self.year, self.reg, self.fuel],
                self.income[self.BaseYr, self.reg, self.fuel],
                self.i_elas[self.reg, self.fuel],
                self.priceIndex[self.year - 1, self.reg, self.fuel],
                self.p_lag[self.reg, self.fuel],
                self.price[self.year, self.reg, self.fuel],
                self.price[self.BaseYr, self.reg, self.fuel],
                self.p_elas[self.reg, self.fuel],
                self.year,
                self.LastHYr,
                self.LastMYr,
                self.trendGR[self.reg, self.fuel],
                self.consumption[self.BaseYr, self.reg, self.fuel],
            ],
            self.demand,
        )

        # Set base Load values if they aren't already set
        if loadFile:
            self.loads['BaseLoads'] = pd.read_csv(loadFile).set_index(['r', 'y', 'hr'], drop=False)
        elif not self.loads:
            root_path = PROJECT_ROOT

            y = 2023
            path_to_load_data = Path(PROJECT_ROOT, 'src/models/residential/input/load/Load_'+str(y)+'.csv')
            self.loads['BaseLoads']  = pd.read_csv(path_to_load_data)
            for y in range(2024,2050):
                path_to_load_data = Path(PROJECT_ROOT, 'src/models/residential/input/load/Load_'+str(y)+'.csv')
                tmp = pd.read_csv(path_to_load_data)
                self.loads['BaseLoads'] = pd.concat([self.loads['BaseLoads'],tmp]).reset_index(drop=True)

            self.loads['BaseLoads'] = self.loads['BaseLoads'].set_index(
                ['r', 'y', 'hr'], drop=False
            )

        # Set base year if not already set
        if not self.baseYear:
            # TODO:  How could this below work after y has been made part of the index?
            self.baseYear = self.loads['BaseLoads'].y.min()

        # Create hour map if not already set
        if self.hr_map.empty:
            # TODO:  update config path reference
            self.hr_map = settings.cw_temporal
            self.hr_map.set_index('hr', inplace=True, drop=False)
        pass

        # Create base price values if they aren't already set
        if 'BasePrices' not in residentialModule.prices.keys():
            path_to_price_data = PROJECT_ROOT / 'src/models/residential/input/BaseElecPrice.csv'
            residentialModule.prices['BasePrices'] = pd.read_csv(path_to_price_data).set_index(
                ['r', 'y', 'hr'], drop=False
            )

        self.calibrate = calibrate

        # Make lambdifiedDemand function easier to use with named inputs and default values for potentially unused variables
        self.demandF = (
            lambda price,
            load,
            year,
            basePrice=1,
            p_elas=-0.10,
            baseYear=residentialModule.baseYear,
            baseIncome=1,
            income=1,
            i_elas=1,
            trend=0,
            priceIndex=1,
            incomeIndex=1,
            p_lag=1,
            i_lag=1: self.lambdifiedDemand(
                incomeIndex,
                i_lag,
                income,
                baseIncome,
                i_elas,
                priceIndex,
                p_lag,
                price,
                basePrice,
                p_elas,
                year,
                baseYear,
                2050,
                trend,
                load,
            )
        )

    def update_load(self, p):
        """Takes in Dual pyomo Parameters or dataframes to update Load values

        Parameters
        ----------
        p : pyo.Param
            Pyomo Parameter or dataframe of newly updated prices from Duals

        Returns
        -------
        pandas DataFrame :
            Load values indexed by region, year, and hour
        """
        # Read in price values
        if type(p) == pyo.base.param.IndexedParam:
            newLoad = pd.DataFrame(
                [(i[0], i[1], i[2], p[i].value) for i in p], columns=['r', 'y', 'hr', 'newPrice']
            )
        elif len(p.columns) == 1:
            newLoad = p.rename(columns={list(p)[0]: 'newPrice'}).reset_index(names=['r', 'y', 'hr'])
        else:
            newLoad = p.rename(
                columns={list(p)[0]: 'newPrice', list(p)[1]: 'r', list(p)[2]: 'y', list(p)[3]: 'hr'}
            )

        newLoad.newPrice = abs(newLoad.newPrice)

        # Create average base prices and loads based on hourly structure used
        # This will store the averaged values in the first run to be called later
        if 'AvgBasePrice' not in residentialModule.prices.keys():
            hours = newLoad.hr.unique()

            # Create a map for hour types to create averages
            if len(hours) == 4:
                hourMap = {i: [] for i in hours}
                for h in range(1, len(self.hr_map) + 1):
                    hourMap[self.hr_map.loc[h, 'Map_s']].append(h)
            elif len(hours) == 8760:
                hourMap = {i: [] for i in hours}
                for h in range(1, len(self.hr_map) + 1):
                    hourMap[self.hr_map.loc[h, 'hr']].append(h)
            else:
                hourMap = {i: [] for i in hours}
                for h in range(1, len(self.hr_map) + 1):
                    hourMap[self.hr_map.loc[h, 'Map_hr']].append(h)

            # Create average base values for price and load based on hours in the new prices
            newLoad['AvgBasePrice'] = newLoad.apply(
                lambda row: sum(
                    self.prices['BasePrices'].loc[(row.r, self.baseYear, hr), 'price_wt']
                    for hr in hourMap[row.hr]
                )
                / (len(hourMap[row.hr])),
                axis=1,
            )
            newLoad['AvgBaseLoad'] = newLoad.apply(
                lambda row: sum(
                    self.loads['BaseLoads'].loc[(row.r, self.baseYear, hr), 'Load']
                    * self.hr_map.loc[hr, 'Hr_weights']
                    for hr in hourMap[row.hr]
                )
                / (len(hourMap[row.hr])),
                axis=1,
            )
            residentialModule.prices['AvgBasePrice'] = newLoad['AvgBasePrice']
            residentialModule.loads['AvgBaseLoad'] = newLoad['AvgBaseLoad']
        else:
            newLoad['AvgBasePrice'] = residentialModule.prices['AvgBasePrice']
            newLoad['AvgBaseLoad'] = residentialModule.loads['AvgBaseLoad']

        # Calculate new load values with or without the calibrate file
        if self.calibrate == True:
            demandInputs = pd.read_csv(
                PROJECT_ROOT / 'src/models/residential/input/demand_inputs.csv'
            )
            newLoad = newLoad.merge(demandInputs, on=['r', 'y', 'hr'])
            newLoad['Load'] = self.demandF(
                newLoad.newPrice,
                newLoad.AvgBaseLoad,
                newLoad.y,
                newLoad.AvgBasePrice,
                newLoad.p_elas,
                self.prices['BasePrices'].y.min(),
                1,
                newLoad.income,
                newLoad.i_elas,
                newLoad.trendGR,
                1,
                1,
                1,
                1,
            )
        else:
            newLoad['Load'] = self.demandF(
                newLoad.newPrice, newLoad.AvgBaseLoad, newLoad.y, newLoad.AvgBasePrice
            )
        newLoad = newLoad.set_index(['r', 'y', 'hr'], drop=False)
        return newLoad

    def sensitivity(self, prices, change_var, percent):
        """This estimates how much the output Load will change due to a change in one of the input variables.
        It can calculate these values for changes in price, price elasticity, income, income elasticity, or long term trend.
        The Load calculation requires input prices, so this function requires that as well for the base output Load.
        Then, an estimate for Load is calculated for the case where the named 'change_var' is changed by 'percent' %.

        Parameters
        ----------
        prices : dataframe or Pyomo Indexed Parameter
            Price values used to calculate the Load value
        change_var : string
            Name of variable of interest for sensitivity. This can be:
                'income', 'i_elas', 'price', 'p_elas', 'trendGR'
        percent : float
            A value 0 - 100 for the percent that the variable of interest can change.

        Returns
        -------
        dataframe
            Indexed values for the calculated Load at the given prices, the Load if the variable of interest is increased by 'percent'%, and the Load if the variable of interest is decreased by 'percent'%
        """
        # Create dummy symbols for all indexed variables. The derivative wasn't working correctly when the indexes were present
        (
            income,
            baseIncome,
            incomeIndex,
            i_elas,
            i_lag,
            price,
            basePrice,
            priceIndex,
            p_elas,
            p_lag,
            trendGR,
            consumption,
            year,
            LastHYr,
            LastMYr,
        ) = sp.symbols(
            (
                'Income',
                'BaseIncome',
                'IncomeIndex',
                'IncomeElasticity',
                'IncomeLagParameter',
                'Price',
                'BasePrice',
                'PriceIndex',
                'PriceElasticity',
                'PriceLagParameter',
                'TrendGR',
                'Consumption',
                'year',
                'LastHYr',
                'LastMYr',
            )
        )

        # Substitute in dummy variables and create new derivative function
        converted = self.demand.subs(
            {
                self.incomeIndex[self.year - 1, self.reg, self.fuel]: incomeIndex,
                self.i_lag[self.reg, self.fuel]: i_lag,
                self.income[self.year, self.reg, self.fuel]: income,
                self.income[self.BaseYr, self.reg, self.fuel]: baseIncome,
                self.i_elas[self.reg, self.fuel]: i_elas,
                self.priceIndex[self.year - 1, self.reg, self.fuel]: priceIndex,
                self.p_lag[self.reg, self.fuel]: p_lag,
                self.price[self.year, self.reg, self.fuel]: price,
                self.price[self.BaseYr, self.reg, self.fuel]: basePrice,
                self.p_elas[self.reg, self.fuel]: p_elas,
                self.year: year,
                self.LastHYr: LastHYr,
                self.LastMYr: LastMYr,
                self.trendGR[self.reg, self.fuel]: trendGR,
                self.consumption[self.BaseYr, self.reg, self.fuel]: consumption,
            }
        )

        if change_var == 'income':
            wrt = income
        elif change_var == 'i_elas':
            wrt = i_elas
        elif change_var == 'price':
            wrt = price
        elif change_var == 'p_elas':
            wrt = p_elas
        elif change_var == 'trendGR':
            wrt = trendGR

        change = percent / 100

        deriv = sp.diff(converted, wrt)
        lambdified_deriv = sp.lambdify(
            [
                incomeIndex,
                i_lag,
                income,
                baseIncome,
                i_elas,
                priceIndex,
                p_lag,
                price,
                basePrice,
                p_elas,
                year,
                LastHYr,
                LastMYr,
                trendGR,
                consumption,
            ],
            deriv,
        )
        deriv_function = (
            lambda price,
            load,
            year,
            basePrice=1,
            p_elas=-0.10,
            baseYear=self.baseYear,
            baseIncome=1,
            income=1,
            i_elas=1,
            trend=0,
            lastYear=2050,
            priceIndex=1,
            incomeIndex=1,
            p_lag=1,
            i_lag=1: lambdified_deriv(
                incomeIndex,
                i_lag,
                income,
                baseIncome,
                i_elas,
                priceIndex,
                p_lag,
                price,
                basePrice,
                p_elas,
                year,
                baseYear,
                lastYear,
                trend,
                load,
            )
        )

        # Create base Load value and then adjust by derivative method
        newValues = self.update_load(prices)

        if self.calibrate:
            newValues['deriv'] = deriv_function(
                newValues.newPrice,
                newValues.AvgBaseLoad,
                newValues.y,
                newValues.AvgBasePrice,
                newValues.p_elas,
                self.baseYear,
                1,
                newValues.income,
                newValues.i_elas,
                newValues.trendGR,
                1,
                1,
                1,
                1,
            )
            if change_var == 'price':
                newValues['upper'] = newValues.Load + newValues.deriv * change * newValues.newPrice
                newValues['lower'] = newValues.Load - newValues.deriv * change * newValues.newPrice
            else:
                newValues['upper'] = (
                    newValues.Load + newValues.deriv * change * newValues[f'{change_var}']
                )
                newValues['lower'] = (
                    newValues.Load - newValues.deriv * change * newValues[f'{change_var}']
                )
        else:
            newValues['deriv'] = deriv_function(
                newValues.newPrice, newValues.AvgBaseLoad, newValues.y, newValues.AvgBasePrice
            )
            if change_var == 'price':
                newValues['upper'] = newValues.Load + newValues.deriv * change * newValues.newPrice
                newValues['lower'] = newValues.Load - newValues.deriv * change * newValues.newPrice
            elif change_var == 'p_elas':
                newValues['upper'] = newValues.Load + newValues.deriv * change * 0.1
                newValues['lower'] = newValues.Load - newValues.deriv * change * 0.1
            else:
                newValues['upper'] = newValues.Load + newValues.deriv * change
                newValues['lower'] = newValues.Load - newValues.deriv * change

        return newValues[['Load', 'upper', 'lower']]

    def complex_step_sensitivity(self, prices, change_var, percent):
        """This estimates how much the output Load will change due to a change in one of the input variables.
        It can calculate these values for changes in price, price elasticity, income, income elasticity, or long term trend.
        The Load calculation requires input prices, so this function requires that as well for the base output Load.
        Then, an estimate for Load is calculated for the case where the named 'change_var' is changed by 'percent' %.

        Parameters
        ----------
        prices : dataframe or Pyomo Indexed Parameter
            Price values used to calculate the Load value
        change_var : string
            Name of variable of interest for sensitivity. This can be:
                'income', 'i_elas', 'price', 'p_elas', 'trendGR'
        percent : float
            A value 0 - 100 for the percent that the variable of interest can change.

        Returns
        -------
        dataframe
            Indexed values for the calculated Load at the given prices, the Load if the variable of interest is increased by 'percent'%, and the Load if the variable of interest is decreased by 'percent'%
        """

        change = percent / 100

        complex_step = 0.0000000001
        dih = complex(0.0, complex_step)

        if type(prices) == pyo.base.param.IndexedParam:
            newLoad = pd.DataFrame(
                [(i[0], i[1], i[2], prices[i].value) for i in prices],
                columns=['r', 'y', 'hr', 'newPrice'],
            )
        elif len(prices.columns) == 1:
            newLoad = prices.rename(columns={list(prices)[0]: 'newPrice'}).reset_index(
                names=['r', 'y', 'hr']
            )
        else:
            newLoad = prices.rename(
                columns={
                    list(prices)[0]: 'newPrice',
                    list(prices)[1]: 'r',
                    list(prices)[2]: 'y',
                    list(prices)[3]: 'hr',
                }
            )
        prices = abs(prices)

        hours = newLoad.hr.unique()

        # Create a map for hour types to create averages
        if len(hours) == 4:
            hourMap = {i: [] for i in hours}
            for h in range(1, len(self.hr_map) + 1):
                hourMap[self.hr_map.loc[h, 'Map_s']].append(h)
        elif len(hours) == 8760:
            hourMap = {i: [] for i in hours}
            for h in range(1, len(self.hr_map) + 1):
                hourMap[self.hr_map.loc[h, 'hr']].append(h)
        else:
            hourMap = {i: [] for i in hours}
            for h in range(1, len(self.hr_map) + 1):
                hourMap[self.hr_map.loc[h, 'Map_hr']].append(h)

        # Create average base values for price and load based on hours in the new prices
        newLoad['AvgBasePrice'] = newLoad.apply(
            lambda row: sum(
                self.prices['BasePrices'].loc[(row.r, self.baseYear, hr), 'price_wt']
                for hr in hourMap[row.hr]
            )
            / (len(hourMap[row.hr])),
            axis=1,
        )
        newLoad['AvgBaseLoad'] = newLoad.apply(
            lambda row: sum(
                self.loads['BaseLoads'].loc[(row.r, self.baseYear, hr), 'Load']
                * self.hr_map.loc[hr, 'Hr_weights']
                for hr in hourMap[row.hr]
            )
            / (len(hourMap[row.hr])),
            axis=1,
        )

        if change_var == 'income':
            newLoad['income'] = 1 + dih
            newLoad['Load'] = self.demandF(
                newLoad.newPrice,
                newLoad.AvgBaseLoad,
                newLoad.y,
                newLoad.AvgBasePrice,
                income=newLoad.income,
            )
        elif change_var == 'i_elas':
            newLoad['i_elas'] = 1 + dih
            newLoad['Load'] = self.demandF(
                newLoad.newPrice,
                newLoad.AvgBaseLoad,
                newLoad.y,
                newLoad.AvgBasePrice,
                i_elas=newLoad.i_elas,
            )
        elif change_var == 'p_elas':
            newLoad['p_elas'] = dih - 0.1
            newLoad['Load'] = self.demandF(
                newLoad.newPrice,
                newLoad.AvgBaseLoad,
                newLoad.y,
                newLoad.AvgBasePrice,
                p_elas=newLoad.p_elas,
            )
        elif change_var == 'trendGR':
            newLoad['trendGR'] = dih
            newLoad['Load'] = self.demandF(
                newLoad.newPrice,
                newLoad.AvgBaseLoad,
                newLoad.y,
                newLoad.AvgBasePrice,
                trend=newLoad.trendGR,
            )
        else:
            newLoad['price'] = newLoad.newPrice + dih
            newLoad['Load'] = self.demandF(
                newLoad.price, newLoad.AvgBaseLoad, newLoad.y, newLoad.AvgBasePrice
            )

        newLoad['deriv'] = np.imag(newLoad.Load) / complex_step
        newLoad.Load = np.real(newLoad.Load)

        newLoad['upper'] = newLoad.Load + newLoad.deriv * change * np.real(newLoad[change_var])
        newLoad['lower'] = newLoad.Load - newLoad.deriv * change * np.real(newLoad[change_var])

        newLoad = newLoad.set_index(['r', 'y', 'hr'], drop=False)

        return newLoad[['Load', 'upper', 'lower']]

    def view_sensitivity(
        self, values: pd.DataFrame, regions: list[int] = [1], years: list[int] = [2023]
    ):
        """This is used by the sensitivity method to display graphs of the calculated values

        Parameters
        ----------
        values : pd.DataFrame
            indexed values for the Load, upper change, and lower change
        regions : list[int], optional
            regions to be graphed
        years : list[int], optional
            years to be graphed
        """
        values.reset_index(inplace=True)
        OUTPUT_ROOT = get_output_root()
        if 'plotly' in sys.modules:
            pd.options.plotting.backend = 'plotly'
            for y in years:
                for r in regions:
                    values.loc[(values.r == r) & (values.y == y)].plot(
                        x='hr',
                        y=['upper', 'lower', 'Load'],
                        title=f'Load Values For Region {r} In Year {y}',
                        labels={'hr': 'Hours', 'value': 'Load Values'},
                    )
                    plt.savefig(
                        Path(OUTPUT_ROOT, f'NewLoadSensitivity_{r}_{y}.png'), format='png', dpi=300
                    )
        else:
            for y in years:
                for r in regions:
                    values.loc[(values.r == r) & (values.y == y)].plot(
                        x='hr',
                        y=['upper', 'lower', 'Load'],
                        title=f'Load Values For Region {r} In Year {y}',
                        xlabel='Hours',
                        ylabel='Load Value',
                    )
                    plt.savefig(
                        Path(OUTPUT_ROOT, f'NewLoadSensitivity_{r}_{y}.png'), format='png', dpi=300
                    )
        pass

    def view_output_load(
        self, values: pd.DataFrame, regions: list[int] = [1], years: list[int] = [2023]
    ):
        """This is used to display the updated Load values after calculation. It will create a graph for each region and year combination.

        Parameters
        ----------
        values : pd.DataFrame
            The Load values calculated in update_load
        regions : list[int], optional
            The regions to be displayed
        years : list[int], optional
            The years to be displayed
        """
        OUTPUT_ROOT = get_output_root()
        if 'plotly' in sys.modules:
            pd.options.plotting.backend = 'plotly'
            for y in years:
                for r in regions:
                    values.loc[(values.r == r) & (values.y == y)].plot(
                        x='hr',
                        y='Load',
                        title=f'Load Values For Region {r} In Year {y}',
                        labels={'hr': 'Hours', 'value': 'Load Values'},
                    )
                    plt.savefig(Path(OUTPUT_ROOT, f'NewLoad_{r}_{y}.png'), format='png', dpi=300)
        else:
            for y in years:
                for r in regions:
                    values.loc[(values.r == r) & (values.y == y)].plot(
                        x='hr',
                        y='Load',
                        title=f'Load Values For Region {r} In Year {y}',
                        xlabel='Hours',
                        ylabel='Load Value',
                    )
                    plt.savefig(Path(OUTPUT_ROOT, f'NewLoad_{r}_{y}.png'), format='png', dpi=300)
        pass

    # Creates a block that can be given to another pyomo model
    # The constraint is essentially just updating the load parameter
    def make_block(self, prices, pricesindex):
        """Updates the value of 'Load' based on the new prices given.
        The new prices are fed into the equations from the residential model.
        The new calculated Loads are used to constrain 'Load' in pyomo blocks.

        Parameters
        ----------
        prices : pyo.Param
            Pyomo Parameter of newly updated prices
        pricesindex : pyo.Set
            Pyomo Set of indexes that matches the prices given

        Returns
        -------
        pyo.Block :
            Block containing constraints that set 'Load' variable equal to the updated load values
        """

        # Create block to be returned
        mod = pyo.Block()

        mod.price_set = pyo.Set(initialize=pricesindex)

        # Call function to get updated values for Load
        mod.updated_load = self.update_load(prices)
        # mod.base_load = pyo.Param(mod.price_set, initialize=updated_load.index, mutable=True)
        mod.Load = pyo.Var(mod.price_set, within=pyo.NonNegativeReals)

        # Create constraints that restrict the Load variable to the newly calculated values
        @mod.Constraint(mod.price_set)
        def create_load(mod, r, y, hr):
            return mod.Load[r, y, hr] == mod.updated_load.loc[(r, y, hr), 'Load']

        return mod


def run_residential(settings: Config_settings):
    """This runs the residential model in stand-alone mode. It can run update_load to calculate new Load values based on prices,
    or it can calculate the new Load value along with estimates for the Load if one of the input variables changes.

    Parameters
    ----------
    settings : Config_settings
        information given from run_config to set several values
    """
    logger.info('Creating residentialModule object')
    input_path = PROJECT_ROOT / 'src/models/residential/input/testPrices.csv'
    model = residentialModule(settings=settings)
    testPrices = pd.read_csv(input_path)
    testPricesSelected = testPrices.loc[
        (testPrices.r.isin(settings.regions)) & (testPrices.y.isin(settings.years))
    ]
    testPricesSelected.set_index(['r', 'y', 'hr'], inplace=True)
    # Run the model using either the sensitivity method or the update_load method based on settings
    if settings.sensitivity & settings.complex:
        logger.info('Calling complex-step sensitivity function')
        Loads = model.complex_step_sensitivity(
            testPricesSelected, settings.change_var, settings.percent_change
        )
        logger.info('Calling viewer')
        model.view_sensitivity(Loads, settings.view_regions, settings.view_years)
    elif settings.sensitivity:
        logger.info('Calling analytical sensitivity function')
        Loads = model.sensitivity(testPricesSelected, settings.change_var, settings.percent_change)
        logger.info('Calling viewer')
        model.view_sensitivity(Loads, settings.view_regions, settings.view_years)
    else:
        logger.info('Calling update load function')
        Loads = model.update_load(testPricesSelected)
        logger.info('Calling viewer')
        model.view_output_load(Loads, settings.view_regions, settings.view_years)
