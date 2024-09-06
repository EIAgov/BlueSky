# src.models.residential package

## Subpackages

* [src.models.residential.scripts package](src.models.residential.scripts.md)
  * [Submodules](src.models.residential.scripts.md#submodules)
  * [src.models.residential.scripts.residential module](src.models.residential.scripts.md#module-src.models.residential.scripts.residential)
    * [`residentialModule`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule)
      * [`residentialModule.baseYear`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule.baseYear)
      * [`residentialModule.hr_map`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule.hr_map)
      * [`residentialModule.loads`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule.loads)
      * [`residentialModule.make_block()`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule.make_block)
      * [`residentialModule.prices`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule.prices)
      * [`residentialModule.sensitivity()`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule.sensitivity)
      * [`residentialModule.update_load()`](src.models.residential.scripts.md#src.models.residential.scripts.residential.residentialModule.update_load)
  * [src.models.residential.scripts.utilities module](src.models.residential.scripts.md#module-src.models.residential.scripts.utilities)
    * [`base_price()`](src.models.residential.scripts.md#src.models.residential.scripts.utilities.base_price)
    * [`scale_load()`](src.models.residential.scripts.md#src.models.residential.scripts.utilities.scale_load)
  * [Module contents](src.models.residential.scripts.md#module-src.models.residential.scripts)

## Submodules

## src.models.residential.residential_block module

The purpose of this module is to buid and hold a persistent residential model in ConcreteModel format
This block can be updated/interrogated to update pricing & load in an iterative solve
Or can be passed on as a block to a unified model

<!-- !! processed by numpydoc !! -->

### *class* src.models.residential.residential_block.ResidentialBlock(\*args, \*\*kwds)

Bases: `ConcreteModel`

<!-- !! processed by numpydoc !! -->

#### poll_load()

A quick pull of the parameter data for use in iterative solving

<!-- !! processed by numpydoc !! -->

#### update_load(prices, price_index)

a quick relay to the residential module updating routines

<!-- !! processed by numpydoc !! -->

## Module contents

<!-- !! processed by numpydoc !! -->
