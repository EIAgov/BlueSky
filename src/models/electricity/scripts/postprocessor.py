"""This file is the main postprocessor for the electricity model. It writes out all relavant model
outputs (e.g., sets, variables, parameters, constraints). It contains:
 - A function that converts pyomo component objects to dataframes
 - A function to make the electricity output sub-directories
 - The postprocessor function, which writes out to csvs all of the electricity model pyomo component
 objects to csvs in the output directory

"""

###################################################################################################
# Setup

# Import pacakges
import pandas as pd
import pyomo.environ as pyo
from datetime import datetime
import os

# Import scripts
from definitions import PROJECT_ROOT
from definitions import OUTPUT_ROOT

###################################################################################################
# Sets
# for set in mod.component_objects(pyo.Set, active=True):set.pprint()


# Variables, Parameters, Constraints
def component_objects_to_df(mod_object):
    """takes pyomo component objects (e.g., variables, parameters, constraints) and processes the
    pyomo data and converts it to a dataframe and then writes the dataframe out to an output dir.
    The dataframe contains a key column which is the original way the pyomo data is structured,
    as well as columns broken out for each set and the final values.

    Parameters
    ----------
    mod_object : pyomo component object
        pyomo component object

    Returns
    -------
    dataframe
        contains the pyomo model results for the component object
    """
    name = str(mod_object)
    # print(name)

    # creating a dataframe that reads in the paramater info
    df = pd.DataFrame()
    df['Key'] = [str(i) for i in mod_object]
    df[name] = [pyo.value(mod_object[i]) for i in mod_object]

    if not df.empty:
        # breaking out the data from the mod_object info into multiple columns
        df['Key'] = df['Key'].str.replace('(', '', regex=False).str.replace(')', '', regex=False)
        temp = df['Key'].str.split(', ', expand=True)
        for col in temp.columns:
            temp.rename(columns={col: 'i_' + str(col)}, inplace=True)
        df = df.join(temp, how='outer')

    return df


###################################################################################################
# Main Project Execution
def make_output_dir():
    """generates an output directory to write model results, output directory is the date/time
    at the time this function executes. It includes subdirs for vars, params, constraints.

    Returns
    -------
    string
        the name of the output directory
    """
    now = datetime.now().strftime('%Y-%m-%d %H%Mh')

    dir = OUTPUT_ROOT / 'electricity'

    if not os.path.exists(dir):
        os.makedirs(dir)
        os.makedirs(dir / 'variables/')
        os.makedirs(dir / 'parameters/')
        os.makedirs(dir / 'constraints/')
        os.makedirs(dir / 'prices/')
        os.makedirs(dir / 'obj/')

    return dir


def postprocessor(instance, cols_dict):
    """master postprocessor function that writes out the final dataframes from to the electricity
    model. Creates the output directories and writes out dataframes for variables, parameters, and
    constraints. Gets the correct columns names for each dataframe using the cols_dict.

    Parameters
    ----------
    instance : pyomo model
        electricity concrete model
    cols_dict : dictionary
        dictionary where keys are the names of the vars, params, or constraints and the values
        are the cooresponding column names for each of the sets the items are indexed by.

    Returns
    -------
    string
        output directory name
    """
    dir = make_output_dir()

    for variable in instance.component_objects(pyo.Var, active=True):
        if variable.name == 'var_elec_request':
            # TODO:  Consider if this var needs reporting, and if so adjust...
            continue
        df = component_objects_to_df(variable)
        if not df.empty:
            df.columns = ['Key'] + cols_dict[str(variable)]
            df.to_csv(dir / 'variables' / '.'.join((str(variable), 'csv')), index=False)
        else:
            print(str(variable) + ' is empty.')

    for parameter in instance.component_objects(pyo.Param, active=True):
        if parameter.name == 'fixed_elec_request':
            # TODO:  consider if this needs reporting...
            continue
        df = component_objects_to_df(parameter)
        if not df.empty:
            df.columns = ['Key'] + cols_dict[str(parameter)]
            df.to_csv(dir / 'parameters' / '.'.join((str(parameter), 'csv')), index=False)
        else:
            print(str(parameter) + ' is empty.')

    for constraint in instance.component_objects(pyo.Constraint, active=True):
        component_objects_to_df(constraint).to_csv(
            dir / 'constraints' / '.'.join((str(constraint), 'csv')), index=False
        )

    # obj_df = pd.DataFrame({'CostType':'totalCost', 'value':instance.totalCost()})
    # obj_df.concat({'dispatchCost': pyo.value(instance.dispatchCost)})
    #
    # pyo.value(instance.dispatchCost)
    # logger.info('unmetLoadCost Value =' + str(pyo.value(instance.unmetLoadCost)))
    # if instance.sw_expansion:
    #     logger.info('Cap expansion Value =' + str(pyo.value(instance.capExpansionCost)))
    #     logger.info('FOMCostObj Value =' + str(pyo.value(instance.FOMCostObj)))
    # if instance.sw_reserves:
    #     logger.info('opres Value =' + str(pyo.value(instance.opresCost)))
    # if instance.sw_ramp:
    #     logger.info('RampCost Value =' + str(pyo.value(instance.RampCost)))
    # if instance.sw_trade:
    #     logger.info('tradeCost Value =' + str(pyo.value(instance.tradeCost)))
    # TODO:  Clean up the path references here
    instance.dir = dir
