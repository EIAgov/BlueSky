# Table of Contents

- [Table of Contents](#table-of-contents)
- [Introduction](#introduction)
- [Preparing data](#preparing-data)
    - [Regions regions.csv](#regions-regionscsv)
    - [Hubs hubs.csv](#hubs-hubscsv)
    - [Transportation Arcs transportation_arcs.csv](#transportation-arcs-transportation_arcscsv)
    - [Parameters parameter_list.xlsx](#parameters-parameter_listxlsx)
- [Loading Data](#loading-data)
- [Creating a Grid](#creating-a-grid)
    - [Grid Methods](#grid-methods)
        - [collapseregion_name:str](#collapseregion_namestr)
        - [collapse_leveldepth:int](#collapse_leveldepthint)
- [Model Overview](#model-overview)
    - [Nomenclature Table](#nomenclature-table)
        - [Sets](#sets)
        - [Parameters](#parameters)
        - [Variables](#variables)
    - [Constraints](#constraints)
        - [Capacity Constraints](#capacity-constraints)
        - [Transportation Capacity Constraints](#transportation-capacity-constraints)
        - [Storage Constraint](#storage-constraint)
        - [Demand Constraint](#demand-constraint)
    - [Objective Function](#objective-function)
        - [Production Cost](#production-cost)
        - [Production Capacity Expansion Cost](#production-capacity-expansion-cost)
        - [Transportation Cost](#transportation-cost)
        - [Transportation Capacity Expansion Cost](#transportation-capacity-expansion-cost)
- [Code Documentation](#code-documentation)

# Introduction

**The Hydrogen model is the first step to a general model framework for any energy system represented by regions, hubs, and transportation arcs.** It is provided with data and functions specific to Hydrogen production and distribution, but aims to eventually be agnostic to the energy carrier being modeled. 

The model centers on an object type called Grid, which creates a collection of objects called Region, Hub, Arc, and Registry, that function together as a unit to allow users to manipulate the model for simplification purposes interactively. This allows a user to input data at the most granular level, and then customize their run for the resolution they desire. 

When the process is complete, they can build a Model object that performs the optimization and outputs results.

# Preparing data

Data for a run must first be prepared in the following files. **For each file, there is a specific format that must be followed:**

### Regions (regions.csv)
  
**This file stores the regionality settings for the grid you are creating.** The CSV should flow from top level regions in the first column, and subregions must be entered in the following columns. Mixed depths are supported, so you can have a blank entry in a subregion column, and the build will look to the subsequent columns to find a subregion. Any region that appears in a column to the right of a region in another column, on the same row, will be treated as a subregion contained in its parent region.

For example, the following table would generate the regionality in the below diagrams:

|  region  |  subregion  | subregion   |  data  |  parameters|
| ---      | ---         | ---         |  ---   |     ---    |
|  A       |             |             |        |   A data   |
|  A       |  A1         |             |        |   A1 data  |
|  A       |  A1         |     A1a     |        |   A1a data |
|  A       |  A2         |             |        |  A2 data   |
|  A       |  A2         |     A2a     |        |  A2a data  |
|  A       |  A2         |     A2b     |        |    A2b data|
|  B       |             |             |        |    B data  |
|  B       |             |     Ba      |        |  Ba data   |

This would append all the rows after the column labeled data to the rightmost region that appears in that row. You can create any parameters you want, the model can freely be expanded upon. 

![Alt](region_sets.png "Set view") ![Alt](tree.png "Tree view")

A few final notes on the *regions* data formatting:
* **IMPORTANT NOTE: region names must be *unique***. If this is a problem (for example, where all region types use numeric-naming) you can hyphenate the names or append a prefix depending on which column it is in.

* The regions included in the standard version are top-level regions, Census Regions, and NERC regions (with NERC regions shoehorned into Census regions)

* Only Census and NERC Regions have data. If you aggregate to top-level regions, they aggregate the data from their subregions to acquire their own data. Region data includes electricity and gas costs, and demand.

### Hubs (hubs.csv)
  
**The fundamental unit of production is the hub.** This CSV simply lists the hubs, what region they are located in, and the rest of the columns are parameter / data fields that get attached to that hub. 

In the first column, insert the names of the hubs, and in the second column, the name of the region. Every column afterwards should contain hub-specific parameters. For example, production capacity, geographic coordinates etc. Currently, hubs are set to be 1 hub per region, for Census Regions and NERC regions. Higher level regions have no hubs of their own.

### Transportation Arcs (transportation_arcs.csv)
  
Transportation of the resource in the model follows entities called transportation arcs. These are connections between hubs, and the data format is a CSV file where the arcs are represented by two columns - 'origin' and 'destination'. All other columns are for data / parameters you want to attach to the arc. Right now that is just capacity and cost.

### Parameters (parameter_list.xlsx)

This is an excel file with 4 sheets. One sheet for region, one for hub, and for arc, and one for global. The purose of this file is to list all the parameters and their properties.

Right now, the two properties for given parameters are 'aggregation_type' and 'default_value'
* *aggregation_type*: can be either summable or meanable (but functionality should be expanded) so that if you load data, and then decide to do a run where you aggregate regions, it knows how to combine the data during aggregation. Meanable quantities get averaged, and summable get summed. So for example, capacities should be summed, and costs are averaged.

* *default_value*: the value that is set if none are specified. It is useful to set it to either zero of inf so that functionally if you do not specify for some reason, it defaults to an infeasible value.


# Loading Data

(this is going to be different in Jeff's refactored code, but it should be easy to fill out later)

# Creating a Grid

**The fundamental structure of the model is an object called a Grid.** Grids coordinates actions between Region, Hub, and Arc, and Registry, allowing you to manipulate data that the model reads. It also visualizes your network.

When a Grid object is created, the regions in the data file are instantiated as a collection of Region objects, and the data for each Region is appended to the object. Hubs are created as independent objects that are assigned a home Region. Arcs are instantiated with references to their origin and destination Hub objects, and the Hub objects record the Arcs they are connected to.

## Grid Methods

The Grid class has a large number of methods that can be called. The main ones a user might interact with (currently) are the aggregation methods: collapse() and collapse_level()

### collapse(region_name:str) 

takes the name of a region as an argument and makes that region absorb all its subregions (and they absorb their subregions etc) so that the region becomes a leaf in the tree hierarchy. For any data entries the region has no field for, it will aggregate the corresponding entries in the subregions and acuqire that value for the region. Currently there are two aggregation methods that the user inputs in the parameter_list.xlsx input file for each data field - "summable" and "meanable". The summable fields get added when aggregating (ie. demand, population etc) and the meanable quantities get averaged (ie. prices, weather conditions etc)

A user who wants to model only some regions in detail and wants a coarser representation of other regions to reduce complexity could use this feature to simplify a grid. For example, see the following grid:

![Alt](grid.png "the set as input")

If the user runs the following method...
```python
grid.collapse('South')
``` 

... they create a grid with the souther region collapsed as vizualized in the network.

![Alt](south_collapse.png "southern region collapsed")


### collapse_level(depth:int)

This method takes the desired depth of region nesting, and collapses all regions at that depth. If you have 4 levels of region-nesting, say Region, Census Region, State, County, and you want to collapse the data to only two levels of depth, you'd use collapse_level. For example, our regionality in the image above:

![Alt](grid.png "the set as input")

would become the following after running ```collapse_level```
```python
grid.collapse_level(2)
```
![Alt](collapse_level_2.png "level 2 collapse")

Collapsing futher to the highest nesting level results in a more "sparse" grid object.
```python
grid.collapse_level(1)
```
![Alt](collapse_level_1.png "level 1 collapse") 

# Model Overview

The Hydrogen Model is a cost minimization linear program that seeks to minimize total cost given the constraints on production capacity, demand, and transportation.

Demand is either exogenous in integrated mode, or included in the input files as a base parameter with changes over time governed by a function in standalone mode.

Demand is specific to regions and the hubs in a region must satisfy the given demand for each time index. Hubs may not exceed their production capacity, but capacity can be expanded to meet demand in subsequent years. In addition, production can be transported along transportation arcs, subject to transportation constraints, incurring a cost per unit transported.

When the model runs, it returns the dual of the demand constraints, giving a regional hydrogen price.

## Nomenclature Table


### Sets

|Name|Symbol|Code|Description
|---|---|---|:--| 
|Hubs|$h\in H$|hubs|The names of all the hubs (str)
|Arcs|$a \in A$|arcs|The names of all the arcs, which are tuples of hubs, in the format (origin hub, destination hub)
|Regions|$r\in R$|regions| The names of all the regions for which demand is being calculated (str)
|Technologies|$t\in T$|technology|The names of technology types for production (str)
|Year|$y\in Y$|year|The year index (RangeSet)




### Parameters
|Name|Symbol|Code|Units|Description|
|---|---|---|---|:--|
|Production Capacity|$PCAP_{h,y}$|capacity|kg H2/year| the base production capacity for each hub and technology type (index: hubs,technology)
|Electricity Consumption Rate|$ELCR_t$|electricity_consumption_rate|GWh/kg| The base electricity_consumption_rate for producing a unit of fuel (index: technology)
|Gas Price|$PGAS_{r,y}$|gas price|$/mmBtu|price of gas in $/mmBtu (index: regions, year)
|Hydrogen Demand|$DMND_{r,y}$|demand|kg H2|hydrogen demand in kg (index: regions, year)
|Electricity Price|$PELE_{r,y}$|electricity_price|$/KWh|price of electricity in $/GWh (index: regions, year)
|Production Cost|$PCST_{h,t,y}$|cost|$/kg|cost to produce 1 kg of hydrogen (index:hubs, technology, year)
|Transportation Capacity|$TCAP_{a}$|transportation_capacity|kg H2/year|
|Transportation Cost|$TCST_{a,y}$||$/kg H2|
|Capacity Expansion Cost|$PCXC_{r,t,y}$||$/ kg H2/year|
|Transportation Capacity Expansion Cost|$TCXC_{a,y}$||$/kg H2/year|


### Variables

|Name|Symbol|Domain|Code|Units|Description
|---|---|---|---|---|:--|
|Hydrogen Production Volume|$\boldsymbol{PVOL}_{h,t,y}$ |$\mathbb R^{+}_{0}$|h2_volume|kg H2|hydrogen production in kg (index: hubs, technology, year)
|Transportation Volume|$\boldsymbol{TVOL}_{a,y}$|$\mathbb R^{+}_{0}$|transportation_volume|kg H2| h2 transported along arc in kg (index: arcs, year)
|Production Capacity Expansion|$\boldsymbol{PCEX}_{h,t,y}$|$\mathbb R^{+}_{0}$|capacity_expansion|kg H2/year| production capacity expansion in kg (index: hubs, technology, year)
|Transportation Capacity Expansion|$\boldsymbol{TCEX}_{a,y}$|$\mathbb R^{+}_{0}$|trans_capacity_expansion|kg H2/year| transportation capacity expansion along arc (index: arcs, year)

## Constraints

Constraints in the model are described as follows

### Capacity Constraints 

Denoted capacity_constraint in the model.

notation:

$H:$ the set of all hubs

$Y:$ the set of years

$T:$ set of technology

$\boldsymbol{PVOL}_{h,t,y}:$ volume of H2 produced at hub h by technology t in year y (kg H2)

$PCAP_{h,t}:$ base production capacity of H2 at hub h, by technology t (kg H2/year)

$\boldsymbol{PCEX}_{h,t,y}:$ the capacity expansion at hub h, for technology t, in year y. (kg H2/year)

$s:$ lifespan of capacity expansion in years (tbd)

--

The Constraint expression for the capacity constraints are by hub, and take the following form:

$\forall y \in Y,\forall h \in H, \forall t \in T:$

$$\boldsymbol{PVOL}_{h,t,y} \leq PCAP_{h,t} + \sum_{
\begin{matrix}
v \in Y\\
y - s \leq v < y
\end{matrix}
}\boldsymbol{PCEX}_{h,t,v}$$

### Transportation Capacity Constraints

not explicitly stored as a parameter, but as data attached to individual arcs (this should be fixed)

notation:

$A:$ set of arcs

$TCAP_{a}:$ transportation capacity of arc a

$\boldsymbol{TEXP}_{a,y}:$ transportation capacity expansion for arc a in year y

$\boldsymbol{TVOL}_{a,y}:$ transportation volume for arc a in year y

--

$\forall y \in Y, \forall a \in A:$

$$\boldsymbol{TVOL}_{a,y} \leq TCAP_{a} + 
\sum_{
\begin{matrix}
v \in Y\\
v < y
\end{matrix}
}\boldsymbol{TEXP}_{a,v}$$

### Storage Constraint
Not implemented
### Demand Constraint

notation:

$H^{r}:$ the subset of hubs that are in region r

$\boldsymbol{TVOL}_{a,y}:$ transportiation_volume along arc a in year y

$h^{out}:$ the subset of arcs a that are outbound from hub h

$h^{in}:$ the suset of arcs a that are inbound to hub h

$\boldsymbol{PVOL}_{h,t,y}:$ the volume of H2 produced at hub h by technology t in year y

$R:$ the set of regions which contain hubs.

$DMND_{r,y}:$ the demand in region r and year y 

--

The constraints are by region, which is how demand is processed for the model. The demand must be met for each region in each year. The constraints add up all production in regions with hubs present, plus the net transportation flow for all of them. Mathematically:

$\forall r \in R, \forall y \in Y:$  

$$\left(\sum_{
\begin{matrix}    
    h \in H^{r}\\
    t\in T
\end{matrix}    
    } \boldsymbol{PVOL}_{h,t,y}\right) + \sum_{h \in H_{r}} \left( \sum_{a \in h_{in}} \boldsymbol{TVOL}_{a,y} - \sum_{a \in h_{out}} \boldsymbol{TVOL}_{a,y} \right)
    = DMND_{r,y}$$


## Objective Function
The Objective function is a total cost expression that can be divided into distinct parts representing production costs, transportation costs, production capacity expansion costs, and transportation capacity expansion costs.

The form of the the Objective function is:

$$TotalCost = ProductionCost + ProductionCapacityExpansionCost+TransportationCost+TransportationCapacityExpansionCost$$

the components are explained below.

### Production Cost

Production cost is a variable cost associated with hydrogen production. In the code, it is initialized as a function, get_production_cost, which should be modifiable with access to all data in the model itself as well as all data stored in the grid. This is open-ended. For the current simplified version, it is set to just energy consumption costs.

currently, Production cost uses the below formula.\
\
Letting $\Theta = H\times T \times Y$ and $r(h) =$ the region hub $h$ is in, Production Cost is:


$$ProductionCost = \sum_{\{h,t,y\}\in \Theta} \boldsymbol{PVOL}_{h,t,y}\cdot PCST_{h,t,y}$$ 

in the current iteration.


### Production Capacity Expansion Cost

Production Capacity Expansion cost is the levelized annual financing cost of building production capacity. It is also the product of many components from preprocessor data, filled in by a function and treated as a black box. For that reason, it is simply represented by the parameter $PCXC_{r,t}$ and oursourced to a function for the details.

Letting $\Theta = H\times T \times Y$ and $r(h) = $ the region hub $h$ is in, Production Capacity Expansion Cost is:

$$ProductionCapacityExpansionCost = \sum_{\{h,t,y\}\in \Theta} \boldsymbol{PCEX}_{h,t,y}\cdot PCXC_{r(h),t} $$

### Transportation Cost

Let $TCST_{a,y}$ be the Transportation cost per kg for Arc a in year $y$. Then we have:

$$TransportationCost = \sum_{a \in A, y\in Y}\boldsymbol{TVOL}_{a,y}\cdot TCST_{a,y}$$

The values going into $TCST$ are left as a black box that a function fills out, with the details of the calculation left for later.

### Transportation Capacity Expansion Cost

Let $TCXC_{a,y}$ be the transportation capacity expansion cost per kg H2/year expansion

$$TransportationCapacityExpansionCost = \sum_{a\in A, y\in Y}TCEX_{a,y}\cdot TCXC_{a,y}$$

the details of transportation capacity expansion cost are glossed over, but should depend on the distance and terrain in between the origin and destination hubs, which isn't fully known. 

# Code Documentation

[Code Documentation](/docs/README.md)
