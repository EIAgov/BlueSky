"""This file is a collection of functions that are used in support of the electricity model."""

###################################################################################################
# Setup

# Import pacakges
import os as os
from pathlib import Path
import sys as sys
import numpy as np
import pyomo.environ as pyo

# import scripts
from definitions import PROJECT_ROOT

# establish paths
data_root = Path(PROJECT_ROOT, 'src/models/electricity/input')


###################################################################################################
# Declare things functions


def declare_set(self, sname, df):
    """Assigns the index from the df to be a pyomo set using the name specified.
    Adds the name and index column names to the column dictionary used for post pocessing.

    Parameters
    ----------
    sname : string
        name of the set to be declared
    df : dataframe
        dataframe from which the index will be grabbed to generate the set

    Returns
    -------
    pyomo set
        a pyomo set
    """
    sset = pyo.Set(initialize=df.index)
    scols = list(df.reset_index().columns)
    scols = scols[-1:] + scols[:-1]
    self.cols_dict[sname] = scols

    return sset


def declare_param(self, pname, p_set, df, default=0, mutable=False):
    """Assigns the df to be a pyomo parameter using the name specified.
    Adds the name and index column names to the column dictionary used for post pocessing.

    Parameters
    ----------
    pname : string
        name of the parameter to be declared
    p_set : pyomo set
        the pyomo set that cooresponds to the parameter data
    df : dataframe
        dataframe used generate the parameter
    default : int, optional
        by default 0
    mutable : bool, optional
        by default False

    Returns
    -------
    pyomo parameter
        a pyomo parameter
    """
    param = pyo.Param(p_set, initialize=df, default=default, mutable=mutable)
    pcols = list(df.reset_index().columns)
    pcols = pcols[-1:] + pcols[:-1]
    self.cols_dict[pname] = pcols

    return param


def declare_var(self, vname, sname, v_set):
    """Assigns the set to be the index for the pyomo variable being declared.
    Adds the name and index column names to the column dictionary used for post pocessing.

    Parameters
    ----------
    vname : string
        name of the variable to be declared
    sname : string
        the name of the set
    v_set : pyomo set
        the pyomo set that the variable data will be indexed by

    Returns
    -------
    pyomo variable
        a pyomo variable
    """
    var = pyo.Var(v_set, within=pyo.NonNegativeReals)
    vcols = [vname] + self.cols_dict[sname][1:]
    self.cols_dict[vname] = vcols
    return var


###################################################################################################
# Populate sets functions


def populate_sets_rule(m1, sname, set_base_name='', set_base2=[]):
    set_in = getattr(m1, sname)
    scols = m1.cols_dict[sname][1:]

    if set_base_name == '':
        scol_base = np.array([s in set_base2 for s in scols], dtype=bool)
        scols2 = list(np.array(scols)[scol_base])
        scol_base_order = np.array([scols2.index(s) for s in set_base2])
        m1.set_out = {}
    else:
        set_base = getattr(m1, set_base_name)
        m1.set_out = pyo.Set(m1.hr)
        scol_base = np.array([s == set_base_name for s in scols], dtype=bool)

    for i in set_in:
        i = np.array(i)
        rest_i = tuple(i[~scol_base])
        if set_base_name == '':
            base_i = tuple(i[scol_base][scol_base_order])
            if base_i not in m1.set_out:
                m1.set_out[base_i] = []
            m1.set_out[base_i].append(rest_i)
        else:
            base_i = int(i[scol_base][0])

            m1.set_out[base_i].add(rest_i)
    set_out = m1.set_out
    m1.del_component('set_out')
    return set_out


def populate_by_hour_sets_rule(m):
    m.StorageSetByHour = populate_sets_rule(m, 'StorageSet', set_base_name='hr')
    m.GenSetByHour = populate_sets_rule(m, 'GenSet', set_base_name='hr')
    m.H2GenSetByHour = populate_sets_rule(m, 'H2GenSet', set_base_name='hr')


def populate_demand_balance_sets_rule(m):
    m.GenSetDemandBalance = populate_sets_rule(m, 'GenSet', set_base2=['y', 'r', 'hr'])
    m.StorageSetDemandBalance = populate_sets_rule(m, 'StorageSet', set_base2=['y', 'r', 'hr'])

    if m.sw_trade == 1:
        m.TradeSetDemandBalance = populate_sets_rule(m, 'TradeSet', set_base2=['y', 'r', 'hr'])
        m.TradeCanSetDemandBalance = populate_sets_rule(
            m, 'TradeCanSet', set_base2=['y', 'r', 'hr']
        )


def populate_trade_sets_rule(m):
    m.TradeCanLineSetUpper = populate_sets_rule(m, 'TradeCanSet', set_base2=['r', 'r1', 'y', 'hr'])
    m.TradeCanSetUpper = populate_sets_rule(m, 'TradeCanSet', set_base2=['r1', 'y', 'CSteps', 'hr'])


def populate_RM_sets_rule(m):
    m.SupplyCurveRM = populate_sets_rule(m, 'SupplyCurveSet', set_base2=['y', 'r', 's'])
