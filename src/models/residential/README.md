# Table of Contents

- [Table of Contents](#table-of-contents)
- [Model Formulation](#model-formulation)
    - [Summary](#summary)
    - [Prepare Data](#prepare-data)
    - [Updating Function](#updating-function)
    - [Nomenclature Table](#nomenclature-table)
        - [Sets](#sets)
        - [Parameters](#parameters)
        - [Variables](#variables)
    - [Model Use](#model-use)
    - [Code Documentation](#code-documentation)

# Model Formulation

## Summary

The residential model calculates updated values for energy consumption based on new input prices. It takes in the new prices from a Pyomo Parameter and calculates the new consumption values. Base values are automatically loaded in from the input files for the calculations, but base "Load" values can be used instead if given to the module. Then, it returns a Pyomo Block with a "Load" variable and constraints that bind the variable to the new consumption values. This Block can be inserted into other Pyomo models in the other modules.

## Prepare Data

The module is set to take in a Pyomo Parameter of prices that is indexed by [region, year, hour]. The regions can be any subset of integers 1 to 25. The years can be any subset of integers 2023 to 2050. The hours are currently only programmed to work with seasonal data (1 to 4) or a custom subset that is valued 1 to 96.

## Updating Function 

The updating function takes in base values from the input files. The original equations used the term "Consumption," but we will use the term "Load" to match the other modules that call upon this one.

The updating function is as follows for each region ($r$), year ($y$), and hour ($h$):

$$ NewLoad_{r,y,h} = BaseLoad_{r,y,h} * PriceIndex_{r,y,h} * IncomeIndex_{r,y,h} * LongTermTrend_{r,y}
$$

The indexes are defined as:

$$
PriceIndex_{r,y,h} = \left(\frac{Price_{r,y,h}}{BasePrice_{r,y,h}}\right)^{PriceElasticity_{r,y}}
$$

$$
IncomeIndex_{r,y,h} = \left(\frac{Income_{r,y,h}}{Income_{r,baseYear,h}}\right)^{IncomeElasticity_{r,y}}
$$

$$
LongTermTrend_{r,y} = 1 + \left(\frac{y-LastModelYear}{LastModelYear - BaseYear}\right) * \left({TrendGrowthRate_{r,y}+1}\right)^{LastModelYear - BaseYear}
$$

## Nomenclature Table

### Sets
|Set    | Code    | Data Type  | Short Description |
|:----- | :------ | :--------- | :---------------- |
|$\Theta_{Price}$  | price_set       | Sparse Set | $(r,y,h)$ or $(r,s,pt,steps,y)$ values for given updating prices
|$\Theta_{Load}$ | load_set | Sparse Set | $(r,y,h)$ values for base loads

### Parameters
| Parameter | Code     | Data Type     | Short Description      | Index |
|:-----     | :------  | :---------    | :----------------      | :-----|
|$BaseLoad$ | loads[BaseLoads] | DataFrame | The base values for Load | $(r,y,h)$ |
|$BasePrice$ | prices[BaseSupplyPrices] or prices[BaseDualPrices}] | DataFrame | The base values for price | $(r,s,pt,steps,y)\in\Theta_{Price}$ or $(r,y,h)\in\Theta_{Price}$ |
|$PriceElasticity$ | p_elas | DataFrame | Price elasticities | (r, y) |
|$Income$ | income | DataFrame | Income values | $(r,y,h)\in\Theta_{Load}$ |
$IncomeElasticity$ | i_elas | DataFrame | Income elasticities | (r,y) |
|$LastModelYear$ | LastMYr | int | Last Year in model data (2050) | |
|$BaseYear$ | baseyear | int | The year used for base values | |
|$TrendGrowthRate$ | TrendGR | DataFrame | Long Term Trend values | (r,y) |



### Variables
| Variable  | Code     | Data Type     | Short Description      | Index |
|:-----     | :------  | :---------    | :----------------      | :-----|
|$Price$ | avgPrices or newPrices| DataFrame | Updating prices | $(r,s,pt,steps,y)\in\Theta_{Price}$ or $(r,y,h)\in\Theta_{Price}$ |
|$NewLoad$ | newLoad or Load| DataFrame | Values for newly calculated Load | $(r,y,h)\in\Theta_{Load}$

## Model Use

The purpose of this module is to calculate a value for $NewLoad$ based on the new values for $Price$. To use this model, first create an instance of the residentialModule. Then, you will need to format the new prices into indexed Pyomo Parameters. These prices and their accompanying indexes will be sent into the make_block function to perform the calculations. The function will return a Pyomo Block with a $Load$ variable and Pyomo Constraints forcing the variable to be equal to the updated values calculated in the function. An example of its use is as follows:

```{Python}
import pyomo.environ as pyo
import residential.py as residential

price_data = 'some load or creation of prices indexed by (r,y,h)'

model = pyo.ConcreteModel()
model.price_index = pyo.Set(initialize=price_data.index)
model.prices = pyo.Param(model.price_index, initialize=price_data)

res = residential.residentialModule()
model.updated_load_block = res.make_block(model.prices,price_data.index)
```
## Code Documentation

[Code Documentation](/docs/README.md)
