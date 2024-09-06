# src.models.hydrogen.model package

## Submodules

## src.models.hydrogen.model.actions module

A sequencer for actions in the model.
This may change up a bit, but it is a place to assert control of the execution sequence for now

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.actions.build_grid(grid_data: [GridData](src.models.hydrogen.network.md#src.models.hydrogen.network.grid_data.GridData))

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.actions.build_model(grid: [Grid](src.models.hydrogen.network.md#src.models.hydrogen.network.grid.Grid))

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.actions.load_data(path_to_input: Path)

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.actions.quick_summary(solved_hm: [H2Model](#src.models.hydrogen.model.h2_model.H2Model))

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.actions.solve_it(hm: [H2Model](#src.models.hydrogen.model.h2_model.H2Model))

<!-- !! processed by numpydoc !! -->

## src.models.hydrogen.model.h2_model module

<!-- !! processed by numpydoc !! -->

### *class* src.models.hydrogen.model.h2_model.H2Model(\*args, \*\*kwds)

Bases: `ConcreteModel`

* **Attributes:**
  `active`
  : Return the active attribute

  `ctype`
  : Return the class type for this component

  `local_name`
  : Get the component name only within the context of the immediate parent container.

  `name`
  : Get the fully qualified component name.

### Methods

| `activate`()                                                                             | Set the active attribute to True                                                                                                |
|------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| `active_blocks`(\*args, \*\*kwargs)                                                      | DEPRECATED.                                                                                                                     |
| `active_component_data`(\*args, \*\*kwargs)                                              | DEPRECATED.                                                                                                                     |
| `active_components`(\*args, \*\*kwargs)                                                  | DEPRECATED.                                                                                                                     |
| `add_component`(name, val)                                                               | Add a component 'name' to the block.                                                                                            |
| `all_blocks`(\*args, \*\*kwargs)                                                         | DEPRECATED.                                                                                                                     |
| `all_component_data`(\*args, \*\*kwargs)                                                 | DEPRECATED.                                                                                                                     |
| `all_components`(\*args, \*\*kwargs)                                                     | DEPRECATED.                                                                                                                     |
| `block_data_objects`([active, sort, ...])                                                | Returns this block and any matching sub-blocks.                                                                                 |
| `clear_suffix_value`(suffix_or_name[, expand])                                           | Set the suffix value for this component data                                                                                    |
| `clone`([memo])                                                                          | TODO                                                                                                                            |
| `cname`(\*args, \*\*kwds)                                                                | DEPRECATED.                                                                                                                     |
| `collect_ctypes`([active, descend_into])                                                 | Count all component types stored on or under this block.                                                                        |
| `component`(name_or_object)                                                              | Return a child component of this block.                                                                                         |
| `component_data_iterindex`([ctype, active, ...])                                         | DEPRECATED.                                                                                                                     |
| `component_data_objects`([ctype, active, ...])                                           | Return a generator that iterates through the component data objects for all components in a block.                              |
| `component_map`([ctype, active, sort])                                                   | Returns a PseudoMap of the components in this block.                                                                            |
| `component_objects`([ctype, active, sort, ...])                                          | Return a generator that iterates through the component objects in a block.                                                      |
| `compute_statistics`([active])                                                           | Compute model statistics                                                                                                        |
| `construct`([data])                                                                      | Initialize the block                                                                                                            |
| `contains_component`(ctype)                                                              | Return True if the component type is in \_ctypes and .                                                                          |
| `create_instance`([filename, data, name, ...])                                           | Create a concrete instance of an abstract model, possibly using data read in from a file.                                       |
| `deactivate`()                                                                           | Set the active attribute to False                                                                                               |
| `del_component`(name_or_object)                                                          | Delete a component from this block.                                                                                             |
| `dim`()                                                                                  | Return the dimension of the index                                                                                               |
| `display`([filename, ostream, prefix])                                                   | Display values in the block                                                                                                     |
| `find_component`(label_or_component)                                                     | Returns a component in the block given a name.                                                                                  |
| `get_suffix_value`(suffix_or_name[, default])                                            | Get the suffix value for this component data                                                                                    |
| `getname`([fully_qualified, name_buffer, ...])                                           | Return a string with the component name and index                                                                               |
| `id_index_map`()                                                                         | Return an dictionary id->index for all ComponentData instances.                                                                 |
| `index`()                                                                                | Returns the index of this ComponentData instance relative to the parent component index set.                                    |
| `index_set`()                                                                            | Return the index set                                                                                                            |
| `is_component_type`()                                                                    | Return True if this class is a Pyomo component                                                                                  |
| `is_constructed`()                                                                       | A boolean indicating whether or not all *active* components of the input model have been properly constructed.                  |
| `is_expression_type`([expression_system])                                                | Return True if this numeric value is an expression                                                                              |
| `is_indexed`()                                                                           | Return true if this component is indexed                                                                                        |
| `is_logical_type`()                                                                      | Return True if this class is a Pyomo Boolean object.                                                                            |
| `is_named_expression_type`()                                                             | Return True if this numeric value is a named expression                                                                         |
| `is_numeric_type`()                                                                      | Return True if this class is a Pyomo numeric object                                                                             |
| `is_parameter_type`()                                                                    | Return False unless this class is a parameter object                                                                            |
| `is_reference`()                                                                         | Return True if this component is a reference, where "reference" is interpreted as any component that does not own its own data. |
| `is_variable_type`()                                                                     | Return False unless this class is a variable object                                                                             |
| `items`([sort, ordered])                                                                 | Return an iterator of (index,data) component data tuples                                                                        |
| `iteritems`()                                                                            | DEPRECATED.                                                                                                                     |
| `iterkeys`()                                                                             | DEPRECATED.                                                                                                                     |
| `itervalues`()                                                                           | DEPRECATED.                                                                                                                     |
| `keys`([sort, ordered])                                                                  | Return an iterator over the component data keys                                                                                 |
| `load`(arg[, namespaces, profile_memory])                                                | Load the model with data from a file, dictionary or DataPortal object.                                                          |
| `model`()                                                                                | Return the model of the component that owns this data.                                                                          |
| `parent_block`()                                                                         | Return the parent of the component that owns this data.                                                                         |
| `parent_component`()                                                                     | Returns the component associated with this object.                                                                              |
| `pprint`([ostream, verbose, prefix])                                                     | Print component information                                                                                                     |
| `preprocess`([preprocessor])                                                             | DEPRECATED.                                                                                                                     |
| `reclassify_component_type`(name_or_object, ...)                                         | TODO                                                                                                                            |
| `reconstruct`([data])                                                                    | REMOVED: reconstruct() was removed in Pyomo 6.0.                                                                                |
| `root_block`()                                                                           | Return self.model()                                                                                                             |
| `set_suffix_value`(suffix_or_name, value[, expand])                                      | Set the suffix value for this component data                                                                                    |
| `to_dense_data`()                                                                        | TODO                                                                                                                            |
| `transfer_attributes_from`(src)                                                          | Transfer user-defined attributes from src to this block                                                                         |
| `type`()                                                                                 | DEPRECATED.                                                                                                                     |
| [`update_demand`](#src.models.hydrogen.model.h2_model.H2Model.update_demand)(new_demand) | insert new demand as a dict in the format: new_demand[region,year]                                                              |
| `valid_model_component`()                                                                | Return True if this can be used as a model component.                                                                           |
| `valid_problem_types`()                                                                  | This method allows the pyomo.opt convert function to work with a Model object.                                                  |
| `values`([sort, ordered])                                                                | Return an iterator of the component data objects                                                                                |
| `write`([filename, format, solver_capability, ...])                                      | Write the model to a file, with a given format.                                                                                 |

| **Skip**                              |    |
|---------------------------------------|----|
| **clear**                             |    |
| **fix_all_vars**                      |    |
| **nconstraints**                      |    |
| **nobjectives**                       |    |
| **nvariables**                        |    |
| **private_data**                      |    |
| **register_private_data_initializer** |    |
| **set_value**                         |    |
| **unfix_all_vars**                    |    |
| **update_electricity_price**          |    |
| **update_exchange_params**            |    |
<!-- !! processed by numpydoc !! -->

#### update_demand(new_demand)

insert new demand as a dict in the format: new_demand[region,year]

<!-- !! processed by numpydoc !! -->

#### update_electricity_price(new_electricity_price)

<!-- !! processed by numpydoc !! -->

#### update_exchange_params(new_demand=None, new_electricity_price=None)

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.h2_model.resolve(hm: [H2Model](#src.models.hydrogen.model.h2_model.H2Model), new_demand=None, new_electricity_price=None, test=False)

For convenience: After building and solving the model initially:

new_demand: dict - new_demand[region,year] for H2demand in (region,year)
new_electricity_price: dict - new_electricity_price[region,year]

then you can access the price duals and the quantities of electricity
consumption as described in the comments in the solve() method

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.h2_model.solve(hm: [H2Model](#src.models.hydrogen.model.h2_model.H2Model))

solve the model

<!-- !! processed by numpydoc !! -->

## src.models.hydrogen.model.validators module

set of validator functions for use in model

<!-- !! processed by numpydoc !! -->

### src.models.hydrogen.model.validators.region_validator(hm: [H2Model](#src.models.hydrogen.model.h2_model.H2Model), region)

currently, region must be STRING

<!-- !! processed by numpydoc !! -->

## Module contents

<!-- !! processed by numpydoc !! -->
