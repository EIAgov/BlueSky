"""This file is a collection of functions that are used to build, run, and solve the electricity model."""

###################################################################################################
# Setup

# Import pacakges
import os as os
from pathlib import Path
import sys as sys
from datetime import datetime
import numpy as np
import pandas as pd
import gc
import pyomo.environ as pyo
from pyomo.common.timing import TicTocTimer
from pyomo.opt import SolutionStatus, SolverStatus, TerminationCondition
from pyomo.util.infeasible import (
    log_infeasible_constraints,
)
from logging import getLogger

# Import scripts
from definitions import PROJECT_ROOT
import src.models.electricity.scripts.preprocessor as prep
import src.models.electricity.scripts.postprocessor as post
import src.models.electricity.scripts.common.common as com
from src.models.electricity.scripts.electricity_model import PowerModel

# Establish logger
logger = getLogger(__name__)

# Establish paths
data_root = Path(PROJECT_ROOT, 'src/models/electricity/input')


###################################################################################################
# RUN MODEL


def build_elec_model(all_frames, setin) -> PowerModel:
    """building pyomo electricity model

    Parameters
    ----------
    all_frames : dict of pd.DataFrame
        input data frames
    setin : Set
        input settings Set

    Returns
    -------
    PowerModel
        built (but unsolved) electricity model
    """
    # disabling garbage collection to improve runtime
    gc.disable()

    # Building model
    logger.info('Build Pyomo')
    instance = PowerModel(all_frames, setin)

    # add electricity price dual
    instance.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    # instance.pprint()

    # number of variables
    nvar = pyo.value(instance.nvariables())
    logger.info('Number of variables =' + str(nvar))
    # number of constraints
    ncon = pyo.value(instance.nconstraints())
    logger.info('Number of constraints =' + str(ncon))

    return instance


def select_solver(instance):
    """Select solver based on learning method

    Parameters
    ----------
    instance : PowerModel
        electricity pyomo model

    Returns
    -------
    solver type (?)
        The pyomo solver
    """

    if instance.sw_learning == 2:  # nonlinear solver
        solver_name = 'ipopt'
        opt = pyo.SolverFactory(solver_name, tee=True)  # , tee=True
        # Select options. The prefix "OF_" tells pyomo to create an options file
        opt.options['OF_mu_strategy'] = 'adaptive'
        opt.options['OF_num_linear_variables'] = 100000
        opt.options['OF_mehrotra_algorithm'] = 'yes'
        # Ask IPOPT to print options so you can confirm that they were used by the solver
        opt.options['print_user_options'] = 'yes'
    else:  # linear solver
        solver_name = 'appsi_highs'
        opt = pyo.SolverFactory(solver_name)
    logger.info('Using Solver: ' + solver_name)

    return opt


def solve_elec_model(instance):
    """solve electicity model

    Parameters
    ----------
    instance : PowerModel
        built (but not solved) electricity pyomo model
    """

    # select solver
    opt = select_solver(instance)

    logger.info('Solving Pyomo')

    if instance.sw_learning == 1:  # run iterative learning
        # Set any high tolerance
        tol = 999
        iter_num = 0

        # initialize capacity to set pricing
        init_old_cap(instance)
        instance.new_cap = instance.old_cap
        update_cost(instance)

        while tol > 0.1 and iter_num < 20:
            logger.info('Linear iteration number: ' + str(iter_num))

            iter_num += 1
            # solve model
            opt_success = opt.solve(instance)

            # set new capacities
            set_new_cap(instance)

            # Update tolerance
            tol = sum(
                [
                    abs(instance.old_cap_wt[(pt, y)] - instance.new_cap_wt[(pt, y)])
                    for (pt, y) in instance.cap_set
                ]
            )

            # update learning costs in model
            update_cost(instance)

            # update old capacities
            instance.old_cap = instance.new_cap
            instance.old_cap_wt = instance.new_cap_wt

            logger.info('Tolerance: ' + str(tol))
    else:
        opt_success = opt.solve(instance)

    ### Check results and load model solutions
    # Check results for termination condition and solution status
    if com.check_results(opt_success, TerminationCondition, SolutionStatus):
        name = 'noclass!'
        logger.info(f'[{name}] Solve failed')
        if opt_success is not None:
            logger.info('status=' + str(opt_success.solver.status))
            logger.info('TerminationCondition=' + str(opt_success.solver.termination_condition))

    # If model solved, load model solutions into model, else exit
    try:
        if (opt_success.solver.status == SolverStatus.ok) and (
            opt_success.solver.termination_condition == TerminationCondition.optimal
        ):
            instance.solutions.load_from(opt_success)
        else:
            logger.warning('Solve Failed.')
            exit()
    except:
        logger.warning('Solve Failed.')
        exit()


def run_model(settings, solve=True) -> PowerModel:
    """build electricity model (and solve if solve=True) after passing in settings

    Parameters
    ----------
    settings : Config_settings
        Configuration settings
    solve : bool, optional
        solve electricity model?, by default True

    Returns
    -------
    PowerModel
        electricity model
    """
    ###############################################################################################
    # Setup Logging

    # Delete old log
    log_name = 'elec_debug.log'

    if os.path.exists(log_name):
        os.remove(log_name)

    # Measuring the run time of code
    start_time = datetime.now()
    timer = TicTocTimer(logger=logger)
    timer.tic('start')

    ###############################################################################################
    # Pre-processing

    logger.info('Preprocessing')

    all_frames, setin = prep.preprocessor(prep.Sets(settings))

    logger.debug(
        f'Proceeding to build model for years: {settings.years} and regions: {settings.regions}'
    )
    timer.toc('preprocessor finished')

    ###############################################################################################
    # Build model

    instance = build_elec_model(all_frames, setin)
    timer.toc('build model finished')

    # stop here if no solve requested...
    if not solve:
        return instance

    ###############################################################################################
    # Solve model
    solve_elec_model(instance)

    timer.toc('solve model finished')
    logger.info('Solve complete')

    # save electricity prices for H2 connection
    # component_objects_to_df(instance.)

    # Check
    # Objective Value
    obj_val = pyo.value(instance.totalCost)
    # print('Objective Function Value =',obj_val)

    logger.info('Displaying solution...')
    logger.info(f'instance.totalCost(): {instance.totalCost()}')

    logger.info('Logging infeasible constraints...')
    logger.info(log_infeasible_constraints(instance))

    logger.info('dispatchCost Value =' + str(pyo.value(instance.dispatchCost)))
    logger.info('unmetLoadCost Value =' + str(pyo.value(instance.unmetLoadCost)))
    if instance.sw_expansion:
        logger.info('Cap expansion Value =' + str(pyo.value(instance.capExpansionCost)))
        logger.info('FOMCostObj Value =' + str(pyo.value(instance.FOMCostObj)))
    if instance.sw_reserves:
        logger.info('opres Value =' + str(pyo.value(instance.opresCost)))
    if instance.sw_ramp:
        logger.info('RampCost Value =' + str(pyo.value(instance.RampCost)))
    if instance.sw_trade:
        logger.info('tradeCost Value =' + str(pyo.value(instance.tradeCost)))

    logger.info('Obj complete')

    timer.toc('done with checks and extracting vars')

    ###############################################################################################
    # Post-procressing

    post.postprocessor(instance, instance.cols_dict)
    timer.toc('postprocessing done')

    # final steps for measuring the run time of the code
    end_time = datetime.now()
    run_time = end_time - start_time
    timer.toc('finished')
    logger.info(
        '\nStart Time: '
        + datetime.strftime(start_time, '%m/%d/%Y %H:%M')
        + ', Run Time: '
        + str(round(run_time.total_seconds() / 60, 2))
        + ' mins'
    )

    return instance


###################################################################################################
# Support functions


def init_old_cap(instance):
    """initialize capacity for 0th iteration

    Parameters
    ----------
    instance : PowerModel
        unsolved electricity model
    """
    instance.old_cap = {}
    instance.cap_set = []
    instance.old_cap_wt = {}

    for r, pt, y, steps in instance.CapCostSet:
        if (pt, y) not in instance.old_cap:
            instance.cap_set.append((pt, y))
            # each pt will increase cap by 1 GW per year. reasonable starting point.
            instance.old_cap[(pt, y)] = (y - instance.setA.start_year) * 1
            instance.old_cap_wt[(pt, y)] = instance.year_weights[y] * instance.old_cap[(pt, y)]


def set_new_cap(instance):
    """calculate new capacity after solve iteration

    Parameters
    ----------
    instance : PowerModel
        solved electricity pyomo model
    """
    instance.new_cap = {}
    instance.new_cap_wt = {}
    for r, pt, y, steps in instance.CapCostSet:
        if (pt, y) not in instance.new_cap:
            instance.new_cap[(pt, y)] = 0.0
        instance.new_cap[(pt, y)] = instance.new_cap[(pt, y)] + sum(
            instance.CapacityBuilds[(r, pt, year, steps)].value
            for year in instance.setA.y
            if year < y
        )
        instance.new_cap_wt[(pt, y)] = instance.year_weights[y] * instance.new_cap[(pt, y)]


def cost_learning_func(instance, pt, y):
    """function for updating learning costs by technology and year

    Parameters
    ----------
    instance : PowerModel
        electricity pyomo model
    pt : int
        technology type
    y : int
        year

    Returns
    -------
    int
        updated capital cost based on learning calculation
    """
    cost = (
        (
            instance.SupplyCurve_learning[pt]
            + 0.0001 * (y - instance.setA.start_year)
            + instance.new_cap[pt, y]
        )
        / instance.SupplyCurve_learning[pt]
    ) ** (-1.0 * instance.LearningRate[pt])
    return cost


def update_cost(instance):
    """update capital cost based on new capacity learning

    Parameters
    ----------
    instance : PowerModel
        electricity pyomo model
    """
    new_multiplier = {}
    for pt, y in instance.cap_set:
        new_multiplier[(pt, y)] = cost_learning_func(instance, pt, y)

    new_cost = {}
    # Assign new learning
    for r, pt, y, steps in instance.CapCostSet:
        # updating learning cost
        new_cost[(r, pt, y, steps)] = instance.CapCost_y0[(r, pt, steps)] * new_multiplier[pt, y]
        instance.capacity_costs_learning[(r, pt, y, steps)].value = new_cost[(r, pt, y, steps)]
