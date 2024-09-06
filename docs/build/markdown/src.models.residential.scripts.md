# src.models.residential.scripts package

## Submodules

## src.models.residential.scripts.residential module

Residential Model.
This file contains the residentialModule class which contains a representation of residential
electricity prices and demands.

<!-- !! processed by numpydoc !! -->

### *class* src.models.residential.scripts.residential.residentialModule(loadFile: str | None = None, load_df: DataFrame | None = None, calibrate: bool | None = False)

Bases: `object`

<!-- !! processed by numpydoc !! -->

#### baseYear *= 0*

#### hr_map *= Empty DataFrame Columns: [] Index: []*

#### loads *= {}*

#### make_block(prices, pricesindex)

Updates the value of ‘Load’ based on the new prices given.
The new prices are fed into the equations from the residential model.
The new calculated Loads are used to constrain ‘Load’ in pyomo blocks.

* **Parameters:**
  **prices**
  : Pyomo Parameter of newly updated prices

  **pricesindex**
  : Pyomo Set of indexes that matches the prices given
* **Returns:**
  pyo.Block
  : Block containing constraints that set ‘Load’ variable equal to the updated load values

<!-- !! processed by numpydoc !! -->

#### prices *= {}*

#### sensitivity(prices, parameter, percent)

This estimates how much the output Load will change due to a change in one of the input variables.
It can calculate these values for changes in price, price elasticity, income, income elasticity, or long term trend.
The Load calculation requires input prices, so this function requires that as well for the base output Load.
Then, an estimate for Load is calculated for the case where the named ‘parameter’ is changed by ‘percent’ %.

* **Parameters:**
  **prices**
  : Price values used to calculate the Load value

  **parameter**
  : Name of variable of interest for sensitivity. This can be:
    : ‘income’, ‘i_elas’, ‘price’, ‘p_elas’, ‘trendGR’

  **percent**
  : A value 0 - 100 for the percent that the variable of interest can change.
* **Returns:**
  dataframe
  : Indexed values for the calculated Load at the given prices, the Load if the variable of interest
    is increased by ‘percent’%, and the Load if the variable of interest is decreased by ‘percent’%

<!-- !! processed by numpydoc !! -->

#### update_load(p)

Takes in Dual pyomo Parameters or dataframes to update Load values

* **Parameters:**
  **p**
  : Pyomo Parameter or dataframe of newly updated prices from Duals
* **Returns:**
  pandas DataFrame
  : Load values indexed by region, year, and hour

<!-- !! processed by numpydoc !! -->

## src.models.residential.scripts.utilities module

This file contains the options to re-create the input files. It creates:
: - Load.csv: electricity demand for all model years (used in residential and electricity)
  - BaseElecPrice.csv: electricity prices for initial model year (used in residential only)

Uncomment out the functions at the end of this file in the “if \_\_name_\_ == ‘_\_main_\_’” statement
in order to generate new load or base electricity prices.

<!-- !! processed by numpydoc !! -->

### src.models.residential.scripts.utilities.base_price()

Runs the electricity model with base price configuration settings and then
merges the electricity prices and temporal crosswalk data produced from the run
to generate base year electricity prices.

* **Returns:**
  pandas.core.frame.DataFrame
  : dataframe that contains base year electricity prices for all regions/hours

<!-- !! processed by numpydoc !! -->

### src.models.residential.scripts.utilities.scale_load()

Reads in BaseLoad.csv (load for all regions/hours for first year)
and LoadScalar.csv (a multiplier for all model years). Merges the
data and multiplies the load by the scalar to generate new load
estimates for all model years.

* **Returns:**
  pandas.core.frame.DataFrame
  : dataframe that contains load for all regions/years/hours

<!-- !! processed by numpydoc !! -->

## Module contents

<!-- !! processed by numpydoc !! -->
