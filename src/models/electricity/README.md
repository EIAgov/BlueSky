# Table of contents

- [Table of contents](#table-of-contents)
- [Run setup](#run-setup)
            - [Feature settings](#feature-settings)
            - [Technology settings](#technology-settings)
- [Feedback](#feedback)
        - [Overall](#overall)
        - [Setup](#setup)
        - [Inputs/Preprocessor](#inputspreprocessor)
        - [Electricity Model](#electricity-model)
        - [Outputs/Viewer](#outputsviewer)
- [Model overview](#model-overview)
    - [Nomenclature Table](#nomenclature-table)
        - [Sets](#sets)
        - [Re-indexed sets](#re-indexed-sets)
        - [Parameters](#parameters)
        - [Variables](#variables)
    - [Objective function](#objective-function)
    - [Constraints](#constraints)
            - [Balance constraints](#balance-constraints)
            - [Generation upper bounds](#generation-upper-bounds)
            - [Capacity expansion](#capacity-expansion)
            - [Trade](#trade)
            - [Reserve Margin](#reserve-margin)
            - [Ramping](#ramping)
            - [Operating reserves](#operating-reserves)

- [Code Documentation](#code-documentation)


# Run setup
There are several files where features can be turned on/off and different crosswalks can be selected. All of these switches exist in the electricity/input directory.

#### Feature settings
The `run_config.toml` file contains the main switches through which options for the electricity module can be changed. The setup column names various constraint settings:

|Switch    | Description   | Values | Notes |
|:----- | :------ | :--------- | :---: |
|sw_trade | Trade | <code> 0 = Off <br> 1 = On </code> | |
|sw_expansion | Capacity Expansion | <code> 0 = Off <br> 1 = On </code> | Note the file cem_inputs/AllowBuilds.csv also contains settings of which technologies are available to expand |
| sw_agg_year | Aggregate Years | <code> 0 = Only runs sw_year <br> 1 = Aggregates all unselected years </code> | Switch to aggregate years based on the selected years in sw_year.csv|
|sw_rm | Reserve Margin Constraint | <code> 0 = Off <br> 1 = On </code> | |
|sw_ramp | Ramping Constraint | <code> 0 = Off <br> 1 = On </code> | |
|sw_reserves | Operating Reserve Constraint | <code> 0 = Off <br> 1 = On </code> ||
|sw_learning | Technology Cost Learning | <code> 0 = No learning <br> 1 = Linear learning <br> 2 = Nonlinear learning | The method of which technology costs decrease as more capacity is built. Note this switch does nothing unless sw_expansion=1 |

#### Technology settings

The model contains 14 power technologies (pt) in its initial layout. Users could change the technology assignments and add more technology types or remove technology types, but any changes to the code would require updates to the cooresponding input data. The technologies represented include:
<br> 1.)	Coal Steam 
<br> 2.)	Oil Steam
<br> 3.)	Natural Gas Combustion Turbine
<br> 4.)	Natural Gas Combined-Cycle
<br> 5.)	Hydrogen Turbine
<br> 6.)	Nuclear
<br> 7.)	Biomass
<br> 8.)	Geothermal
<br> 9.)	Municipal-Solid-Waste
<br> 10.)	Hydroelectric Generation
<br> 11.)	Pumped Hydroelectric Storage
<br> 12.)	Battery Energy Storage
<br> 13.)	Wind, Offshore
<br> 14.)	Wind, Onshore
<br> 15.)	Solar  (step 1 = utility-scale; step 2 = end-use)

The power technologies (pt) are also combined into group based on  the applicability of different constraints. These groups are defined in `pt_subsets.csv` and includes:
- ptc: conventional
- ptr: renewable
- pth: hydroelectric
- pts: storage 
- pti: intermittent 
- ptw: wind
- ptsol: solar
- pth2: hydrogen
- ptd: dispatchable
- ptg: generating


When the capacity expansion switch is turned on, a user can select which technologies they want to have expansion and retirement capabilities. Turning these switches on allows for builds and/or retirements of a given technology and supply curve step.

|Switch    | Description   | Values | Notes |
|:----- | :------: | :--------- | :---: |
|sw_ptbuilds | Contains switches for technologies and supply curve steps where capacity is allowed to build | <code>0 = Not Allowed to Build <br> 1 = Allowed to Build | Switches contained in Sw_ptbuilds.csv |
| sw_ptretires | Contains switches for technologies and supply curve steps where capacity is allowed to retire | <code> 0 = Not Allowed to Retire <br> 1 = Allowed to Retire | Switches contained in Sw_ptbuilds.csv |


# Feedback

### Overall 

- Is this layout and files structure for the electricity model intuitive?
- Is the documentation and are the docstrings clear and easy to understand?
- Does the model need to run for all years between 2023-2050 or do you think the averaging approach applied for groups of years is a useful flexibility?

### Setup 

- Should we have a scedes file like we have for NEMS? Should it include all files within the project or just the switches/crosswalks (like how it is set up now)?
- Is the switch structure useful for model development?
- Is the crosswalk structure useful for model development or would you execute temporal/spatial flexibility using a different method?
- Would you rather the switches and cross walks be read in through arguments in command line, toml files, csvs, the current mix is good, or something totally different?

### Inputs/Preprocessor

- Inputs are currently setup as CSVs, but we built the capability to store them all in SQLite database. Would you rather have the data stored as CSVs or as a database?
- For example, the load data is not readable in excel because the file format is so large. Does it matter?
- The csv inputs are not in the final format for the model. Preprocessor modifies the inputs to get them ready for the electricity model. For example, we have switches that pick what regions/years we want to test, we also average data by the time segments selected. Preprocessor is apart of the model run, so data is processed when you run the model. Is that ok? Or should we write out all the model run CSVs as a separate step before the model runs. 

### Electricity Model

- Is the class structure for PowerModel a good approach? 
- Should other parts of the electricity model code be in classes? Should sets and parameters be in their own classes? Should utility functions be in a class? Or is just having functions without classes reasonable?

### Outputs/Viewer

- Is it useful to write out all of the parameters, constraint, and variable results?
- Are you able to launch the viewer from the bat file? Are you able to run the viewer from within your IDE? What is your preferred way to launch the viewer?
 

# Model overview

## Nomenclature Table

### Sets
|Set    | Code    | Data Type  | Short Description |
|:----- | :------ | :--------- | :---------------- |
|$$H$$ | hr | Set | All representative hours|
|$$Y$$ | y | Sparse set | All selected model years|
|$$SEA$$ | s | Set | All seasons|
|$$D$$ | day | Set | All representative days|
|$$R$$ | r | Set | All selected model domestic regions|
|$$R^{can}$$ | r | Set | All selected model international regions|
|$$\Theta_{load}$$ |LoadSet | Sparse set | All load sparse set|
|$$\Theta_{gen}$$ |GenSet | Sparse set | All non-storage generation sparse set|
|$$\Theta_{H2gen}$$ |H2GenSet | Sparse set | All hydrogen generation sparse set|
|$$\Theta_{stor}$$ | StorageSet | Sparse set | All storage set|
|$$\Theta_{um}$$ |UnmetSet | Sparse Set | All unmet load set|
|$$\Theta_{SC}$$ | SupplyCurveSet| Sparse Set | Existing capacity set|
|$$\Theta_{dt^{max}}$$ | ptd_upper_set| Sparse Set | Dispatchable technology generation upper bound set|
|$$\Theta_{it^{max}}$$ | ptiUpperSet| Sparse Set | Intermittent technology generation upper bound set|
|$$\Theta_{ht^{max}}$$ | pth_upper_set| Sparse Set | Hydroelectric generation upper bound set|
|$$\Theta_{hs}$$ | HydroMonthsSet (TODO: rename to season) | Sparse Set | Hydroelectric generation seasonal upper bound set|
|$$\Theta_{ret}$$ | RetSet| Sparse Set | Retirable capacity set|
|$$\Theta_{new}$$ | BuildSet| Sparse Set | Buildable capacity set|
|$$\Theta_{cc}$$ | CapCostSet| Sparse Set | Set of  capacity costs |
|$$\Theta_{cc0}$$ | CapCost0Set| Sparse Set | Set of initial year's capacity costs |
|$$\Theta_{SBFH}$$ |FirstHourStorageBalance_set | Sparse set | First hour storage balance set|
|$$\Theta_{SBH}$$ | StorageBalance_set | Sparse set | (non-first hour) storage balance set|
|$$\Theta_{proc}$$ | ProcurementSet | Sparse set | Set for procurement of operating reserves |
|$$\Theta_{ramp}$$ | RampSet | Sparse set | Set for ramping |
|$$\Theta_{ramp1}$$ | FirstHour_gen_ramp_set | Sparse set | Set for ramping in first hour of each representative day |
|$$\Theta_{ramp23}$$ | Gen_ramp_set | Sparse set | Set for ramping in non-first hour of each representative day |
|$$\Theta_{tra}$$ | TradeSet | Sparse set | Domestic interregional trade set |
|$$\Theta_{tracan}$$ | TradeCanSet | Sparse set | International interregional trade set |
|$$\Theta_{traL^{can}}$$ | TranLimitCanSet | Sparse set | International interregional trade limit set |
|$$\Theta_{traLL}$$ | TranLimitSet | Sparse set | Domestic interregional trade limit set |
|$$\Theta_{traLL^{can}}$$ | TranLineLimitCanSet | Sparse set | International interregional trade line limit set |

### Re-indexed sets
These sets are re-indexed for specific constraints. They are all sub-sets accessed by certain indicies to return the remaining indicies.
|Set    | Code    | Data Type  | Short Description |
|:----- | :------ | :--------- | :---------------- |
|$$\theta^{H2H}_h$$ | H2GenSetByHour | Sparse subset | Set for H2 generation indexed by hour |
|$$\theta^{GSH}_h$$ | GenSetByHour | Sparse subset | Set for generation indexed by hour |
|$$\theta^{SSH}_h$$ | StorageSetByHour | Sparse subset | Set for storage indexed by hour |
|$$\theta^{GDB}_{y,r,h}$$ | GenSetDemandBalance | Sparse subset | Set for generation indexed by y,r,h |
|$$\theta^{SDB}_{y,r,h}$$ | StorageSetDemandBalance | Sparse subset | Set for storage indexed by y,r,h |
|$$\theta^{TDB}_{y,r,h}$$ | TradeSetDemandBalance | Sparse subset | Set for trade indexed by y,r,h |
|$$\theta^{TCDB}_{y,r,h}$$ | TradeCanSetDemandBalance| Sparse subset | Set for international trade indexed by y,r,h |
|$$\theta^{windor}_{y,r,h}$$ |WindSetReserves| Sparse subset | Set for wind generaton for operational reserves indexed by y,r,h |
|$$\theta^{solor}_{y,r,h}$$ | SolarSetReserves| Sparse subset | Set for solar capacity for operational reserves indexed by y,r,h |
|$$\theta^{opres}_{y,r,h}$$ | ProcurementSetReserves| Sparse subset | Set for procurement of operating reserves for operational reserves indexed by y,r,h |
|$$\theta^{scrm}_{y,r,seas}$$ | SupplyCurveRM| Sparse subset | Set for supply curve for reserve margin indexed by y,r,seas |

### Parameters
Note: the existing code shows cost units in MW/MWh instead of GW/GWh; we are aware and just haven't updated the code yet.
| Parameter | Code     | Domain     | Short Description      | Units |
|:-----     | :------  | :---------    | :----------------      | :-----|
|$$YR0$$ | y0 | $$\mathbb{I}$$ | First year of model | unitless |
|$$LOAD_{r,y,h}$$ | Load | $$\mathbb{R}^+_0$$ | Electricity demand | instantaneous GW |
|$$CAP^{exist}_{r,seas,t,s,y}$$ | SupplyCurve | $$\mathbb{R}^+_0$$ | Existing capacity (prescribed or initial) | GW |
|$$SP_{}$$ | SupplyPrice | $$\mathbb{R}^+_0$$ | Fuel + variable O&M price | $/GWh |
|$$ICF_{t,y,r,s,h}$$ | SolWindCapFactor | $$\mathbb{R}^+_0$$ | Intermittent technology maximum capacity factor | fraction |
|$$HCF_{t,y,r,s,h}$$ | HydroCapFactor | $$\mathbb{R}^+_0$$ | Hydroelectric technology maximum capacity factor | fraction |
|$$STORLC$$ | Storagelvl_cost |$$\mathbb{R}^+_0$$  | Cost to hold storage (mimics losses) | $/GWh |
|$$EFF_t$$ | StorageEfficiency | $$\mathbb{R}^+_0$$ | Roundtrip efficiency of storage | fraction |
|$$STOR^{dur}_t$$ | HourstoBuy | $$\mathbb{R}^+_0$$ | Storage duration | hours |
|$$UMLPEN$$ | UnmetLoad_penalty | $$\mathbb{R}^+_0$$ | Unmet load penalty | $/GWh |
|$$WY_y$$ | year_weights | $$\mathbb{I}$$ | number of years represented by a representative year (weight) | years/representative years |
|$$HW_h$$ | Hr_weights | $$\mathbb{I}$$ | number of hours represented by a representative hours(weight) | hours/representative hours |
|$$Idaytq_d$$ | Idaytq | $$\mathbb{I}$$ | number of days representated by a representative day (weight) | days/representative day |
|$$MHD_h$$ | Map_hr_d | $$\mathbb{I}$$ | map representative hour to representative day | unitless |
|$$MHS_h$$ | Map_hr_s |$$\mathbb{I}$$  | map representative hour to season | unitless |
|$$FOMC_{r,t,s}$$ | FOMCost | $$\mathbb{R}^+_0$$ | Fixed O&M cost | $/GW-year |
|$$CC_{t,y,r,s,h}$$ | CapacityCredit | $$\mathbb{R}^+_0$$ | Capacity credit | fraction |
|$$RM_r$$ | ReserveMargin | $$\mathbb{R}^+_0$$ | Reserve margin requirement | fraction |
|$$RUC_{t}$$ | RampUp_Cost | $$\mathbb{R}^+_0$$ | Ramp up cost | $/GW |
|$$RDC_{t}$$ | RampDown_Cost | $$\mathbb{R}^+_0$$ | Ramp down cost | $/GW |
|$$RR_t$$ | RampRate | $$\mathbb{R}^+_0$$ | Max ramp rate | GW |
|$$TRALINLIM_{r,r1,seas,y}$$ | TranLimit | $$\mathbb{R}^+_0$$ | Domestic interregional trade line limit | GW |
|$$TRALIM^{can}_{r^{can},c,y,h}$$ | TranLimitCan | $$\mathbb{R}^+_0$$ |  International interregional trade limit | GW |
|$$TRALINLIM^{can}_{r,r^{can},y,h}$$ | TranLineLimitCan | $$\mathbb{R}^+_0$$ | International interregional trade line limit | GW |
|$$TRAC_{r,r1,y}$$ | TranCost | $$\mathbb{R}^+_0$$ | Transmission hurdle rate (cost) | $/GWh |
|$$TRACC_{r,r^{can},c,y}$$ | TranCostCan | $$\mathbb{R}^+_0$$ | International transmission hurdle rate (cost) | $/GWh |
|$$LL$$ | TransLoss | $$\mathbb{R}^+_0$$ | Transmission line losses from 1 region to another  | fraction |
|$$OPRP_t$$ | RegReservesCost | $$\mathbb{R}^+_0$$ | Cost of operating reserve procurement (TODO: update this in code so it contains all optypes) | $/GWh |
|$$RTUB_{o,t}$$ | ResTechUpperBound | $$\mathbb{R}^+_0$$ | Maximum amount of capacity which can be used to procure operating reserves | fraction |
|$$H2HR$$ | H2_heatrate | $$\mathbb{R}^+_0$$ | Hydrogen heatrate | kg/GWh |
|$$H2PR_{r,seas,t,s,y} $$ | H2Price | $$\mathbb{R}^+_0$$ | Hydrogen fuel price. Mutable parameter. | $/kg |
|$$CAPCL_{r,t,y,s} $$ | capacity_costs_learning | $$\mathbb{R}^+_0$$ | Cost of capacity based on technology learning. Mutable parameter. | $/GW |
|$$CAPC0_{r,t,s} $$ |CapCost_y0 | $$\mathbb{R}^+_0$$ | Initial year's capacity cost to build | $/GW |
|$$LR_t $$ | LearningRate | $$\mathbb{R}^+_0$$ | Learning rate factor | unitless |
|$$SCL_t $$ | SupplyCurve_learning | $$\mathbb{R}^+_0$$ | Learning rate factor | unitless |


### Variables
| Variable  | Code     | Domain     | Short Description      | Units | Switch notes |
|:-----     | :------  | :---------    | :----------------      | :-----| :---------|
|$$STOR^{in}_{t,y,r,s,h}$$ | Storage_inflow | $$\mathbb{R}^+_0$$ | Storage inflow | GW | |
|$$STOR^{out}_{t,y,r,s,h}$$ | Storage_outflow |$$\mathbb{R}^+_0$$  | Storage outflow | GW | |
|$$STOR^{level}_{t,y,r,s,h}$$ | Storage_level |$$\mathbb{R}^+_0$$  | Storage level (state-of-charge) | GWh | |
|$$GEN_{t,y,r,s,h}$$ | Generation | $$\mathbb{R}^+_0$$ | Instantaneous generation | GW | |
|$$UNLOAD_{r,y,h}$$ | Unmet_Load | $$\mathbb{R}^+_0$$ | Unmet load | GW | |
|$$CAP^{tot}_{r,seas,t,s,y}$$ | TotalCapacity | $$\mathbb{R}^+_0$$  | Total capacity | GW | |
|$$CAP^{new}_{r,t,y,s}$$ | CapacityBuilds | $$\mathbb{R}^+_0$$ | New capacity built | GW | Only created if sw_expansion=1 |
|$$CAP^{ret}_{t,y,r,s}$$ | CapacityRetirements | $$\mathbb{R}^+_0$$ | Retirement capacity | GW | Only created if sw_expansion=1|
|$$TRA_{r,r1,y,h}$$ | TradeToFrom | $$\mathbb{R}^+_0$$ | Interregional trade from region $r1$ to region $r$ | GW | Only created if sw_trade=1 |
|$$TRA^{can}_{r,r^{can},y,c,h}$$ | TradeToFromCan | $$\mathbb{R}^+_0$$ | International interregional trade from region $r^{can}$ to region $r$ | GW | Only created if sw_trade=1 |
|$$RAMP^{up}_{t,y,r,s,h}$$ | RampUp | $$\mathbb{R}^+_0$$  | Ramp up (increase in generation for dispatchable cap) | GW | Only created if sw_ramp=1 |
|$$RAMP^{down}_{t,y,r,s,h}$$ | RampDown  | $$\mathbb{R}^+_0$$ | Ramp down (decrease in generation for dispatchable cap) | GW | Only created if sw_ramp=1 |
|$$ORP_{o,t,y,r,s,h}$$ | ReservesProcurement | $$\mathbb{R}^+_0$$ | Operating reserves procurement amount | GW | Only created if sw_reserves=1 |
|$$STOR^{avail}_{t,y,r,s,h}R$$ | AvailStorCap | $$\mathbb{R}^+_0$$ | Available storage capacity to meet the reserve margin | GW | Only created if sw_rm=1 |


## Objective function

Minimize total cost ($)

$$
        \min \mathbf{C_{tot}} =  C_{disp}+ C_{unload} \\
        (+ C_{exp} + C_{fom} \quad if \quad sw\_expansion = 1 )\\ 
        (+ C_{tra} \quad if \quad sw\_trade = 1 )\\
        (+ C_{ramp} \quad if \quad sw\_ramp = 1 )\\
        (+ C_{or}\quad if \quad sw\_reserves = 1 )
        \tag{1}
$$

where:

Dispatch cost: 
$$C_{disp} = 
        \sum_{h \in H | s=MHS_h}{}
        (WD_h \times 
        \sum_{{t,y,r,s} \in \theta^{GSH}_h}{WY_y \times SPR_{r,seas,t,s,y} \times \mathbf{GEN}_{t,y,r,s,h}}\\
        +\sum_{{t,y,r,s} \in \theta^{SSH}_h}{(WY_y \times (0.5 \times SPR_{r,seas,t,s,y} \times (\mathbf{STOR^{in}}_{t,y,r,s,h} + \mathbf{STOR^{out}}_{t,y,r,s,h})}\\
        + (HW_h \times STORLC) \times \mathbf{STOR^{level}}_{t,y,r,s,h}))\\
        +\sum_{{t,y,r,s} \in \theta^{H2SH}_h}{WY_y \times H2PR_{r,seas,t,s,y} \times H2HR \times \mathbf{GEN}_{t,y,r,1,h}}) 
        \tag{2}
$$

Unmet load cost:
$$
        C_{unload} = 
        \sum_{{r,y,h} \in \Theta_{um}}{
        WD_h \times 
        WY_y \times UMLPEN \times \mathbf{UNLOAD}_{r,y,h}}
        \tag{3}
$$

Capacity expansion cost: 
$$        C_{exp} = 
        \sum_{{r,t,y,s} \in \Theta_{cc}}
       ( CAPC0_{r,t,y,s} 
       \\
       \times \left( \frac{
            SCL_t + 0.001 \times (y-YR0) 
            + \sum_{{r,t1,s} \in \Theta_{cc0} | t1 = t}{ \sum_{y1 \in Y | y1<y}{\mathbf{CAP^{new}}_{r,t1,y1,s}}}
            }{SCL_t} \right) ^{-LR_t} 
            \\
            \times \mathbf{CAP^{new}}_{r,t,y,s} )
         \\
        \quad if \quad sw\_learning = 2 
       \tag{4a}
$$
<br />

$$
        C_{exp} = 
        \sum_{{r,t,y,s} \in \Theta_{cc}}{
       CAPCL_{r,t,y,s} \times \mathbf{CAP^{new}}_{r,t,y,s}} \\
       \quad if \quad sw\_learning < 2 
       \tag{4b}
$$

Fixed O\&M cost:
$$
        C_{fom} =
        \sum_{{r,seas,t,s,y} \in \Theta_{sc} | seas=2}{
        WY_y \times FOMC_{r,t,s} \times \mathbf{CAP^{tot}}_{r,seas,t,s,y}}
        \tag{5}
$$

Interregional trade cost:
$$
        C_{tra} =
        \sum_{{r,r1,y,h} \in \Theta_{tra}}{
        WD_h \times WY_y \times TRAC_{r,r1,y} \times \mathbf{TRA}_{r,r1,y,h}}\\
        +
        \sum_{{r,r^{can},y,c,h} \in \Theta_{tracan}}{WD_h \times WY_y \times TRACC_{r,r^{can},c,y} \times 
        \mathbf{TRA^{can}_{r,r^{can},y,c,h}}}
        \tag{6}
$$

Ramping cost:
$$
        C_{ramp} =
        \sum_{{t,y,r,s,h} \in \Theta_{ramp}}{
        WD_h \times WY_y \times 
        (RUC_t \times \mathbf{RAMP^{up}}_{t,y,r,s,h}
        + RDC_t \times \mathbf{RAMP^{up}}_{t,y,r,s,h})}
        \tag{7}
$$

Operating reserve cost:
$$
    C_{op} =
        \sum_{{o,t,y,r,s,h} \in \Theta_{orp}}{
        WD_h \times WY_y \times 
        ORC_t \times
        \mathbf{ORP}_{o,t,y,r,s,h}
        }
        \tag{8}
$$

## Constraints

#### Balance constraints

Demand balance constraint:
$$
    LOAD_{r,y,h} \leq \sum_{{t,s} \in \theta^{GDB}_{y,r,h}}{\mathbf{GEN}_{t,y,r,s,h}}\\
    + \sum_{{t,s} \in \theta^{SDB}_{y,r,h}}{(\mathbf{STOR^{out}}_{t,y,r,s,h} 
    - \mathbf{STOR^{in}}_{t,y,r,s,h})}\\
        + \mathbf{UNLOAD}_{r,y,h}\\
        (+ \sum_{r1 \in \theta^{TDB}_{y,r,h}}{\left(\mathbf{TRA}_{r,r1,y,h} \times (1 - LL) - \mathbf{TRA}_{r1,r,y,h}\right)} 
        \quad if \quad sw\_trade = 1)\\
    (+ \sum_{r_{can},c \in \theta^{TCDB}_{y,r,h}}{(\mathbf{TRA}^{can}_{r,r_{can},y,c,h} 
    \times (1 - LL) - \mathbf{TRA}^{can}_{r_{can},r,y,c,h})} 
    \quad if \quad sw\_trade = 1)\\
        \forall  {r,y,h} \in \Theta_{load}
        \tag{1}
$$

First hour storage balance constraint:
$$
        \mathbf{STOR^{level}}_{t,y,r,s,h} = 
        \mathbf{STOR^{level}}_{t,y,r,s,h+N - 1}\\
        + EFF_t \times \mathbf{STOR^{in}}_{t,y,r,s,h} - \mathbf{STOR^{out}}_{t,y,r,s,h}\\
        \forall {t,y,r,s,h} \in \Theta_{SBFH}
        \tag{2}
$$ 


Storage balance (not first hour) constraint:
$$
        \mathbf{STOR^{level}}_{t,y,r,s,h} = 
        \mathbf{STOR^{level}}_{t,y,r,s,h - 1}\\
        + EFF_t \times \mathbf{STOR^{in}}_{t,y,r,s,h} - \mathbf{STOR^{out}}_{t,y,r,s,h}\\
        \forall {t,y,r,s,h} \in \Theta_{SBH}
        \tag{3}
$$

#### Generation upper bounds

Hydroelectric generation seasonal upper bound:
$$
        \sum_{h \in H_s}{\mathbf{GEN}_{t,y,r,1,h} \times Idaytq_{MHD_{h}}} \leq \mathbf{CAP^{tot}}_{r,s,t,1,y} \times HCF_{r,seas}
        \times SWtHydro_s\\
            \forall {t,y,r,s} \in \Theta_{hs}
            \tag{4}
$$


Dispatchable technology generation upper bound:
$$
        \mathbf{GEN}_{t,y,r,s,h} \\
        (+ \sum_{rt \in RT}{\mathbf{OPRP}_{rt,t,y,r,s,h}} 
        \quad if \quad sw\_rm = 1)\\
        \leq \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y} \times HW_h\\
        \forall {t,y,r,s,h} \in \Theta_{dt^{max}}
        \tag{5}
$$


Hydroelectric technology generation upper bound:
$$
        \mathbf{GEN}_{t,y,r,s,h} \\
        (+ \sum_{rt \in RT}{\mathbf{OPRP}_{rt,t,y,r,s,h}}
        \quad if \quad sw\_rm = 1)\\
        \leq \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y} \times HCF_{r,MHS_h} \times HW_h\\
        \forall {t,y,r,s,h} \in \Theta_{ht^{max}}
        \tag{6}
$$


Intermittent technology upper bound:
$$
        \mathbf{GEN}_{t,y,r,s,h} \\
        (+ \sum_{rt \in RT}{\mathbf{OPRP}_{rt,t,y,r,s,h}}
        \quad if \quad sw\_rm = 1)\\
        \leq \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y} \times ICF_{t,y,r,s,h} \times HW_h\\
        \forall {t,y,r,s,h} \in \Theta_{it^{max}}
        \tag{7}
$$


Storage technology inflow upper bound:
$$
        \mathbf{STOR^{in}}_{t,y,r,s,h} + 
        \leq \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y} \times HW_h\\
        \forall {t,y,r,s,h} \in \Theta_{stor}
        \tag{8}
$$ 

Storage technology outflow upper bound:
$$
        \mathbf{STOR^{out}}_{t,y,r,s,h} \\
        (+\sum_{rt \in RT}{\mathbf{OPRP}_{rt,t,y,r,s,h}}
        \quad if \quad sw\_rm = 1)\\
        \leq \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y} \times HW_h\\
        \forall {t,y,r,s,h} \in \Theta_{stor}
        \tag{9}
$$


Storage technology level upper bound:
$$
        \mathbf{STOR^{level}}_{t,y,r,s,h} 
        \leq \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y} \times STOR^{dur}_t\\
        \forall {t,y,r,s,h} \in \Theta_{stor}
        \tag{10}
$$

#### Capacity expansion

Total capacity balance:
$$
        \mathbf{CAP^{tot}}_{r,seas,t,s,y}
        = CAP^{exist}_{r,seas,t,s,y} \\
        (+ \sum_{cy \in Y \leq y}{\mathbf{CAP^{new}}_{r,t,cy,s}} 
        \quad if \quad sw\_expansion = 1)\\
        (+ \sum_{cy \in Y \leq y}{\mathbf{CAP^{ret}}_{t,cy,r,s}} 
        \quad if \quad sw\_expansion = 1)\\
        \forall {r,seas,t,s,y} \in \Theta_{SC}
        \tag{11}
$$


Capacity retirement upper bound:
$$
        \mathbf{CAP^{ret}}_{t,y,r,s} \leq
        CAP^{exist}_{r,2,t,s,y} +
        \sum_{cy \in Y < y}{\mathbf{CAP^{new}}_{r,t,cy,s}} -
        \sum_{cy \in Y < y}{\mathbf{CAP^{ret}}_{t,cy,r,s}} \\
        \forall {t,y,r,s} \in \Theta_{ret} \\
        \quad if \quad sw\_expansion = 1 \\
        \tag{12}
$$


#### Trade


International interregional trade line capacity upper bound:
$$
        \sum_{c}{\mathbf{TRA^{can}}_{r,r^{can},y,c,h}} \leq
        TRALINLIM^{can}_{r,r^{can},y,h} * HW_h \\
        \forall {r,r^{can},y,h} \in \Theta_{traLL^{can}} \\
        \quad if \quad sw\_trade = 1\\
        \tag{13}
$$

International interregional trade resource capacity upper bound:
$$
        \sum_{r}{\mathbf{TRA^{can}}_{r,r^{can},y,c,h}} \leq
        TRALIM^{can}_{r^{can},c,y,h} * HW_h \\
        \forall {r,r^{can},y,h} \in \Theta_{traL^{can}} \\
        \quad if \quad sw\_trade = 1\\
        \tag{14}
$$ 


Domestic interregional trade line capacity upper bound:
$$
        \mathbf{TRA}_{r,r1,y,h} \leq
        TRALINLIM_{r,r1,MHS_h,y} * HW_h \\
        \forall {r,r1,y,h} \in \Theta_{traLL} \\
        \quad if \quad sw\_trade = 1\\
        \tag{15}
$$

#### Reserve Margin


Reserve margin requirement constraint NEED TO FIX THIS ONE:
$$
        LOAD_{r,y,h} \times
        (1 + RM_r ) \leq
        HW_h \times \\
        \sum_{{t,s} \in \theta^{scrm}_{y,r,MHS_h}}{CC_{t,y,r,s,h} \times (\mathbf{STOR^{avail}}_{t,y,r,s,h} + \mathbf{CAP^{tot}_{r,MHS_h,t,s,y}})}\\
        \forall {r,y,h} \in \Theta_{load}\\
        \quad if \quad sw\_rm = 1\\
        \tag{16}
$$


Constraint to ensure available storage capacity to meet RM <= power cap, upper bound:
$$
    \mathbf{STOR^{avail}}_{t,y,r,s,h} \leq    \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y}\\
        \forall {t,y,r,s,h} \in \Theta_{stor}\\
        \quad if \quad sw\_rm = 1\\
        \tag{17}
$$


Constraint to ensure available storage capacity to meet RM <= existing storage level, upper bound:
$$
    \mathbf{STOR^{avail}}_{t,y,r,s,h} \leq    
    \mathbf{STOR^{level}}_{t,y,r,s,h}\\
        \forall {t,y,r,s,h} \in \Theta_{stor}\\
        \quad if \quad sw\_rm = 1\\
        \tag{18}
$$

#### Ramping


First hour ramping balance constraint:
$$
    \mathbf{GEN}_{t,y,r,s,h} =    \mathbf{GEN}_{t,y,r,s,h+N-1} + \mathbf{RAMP^{up}}_{t,y,r,s,h} - \mathbf{RAMP^{down}}_{t,y,r,s,h}\\
    \forall {t,y,r,s,h} \in \Theta_{ramp1} \\
        \quad if \quad sw\_ramp = 1\\
    \tag{19}
$$

Ramping balance (not first hour) constraint:
$$
    \mathbf{GEN}_{t,y,r,s,h} =    \mathbf{GEN}_{t,y,r,s,h-1} + \mathbf{RAMP^{up}}_{t,y,r,s,h} - \mathbf{RAMP^{down}}_{t,y,r,s,h}\\
    \forall {t,y,r,s,h} \in \Theta_{ramp23} \\
        \quad if \quad sw\_ramp = 1\\
    \tag{20}
$$


Ramp up upper bound:
$$
    \mathbf{RAMP^{up}}_{t,y,r,s,h} \leq   
    HW_h \times RR_t \times
    \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y}\\
    \forall {t,y,r,s,h} \in \Theta_{ramp} \\
        \quad if \quad sw\_ramp = 1\\
    \tag{21}
$$


Ramp down upper bound:
$$
    \mathbf{RAMP^{down}}_{t,y,r,s,h} \leq   
    HW_h \times RR_t \times
    \mathbf{CAP^{tot}}_{r,MHS_h,t,s,y}\\
    \forall {t,y,r,s,h} \in \Theta_{ramp} \\
        \quad if \quad sw\_ramp = 1\\
    \tag{22}
$$

#### Operating reserves

Spinning reserve requirement constraint. 3\% of load required:
$$
    0.03 \times LOAD_{r,y,h} \leq 
    \sum_{{t,s} \in \theta^{opres}_{1,r,y,h}}{\mathbf{ORP}_{1,t,y,r,s,h}}\\
    \forall {r,y,h} \in \Theta_{load} \\
        \quad if \quad sw\_reserves = 1\\
    \tag{23}
$$

Regulation reserve requirement constraint. 1\% of load + 0.5\% of wind generation + 0.3\% of solar capacity required:
$$
    0.01 \times LOAD_{r,y,h}\\
    + 0.005 \times \sum_{{t^w,s} \in \theta^{windor}_{y,r,h}}{\mathbf{GEN}_{t^w,y,r,s,h}} \\
    + 0.003 \times HW_h \times \sum_{{t^s,s} \in \theta^{solor}_{y,r,h}}{\mathbf{CAP^{tot}}_{r,MHS_h,t^s,s,y}}\\
    \leq
    \sum_{{t,s} \in \theta^{opres}_{2,r,y,h}}{\mathbf{ORP}_{2,t,y,r,s,h}}\\
    \forall {r,y,h} \in \Theta_{load} \\
        \quad if \quad sw\_reserves = 1\\
    \tag{24}
$$


Flexibility reserve requirement constraint. 10\% of wind generation + 4\% of solar capacity required:
$$
    0.1 \times \sum_{{t^w,s} \in \theta^{windor}_{y,r,h}}{\mathbf{GEN}_{t^w,y,r,s,h}} \\
    + 0.04 \times HW_h \times \sum_{{t^s,s} \in \theta^{solor}_{y,r,h}}{\mathbf{CAP^{tot}}_{r,MHS_h,t^s,s,y}}\\
    \leq
    \sum_{{t,s} \in \theta^{opres}_{3,r,y,h}}{\mathbf{ORP}_{3,t,y,r,s,h}}\\
    \forall {r,y,h} \in \Theta_{load} \\
        \quad if \quad sw\_reserves = 1\\
    \tag{25}
$$

Operating reserve procurement upper bound:
$$
    \mathbf{ORP}_{o,t,y,r,s,h}
    \leq
    RTUB_{o,t} \times HW_h \times
    \mathbf{CAP^{tot}}_{r,MHS_h,t^s,s,y}\\
    \forall {o,t,y,r,s,h} \in \Theta_{proc} \\
    \quad if \quad sw\_reserves = 1\\
    \tag{26}
$$


# Code Documentation

[Code Documentation](/docs/README.md)