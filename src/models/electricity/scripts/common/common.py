"""Utility file containing miscellaneous common functions used in CCATS.

Summary
-------
This is a utility file containing general functions that are either a) used frequently in a single submodule, or are used
by several submodules. Example functions include "read_dataframe", which is a universal function for reading files into
dataframes, and "calculate_inflation" which applies the NEMS inflation multipliers to CCATS DataFrames. Full accounting
of common functions below:

    * calculate_inflation: Inflation calculator using restart file inflation multiplier, applied to pandas DataFrames.
    * unpack_pyomo: Unpacks pyomo results and converts results to DataFrames
    * check_results: Checks optimization termination condition

Notes
-----
Convention for import alias is import common as com

"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger('common.py')


def calculate_inflation(rest_mc_jpgdp, from_year, to_year=None):
    """Inflation calculator using restart file inflation multiplier, applied to pandas DataFrames.

    Returns
    -------
    self.rest_mc_jpgdp
    """
    if to_year is None:
        to_year = 1987  # Hardcoded in NEMS

    temp = rest_mc_jpgdp.at[(to_year), 'value'] / rest_mc_jpgdp.at[(from_year), 'value']
    return temp


def unpack_pyomo(variable, values, levels):
    """Tool for unpacking pyomo variable outputs and converting them to dfs.

    Parameters
    ----------
    variable: array
        Target variable to unpack
    values: array
        Pyomo output values
    levels: int
        Number of levels in array to unpack (i.e. CO2 supplied from i is one level, while CO2 piped from i to j is two levels)

    Returns
    -------
    df
    """
    if levels == 1:
        pyomo_dict = {(i, v.name): values(v) for (i), v in variable.items()}

    elif levels == 2:
        pyomo_dict = {(i, j, v.name): values(v) for (i, j), v in variable.items()}

    elif levels == 3:
        pyomo_dict = {(i, j, k, v.name): values(v) for (i, j, k), v in variable.items()}

    df = pd.DataFrame.from_dict(pyomo_dict, orient='index', columns=['variable value'])
    df = df.reset_index()
    temp = pd.DataFrame(df['index'].tolist())
    df[temp.columns] = temp[temp.columns]

    return df


def check_results(results, SolutionStatus, TerminationCondition):
    """

    Parameters
    ----------
    results : str
        Results from pyomo
    SolutionStatus : str
        Solution Status from pyomo
    TerminationCondition : str
        Termination Condition from pyomo

    Returns
    -------
    results
    """
    return (
        (results is None)
        or (len(results.solution) == 0)
        or (results.solution(0).status == SolutionStatus.infeasible)
        or (results.solver.termination_condition == TerminationCondition.infeasible)
        or (results.solver.termination_condition == TerminationCondition.unbounded)
    )
