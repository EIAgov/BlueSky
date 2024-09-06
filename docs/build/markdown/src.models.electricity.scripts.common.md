# src.models.electricity.scripts.common package

## Submodules

## src.models.electricity.scripts.common.common module

Utility file containing miscellaneous common functions used in CCATS.

### Summary

This is a utility file containing general functions that are either a) used frequently in a single submodule, or are used
by several submodules. Example functions include “read_dataframe”, which is a universal function for reading files into
dataframes, and “calculate_inflation” which applies the NEMS inflation multipliers to CCATS DataFrames. Full accounting
of common functions below:

> * read_dataframe: Reads multiple filetypes into python as pandas DataFrames, checking for nans.
> * calculate_inflation: Inflation calculator using restart file inflation multiplier, applied to pandas DataFrames.
> * array_to_df: Creates a pandas DataFrame from a numpy array
> * df_to_array: Creates a numpy array from a pandas DataFrame
> * unpack_pyomo: Unpacks pyomo results and converts results to DataFrames
> * check_results: Checks optimization termination condition
> * align_index: Aligns the index types of two tables based on the restart variable type
> * compare_lists: Check if lista is equal or a subset of listb
> * check_dicts_ruleset: Check the list of dicts against defined ruleset

### Notes

Convention for import alias is import common as com

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.align_index(df1, df2, restart_var=None)

Aligns the index types of two tables based on the restart variable type.

> * If the restart variable is provided we use that to determine the index types
> * If restaet_var is none, we assume that df1 has the correct index type
* **Parameters:**
  **df1: 2 dimensional dataframe**
  : restart variable table

  **df2: 2 dimensional dataframe**
  : restart variable table

  **restart_var: 2 dimensional dataframe**
  : restart variable, used to decide the index type
* **Returns:**
  df1, df2

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.array_to_df(array)

Create df from array.

> * Creates a multi-index DataFrame from a multi-dimensional array
> * Each array dimension is stored as a binary index column in the DataFrame multi-index
> * Multi-index columns are currently numbered to reflect array dimension level
* **Parameters:**
  **series**
  : A multi-dimensional array containing restart file data
* **Returns:**
  df

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.calculate_inflation(rest_mc_jpgdp, from_year, to_year=None)

Inflation calculator using restart file inflation multiplier, applied to pandas DataFrames.

* **Returns:**
  self.rest_mc_jpgdp

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.check_dicts_ruleset(dict_list)

Check the list of dicts against defined ruleset

> * 1. check for nans
> * 1. make sure lengths of each dict are the same length
* **Parameters:**
  **dict_list: list**
  : list of dicts

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.check_results(results, SolutionStatus, TerminationCondition)

* **Parameters:**
  **results**
  : Results from pyomo

  **SolutionStatus**
  : Solution Status from pyomo

  **TerminationCondition**
  : Termination Condition from pyomo
* **Returns:**
  results

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.compare_lists(lista, listb)

Check if lista is equal or a subset of listb

> * used to check that node ids(supply,hubs,storage)in lista
>   : are part of the set in listb
* **Parameters:**
  **lista: list**

  **listb: list**

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.df_to_array(df)

Turns multi-index DataFrame into multi-dimensional array.

> * Creates a multi-dimensional array from a multi-index dataframe
> * Each DataFrame multi-index is stored as an array dimension
* **Parameters:**
  **series**
  : A multi-index DataFrame containing restart file data
* **Returns:**
  array

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.read_dataframe(filename, sheet_name=0, index_col=None, skiprows=None, to_int=True)

Reads multiple filetypes into python as pandas DataFrames, checking for nans.

* **Parameters:**
  **filename**
  : Filename, including file type extension (e.g. .csv)

  **sheet_name**
  : Name of the sheet if using excel or hdf

  **index_col**
  : Column number to use as row labels

  **skiprows**
  : Column number to use as row labels
* **Returns:**
  pd.DataFrame

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common.unpack_pyomo(variable, values, levels)

Tool for unpacking pyomo variable outputs and converting them to dfs.

* **Parameters:**
  **variable: array**
  : Target variable to unpack

  **values: array**
  : Pyomo output values

  **levels: int**
  : Number of levels in array to unpack (i.e. CO2 supplied from i is one level, while CO2 piped from i to j is two levels)
* **Returns:**
  df

<!-- !! processed by numpydoc !! -->

## src.models.electricity.scripts.common.common_debug module

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common_debug.check_for_infvalues(df, tablename='my_table')

checks table for infinity values.

* **Parameters:**
  **df1: 2 dimensional dataframe**
  : restart variable table

  **tablename: string**
  : name for the output file
* **Returns:**
  boolean

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common_debug.check_table_for_nans(df, tablename='my_table')

checks table for nan values.

* **Parameters:**
  **df1: 2 dimensional dataframe**
  : restart variable table

  **tablename: string**
  : name for the output file
* **Returns:**
  boolean

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common_debug.compute_infeasibility_explanation(model, solver=None, tee=False, tolerance=1e-08)

This function attempts to determine why a given model is infeasible. It deploys
two main algorithms:

1. Successfully relaxes the constraints of the problem, and reports to the user
   some sets of constraints and variable bounds, which when relaxed, creates a
   feasible model.
2. Uses the information collected from (1) to attempt to compute a Minimal
   Infeasible System (MIS), which is a set of constraints and variable bounds
   which appear to be in conflict with each other. It is minimal in the sense
   that removing any single constraint or variable bound would result in a
   feasible subsystem.

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common_debug.print_table(df, outputfilename=None)

prints a table for easy debugging.

* **Parameters:**
  **df1: 2 dimensional dataframe**
  : restart variable table

  **outputfilename: string**
  : name of output file

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common_debug.run_pylint(filelist=None, errors_only=False)

runs pylint.

> ```
> *
> ```

> checks if index type of df1 is equal to index type of df2

> ```
> *
> ```

> logs the result
* **Parameters:**
  **filelist: list**
  : list of files to evalutes, if None, then pylint will evalute the cwd

  **errors_only: boolean**
  : determines if we run pylint against all checks or errors only
* **Returns:**
  boolean

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common_debug.table_analysis(df, df_name='table_analysis.csv')

<!-- !! processed by numpydoc !! -->

### src.models.electricity.scripts.common.common_debug.table_update_status(df1, df2)

checks two tables index types to see if they are aligned for a .merge() or .update().

> ```
> *
> ```

> checks if index type of df1 is equal to index type of df2

> ```
> *
> ```

> logs the result
* **Parameters:**
  **df1: 2 dimensional dataframe**
  : restart variable table

  **df2: 2 dimensional dataframe**
  : restart variable table
* **Returns:**
  boolean

<!-- !! processed by numpydoc !! -->

## Module contents

<!-- !! processed by numpydoc !! -->
