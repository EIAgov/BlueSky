"""Electricity Model.
This file contains the PowerModel class which contains a pyomo optimization model of the electric
power sector. The class is organized by sections: settings, sets, parameters, variables, objective
function, constraints, plus additional misc support functions.
"""
###################################################################################################
# Setup

# Import packages
from collections import defaultdict
from logging import getLogger
import pyomo.environ as pyo

# Import scripts
from src.integrator.utilities import HI
import src.models.electricity.scripts.utilities as f

# Establish logger
logger = getLogger(__name__)

###################################################################################################
# MODEL


class PowerModel(pyo.ConcreteModel):
    """A PowerModel instance. Builds electricity pyomo model.

    Parameters
    ----------
    all_frames : dictionary of pd.DataFrames
        Contains all dataframes of inputs
    setA : Sets
        Contains all other non-dataframe inputs
    """

    def __init__(self, all_frames, setA, *args, **kwargs):
        pyo.ConcreteModel.__init__(self, *args, **kwargs)

        ###########################################################################################
        # Settings

        self.sw_trade = setA.sw_trade
        self.sw_expansion = setA.sw_expansion
        self.sw_agg_years = setA.sw_agg_years
        self.sw_rm = setA.sw_rm
        self.sw_ramp = setA.sw_ramp
        self.sw_reserves = setA.sw_reserves
        self.sw_h2int = 0

        # 0=no learning, 1=linear iterations, 2=nonlinear learning
        self.sw_learning = setA.sw_learning

        # dictionary to lookup column names for sets, params, variables
        self.cols_dict = {}

        ###########################################################################################
        # Sets

        # TODO: extra reference to the setA for external use... ?
        self.setA = setA

        # temporal sets
        self.hr = pyo.Set(initialize=setA.hr)
        self.day = pyo.Set(initialize=setA.day)
        self.y = pyo.Set(initialize=setA.years)
        self.s = pyo.Set(initialize=setA.s)

        # spatial sets
        self.r = pyo.Set(initialize=setA.r)
        self.r_can = pyo.Set(initialize=setA.r_can)

        # Load sets
        self.LoadSet = f.declare_set(self, 'LoadSet', all_frames['Load'])
        self.UnmetSet = self.r * self.y * self.hr
        self.cols_dict['UnmetSet'] = ['UnmetSet', 'r', 'y', 'hr']

        # Supply price and quanity sets and subsets
        self.SupplyCurveSet = f.declare_set(self, 'SupplyCurveSet', all_frames['SupplyCurve'])
        self.GenSet = f.declare_set(self, 'GenSet', getattr(setA, 'GenSet'))
        self.ptd_upper_set = f.declare_set(self, 'ptd_upper_set', getattr(setA, 'ptd_upper_set'))
        self.StorageSet = f.declare_set(self, 'StorageSet', getattr(setA, 'StorageSet'))
        self.H2GenSet = f.declare_set(self, 'H2GenSet', getattr(setA, 'H2GenSet'))
        self.pth_upper_set = f.declare_set(self, 'pth_upper_set', getattr(setA, 'pth_upper_set'))
        self.Gen_ramp_set = f.declare_set(self, 'Gen_ramp_set', getattr(setA, 'Gen_ramp_set'))
        self.FirstHour_gen_ramp_set = f.declare_set(
            self, 'FirstHour_gen_ramp_set', getattr(setA, 'FirstHour_gen_ramp_set')
        )
        self.StorageBalance_set = f.declare_set(
            self, 'StorageBalance_set', getattr(setA, 'StorageBalance_set')
        )
        self.FirstHourStorageBalance_set = f.declare_set(
            self, 'FirstHourStorageBalance_set', getattr(setA, 'FirstHourStorageBalance_set')
        )
        self.HydroMonthsSet = f.declare_set(self, 'HydroMonthsSet', getattr(setA, 'HydroMonthsSet'))

        # Other technology sets
        self.HydroSet = f.declare_set(self, 'HydroSet', all_frames['HydroCapFactor'])
        self.DaySHydro = pyo.Set(self.s)
        self.HourSHydro = pyo.Set(self.s)
        self.ptiUpperSet = f.declare_set(self, 'ptiUpperSet', all_frames['ptiUpperSet'])
        self.H2PriceSet = f.declare_set(self, 'H2PriceSet', all_frames['H2Price'])

        # if capacity expansion is on
        if self.sw_expansion:
            self.CapCostSet = f.declare_set(self, 'CapCostSet', all_frames['CapCost'])
            self.FOMCostSet = f.declare_set(self, 'FOMCostSet', all_frames['FOMCost'])
            self.BuildSet = f.declare_set(self, 'BuildSet', getattr(setA, 'BuildSet'))
            self.CapacityCreditSet = f.declare_set(
                self, 'CapacityCreditSet', all_frames['CapacityCredit']
            )
            self.RetSet = f.declare_set(self, 'RetSet', getattr(setA, 'RetSet'))

            # if capacity expansion and learning are on
            if self.sw_learning > 0:
                self.LearningRateSet = f.declare_set(
                    self, 'LearningRateSet', all_frames['LearningRate']
                )
                self.CapCost0Set = f.declare_set(self, 'CapCost0Set', all_frames['CapCost_y0'])
                self.LearningPtSet = f.declare_set(
                    self, 'LearningPtSet', all_frames['SupplyCurve_learning']
                )

        # if trade operation is on
        if self.sw_trade:
            self.TranCostSet = f.declare_set(self, 'TranCostSet', all_frames['TranCost'])
            self.TranLimitSet = f.declare_set(self, 'TranLimitSet', all_frames['TranLimit'])
            self.TradeSet = f.declare_set(self, 'TradeSet', getattr(setA, 'TradeSet'))
            self.TranCostCanSet = f.declare_set(self, 'TranCostCanSet', all_frames['TranCostCan'])
            self.TranLimitCanSet = f.declare_set(
                self, 'TranLimitCanSet', all_frames['TranLimitCan']
            )
            self.TradeCanSet = f.declare_set(self, 'TradeCanSet', getattr(setA, 'TradeCanSet'))
            self.TranLineLimitCanSet = f.declare_set(
                self, 'TranLineLimitCanSet', all_frames['TranLineLimitCan']
            )

        # if ramping requirements are on
        if self.sw_ramp:
            self.RampUp_CostSet = f.declare_set(self, 'RampUp_CostSet', all_frames['RampUp_Cost'])
            self.RampRateSet = f.declare_set(self, 'RampRateSet', all_frames['RampRate'])
            self.RampSet = f.declare_set(self, 'RampSet', getattr(setA, 'RampSet'))

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.ProcurementSet = f.declare_set(
                self, 'ProcurementSet', getattr(setA, 'ProcurementSet')
            )
            self.RegReservesCostSet = f.declare_set(
                self, 'RegReservesCostSet', all_frames['RegReservesCost']
            )
            self.ResTechUpperBoundSet = f.declare_set(
                self, 'ResTechUpperBoundSet', all_frames['ResTechUpperBound']
            )

        ###########################################################################################
        # Parameters

        # temporal parameters
        self.Map_hr_s = f.declare_param(self, 'Map_hr_s', self.hr, all_frames['Map_hr_s'])
        self.Map_hr_d = f.declare_param(self, 'Map_hr_d', self.hr, all_frames['Map_hr_d']['day'])

        self.df_Map_hr_d = all_frames['Map_hr_d'].reset_index()  # used in postprocessing duals

        self.year_weights = f.declare_param(
            self, 'year_weights', self.y, all_frames['year_weights']
        )
        self.df_year_weights = all_frames[
            'year_weights'
        ].reset_index()  # used in postprocessing duals

        self.Hr_weights = f.declare_param(
            self, 'Hr_weights', self.hr, all_frames['Hr_weights']['Hr_weights']
        )
        self.df_Hr_weights = all_frames['Hr_weights'].reset_index()  # used in postprocessing dual

        self.Idaytq = f.declare_param(self, 'Idaytq', self.day, all_frames['Idaytq'])
        self.df_Idaytq = all_frames['Idaytq'].reset_index()  # used in postprocessing duals

        # quick helper for annualizations....  # TODO:  Find this a better home and make a test for it

        # quick test....  the aggregate weight of all the rep hours must = 8760
        assert sum(self.annual_count(t) for t in self.hr) == 8760, 'Annualized hours do not add up!'

        # load and technology parameters
        self.Load = f.declare_param(self, 'Load', self.LoadSet, all_frames['Load'], mutable=True)
        self.SupplyPrice = f.declare_param(
            self, 'SupplyPrice', self.SupplyCurveSet, all_frames['SupplyPrice']
        )
        self.SupplyCurve = f.declare_param(
            self, 'SupplyCurve', self.SupplyCurveSet, all_frames['SupplyCurve']
        )
        self.SolWindCapFactor = f.declare_param(
            self, 'SolWindCapFactor', self.ptiUpperSet, all_frames['ptiUpperSet']
        )
        self.HydroCapFactor = f.declare_param(
            self, 'HydroCapFactor', self.HydroSet, all_frames['HydroCapFactor']
        )
        self.BatteryEfficiency = f.declare_param(
            self, 'BatteryEfficiency', setA.pts, all_frames['BatteryEfficiency']
        )
        self.HourstoBuy = f.declare_param(self, 'HourstoBuy', setA.pts, all_frames['HourstoBuy'])
        self.H2Price = f.declare_param(
            self, 'H2Price', self.H2PriceSet, all_frames['H2Price'], mutable=True
        )

        # misc single value parameters
        self.Storagelvl_cost = pyo.Param(initialize=0.00000001)
        self.Storagelvl_cost_col = ['Storagelvl_cost', 'None']
        self.cols_dict['Storagelvl_cost'] = self.Storagelvl_cost_col
        self.H2_HEATRATE: float = setA.H2_heatrate
        """Gwh/kg of H2"""

        # TODO: Does this need to exist as a param or is this just the seasons set
        self.SWtHydro = pyo.Param(self.s, default=0, mutable=True)
        self.SWtHydro_cols = ['SWtHydro', 's']
        self.cols_dict['SWtHydro'] = self.SWtHydro_cols

        self.UnmetLoad_penalty = pyo.Param(initialize=500000)  # 500 $/MWh -> 500,000 $/GWh
        self.UnmetLoad_penalty_col = ['UnmetLoad_penalty', 'None']
        self.cols_dict['UnmetLoad_penalty'] = self.UnmetLoad_penalty_col

        # if capacity expansion is on
        if self.sw_expansion:
            self.FOMCost = f.declare_param(self, 'FOMCost', self.FOMCostSet, all_frames['FOMCost'])
            self.CapacityCredit = f.declare_param(
                self, 'CapacityCredit', self.CapacityCreditSet, all_frames['CapacityCredit']
            )

            # if capacity expansion and learning are on
            if self.sw_learning > 0:
                self.LearningRate = f.declare_param(
                    self, 'LearningRate', self.LearningRateSet, all_frames['LearningRate']
                )
                self.CapCost_y0 = f.declare_param(
                    self, 'CapCost_y0', self.CapCost0Set, all_frames['CapCost_y0']
                )
                self.SupplyCurve_learning = f.declare_param(
                    self,
                    'SupplyCurve_learning',
                    self.LearningPtSet,
                    all_frames['SupplyCurve_learning'],
                )

            # if learning is not to be solved nonlinearly directly in the obj
            if self.sw_learning < 2:
                if self.sw_learning == 0:
                    mute = False
                else:
                    mute = True
                self.capacity_costs_learning = f.declare_param(
                    self,
                    'capacity_costs_learning',
                    self.CapCostSet,
                    all_frames['CapCost'],
                    mutable=mute,
                )

        # if trade operation is on
        if self.sw_trade:
            self.TranCost = f.declare_param(
                self, 'TranCost', self.TranCostSet, all_frames['TranCost']
            )
            self.TranLimit = f.declare_param(
                self, 'TranLimit', self.TranLimitSet, all_frames['TranLimit']
            )
            self.TranCostCan = f.declare_param(
                self, 'TranCostCan', self.TranCostCanSet, all_frames['TranCostCan']
            )
            self.TranLimitCan = f.declare_param(
                self, 'TranLimitCan', self.TranLimitCanSet, all_frames['TranLimitCan']
            )
            self.TranLineLimitCan = f.declare_param(
                self, 'TranLineLimitCan', self.TranLineLimitCanSet, all_frames['TranLineLimitCan']
            )

        # if reserve margin requirements are on
        if self.sw_rm:
            self.ReserveMargin = f.declare_param(
                self, 'ReserveMargin', self.r, all_frames['ReserveMargin']
            )

        # if ramping requirements are on
        if self.sw_ramp:
            self.RampUp_Cost = f.declare_param(
                self, 'RampUp_Cost', self.RampUp_CostSet, all_frames['RampUp_Cost']
            )
            self.RampDown_Cost = f.declare_param(
                self, 'RampDown_Cost', self.RampUp_CostSet, all_frames['RampDown_Cost']
            )
            self.RampRate = f.declare_param(
                self, 'RampRate', self.RampRateSet, all_frames['RampRate']
            )

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.RegReservesCost = f.declare_param(
                self, 'RegReservesCost', self.RegReservesCostSet, all_frames['RegReservesCost']
            )
            self.ResTechUpperBound = f.declare_param(
                self,
                'ResTechUpperBound',
                self.ResTechUpperBoundSet,
                all_frames['ResTechUpperBound'],
            )

        ##########################
        # Cross-talk from H2 model
        self.fixed_elec_request = pyo.Param(
            self.r,
            self.y,
            domain=pyo.NonNegativeReals,
            initialize=0,
            mutable=True,
            doc='a known fixed request from H2',
        )
        self.var_elec_request = pyo.Var(
            self.r,
            self.y,
            domain=pyo.NonNegativeReals,
            initialize=0,
            doc='variable request from H2',
        )

        ###########################################################################################
        # Variables

        # Generation, capacity, and technology variables
        self.Generation = f.declare_var(self, 'Generation', 'GenSet', self.GenSet)
        self.unmet_Load = f.declare_var(self, 'unmet_Load', 'UnmetSet', self.UnmetSet)
        self.TotalCapacity = f.declare_var(
            self, 'TotalCapacity', 'SupplyCurveSet', self.SupplyCurveSet
        )
        self.Storage_inflow = f.declare_var(self, 'Storage_inflow', 'StorageSet', self.StorageSet)
        self.Storage_outflow = f.declare_var(self, 'Storage_outflow', 'StorageSet', self.StorageSet)
        self.Storage_level = f.declare_var(self, 'Storage_level', 'StorageSet', self.StorageSet)

        # if capacity expansion is on
        if self.sw_expansion:
            self.CapacityBuilds = f.declare_var(
                self, 'CapacityBuilds', 'CapCostSet', self.CapCostSet
            )
            self.CapacityRetirements = f.declare_var(
                self, 'CapacityRetirements', 'RetSet', self.RetSet
            )

        # if trade operation is on
        if self.sw_trade:
            self.TradeToFrom = f.declare_var(self, 'TradeToFrom', 'TradeSet', self.TradeSet)
            self.TradeToFromCan = f.declare_var(
                self, 'TradeToFromCan', 'TradeCanSet', self.TradeCanSet
            )

        # if reserve margin constraints are on
        if self.sw_rm:
            self.AvailStorCap = f.declare_var(self, 'AvailStorCap', 'StorageSet', self.StorageSet)

        # if ramping requirements are on
        if self.sw_ramp:
            self.RampUp = f.declare_var(self, 'RampUp', 'RampSet', self.RampSet)
            self.RampDown = f.declare_var(self, 'RampDown', 'RampSet', self.RampSet)

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.ReservesProcurement = f.declare_var(
                self, 'ReservesProcurement', 'ProcurementSet', self.ProcurementSet
            )

        ###########################################################################################
        # Objective Function

        self.populate_by_hour_sets = pyo.BuildAction(rule=f.populate_by_hour_sets_rule)

        # TODO: make sure to correct all costs to multiply by year weights
        def dispatchCost(self):
            """Dispatch cost (e.g., variable O&M cost) component for the objective function.

            Returns
            -------
            int
                Dispatch cost
            """
            return sum(
                self.Idaytq[self.Map_hr_d[hr]]
                * (
                    sum(
                        self.year_weights[y]
                        * self.SupplyPrice[(reg, s, tech, step, y)]
                        * self.Generation[(tech, y, reg, step, hr)]
                        for (tech, y, reg, step) in self.GenSetByHour[hr]
                    )
                    + sum(
                        self.year_weights[y]
                        * (
                            0.5
                            * self.SupplyPrice[(reg, s, tech, step, y)]
                            * (
                                self.Storage_inflow[(tech, y, reg, step, hr)]
                                + self.Storage_outflow[(tech, y, reg, step, hr)]
                            )
                            + (self.Hr_weights[hr] * self.Storagelvl_cost)
                            * self.Storage_level[(tech, y, reg, step, hr)]
                        )
                        for (tech, y, reg, step) in self.StorageSetByHour[hr]
                    )
                    # dimensional analysis for cost:
                    # $/kg * kg/Gwh * Gwh = $
                    # so we need 1/heatrate for kg/Gwh
                    + sum(
                        self.year_weights[y]
                        * self.H2Price[reg, s, tech, step, y]
                        / self.H2_HEATRATE
                        * self.Generation[(tech, y, reg, 1, hr)]
                        for (tech, y, reg, step) in self.H2GenSetByHour[hr]
                    )
                )
                for hr in self.hr
                if (s := self.Map_hr_s[hr])
            )

        self.dispatchCost = pyo.Expression(expr=dispatchCost)

        def unmetLoadCost(self):
            """Unmet load cost component for the objective function. Should equal zero.

            Returns
            -------
            int
                Unmet load cost
            """
            return sum(
                self.Idaytq[self.Map_hr_d[hour]]
                * self.year_weights[y]
                * self.unmet_Load[(reg, y, hour)]
                * self.UnmetLoad_penalty
                for (reg, y, hour) in self.UnmetSet
            )

        self.unmetLoadCost = pyo.Expression(expr=unmetLoadCost)

        # if capacity expansion is on
        if self.sw_expansion:
            # TODO: choosing summer for capacity, may want to revisit this assumption
            def FOMCostObj(self):
                """Fixed operation and maintenance (FOM) cost component for the objective function.

                Returns
                -------
                int
                    FOM cost component
                """
                return sum(
                    self.year_weights[y]
                    * self.FOMCost[(reg, pt, steps)]
                    * self.TotalCapacity[(reg, s, pt, steps, y)]
                    for (reg, s, pt, steps, y) in self.SupplyCurveSet
                    if s == 2
                )  # TODO: need to fix this weighting

            self.FOMCostObj = pyo.Expression(expr=FOMCostObj)

            # nonlinear expansion costs
            if self.sw_learning == 2:
                # TODO: not sure if I need self.year_weights[y] weighting here, I don't think so?
                def capExpansionCost(self):
                    """Capacity expansion cost component for the objective function if
                    learning switch is set to non-linear option.

                    Returns
                    -------
                    int
                        Capacity expansion cost component (non-linear learning)
                    """
                    return sum(
                        (
                            self.CapCost_y0[(reg, pt, step)]
                            * (
                                (
                                    (
                                        self.SupplyCurve_learning[pt]
                                        + 0.0001 * (y - setA.start_year)
                                        + sum(
                                            sum(
                                                self.CapacityBuilds[(r, pt, year, steps)]
                                                for year in setA.y
                                                if year < y
                                            )
                                            for (r, tech, steps) in self.CapCost0Set
                                            if tech == pt
                                        )
                                    )
                                    / self.SupplyCurve_learning[pt]
                                )
                                ** (-1.0 * self.LearningRate[pt])
                            )
                        )
                        * self.CapacityBuilds[(reg, pt, y, step)]
                        for (reg, pt, y, step) in self.CapCostSet
                    )

                self.capExpansionCost = pyo.Expression(expr=capExpansionCost)

            # linear expansion costs
            else:
                # TODO: not sure if I need self.year_weights[y] weighting here, I don't think so?
                def capExpansionCost(self):
                    """Capacity expansion cost component for the objective function if
                    learning switch is set to linear option.

                    Returns
                    -------
                    int
                        Capacity expansion cost component (linear learning)
                    """
                    return sum(
                        self.capacity_costs_learning[(reg, pt, y, step)]
                        * self.CapacityBuilds[(reg, pt, y, step)]
                        for (reg, pt, y, step) in self.CapCostSet
                    )

                self.capExpansionCost = pyo.Expression(expr=capExpansionCost)

        # if trade operation is on
        if self.sw_trade:

            def tradeCost(self):
                """Interregional trade cost component for the objective function.

                Returns
                -------
                int
                    Interregional trade cost component
                """
                return sum(
                    self.Idaytq[self.Map_hr_d[hour]]
                    * self.year_weights[y]
                    * self.TradeToFrom[(reg, reg1, y, hour)]
                    * self.TranCost[(reg, reg1, y)]
                    for (reg, reg1, y, hour) in self.TradeSet
                ) + sum(
                    self.Idaytq[self.Map_hr_d[hour]]
                    * self.year_weights[y]
                    * self.TradeToFromCan[(reg, reg_can, y, CSteps, hour)]
                    * self.TranCostCan[(reg, reg_can, CSteps, y)]
                    for (reg, reg_can, y, CSteps, hour) in self.TradeCanSet
                )

            self.tradeCost = pyo.Expression(expr=tradeCost)

        # if ramping requirements are on
        if self.sw_ramp:

            def RampCost(self):
                """Ramping cost component for the objective function.

                Returns
                -------
                int
                    Ramping cost component
                """
                return sum(
                    self.Idaytq[self.Map_hr_d[hour]]
                    * self.year_weights[y]
                    * (
                        self.RampUp[(ptc, y, reg, step, hour)] * self.RampUp_Cost[ptc]
                        + self.RampDown[(ptc, y, reg, step, hour)] * self.RampDown_Cost[ptc]
                    )
                    for (ptc, y, reg, step, hour) in self.RampSet
                )

            self.RampCost = pyo.Expression(expr=RampCost)

        # if operating reserve requirements are on
        if self.sw_reserves:

            def opresCost(self):
                """Operating reserve cost component for the objective function.

                Returns
                -------
                int
                    Operating reserve cost component
                """
                return sum(
                    (self.RegReservesCost[pt] if restype == 2 else 0.01)
                    * self.Idaytq[self.Map_hr_d[hr]]
                    * self.year_weights[y]
                    * self.ReservesProcurement[(restype, pt, y, r, steps, hr)]
                    for (restype, pt, y, r, steps, hr) in self.ProcurementSet
                )

            self.opresCost = pyo.Expression(expr=opresCost)

        # Final Objective Function
        def objFunction(self):
            """Objective function, objective is to minimize costs to the electric power system.

            Returns
            -------
            int
                Objective function
            """
            return (
                self.dispatchCost
                + self.unmetLoadCost
                + (self.RampCost if self.sw_ramp else 0)
                + (self.tradeCost if self.sw_trade else 0)
                + (self.capExpansionCost + self.FOMCostObj if self.sw_expansion else 0)
                + (self.opresCost if self.sw_reserves else 0)
            )

        self.totalCost = pyo.Objective(rule=objFunction, sense=pyo.minimize)

        ###########################################################################################
        # Constraints

        self.populate_demand_balance_sets = pyo.BuildAction(
            rule=f.populate_demand_balance_sets_rule
        )

        # Property: ShadowPrice
        @self.Constraint(self.LoadSet)
        def Demand_balance(self, r, y, hr):
            """Deland balance constraint where Load <= Generation.

            Parameters
            ----------
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            hr : pyomo.core.base.set.OrderedScalarSet
                time segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Demand balance constraint
            """
            return self.Load[(r, y, hr)] <= sum(
                self.Generation[(tech, y, r, step, hr)]
                for (tech, step) in self.GenSetDemandBalance[(y, r, hr)]
            ) + sum(
                self.Storage_outflow[(tech, y, r, step, hr)]
                - self.Storage_inflow[(tech, y, r, step, hr)]
                for (tech, step) in self.StorageSetDemandBalance[(y, r, hr)]
            ) + self.unmet_Load[(r, y, hr)] + (
                sum(
                    self.TradeToFrom[(r, reg1, y, hr)] * (1 - setA.TransLoss)
                    - self.TradeToFrom[(reg1, r, y, hr)]
                    for (reg1) in self.TradeSetDemandBalance[(y, r, hr)]
                )
                if self.sw_trade and r in setA.trade_regs
                else 0
            ) + (
                sum(
                    self.TradeToFromCan[(r, r_can, y, CSteps, hr)] * (1 - setA.TransLoss)
                    for (r_can, CSteps) in self.TradeCanSetDemandBalance[(y, r, hr)]
                )
                if (self.sw_trade == 1 and r in setA.r_can_conn)
                else 0
            )

        def Annual_balance(self, r, y):
            """A quick & ugly summation to balance load on an annual basis if there are
            external, annual demands for electricity
            """
            annual_demand = (
                sum(self.Load[(r, y, hr)] * self.annual_count(hr) for hr in self.hr)
                + self.fixed_elec_request[r, y]
            )

            annual_production = (
                sum(
                    self.Generation[(tech, y, r, step, hr)] * self.annual_count(hr)
                    for hr in self.hr
                    for (tech, step) in self.GenSetDemandBalance[(y, r, hr)]
                )
                + sum(
                    self.Storage_outflow[(tech, y, r, step, hr)] * self.annual_count(hr)
                    - self.Storage_inflow[(tech, y, r, step, hr)] * self.annual_count(hr)
                    for hr in self.hr
                    for (tech, step) in self.StorageSetDemandBalance[(y, r, hr)]
                )
                + sum(self.unmet_Load[(r, y, hr)] * self.annual_count(hr) for hr in self.hr)
                + (
                    sum(
                        (
                            self.TradeToFrom[(r, reg1, y, hr)] * (1 - setA.TransLoss)
                            - self.TradeToFrom[(reg1, r, y, hr)]
                        )
                        * self.annual_count(hr)
                        for hr in self.hr
                        for (reg1) in self.TradeSetDemandBalance[(y, r, hr)]
                    )
                    if self.sw_trade and r in setA.trade_regs
                    else 0
                )
                + (
                    sum(
                        self.TradeToFromCan[(r, r_can, y, CSteps, hr)]
                        * (1 - setA.TransLoss)
                        * self.annual_count(hr)
                        for hr in self.hr
                        for (r_can, CSteps) in self.TradeCanSetDemandBalance[(y, r, hr)]
                    )
                    if (self.sw_trade == 1 and r in setA.r_can_conn)
                    else 0
                )
            )

            return annual_production >= annual_demand

        # self.Annual_balance = pyo.Constraint(self.r, self.y, rule=Annual_balance)

        # #First hour
        @self.Constraint(self.FirstHourStorageBalance_set)
        def FirstHourStorageBalance(self, pts, y, r, steps, hr1):
            """Storage balance constraint for the first hour time-segment in each day-type where
            Storage level == Storage level (in final hour time-segment in current day-type)
                            + Storage inflow * Battery efficiency
                            - Storage outflow

            Parameters
            ----------
            pts : pyomo.core.base.set.OrderedScalarSet
                storage technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr1 : pyomo.core.base.set.OrderedScalarSet
                set containing first hour time-segment in each day-type

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage balance constraint for the first hour time-segment in each day-type
            """
            return (
                self.Storage_level[(pts, y, r, steps, hr1)]
                == self.Storage_level[(pts, y, r, steps, hr1 + setA.num_hr_day - 1)]
                + self.BatteryEfficiency[pts] * self.Storage_inflow[(pts, y, r, steps, hr1)]
                - self.Storage_outflow[(pts, y, r, steps, hr1)]
            )

        # #Not first hour
        @self.Constraint(self.StorageBalance_set)
        def StorageBalance(self, pts, y, r, steps, hr23):
            """Storage balance constraint for the time-segment in each day-type other than
            the first hour time-segment where
            Storage level == Storage level (in previous hour time-segment)
                            + Storage inflow * Battery efficiency
                            - Storage outflow

            Parameters
            ----------
            pts : pyomo.core.base.set.OrderedScalarSet
                storage technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr23 : pyomo.core.base.set.OrderedScalarSet
                set containing time-segment except first hour in each day-type

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage balance constraint for the time-segment in each day-type other than
            the first hour time-segment
            """
            return (
                self.Storage_level[(pts, y, r, steps, hr23)]
                == self.Storage_level[(pts, y, r, steps, hr23 - 1)]
                + self.BatteryEfficiency[pts] * self.Storage_inflow[(pts, y, r, steps, hr23)]
                - self.Storage_outflow[(pts, y, r, steps, hr23)]
            )

        # TODO: replace all_frames['Map_hr_s'] with m.Map_hr_s and move function to util
        def populate_hydro_sets_rule(m):
            for s, hr in all_frames['Map_hr_s'].reset_index().set_index(['s', 'hr']).index:
                m.HourSHydro[s].add(hr)
                m.SWtHydro[s] = m.SWtHydro[s] + m.Hr_weights[hr] * m.Idaytq[m.Map_hr_d[hr]]
            for s, day in all_frames['Map_day_s'].reset_index().set_index(['s', 'day']).index:
                m.DaySHydro[s].add(day)

        self.populate_hydro_sets = pyo.BuildAction(rule=populate_hydro_sets_rule)

        @self.Constraint(self.HydroMonthsSet)
        def Hydro_Gen_Cap(self, pth, y, r, s):
            """hydroelectric generation seasonal upper bound where
            Hydo generation <= Hydo capacity * Hydro capacity factor

            Parameters
            ----------
            pth : pyomo.core.base.set.OrderedScalarSet
                hydro technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            s : pyomo.core.base.set.OrderedScalarSet
                season set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                hydroelectric generation seasonal upper bound
            """
            return (
                sum(
                    self.Generation[pth, y, r, 1, hr] * self.Idaytq[self.Map_hr_d[hr]]
                    for hr in self.HourSHydro[s]
                )
                <= self.TotalCapacity[(r, s, pth, 1, y)]
                * self.HydroCapFactor[r, s]
                * self.SWtHydro[s]
            )

        @self.Constraint(self.ptd_upper_set)
        def ptd_upper(self, ptd, y, r, steps, hr):
            """Dispatchable generation upper bound where
            Dispatchable generation + reserve procurement <= capacity * capacity factor

            Parameters
            ----------
            ptd : pyomo.core.base.set.OrderedScalarSet
                dispatchable technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Dispatchable generation upper bound
            """
            return (
                self.Generation[(ptd, y, r, steps, hr)]
                + (
                    sum(
                        self.ReservesProcurement[(restype, ptd, y, r, steps, hr)]
                        for restype in setA.restypes
                    )
                    if self.sw_reserves
                    else 0
                )
                <= self.TotalCapacity[(r, self.Map_hr_s[hr], ptd, steps, y)] * self.Hr_weights[hr]
            )

        @self.Constraint(self.pth_upper_set)
        def pth_upper(self, pth, y, r, steps, hr):
            """Hydroelectric generation upper bound where
            Hydroelectric generation + reserve procurement <= capacity * capacity factor

            Parameters
            ----------
            pth : pyomo.core.base.set.OrderedScalarSet
                hydro technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Hydroelectric generation upper bound
            """
            return (
                self.Generation[(pth, y, r, steps, hr)]
                + sum(
                    self.ReservesProcurement[(restype, pth, y, r, steps, hr)]
                    for restype in setA.restypes
                )
                if self.sw_reserves
                else 0
            ) <= self.TotalCapacity[(r, self.Map_hr_s[hr], pth, steps, y)] * self.HydroCapFactor[
                (r, self.Map_hr_s[hr])
            ] * self.Hr_weights[hr]

        @self.Constraint(self.ptiUpperSet)
        def pti_upper(self, pti, y, r, steps, hr):
            """Intermittent generation upper bound where
            Intermittent generation + reserve procurement <= capacity * capacity factor

            Parameters
            ----------
            pti : pyomo.core.base.set.OrderedScalarSet
                intermittent technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                intermittent generation upper bound
            """
            return (
                self.Generation[(pti, y, r, steps, hr)]
                + (
                    sum(
                        self.ReservesProcurement[(restype, pti, y, r, steps, hr)]
                        for restype in setA.restypes
                    )
                    if self.sw_reserves
                    else 0
                )
                <= self.TotalCapacity[(r, self.Map_hr_s[hr], pti, steps, y)]
                * self.SolWindCapFactor[(pti, y, r, steps, hr)]
                * self.Hr_weights[hr]
            )

        @self.Constraint(self.StorageSet)
        def Storage_inflow_upper(self, pt, y, r, steps, hr):
            """Storage inflow upper bound where
            Storage inflow <= Storage Capacity

            Parameters
            ----------
            pt : pyomo.core.base.set.OrderedScalarSet
                technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage inflow upper bound
            """
            return (
                self.Storage_inflow[(pt, y, r, steps, hr)]
                <= self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)] * self.Hr_weights[hr]
            )

        # TODO check if it's only able to build in regions with existing capacity?
        @self.Constraint(self.StorageSet)
        def Storage_outflow_upper(self, pt, y, r, steps, hr):
            """Storage outflow upper bound where
            Storage outflow <= Storage Capacity

            Parameters
            ----------
            pt : pyomo.core.base.set.OrderedScalarSet
                technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage outflow upper bound
            """
            return (
                self.Storage_outflow[(pt, y, r, steps, hr)]
                + (
                    sum(
                        self.ReservesProcurement[(restype, pt, y, r, steps, hr)]
                        for restype in setA.restypes
                    )
                    if self.sw_reserves
                    else 0
                )
                <= self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)] * self.Hr_weights[hr]
            )

        @self.Constraint(self.StorageSet)
        def Storage_level_upper(self, pt, y, r, steps, hr):
            """Storage level upper bound where
            Storage level <= Storage power capacity * storage energy capacity

            Parameters
            ----------
            pt : pyomo.core.base.set.OrderedScalarSet
                technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage level upper bound
            """
            return (
                self.Storage_level[(pt, y, r, steps, hr)]
                <= self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)] * self.HourstoBuy[(pt)]
            )

        @self.Constraint(self.SupplyCurveSet)
        def totalCapacityEq(self, r, s, pt, steps, y):
            """Capacity Equality constraint where
            Capacity = Operating Capacity
                      + New Builds Capacity
                      - Retired Capacity

            Parameters
            ----------
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            s : pyomo.core.base.set.OrderedScalarSet
                season set
            pt : pyomo.core.base.set.OrderedScalarSet
                technology set
            steps : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            y : pyomo.core.base.set.OrderedScalarSet
                year set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Capacity Equality

            """
            return self.TotalCapacity[(r, s, pt, steps, y)] == self.SupplyCurve[
                (r, s, pt, steps, y)
            ] + (
                sum(self.CapacityBuilds[(r, pt, year, steps)] for year in setA.y if year <= y)
                if self.sw_expansion and (pt, steps) in self.BuildSet
                else 0
            ) - (
                sum(self.CapacityRetirements[(pt, year, r, steps)] for year in setA.y if year <= y)
                if self.sw_expansion and (pt, y, r, steps) in self.RetSet
                else 0
            )

        # if capacity expansion is on
        if self.sw_expansion:

            @self.Constraint(self.RetSet)
            def Ret_upper(self, pt, y, r, steps):
                """Retirement upper bound where
                Capacity Retired <= Operating Capacity
                                   + New Builds Capacity
                                   - Retired Capacity

                Parameters
                ----------
                pt : pyomo.core.base.set.OrderedScalarSet
                    technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Retirement upper bound
                """
                return self.CapacityRetirements[(pt, y, r, steps)] <= (
                    (
                        self.SupplyCurve[(r, 2, pt, steps, y)]
                        if (r, 2, pt, steps, y) in self.SupplyCurveSet
                        else 0
                    )
                    + (
                        sum(
                            self.CapacityBuilds[(r, pt, year, steps)] for year in setA.y if year < y
                        )
                        if (pt, steps) in self.BuildSet
                        else 0
                    )
                    - sum(
                        self.CapacityRetirements[(pt, year, r, steps)]
                        for year in setA.y
                        if year < y
                    )
                )

        # if trade operation is on
        if self.sw_trade and all_frames['TranLineLimitCan'].size != 0:
            self.populate_trade_sets = pyo.BuildAction(rule=f.populate_trade_sets_rule)

            @self.Constraint(self.TranLineLimitCanSet)
            def tradelinecan_upper(self, r, r_can, y, hr):
                """International interregional trade upper bound where
                Interregional Trade <= Interregional Transmission Capabilities * Time

                Parameters
                ----------
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                r_can : pyomo.core.base.set.OrderedScalarSet
                    international region set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    International interregional trade capacity upper bound
                """
                return (
                    sum(
                        self.TradeToFromCan[(r, r_can, y, c, hr)]
                        for c in self.TradeCanLineSetUpper[(r, r_can, y, hr)]
                    )
                    <= self.TranLineLimitCan[(r, r_can, y, hr)] * self.Hr_weights[hr]
                )

            @self.Constraint(self.TranLimitCanSet)
            def tradecan_upper(self, r_can, CSteps, y, hr):
                """International electricity supply upper bound where
                Interregional Trade <= Interregional Supply

                Parameters
                ----------
                r_can : pyomo.core.base.set.OrderedScalarSet
                    international region set
                CSteps : pyomo.core.base.set.OrderedScalarSet
                    international trade supply curve steps set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    International electricity supply upper bound
                """
                return (
                    sum(
                        self.TradeToFromCan[(r, r_can, y, CSteps, hr)]
                        for r in self.TradeCanSetUpper[(r_can, y, CSteps, hr)]
                    )
                    <= self.TranLimitCan[(r_can, CSteps, y, hr)] * self.Hr_weights[hr]
                )

            @self.Constraint(self.TradeSet)
            def Trade_upper(self, r, r1, y, hr):
                """Interregional trade upper bound where
                Interregional Trade <= Interregional Transmission Capabilities * Time

                Parameters
                ----------
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                r1 : pyomo.core.base.set.OrderedScalarSet
                    region set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Interregional trade capacity upper bound
                """
                return (
                    self.TradeToFrom[(r, r1, y, hr)]
                    <= self.TranLimit[(r, r1, self.Map_hr_s[hr], y)] * self.Hr_weights[hr]
                )

        # if reserve margin requirements are on
        if self.sw_expansion and self.sw_rm:
            self.populate_RM_sets = pyo.BuildAction(rule=f.populate_RM_sets_rule)

            @self.Constraint(self.LoadSet)
            def ReserveMarginLower(self, r, y, hr):
                """Reserve margin requirement where
                Load * Reserve Margin <= Capacity * Capacity Credit * Time

                # must meet reserve margin requirement
                # apply to every hour, a fraction above the final year's load
                # ReserveMarginReq <= sum(Max capacity in that hour)

                Parameters
                ----------
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Reserve margin requirement
                """
                return self.Load[(r, y, hr)] * (1 + self.ReserveMargin[r]) <= self.Hr_weights[
                    hr
                ] * sum(
                    (
                        self.CapacityCredit[(pt, y, r, steps, hr)]
                        * (
                            self.AvailStorCap[(pt, y, r, steps, hr)]
                            if pt in setA.pts
                            else self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)]
                        )
                    )
                    for (pt, steps) in self.SupplyCurveRM[(y, r, self.Map_hr_s[hr])]
                )

            @self.Constraint(self.StorageSet)
            def AvailCapStor1_Upper(self, pts, y, r, steps, hr):
                """Available storage power capacity for meeting reserve margin

                # ensure available capacity to meet RM for storage < power capacity

                Parameters
                ----------
                pts : pyomo.core.base.set.OrderedScalarSet
                    storage technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time-segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Available storage power capacity for meeting reserve margin
                """
                return (
                    self.AvailStorCap[(pts, y, r, steps, hr)]
                    <= self.TotalCapacity[(r, self.Map_hr_s[hr], pts, steps, y)]
                )

            @self.Constraint(self.StorageSet)
            def AvailCapStor2_Upper(self, pts, y, r, steps, hr):
                """Available storage energy capacity for meeting reserve margin

                # ensure available capacity to meet RM for storage < existing SOC

                Parameters
                ----------
                pts : pyomo.core.base.set.OrderedScalarSet
                    storage technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time-segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Available storage energy capacity for meeting reserve margin
                """
                return (
                    self.AvailStorCap[(pts, y, r, steps, hr)]
                    <= self.Storage_level[(pts, y, r, steps, hr)]
                )

        # if ramping requirements are on
        if self.sw_ramp:

            @self.Constraint(self.FirstHour_gen_ramp_set)
            def FirstHour_gen_ramp(self, ptc, y, r, steps, hr1):
                """Ramp constraint for the first hour time-segment in each day-type where
                Generation == Generation (in final hour time-segment in current day-type)
                            + Ramp Up
                            - Ramp Down

                Parameters
                ----------
                ptc : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr1 : pyomo.core.base.set.OrderedScalarSet
                    set containing first hour time-segment in each day-type

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp constraint for the first hour
                """
                return (
                    self.Generation[(ptc, y, r, steps, hr1)]
                    == self.Generation[(ptc, y, r, steps, hr1 + setA.num_hr_day - 1)]
                    + self.RampUp[(ptc, y, r, steps, hr1)]
                    - self.RampDown[(ptc, y, r, steps, hr1)]
                )

            @self.Constraint(self.Gen_ramp_set)
            def Gen_ramp(self, ptc, y, r, steps, hr23):
                """Ramp constraint for the time-segment in each day-type other than
                the first hour time-segment where
                Generation == Generation (in previous hour time-segment)
                            + Ramp Up
                            - Ramp Down

                Parameters
                ----------
                ptc : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr23 : pyomo.core.base.set.OrderedScalarSet
                    set containing time-segment except first hour in each day-type

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp constraint for the first hour
                """
                return (
                    self.Generation[(ptc, y, r, steps, hr23)]
                    == self.Generation[(ptc, y, r, steps, hr23 - 1)]
                    + self.RampUp[(ptc, y, r, steps, hr23)]
                    - self.RampDown[(ptc, y, r, steps, hr23)]
                )

            @self.Constraint(self.RampSet)
            def RampUp_upper(self, ptc, y, r, steps, hr):
                """Ramp rate up upper constraint where
                Ramp Up <= Capaciry * Ramp Rate * Time

                Parameters
                ----------
                ptc : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp rate up upper constraint
                """
                return (
                    self.RampUp[(ptc, y, r, steps, hr)]
                    <= self.Hr_weights[hr]
                    * self.RampRate[ptc]
                    * self.TotalCapacity[(r, self.Map_hr_s[hr], ptc, steps, y)]
                )

            @self.Constraint(self.RampSet)
            def RampDown_upper(self, ptc, y, r, steps, hr):
                """Ramp rate down upper constraint where
                Ramp Up <= Capaciry * Ramp Rate * Time

                Parameters
                ----------
                ptc : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp rate down upper constraint
                """
                return (
                    self.RampDown[(ptc, y, r, steps, hr)]
                    <= self.Hr_weights[hr]
                    * self.RampRate[ptc]
                    * self.TotalCapacity[(r, self.Map_hr_s[hr], ptc, steps, y)]
                )

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.WindSetReserves = {}
            self.SolarSetReserves = {}

            # TODO: declare all pt subsets as sets, change setA to m below,
            # and move this funct over to utils
            def populate_reserves_sets_rule(m):
                m.ProcurementSetReserves = f.populate_sets_rule(
                    m, 'ProcurementSet', set_base2=['restypes', 'r', 'y', 'hr']
                )
                #
                for pt, year, reg, step, hour in m.ptiUpperSet:
                    if (year, reg, hour) not in m.WindSetReserves:
                        m.WindSetReserves[(year, reg, hour)] = []
                    if (year, reg, hour) not in m.SolarSetReserves:
                        m.SolarSetReserves[(year, reg, hour)] = []

                    if pt in setA.ptw:
                        m.WindSetReserves[(year, reg, hour)].append((pt, step))
                    elif pt in setA.ptsol:
                        m.SolarSetReserves[(year, reg, hour)].append((pt, step))

            self.populate_reserves_sets = pyo.BuildAction(rule=populate_reserves_sets_rule)

            @self.Constraint(self.LoadSet)
            def spinReservesRequirement(self, r, y, hr):
                """Spinning reserve requirements (3% of load) where
                Spinning reserve procurement >= 0.03 * Load

                Parameters
                ----------
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time-segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Spinning reserve requirements
                """
                return (
                    sum(
                        self.ReservesProcurement[(1, pt, y, r, step, hr)]
                        for (pt, step) in self.ProcurementSetReserves[(1, r, y, hr)]
                    )
                    >= 0.03 * self.Load[(r, y, hr)]
                )

            @self.Constraint(self.LoadSet)
            def regReservesRequirement(self, r, y, hr):
                """Regulation Reserve Requirement (1% of load + 0.5% of wind gen + 0.3% of solar cap) where
                Reserves Requirement >= 0.01 * Load
                                      + 0.005 * Wind Gen
                                      + 0.003 * Solar Cap

                Parameters
                ----------
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time-segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Regulation reserve requirement
                """
                return sum(
                    self.ReservesProcurement[(2, pt, y, r, step, hr)]
                    for (pt, step) in self.ProcurementSetReserves[(2, r, y, hr)]
                ) >= 0.01 * self.Load[(r, y, hr)] + 0.005 * sum(
                    self.Generation[(ptw, y, r, step, hr)]
                    for (ptw, step) in self.WindSetReserves[(y, r, hr)]
                ) + 0.003 * self.Hr_weights[hr] * sum(
                    self.TotalCapacity[(r, self.Map_hr_s[hr], ptsol, step, y)]
                    for (ptsol, step) in self.SolarSetReserves[(y, r, hr)]
                )

            @self.Constraint(self.LoadSet)
            def flexReservesRequirement(self, r, y, hr):
                """Flexible Reserve Requirement (10% of wind gen + 4% of solar cap) where
                Reserves Requirement >= 0.01 * Wind Gen
                                      + 0.04 * Solar Cap

                Parameters
                ----------
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time-segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Flexible reserve requirement
                """
                return sum(
                    self.ReservesProcurement[(3, pt, y, r, step, hr)]
                    for (pt, step) in self.ProcurementSetReserves[(3, r, y, hr)]
                ) >= +0.1 * sum(
                    self.Generation[(ptw, y, r, step, hr)]
                    for (ptw, step) in self.WindSetReserves[(y, r, hr)]
                ) + 0.04 * self.Hr_weights[hr] * sum(
                    self.TotalCapacity[(r, self.Map_hr_s[hr], ptsol, step, y)]
                    for (ptsol, step) in self.SolarSetReserves[(y, r, hr)]
                )

            @self.Constraint(self.ProcurementSet)
            def resProcurementUpper(self, restypes, pt, y, r, steps, hr):
                """Reserve Requirement Procurement Upper Bound where
                Reserve Procurement <= Capacity
                                    * Tech Reserve Contribution Share
                                    * Time

                Parameters
                ----------
                restypes : pyomo.core.base.set.OrderedScalarSet
                    reserve requirement type set
                pt : pyomo.core.base.set.OrderedScalarSet
                    technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                steps : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Reserve Requirement Procurement Upper Bound
                """
                return (
                    self.ReservesProcurement[(restypes, pt, y, r, steps, hr)]
                    <= self.ResTechUpperBound[(restypes, pt)]
                    * self.Hr_weights[hr]
                    * self.TotalCapacity[(r, self.Map_hr_s[hr], pt, steps, y)]
                )

    ###############################################################################################
    # Additional Functionality
    # TODO: Move these functions to the utilities script

    def annual_count(self, hour) -> int:
        """return the aggregate weight of this hour in the representative year
        we know the hour weight, and the hours are unique to days, so we can
        get the day weight

        Parameters
        ----------
        hour : _type_
            the rep_hour

        Returns
        -------
        int
            the aggregate weight (count) of this hour in the rep_year.  NOT the hour weight!
        """
        day_weight = self.Idaytq[self.Map_hr_d[hour]]
        hour_weight = self.Hr_weights[hour]
        return day_weight * hour_weight

    def update_h2_prices(self, h2_prices: dict[HI, float]) -> None:
        """Update the H2 prices held in the model

        Parameters
        ----------
        h2_prices : list[tuple[HI, float]]
            new prices
        """

        # TODO:  Fix this hard-coding below!
        h2_techs = {5}  # temp hard-coding of the tech who's price we're going to set

        update_count = 0
        no_update = set()
        good_updates = set()
        for region, season, pt, step, yr in self.H2Price:  # type: ignore
            if pt in h2_techs:
                if (region, yr) in h2_prices:
                    self.H2Price[region, season, pt, step, yr] = h2_prices[
                        HI(region=region, year=yr)
                    ]
                    update_count += 1
                    good_updates.add((region, yr))
                else:
                    no_update.add((region, yr))
        logger.debug('Updated %d H2 prices: %s', update_count, good_updates)

        # check for any missing data

        if no_update:
            logger.warning('No new price info for region-year combos: %s', no_update)

    def update_elec_demand(self, elec_demand: dict[HI, float]) -> None:
        """
        Update the external electical demand parameter with demands from the H2 model

        Parameters
        ----------
        elec_demand : dict[HI, float]
            the new demands broken out by hyd index (region, year)
        """
        # this is kind of a 1-liner right now, but may evolve into something more elaborate when
        # time scale is tweaked

        self.fixed_elec_request.store_values(elec_demand)
        logger.debug('Stored new fixed electrical request in elec model: %s', elec_demand)

    def poll_h2_demand(self) -> dict[HI, float]:
        """
        Get the hydrogen demand by rep_year and region

        Use the Generation variable for h2 techs

        NOTE:  Not sure about day weighting calculation here!!

        Returns
        -------
        dict[HI, float]
            dictionary of prices by H2 Index: price
        """
        h2_consuming_techs = {5}  # TODO:  get rid of this hard-coding

        # gather results
        res: dict[HI, float] = defaultdict(float)
        tot_by_rep_year = defaultdict(float)
        # iterate over the Generation variable and screen out the H2 "demanders"
        # dimensional analysis for H2 demand:
        #
        # Gwh * kg/Gwh = kg
        # so we need 1/heat_rate for kg/Gwh
        for idx in self.Generation.index_set():
            tech, y, reg, step, hr = idx
            if tech in h2_consuming_techs:
                h2_demand_weighted = (
                    pyo.value(self.Generation[idx])
                    * self.Idaytq[self.Map_hr_d[hr]]
                    / self.H2_HEATRATE
                )
                res[HI(region=reg, year=y)] += h2_demand_weighted
                tot_by_rep_year[y] += h2_demand_weighted

        logger.debug('Calculated cumulative H2 demand by year as: %s', tot_by_rep_year)
        return res
