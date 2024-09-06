# src.integrator package

## Submodules

## src.integrator.config_setup module

This file contains Config_settings class. It establishes the main settings used when running
the model. It takes these settings from the run_config.toml file. It contains universal configurations
(e.g., configs that cut across modules and/or solve options) and module specific configs.

<!-- !! processed by numpydoc !! -->

### *class* src.integrator.config_setup.Config_settings(config_path, test=False, years_ow=[], regions_ow=[])

Bases: `object`

Generates the model settings that are used to solve. Settings include:
- Iterative Solve Config Settings
- Spatial Config Settings
- Temporal Config Settings
- Electricity Config Settings
- Other

<!-- !! processed by numpydoc !! -->

## src.integrator.gs_elec_hyd_res module

Iteratively solve 3 models with GS methodology

Gameplan:
1.  Use a config file to control the regions & years to sync
2.  Make a fake set of demands for the H2 model to kick-start it and get a non-zero H2 price
3.  Make an ELEC model
4.  Make an H2 model
5.  Solve the ELEC model
5b.  Catch metrics from ELEC
6.  Update the H2 model

> 1. pass in Elec Price (GS!!)
> 2. pass in H2 demand (GS!!)
1. Solve H2 model
2. Make Res Model
3. Pass ELEC Prices in (GS!! ~kinda right now)
4. Solve Res Model
5. Update the Elec model

> 1. new Load
> 2. new H2 Price
> 3. Future:  Elec demand from H2 (ON HOLD!)
1. Evaluate termination conditions
2. Loop to 5
3. Process output
   > > ~~~~~~ INFO SWAP PLAN ~~~~~

   > [ solve points annotated with =S= ]

> H2 MODEL                    ELEC MODEL                  RES/DEMAND
> : > |                           |
>   > <br/>
>   > =S=                          |
>   > <br/>
>   > |                           |
>   > <br/>
>   <br/>
>   > ```
>   > |<<<--- ELEC Prices --------|
>   > ```
>   <br/>
>   >                            |
>   <br/>
>   > ```
>   > |<<<--- H2 Demand ----------|
>   > ```
>   <br/>
>   >                            |
>   > |                           |                           |
>   <br/>
>   =S=                          |                           |
>   : |                           |
>     <br/>
>     ```
>     |------- ELEC Prices ---->>>|
>     ```
>     <br/>
>     |                           |
>     <br/>
>     |                          =S=
>     <br/>
>     <br/>
>     ```
>     |------ H2 Prices ------->>>|
>     ```
>     <br/>
>                                |
>     |                           
>     <br/>
>     ```
>     |<<<--- New Load -----------|
>     ```
>     <br/>
>     <br/>
>     |                           |                           |
1. re-solve each model
2. Calculate prev_value - 

   ```
   |H2.obj|
   ```

    + 

   ```
   |ELEC.obj|
   ```

    < tolerance
3. No?:  goto 5

<!-- !! processed by numpydoc !! -->

### src.integrator.gs_elec_hyd_res.run_gs_combo(config_path: Path)

Start the iterative GS process

* **Parameters:**
  **config_path**
  : Path to config file

<!-- !! processed by numpydoc !! -->

### src.integrator.gs_elec_hyd_res.simple_solve(m: ConcreteModel)

a simple solve routine

<!-- !! processed by numpydoc !! -->

## src.integrator.progress_plot module

A plotter that can be used for combined solves

Currently, this makes live plot.  It could be mod’ed to just save them to outputs

<!-- !! processed by numpydoc !! -->

### src.integrator.progress_plot.plot_it(h2_price_records=[], elec_price_records=[], h2_obj_records=[], elec_obj_records=[], h2_demand_records=[], elec_demand_records=[], load_records=[], elec_price_to_res_records=[])

cheap plotter of iterative progress

<!-- !! processed by numpydoc !! -->

## src.integrator.runner module

<!-- !! processed by numpydoc !! -->

### src.integrator.runner.plot_price_distro(instance: [PowerModel](src.models.electricity.scripts.md#src.models.electricity.scripts.electricity_model.PowerModel), price_records: list[float])

cheap/quick analyisis and plot of the price records

<!-- !! processed by numpydoc !! -->

### src.integrator.runner.run_elec_solo(config_path: Path | None = None)

<!-- !! processed by numpydoc !! -->

### src.integrator.runner.run_h2_solo(data_path: Path, config_path: Path | None = None)

<!-- !! processed by numpydoc !! -->

## src.integrator.unified_elec_hyd_res module

A first crack at unifying the solve of both H2 and Elec and Res

Dev Notes:

(1).  This borrows heavily from (aka is a cheap copy of) the unified_solver.py which solves
: the elec and h2 jointly

(2).  This is for demonstration purposes only, and it is presumed that an improved single
: class “unified solver” would have selectable options to join models?  Maybe?

(3).  As is the case with the original effort, this can/should be refactored a bit when the
: grand design pattern stabilizes

(4).  The “annual demand” constraint that is present and INACTIVE in the unified_solver.py
: class is omitted here for clarity.  It may likely be needed–in some form–at a later
  time.  Recall, the key linkages to share the electrical demand primary variable are:
  <br/>
  > (a).  an annual level demand constraint (see unified_solver.py)
  > (b).  an accurate price-pulling function that can consider weighted duals
  <br/>
  > > from both constraints [NOT done]

(5).  This model has a 2-solve update cycle as commented on near the termination check
: elec_prices gleaned from      cycle[n] results -> solve cycle[n+1]
  new_load gleaned from         cycle[n+1] results -> solve cycle[n+2]
  elec_pices gleaned from       cycle[n+2]

(6).  This iterative process could benefit from refactoring to use a persistent solver, after
: some decisions are made about how to handle arbitrary solvers–some may/may not have
  that capability.

<!-- !! processed by numpydoc !! -->

### src.integrator.unified_elec_hyd_res.run_unified_res_elec_h2(config_path: Path)

<!-- !! processed by numpydoc !! -->

### src.integrator.unified_elec_hyd_res.simple_solve(m: ConcreteModel)

a simple solve routine

<!-- !! processed by numpydoc !! -->

## src.integrator.utilities module

A gathering of utility functions for dealing with model interconnectivity

Dev Note:  At some review point, some decisions may move these back & forth with parent
models after it is decided if it is a utility job to do …. or a class method.

Additionally, there is probably some renaming due here for consistency

<!-- !! processed by numpydoc !! -->

### *class* src.integrator.utilities.EI(region, year, hour)

Bases: `tuple`

(region, year, hour)

<!-- !! processed by numpydoc !! -->

#### hour

Alias for field number 2

<!-- !! processed by numpydoc !! -->

#### region

Alias for field number 0

<!-- !! processed by numpydoc !! -->

#### year

Alias for field number 1

<!-- !! processed by numpydoc !! -->

### *class* src.integrator.utilities.HI(region, year)

Bases: `tuple`

(region, year)

<!-- !! processed by numpydoc !! -->

#### region

Alias for field number 0

<!-- !! processed by numpydoc !! -->

#### year

Alias for field number 1

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.convert_elec_price_to_lut(prices: list[tuple[[EI](#src.integrator.utilities.EI), float]])

convert electricity prices to dictionary, look up table

* **Parameters:**
  **prices**
  : list of prices
* **Returns:**
  dict[EI, float]
  : dict of prices

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.convert_h2_price_records(records: list[tuple[[HI](#src.integrator.utilities.HI), float]])

simple coversion from list of records to a dictionary LUT
repeat entries should not occur and will generate an error

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.create_temporal_mapping(sw_temporal)

Combines the input mapping files within the electricity model to create a master temporal
mapping dataframe. The df is used to build multiple temporal parameters used within the  model.
It creates a single dataframe that has 8760 rows for each hour in the year.
Each hour in the year is assigned a season type, day type, and hour type used in the model.
This defines the number of time periods the model will use based on cw_s_day and cw_hr inputs.

* **Returns:**
  dataframe
  : a dataframe with 8760 rows that include each hour, hour type, day, day type, and season.
    It also includes the weights for each day type and hour type.

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.get_annual_wt_avg(elec_price: DataFrame)

takes annual weighted average of hourly electricity prices

* **Parameters:**
  **elec_price**
  : hourly electricity prices
* **Returns:**
  dict[HI, float]
  : annual weighted average electricity prices

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.get_elec_price(instance: [PowerModel](src.models.electricity.scripts.md#src.models.electricity.scripts.electricity_model.PowerModel) | ConcreteModel, block=None)

pulls hourly electricity prices from completed PowerModel and weights correctly

* **Parameters:**
  **instance**
  : solved electricity model
* **Returns:**
  pd.DataFrame
  : df full of electricity prices

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.make_output_dir(dir)

generates an output directory to write model results, output directory is the date/time
at the time this function executes. It includes subdirs for vars, params, constraints.

* **Returns:**
  string
  : the name of the output directory

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.poll_h2_prices_from_elec(model: [PowerModel](src.models.electricity.scripts.md#src.models.electricity.scripts.electricity_model.PowerModel), tech, regions: Iterable)

poll the step-1 H2 price currently in the model for region/year, averaged over any steps

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.poll_hydrogen_price(model: [H2Model](src.models.hydrogen.model.md#src.models.hydrogen.model.h2_model.H2Model) | ConcreteModel, block=None)

Retrieve the price of H2 from the H2 model

* **Parameters:**
  **model**
  : the model to poll

  **block: optional**
  : block model to poll
* **Returns:**
  list[tuple[HI, float]]
  : list of H2 Index, price tuples

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.poll_year_avg_elec_price(price_list: list[tuple[[EI](#src.integrator.utilities.EI), float]])

retrieve a REPRESENTATIVE price at the annual level from a listing of prices

This function computes the AVERAGE elec price for each region-year combo

* **Parameters:**
  **price_list**
  : input price list
* **Returns:**
  dict[HI, float]
  : a dictionary of (region, year): price

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.regional_annual_prices(m: [PowerModel](src.models.electricity.scripts.md#src.models.electricity.scripts.electricity_model.PowerModel) | ConcreteModel, block=None)

pulls all regional annual weighted electricity prices

* **Parameters:**
  **m**
  : solved PowerModel

  **block**
  : solved block model if applicable, by default None
* **Returns:**
  dict[HI, float]
  : dict with regional annual electricity prices

<!-- !! processed by numpydoc !! -->

### src.integrator.utilities.setup_logger(output_dir)

<!-- !! processed by numpydoc !! -->

## Module contents

<!-- !! processed by numpydoc !! -->
