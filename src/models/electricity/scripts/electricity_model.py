"""Electricity Model, a pyomo optimization model of the electric power sector.

The class is organized by sections: settings, sets, parameters, variables, objective function,
constraints, plus additional misc support functions.
"""
###################################################################################################
# Setup

# Import packages
from collections import defaultdict
from logging import getLogger
import pyomo.environ as pyo

# Import python modules
from src.integrator.utilities import HI
from src.common.model import Model

# move to new file
from src.models.electricity.scripts.utilities import ElectricityMethods as em

# Establish logger
logger = getLogger(__name__)

###################################################################################################
# MODEL


class PowerModel(Model):
    """A PowerModel instance. Builds electricity pyomo model.

    Parameters
    ----------
    all_frames : dictionary of pd.DataFrames
        Contains all dataframes of inputs
    setA : Sets
        Contains all other non-dataframe inputs
    """

    def __init__(self, all_frames, setA, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)

        ###########################################################################################
        # Settings

        self.OUTPUT_ROOT = setA.OUTPUT_ROOT
        self.sw_trade = setA.sw_trade
        self.sw_expansion = setA.sw_expansion
        self.sw_agg_years = setA.sw_agg_years
        self.sw_rm = setA.sw_rm
        self.sw_ramp = setA.sw_ramp
        self.sw_reserves = setA.sw_reserves
        self.sw_h2int = 0

        # 0=no learning, 1=linear iterations, 2=nonlinear learning
        self.sw_learning = setA.sw_learning

        ###########################################################################################
        # TODO: Example future model concept
        # Note: the goal would be to eventually reorganize the preprocessor so that most data would
        # fit something similar to this example structure below.

        def declare_set_and_param(name):
            """declare set and parameter based on data frame name

            Parameters
            ----------
            name : str
                name of data frame to create into set and parameter
            """
            index_name = name + '_index'
            self.declare_set(index_name, all_frames[name])
            self.declare_param(name, getattr(self, index_name), all_frames[name])

        # self.declare_set_and_param('FOMCost')
        # self.declare_set_and_param('HydroCapFactor')

        ###########################################################################################
        # Sets

        # temporal sets
        self.declare_set('hour', setA.hour)
        self.declare_set('day', setA.day)
        self.declare_set('season', setA.season)
        self.declare_set('year', setA.years)

        # spatial sets
        self.declare_set('region', setA.region)
        self.declare_set('region_int', setA.region_int)
        self.declare_set('region_trade', setA.region_trade)
        self.declare_set('region_int_trade', setA.region_int_trade)

        # Load sets
        self.declare_set('demand_balance_index', all_frames['Load'])
        self.declare_set_with_sets('unmet_load_index', self.region, self.year, self.hour)

        # Supply price and quantity sets and subsets
        self.declare_set('capacity_total_index', all_frames['SupplyCurve'])
        self.declare_set('generation_total_index', setA.generation_total_index)
        self.declare_set('generation_dispatchable_ub_index', setA.generation_dispatchable_ub_index)
        self.declare_set('Storage_index', setA.Storage_index)
        self.declare_set('H2Gen_index', setA.H2Gen_index)
        self.declare_set('generation_hydro_ub_index', setA.generation_hydro_ub_index)
        self.declare_set('ramp_most_hours_balance_index', setA.ramp_most_hours_balance_index)
        self.declare_set('ramp_first_hour_balance_index', setA.ramp_first_hour_balance_index)
        self.declare_set('storage_most_hours_balance_index', setA.storage_most_hours_balance_index)
        self.declare_set('storage_first_hour_balance_index', setA.storage_first_hour_balance_index)
        self.declare_set('capacity_hydro_ub_index', setA.capacity_hydro_ub_index)

        # Other technology sets
        self.declare_set('HydroCapFactor_index', all_frames['HydroCapFactor'])
        self.declare_set('generation_vre_ub_index', all_frames['CapFactorVRE'])
        self.declare_set('H2Price_index', all_frames['H2Price'])

        for tss in setA.tech_subset_names:
            # create the technology subsets based on the tech_subsets input
            self.declare_set(tss, getattr(setA, tss))

        # if capacity expansion is on
        if self.sw_expansion:
            self.declare_set('capacity_builds_index', all_frames['CapCost'])
            self.declare_set('FOMCost_index', all_frames['FOMCost'])
            self.declare_set('Build_index', setA.Build_index)
            self.declare_set('CapacityCredit_index', all_frames['CapacityCredit'])
            self.declare_set('capacity_retirements_index', setA.capacity_retirements_index)

        # if capacity expansion and learning are on
        # this block of code demonstrates the application of the switch option,
        # but in general we found it easier to read if we continued to use if statements
        if self.sw_learning > 0:
            self.declare_set(
                'LearningRate_index', all_frames['LearningRate'], switch=self.sw_expansion
            )
            self.declare_set(
                'CapCostInitial_index', all_frames['CapCostInitial'], switch=self.sw_expansion
            )
            self.declare_set(
                'SupplyCurveLearning_index',
                all_frames['SupplyCurveLearning'],
                switch=self.sw_expansion,
            )

        # if trade operation is on
        if self.sw_trade:
            self.declare_set('TranCost_index', all_frames['TranCost'])
            self.declare_set('TranLimit_index', all_frames['TranLimit'])
            self.declare_set('trade_interregional_index', setA.trade_interregional_index)
            self.declare_set('TranCostInt_index', all_frames['TranCostInt'])
            self.declare_set('TranLimitInt_index', all_frames['TranLimitGenInt'])
            self.declare_set('trade_interational_index', setA.trade_interational_index)
            self.declare_set('TranLineLimitInt_index', all_frames['TranLimitCapInt'])

        # if ramping requirements are on
        if self.sw_ramp:
            self.declare_set('RampUpCost_index', all_frames['RampUpCost'])
            self.declare_set('RampRate_index', all_frames['RampRate'])
            self.declare_set('generation_ramp_index', setA.generation_ramp_index)

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.declare_set('restypes', setA.restypes)
            self.declare_set('reserves_procurement_index', setA.reserves_procurement_index)
            self.declare_set('RegReservesCost_index', all_frames['RegReservesCost'])
            self.declare_set('ResTechUpperBound_index', all_frames['ResTechUpperBound'])

        ###########################################################################################
        # Parameters

        # temporal parameters
        self.declare_param('y0', None, setA.start_year)
        self.declare_param('num_hr_day', None, setA.num_hr_day)
        self.declare_param('MapHourSeason', self.hour, all_frames['MapHourSeason'])
        self.declare_param('MapHourDay', self.hour, all_frames['MapHourDay']['day'])
        self.declare_param('WeightYear', self.year, all_frames['WeightYear'])
        self.declare_param('WeightHour', self.hour, all_frames['WeightHour']['WeightHour'])
        self.declare_param('WeightDay', self.day, all_frames['WeightDay'])
        self.declare_param('WeightSeason', self.season, all_frames['WeightSeason'])

        # load and technology parameters
        self.declare_param('Load', self.demand_balance_index, all_frames['Load'], mutable=True)
        self.declare_param('UnmetLoadPenalty', None, 500000)
        self.declare_param('SupplyPrice', self.capacity_total_index, all_frames['SupplyPrice'])
        self.declare_param('SupplyCurve', self.capacity_total_index, all_frames['SupplyCurve'])
        self.declare_param('CapFactorVRE', self.generation_vre_ub_index, all_frames['CapFactorVRE'])
        self.declare_param(
            'HydroCapFactor', self.HydroCapFactor_index, all_frames['HydroCapFactor']
        )
        self.declare_param('BatteryEfficiency', setA.T_stor, all_frames['BatteryEfficiency'])
        self.declare_param('HourstoBuy', setA.T_stor, all_frames['HourstoBuy'])
        self.declare_param('H2Price', self.H2Price_index, all_frames['H2Price'], mutable=True)
        self.declare_param('StorageLevelCost', None, 0.00000001)
        self.declare_param('H2Heatrate', None, setA.H2Heatrate)

        # if capacity expansion is on
        if self.sw_expansion:
            self.declare_param('FOMCost', self.FOMCost_index, all_frames['FOMCost'])
            self.declare_param(
                'CapacityCredit', self.CapacityCredit_index, all_frames['CapacityCredit']
            )

            # if capacity expansion and learning are on
            if self.sw_learning > 0:
                self.declare_param(
                    'LearningRate', self.LearningRate_index, all_frames['LearningRate']
                )
                self.declare_param(
                    'CapCostInitial', self.CapCostInitial_index, all_frames['CapCostInitial']
                )
                self.declare_param(
                    'SupplyCurveLearning',
                    self.SupplyCurveLearning_index,
                    all_frames['SupplyCurveLearning'],
                )

            # if learning is not to be solved nonlinearly directly in the obj
            if self.sw_learning < 2:
                if self.sw_learning == 0:
                    mute = False
                else:
                    mute = True
                self.declare_param(
                    'CapCostLearning',
                    self.capacity_builds_index,
                    all_frames['CapCost'],
                    mutable=mute,
                )

        # if trade operation is on
        if self.sw_trade:
            self.declare_param('TransLoss', None, setA.TransLoss)
            self.declare_param('TranCost', self.TranCost_index, all_frames['TranCost'])
            self.declare_param('TranLimit', self.TranLimit_index, all_frames['TranLimit'])
            self.declare_param('TranCostInt', self.TranCostInt_index, all_frames['TranCostInt'])
            self.declare_param(
                'TranLimitGenInt', self.TranLimitInt_index, all_frames['TranLimitGenInt']
            )
            self.declare_param(
                'TranLimitCapInt', self.TranLineLimitInt_index, all_frames['TranLimitCapInt']
            )

        # if reserve margin requirements are on
        if self.sw_rm:
            self.declare_param('ReserveMargin', self.region, all_frames['ReserveMargin'])

        # if ramping requirements are on
        if self.sw_ramp:
            self.declare_param('RampUpCost', self.RampUpCost_index, all_frames['RampUpCost'])
            self.declare_param('RampDownCost', self.RampUpCost_index, all_frames['RampDownCost'])
            self.declare_param('RampRate', self.RampRate_index, all_frames['RampRate'])

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.declare_param(
                'RegReservesCost', self.RegReservesCost_index, all_frames['RegReservesCost']
            )
            self.declare_param(
                'ResTechUpperBound', self.ResTechUpperBound_index, all_frames['ResTechUpperBound']
            )

        ##########################
        # Cross-talk from H2 model
        # TODO: fit these into the declare param format for consistency
        self.FixedElecRequest = pyo.Param(
            self.region,
            self.year,
            domain=pyo.NonNegativeReals,
            initialize=0,
            mutable=True,
            doc='a known fixed request from H2',
        )
        self.var_elec_request = pyo.Var(
            self.region,
            self.year,
            domain=pyo.NonNegativeReals,
            initialize=0,
            doc='variable request from H2',
        )

        ###########################################################################################
        # TODO: Example future model concept
        # Note: the goal would be to eventually reorganize the preprocessor so that most data would
        # fit something similar to this example structure below.

        self.var_switch_dict = {
            'capacity_builds': self.sw_expansion,
            'capacity_retirements': self.sw_expansion,
        }

        for var in self.var_switch_dict.keys():
            # self.declare_var(var, getattr(self, var + '_index'), switch=self.var_switch_dict[var])
            pass

        ###########################################################################################
        # Variables

        # Generation, capacity, and technology variables
        self.declare_var('generation_total', self.generation_total_index)
        self.declare_var('unmet_load', self.unmet_load_index)
        self.declare_var('capacity_total', self.capacity_total_index)
        self.declare_var('storage_inflow', self.Storage_index)
        self.declare_var('storage_outflow', self.Storage_index)
        self.declare_var('storage_level', self.Storage_index)

        # if capacity expansion is on
        if self.sw_expansion:
            self.declare_var('capacity_builds', self.capacity_builds_index)
            self.declare_var('capacity_retirements', self.capacity_retirements_index)

        # if trade operation is on
        if self.sw_trade:
            self.declare_var('trade_interregional', self.trade_interregional_index)
            self.declare_var('trade_international', self.trade_interational_index)

        # if reserve margin constraints are on
        if self.sw_rm:
            self.declare_var('storage_avail_cap', self.Storage_index)

        # if ramping requirements are on
        if self.sw_ramp:
            self.declare_var('generation_ramp_up', self.generation_ramp_index)
            self.declare_var('generation_ramp_down', self.generation_ramp_index)

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.declare_var('reserves_procurement', self.reserves_procurement_index)

        ###########################################################################################
        # Objective Function

        self.populate_by_hour_sets = pyo.BuildAction(rule=em.populate_by_hour_sets_rule)

        def dispatch_cost(self):
            """Dispatch cost (e.g., variable O&M cost) component for the objective function.

            Returns
            -------
            int
                Dispatch cost
            """
            return sum(
                self.WeightDay[self.MapHourDay[hr]]
                * (
                    sum(
                        self.WeightYear[y]
                        * self.SupplyPrice[(r, season, tech, step, y)]
                        * self.generation_total[(tech, y, r, step, hr)]
                        for (tech, y, r, step) in self.GenHour_index[hr]
                    )
                    + sum(
                        self.WeightYear[y]
                        * (
                            0.5
                            * self.SupplyPrice[(r, season, tech, step, y)]
                            * (
                                self.storage_inflow[(tech, y, r, step, hr)]
                                + self.storage_outflow[(tech, y, r, step, hr)]
                            )
                            + (self.WeightHour[hr] * self.StorageLevelCost)
                            * self.storage_level[(tech, y, r, step, hr)]
                        )
                        for (tech, y, r, step) in self.StorageHour_index[hr]
                    )
                    # dimensional analysis for cost:
                    # $/kg * kg/Gwh * Gwh = $
                    # so we need 1/heatrate for kg/Gwh
                    + sum(
                        self.WeightYear[y]
                        * self.H2Price[r, season, tech, step, y]
                        / self.H2Heatrate
                        * self.generation_total[(tech, y, r, 1, hr)]
                        for (tech, y, r, step) in self.H2GenHour_index[hr]
                    )
                )
                for hr in self.hour
                if (season := self.MapHourSeason[hr])
            )

        self.dispatch_cost = pyo.Expression(expr=dispatch_cost)

        def unmet_load_cost(self):
            """Unmet load cost component for the objective function. Should equal zero.

            Returns
            -------
            int
                Unmet load cost
            """
            return sum(
                self.WeightDay[self.MapHourDay[hr]]
                * self.WeightYear[y]
                * self.unmet_load[(r, y, hr)]
                * self.UnmetLoadPenalty
                for (r, y, hr) in self.unmet_load_index
            )

        self.unmet_load_cost = pyo.Expression(expr=unmet_load_cost)

        # if capacity expansion is on
        if self.sw_expansion:
            # TODO: choosing summer for capacity, may want to revisit this, fix hard coded value
            def fixed_om_cost(self):
                """Fixed operation and maintenance (FOM) cost component for the objective function.

                Returns
                -------
                int
                    FOM cost component
                """
                return sum(
                    self.WeightYear[y]
                    * self.FOMCost[(r, tech, step)]
                    * self.capacity_total[(r, season, tech, step, y)]
                    for (r, season, tech, step, y) in self.capacity_total_index
                    if season == 2
                )

            self.fixed_om_cost = pyo.Expression(expr=fixed_om_cost)

            # nonlinear expansion costs
            if self.sw_learning == 2:

                def capacity_expansion_cost(self):
                    """Capacity expansion cost component for the objective function if
                    learning switch is set to nonlinear option.

                    Returns
                    -------
                    int
                        Capacity expansion cost component (nonlinear learning)
                    """
                    return sum(
                        (
                            self.CapCostInitial[(r, tech, step)]
                            * (
                                (
                                    (
                                        self.SupplyCurveLearning[tech]
                                        + 0.0001 * (y - self.y0)
                                        + sum(
                                            sum(
                                                self.capacity_builds[(r, tech, year, step)]
                                                for year in self.year
                                                if year < y
                                            )
                                            for (r, t, step) in self.CapCostInitial_index
                                            if t == tech
                                        )
                                    )
                                    / self.SupplyCurveLearning[tech]
                                )
                                ** (-1.0 * self.LearningRate[tech])
                            )
                        )
                        * self.capacity_builds[(r, tech, y, step)]
                        for (r, tech, y, step) in self.capacity_builds_index
                    )

                self.capacity_expansion_cost = pyo.Expression(expr=capacity_expansion_cost)

            # linear expansion costs
            else:

                def capacity_expansion_cost(self):
                    """Capacity expansion cost component for the objective function if
                    learning switch is set to linear option.

                    Returns
                    -------
                    int
                        Capacity expansion cost component (linear learning)
                    """
                    return sum(
                        self.CapCostLearning[(r, tech, y, step)]
                        * self.capacity_builds[(r, tech, y, step)]
                        for (r, tech, y, step) in self.capacity_builds_index
                    )

                self.capacity_expansion_cost = pyo.Expression(expr=capacity_expansion_cost)

        # if trade operation is on
        if self.sw_trade:

            def trade_cost(self):
                """Interregional and international trade cost component for the objective function.

                Returns
                -------
                int
                    Interregional trade cost component
                """
                return sum(
                    self.WeightDay[self.MapHourDay[hr]]
                    * self.WeightYear[y]
                    * self.trade_interregional[(r, r1, y, hr)]
                    * self.TranCost[(r, r1, y)]
                    for (r, r1, y, hr) in self.trade_interregional_index
                ) + sum(
                    self.WeightDay[self.MapHourDay[hr]]
                    * self.WeightYear[y]
                    * self.trade_international[(r, R_int, y, step, hr)]
                    * self.TranCostInt[(r, R_int, step, y)]
                    for (r, R_int, y, step, hr) in self.trade_interational_index
                )

            self.trade_cost = pyo.Expression(expr=trade_cost)

        # if ramping requirements are on
        if self.sw_ramp:

            def ramp_cost(self):
                """Ramping cost component for the objective function.

                Returns
                -------
                int
                    Ramping cost component
                """
                return sum(
                    self.WeightDay[self.MapHourDay[hr]]
                    * self.WeightYear[y]
                    * (
                        self.generation_ramp_up[(T_conv, y, r, step, hr)] * self.RampUpCost[T_conv]
                        + self.generation_ramp_down[(T_conv, y, r, step, hr)]
                        * self.RampDownCost[T_conv]
                    )
                    for (T_conv, y, r, step, hr) in self.generation_ramp_index
                )

            self.ramp_cost = pyo.Expression(expr=ramp_cost)

        # if operating reserve requirements are on
        if self.sw_reserves:

            def operating_reserves_cost(self):
                """Operating reserve cost component for the objective function.

                Returns
                -------
                int
                    Operating reserve cost component
                """
                return sum(
                    (self.RegReservesCost[tech] if restype == 'regulation' else 0.01)
                    * self.WeightDay[self.MapHourDay[hr]]
                    * self.WeightYear[y]
                    * self.reserves_procurement[(restype, tech, y, r, step, hr)]
                    for (restype, tech, y, r, step, hr) in self.reserves_procurement_index
                )

            self.operating_reserves_cost = pyo.Expression(expr=operating_reserves_cost)

        # Final Objective Function
        def electricity_objective_function(self):
            """Objective function, objective is to minimize costs to the electric power system.

            Returns
            -------
            int
                Objective function
            """
            return (
                self.dispatch_cost
                + self.unmet_load_cost
                + (self.ramp_cost if self.sw_ramp else 0)
                + (self.trade_cost if self.sw_trade else 0)
                + (self.capacity_expansion_cost + self.fixed_om_cost if self.sw_expansion else 0)
                + (self.operating_reserves_cost if self.sw_reserves else 0)
            )

        self.total_cost = pyo.Objective(rule=electricity_objective_function, sense=pyo.minimize)

        ###########################################################################################
        # Constraints

        self.populate_demand_balance_sets = pyo.BuildAction(
            rule=em.populate_demand_balance_sets_rule
        )

        # Property: ShadowPrice
        @self.Constraint(self.demand_balance_index)
        def demand_balance(self, r, y, hr):
            """Demand balance constraint where Load <= Generation.

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
                self.generation_total[(tech, y, r, step, hr)]
                for (tech, step) in self.GenSetDemandBalance[(y, r, hr)]
            ) + sum(
                self.storage_outflow[(tech, y, r, step, hr)]
                - self.storage_inflow[(tech, y, r, step, hr)]
                for (tech, step) in self.StorageSetDemandBalance[(y, r, hr)]
            ) + self.unmet_load[(r, y, hr)] + (
                sum(
                    self.trade_interregional[(r, r1, y, hr)] * (1 - self.TransLoss)
                    - self.trade_interregional[(r1, r, y, hr)]
                    for (r1) in self.TradeSetDemandBalance[(y, r, hr)]
                )
                if self.sw_trade and r in self.region_trade
                else 0
            ) + (
                sum(
                    self.trade_international[(r, R_int, y, step, hr)] * (1 - self.TransLoss)
                    for (R_int, step) in self.TradeCanSetDemandBalance[(y, r, hr)]
                )
                if (self.sw_trade == 1 and r in self.region_int_trade)
                else 0
            )

        # #First hour
        @self.Constraint(self.storage_first_hour_balance_index)
        def storage_first_hour_balance(self, T_stor, y, r, step, hr1):
            """Storage balance constraint for the first hour time-segment in each day-type where
            Storage level == Storage level (in final hour time-segment in current day-type)
                            + Storage inflow * Battery efficiency
                            - Storage outflow

            Parameters
            ----------
            T_stor : pyomo.core.base.set.OrderedScalarSet
                storage technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr1 : pyomo.core.base.set.OrderedScalarSet
                set containing first hour time-segment in each day-type

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage balance constraint for the first hour time-segment in each day-type
            """
            return (
                self.storage_level[(T_stor, y, r, step, hr1)]
                == self.storage_level[(T_stor, y, r, step, hr1 + self.num_hr_day - 1)]
                + self.BatteryEfficiency[T_stor] * self.storage_inflow[(T_stor, y, r, step, hr1)]
                - self.storage_outflow[(T_stor, y, r, step, hr1)]
            )

        # #Not first hour
        @self.Constraint(self.storage_most_hours_balance_index)
        def storage_most_hours_balance(self, T_stor, y, r, step, hr23):
            """Storage balance constraint for the time-segment in each day-type other than
            the first hour time-segment where
            Storage level == Storage level (in previous hour time-segment)
                            + Storage inflow * Battery efficiency
                            - Storage outflow

            Parameters
            ----------
            T_stor : pyomo.core.base.set.OrderedScalarSet
                storage technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
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
                self.storage_level[(T_stor, y, r, step, hr23)]
                == self.storage_level[(T_stor, y, r, step, hr23 - 1)]
                + self.BatteryEfficiency[T_stor] * self.storage_inflow[(T_stor, y, r, step, hr23)]
                - self.storage_outflow[(T_stor, y, r, step, hr23)]
            )

        self.populate_hydro_sets = pyo.BuildAction(rule=em.populate_hydro_sets_rule)

        @self.Constraint(self.capacity_hydro_ub_index)
        def capacity_hydro_ub(self, T_hydro, y, r, season):
            """hydroelectric generation seasonal upper bound where
            Hydo generation <= Hydo capacity * Hydro capacity factor

            Parameters
            ----------
            T_hydro : pyomo.core.base.set.OrderedScalarSet
                hydro technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            season : pyomo.core.base.set.OrderedScalarSet
                season set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                hydroelectric generation seasonal upper bound
            """
            return (
                sum(
                    self.generation_total[T_hydro, y, r, 1, hr]
                    * self.WeightDay[self.MapHourDay[hr]]
                    for hr in self.HourSeason_index[season]
                )
                <= self.capacity_total[(r, season, T_hydro, 1, y)]
                * self.HydroCapFactor[r, season]
                * self.WeightSeason[season]
            )

        @self.Constraint(self.generation_dispatchable_ub_index)
        def generation_dispatchable_ub(self, T_disp, y, r, step, hr):
            """Dispatchable generation upper bound where
            Dispatchable generation + reserve procurement <= capacity * capacity factor

            Parameters
            ----------
            T_disp : pyomo.core.base.set.OrderedScalarSet
                dispatchable technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Dispatchable generation upper bound
            """
            return (
                self.generation_total[(T_disp, y, r, step, hr)]
                + (
                    sum(
                        self.reserves_procurement[(restype, T_disp, y, r, step, hr)]
                        for restype in self.restypes
                    )
                    if self.sw_reserves
                    else 0
                )
                <= self.capacity_total[(r, self.MapHourSeason[hr], T_disp, step, y)]
                * self.WeightHour[hr]
            )

        @self.Constraint(self.generation_hydro_ub_index)
        def generation_hydro_ub(self, T_hydro, y, r, step, hr):
            """Hydroelectric generation upper bound where
            Hydroelectric generation + reserve procurement <= capacity * capacity factor

            Parameters
            ----------
            T_hydro : pyomo.core.base.set.OrderedScalarSet
                hydro technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Hydroelectric generation upper bound
            """
            return (
                self.generation_total[(T_hydro, y, r, step, hr)]
                + sum(
                    self.reserves_procurement[(restype, T_hydro, y, r, step, hr)]
                    for restype in self.restypes
                )
                if self.sw_reserves
                else 0
            ) <= self.capacity_total[
                (r, self.MapHourSeason[hr], T_hydro, step, y)
            ] * self.HydroCapFactor[(r, self.MapHourSeason[hr])] * self.WeightHour[hr]

        @self.Constraint(self.generation_vre_ub_index)
        def generation_vre_ub(self, T_vre, y, r, step, hr):
            """Intermittent generation upper bound where
            Intermittent generation + reserve procurement <= capacity * capacity factor

            Parameters
            ----------
            T_vre : pyomo.core.base.set.OrderedScalarSet
                intermittent technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                intermittent generation upper bound
            """
            return (
                self.generation_total[(T_vre, y, r, step, hr)]
                + (
                    sum(
                        self.reserves_procurement[(restype, T_vre, y, r, step, hr)]
                        for restype in self.restypes
                    )
                    if self.sw_reserves
                    else 0
                )
                <= self.capacity_total[(r, self.MapHourSeason[hr], T_vre, step, y)]
                * self.CapFactorVRE[(T_vre, y, r, step, hr)]
                * self.WeightHour[hr]
            )

        @self.Constraint(self.Storage_index)
        def storage_inflow_ub(self, tech, y, r, step, hr):
            """Storage inflow upper bound where
            Storage inflow <= Storage Capacity

            Parameters
            ----------
            tech : pyomo.core.base.set.OrderedScalarSet
                technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage inflow upper bound
            """
            return (
                self.storage_inflow[(tech, y, r, step, hr)]
                <= self.capacity_total[(r, self.MapHourSeason[hr], tech, step, y)]
                * self.WeightHour[hr]
            )

        # TODO check if it's only able to build in regions with existing capacity?
        @self.Constraint(self.Storage_index)
        def storage_outflow_ub(self, tech, y, r, step, hr):
            """Storage outflow upper bound where
            Storage outflow <= Storage Capacity

            Parameters
            ----------
            tech : pyomo.core.base.set.OrderedScalarSet
                technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage outflow upper bound
            """
            return (
                self.storage_outflow[(tech, y, r, step, hr)]
                + (
                    sum(
                        self.reserves_procurement[(restype, tech, y, r, step, hr)]
                        for restype in self.restypes
                    )
                    if self.sw_reserves
                    else 0
                )
                <= self.capacity_total[(r, self.MapHourSeason[hr], tech, step, y)]
                * self.WeightHour[hr]
            )

        @self.Constraint(self.Storage_index)
        def storage_level_ub(self, tech, y, r, step, hr):
            """Storage level upper bound where
            Storage level <= Storage power capacity * storage energy capacity

            Parameters
            ----------
            tech : pyomo.core.base.set.OrderedScalarSet
                technology set
            y : pyomo.core.base.set.OrderedScalarSet
                year set
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            hr : pyomo.core.base.set.OrderedScalarSet
                time-segment set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Storage level upper bound
            """
            return (
                self.storage_level[(tech, y, r, step, hr)]
                <= self.capacity_total[(r, self.MapHourSeason[hr], tech, step, y)]
                * self.HourstoBuy[(tech)]
            )

        @self.Constraint(self.capacity_total_index)
        def capacity_balance(self, r, season, tech, step, y):
            """Capacity Equality constraint where
            Capacity = Operating Capacity
                      + New Builds Capacity
                      - Retired Capacity

            Parameters
            ----------
            r : pyomo.core.base.set.OrderedScalarSet
                region set
            season : pyomo.core.base.set.OrderedScalarSet
                season set
            tech : pyomo.core.base.set.OrderedScalarSet
                technology set
            step : pyomo.core.base.set.OrderedScalarSet
                supply curve price/quantity step set
            y : pyomo.core.base.set.OrderedScalarSet
                year set

            Returns
            -------
            pyomo.core.base.constraint.IndexedConstraint
                Capacity Equality

            """
            return self.capacity_total[(r, season, tech, step, y)] == self.SupplyCurve[
                (r, season, tech, step, y)
            ] + (
                sum(self.capacity_builds[(r, tech, year, step)] for year in self.year if year <= y)
                if self.sw_expansion and (tech, step) in self.Build_index
                else 0
            ) - (
                sum(
                    self.capacity_retirements[(tech, year, r, step)]
                    for year in self.year
                    if year <= y
                )
                if self.sw_expansion and (tech, y, r, step) in self.capacity_retirements_index
                else 0
            )

        # if capacity expansion is on
        if self.sw_expansion:

            @self.Constraint(self.capacity_retirements_index)
            def capacity_retirements_ub(self, tech, y, r, step):
                """Retirement upper bound where
                Capacity Retired <= Operating Capacity
                                   + New Builds Capacity
                                   - Retired Capacity

                Parameters
                ----------
                tech : pyomo.core.base.set.OrderedScalarSet
                    technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Retirement upper bound
                """
                return self.capacity_retirements[(tech, y, r, step)] <= (
                    (
                        self.SupplyCurve[(r, 2, tech, step, y)]
                        if (r, 2, tech, step, y) in self.capacity_total_index
                        else 0
                    )
                    + (
                        sum(
                            self.capacity_builds[(r, tech, year, step)]
                            for year in self.year
                            if year < y
                        )
                        if (tech, step) in self.Build_index
                        else 0
                    )
                    - sum(
                        self.capacity_retirements[(tech, year, r, step)]
                        for year in self.year
                        if year < y
                    )
                )

        # if trade operation is on
        if self.sw_trade and len(self.TranLineLimitInt_index) != 0:
            self.populate_trade_sets = pyo.BuildAction(rule=em.populate_trade_sets_rule)

            @self.Constraint(self.TranLineLimitInt_index)
            def trade_interational_capacity_ub(self, r, R_int, y, hr):
                """International interregional trade upper bound where
                Interregional Trade <= Interregional Transmission Capabilities * Time

                Parameters
                ----------
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                R_int : pyomo.core.base.set.OrderedScalarSet
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
                        self.trade_international[(r, R_int, y, c, hr)]
                        for c in self.TradeCanLineSetUpper[(r, R_int, y, hr)]
                    )
                    <= self.TranLimitCapInt[(r, R_int, y, hr)] * self.WeightHour[hr]
                )

            @self.Constraint(self.TranLimitInt_index)
            def trade_interational_generation_ub(self, R_int, step, y, hr):
                """International electricity supply upper bound where
                Interregional Trade <= Interregional Supply

                Parameters
                ----------
                R_int : pyomo.core.base.set.OrderedScalarSet
                    international region set
                step : pyomo.core.base.set.OrderedScalarSet
                    international trade supply curve step set
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
                        self.trade_international[(r, R_int, y, step, hr)]
                        for r in self.TradeCanSetUpper[(R_int, y, step, hr)]
                    )
                    <= self.TranLimitGenInt[(R_int, step, y, hr)] * self.WeightHour[hr]
                )

            @self.Constraint(self.trade_interregional_index)
            def trade_domestic_ub(self, r, r1, y, hr):
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
                    self.trade_interregional[(r, r1, y, hr)]
                    <= self.TranLimit[(r, r1, self.MapHourSeason[hr], y)] * self.WeightHour[hr]
                )

        # if reserve margin requirements are on
        if self.sw_expansion and self.sw_rm:
            self.populate_RM_sets = pyo.BuildAction(rule=em.populate_RM_sets_rule)

            @self.Constraint(self.demand_balance_index)
            def reserve_margin_lb(self, r, y, hr):
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
                return self.Load[(r, y, hr)] * (1 + self.ReserveMargin[r]) <= self.WeightHour[
                    hr
                ] * sum(
                    (
                        self.CapacityCredit[(tech, y, r, step, hr)]
                        * (
                            self.storage_avail_cap[(tech, y, r, step, hr)]
                            if tech in self.T_stor
                            else self.capacity_total[(r, self.MapHourSeason[hr], tech, step, y)]
                        )
                    )
                    for (tech, step) in self.SupplyCurveRM[(y, r, self.MapHourSeason[hr])]
                )

            @self.Constraint(self.Storage_index)
            def reserve_margin_storage_avail_cap_ub(self, T_stor, y, r, step, hr):
                """Available storage power capacity for meeting reserve margin

                # ensure available capacity to meet RM for storage < power capacity

                Parameters
                ----------
                T_stor : pyomo.core.base.set.OrderedScalarSet
                    storage technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time-segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Available storage power capacity for meeting reserve margin
                """
                return (
                    self.storage_avail_cap[(T_stor, y, r, step, hr)]
                    <= self.capacity_total[(r, self.MapHourSeason[hr], T_stor, step, y)]
                )

            @self.Constraint(self.Storage_index)
            def reserve_margin_storage_avail_level_ub(self, T_stor, y, r, step, hr):
                """Available storage energy capacity for meeting reserve margin

                # ensure available capacity to meet RM for storage < existing SOC

                Parameters
                ----------
                T_stor : pyomo.core.base.set.OrderedScalarSet
                    storage technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time-segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Available storage energy capacity for meeting reserve margin
                """
                return (
                    self.storage_avail_cap[(T_stor, y, r, step, hr)]
                    <= self.storage_level[(T_stor, y, r, step, hr)]
                )

        # if ramping requirements are on
        if self.sw_ramp:

            @self.Constraint(self.ramp_first_hour_balance_index)
            def ramp_first_hour_balance(self, T_conv, y, r, step, hr1):
                """Ramp constraint for the first hour time-segment in each day-type where
                Generation == Generation (in final hour time-segment in current day-type)
                            + Ramp Up
                            - Ramp Down

                Parameters
                ----------
                T_conv : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr1 : pyomo.core.base.set.OrderedScalarSet
                    set containing first hour time-segment in each day-type

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp constraint for the first hour
                """
                return (
                    self.generation_total[(T_conv, y, r, step, hr1)]
                    == self.generation_total[(T_conv, y, r, step, hr1 + self.num_hr_day - 1)]
                    + self.generation_ramp_up[(T_conv, y, r, step, hr1)]
                    - self.generation_ramp_down[(T_conv, y, r, step, hr1)]
                )

            @self.Constraint(self.ramp_most_hours_balance_index)
            def ramp_most_hours_balance(self, T_conv, y, r, step, hr23):
                """Ramp constraint for the time-segment in each day-type other than
                the first hour time-segment where
                Generation == Generation (in previous hour time-segment)
                            + Ramp Up
                            - Ramp Down

                Parameters
                ----------
                T_conv : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr23 : pyomo.core.base.set.OrderedScalarSet
                    set containing time-segment except first hour in each day-type

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp constraint for the first hour
                """
                return (
                    self.generation_total[(T_conv, y, r, step, hr23)]
                    == self.generation_total[(T_conv, y, r, step, hr23 - 1)]
                    + self.generation_ramp_up[(T_conv, y, r, step, hr23)]
                    - self.generation_ramp_down[(T_conv, y, r, step, hr23)]
                )

            @self.Constraint(self.generation_ramp_index)
            def ramp_up_ub(self, T_conv, y, r, step, hr):
                """Ramp rate up upper constraint where
                Ramp Up <= Capaciry * Ramp Rate * Time

                Parameters
                ----------
                T_conv : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp rate up upper constraint
                """
                return (
                    self.generation_ramp_up[(T_conv, y, r, step, hr)]
                    <= self.WeightHour[hr]
                    * self.RampRate[T_conv]
                    * self.capacity_total[(r, self.MapHourSeason[hr], T_conv, step, y)]
                )

            @self.Constraint(self.generation_ramp_index)
            def ramp_down_ub(self, T_conv, y, r, step, hr):
                """Ramp rate down upper constraint where
                Ramp Up <= Capaciry * Ramp Rate * Time

                Parameters
                ----------
                T_conv : pyomo.core.base.set.OrderedScalarSet
                    conventional technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Ramp rate down upper constraint
                """
                return (
                    self.generation_ramp_down[(T_conv, y, r, step, hr)]
                    <= self.WeightHour[hr]
                    * self.RampRate[T_conv]
                    * self.capacity_total[(r, self.MapHourSeason[hr], T_conv, step, y)]
                )

        # if operating reserve requirements are on
        if self.sw_reserves:
            self.populate_reserves_sets = pyo.BuildAction(rule=em.populate_reserves_sets_rule)

            @self.Constraint(self.demand_balance_index)
            def reserve_requirement_spin_lb(self, r, y, hr):
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
                        self.reserves_procurement[('spinning', tech, y, r, step, hr)]
                        for (tech, step) in self.ProcurementSetReserves[('spinning', r, y, hr)]
                    )
                    >= 0.03 * self.Load[(r, y, hr)]
                )

            @self.Constraint(self.demand_balance_index)
            def reserve_requirement_reg_lb(self, r, y, hr):
                """Regulation Reserve Req (1% of load + 0.5% of wind gen + 0.3% of solar cap) where
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
                    self.reserves_procurement[('regulation', tech, y, r, step, hr)]
                    for (tech, step) in self.ProcurementSetReserves[('regulation', r, y, hr)]
                ) >= 0.01 * self.Load[(r, y, hr)] + 0.005 * sum(
                    self.generation_total[(T_wind, y, r, step, hr)]
                    for (T_wind, step) in self.WindSetReserves[(y, r, hr)]
                ) + 0.003 * self.WeightHour[hr] * sum(
                    self.capacity_total[(r, self.MapHourSeason[hr], T_solar, step, y)]
                    for (T_solar, step) in self.SolarSetReserves[(y, r, hr)]
                )

            @self.Constraint(self.demand_balance_index)
            def reserve_requirement_flex_lb(self, r, y, hr):
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
                    self.reserves_procurement[('flex', tech, y, r, step, hr)]
                    for (tech, step) in self.ProcurementSetReserves[('flex', r, y, hr)]
                ) >= +0.1 * sum(
                    self.generation_total[(T_wind, y, r, step, hr)]
                    for (T_wind, step) in self.WindSetReserves[(y, r, hr)]
                ) + 0.04 * self.WeightHour[hr] * sum(
                    self.capacity_total[(r, self.MapHourSeason[hr], T_solar, step, y)]
                    for (T_solar, step) in self.SolarSetReserves[(y, r, hr)]
                )

            @self.Constraint(self.reserves_procurement_index)
            def reserve_procurement_ub(self, restypes, tech, y, r, step, hr):
                """Reserve Requirement Procurement Upper Bound where
                Reserve Procurement <= Capacity
                                    * Tech Reserve Contribution Share
                                    * Time

                Parameters
                ----------
                restypes : pyomo.core.base.set.OrderedScalarSet
                    reserve requirement type set
                tech : pyomo.core.base.set.OrderedScalarSet
                    technology set
                y : pyomo.core.base.set.OrderedScalarSet
                    year set
                r : pyomo.core.base.set.OrderedScalarSet
                    region set
                step : pyomo.core.base.set.OrderedScalarSet
                    supply curve price/quantity step set
                hr : pyomo.core.base.set.OrderedScalarSet
                    time segment set

                Returns
                -------
                pyomo.core.base.constraint.IndexedConstraint
                    Reserve Requirement Procurement Upper Bound
                """
                return (
                    self.reserves_procurement[(restypes, tech, y, r, step, hr)]
                    <= self.ResTechUpperBound[(restypes, tech)]
                    * self.WeightHour[hr]
                    * self.capacity_total[(r, self.MapHourSeason[hr], tech, step, y)]
                )
