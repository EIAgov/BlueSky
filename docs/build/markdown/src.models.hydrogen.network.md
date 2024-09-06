# src.models.hydrogen.network package

## Submodules

## src.models.hydrogen.network.grid module

### GRID CLASS

> This is the central class that binds all the other classes together. No class
> instance exists in a reference that isn’t fundamentally contained in a grid.
> The grid is used to instantiate a model, read data, create the regionality
> and hub / arc network within that regionality, assign data to objects and more.

> notably, the grid is used to coordinate internal methods in various classes to
> make sure that their combined actions keep the model consistent and accomplish
> the desired task.

> data = this is a data object
<!-- !! processed by numpydoc !! -->

### *class* src.models.hydrogen.network.grid.Grid(data: [GridData](#src.models.hydrogen.network.grid_data.GridData) | None = None)

Bases: `object`

### Methods

| **aggregate_hubs**              |    |
|---------------------------------|----|
| **arc_generation**              |    |
| **build_grid**                  |    |
| **collapse**                    |    |
| **collapse_level**              |    |
| **combine_arcs**                |    |
| **connect_subregions**          |    |
| **create_arc**                  |    |
| **create_hub**                  |    |
| **create_region**               |    |
| **delete**                      |    |
| **load_hubs**                   |    |
| **recursive_region_generation** |    |
| **test**                        |    |
| **visualize**                   |    |
| **write_data**                  |    |
<!-- !! processed by numpydoc !! -->

#### aggregate_hubs(hublist, region)

<!-- !! processed by numpydoc !! -->

#### arc_generation(df)

<!-- !! processed by numpydoc !! -->

#### build_grid(vis=True)

<!-- !! processed by numpydoc !! -->

#### collapse(region_name)

<!-- !! processed by numpydoc !! -->

#### collapse_level(level)

<!-- !! processed by numpydoc !! -->

#### combine_arcs(arclist, origin, destination)

<!-- !! processed by numpydoc !! -->

#### connect_subregions()

<!-- !! processed by numpydoc !! -->

#### create_arc(origin, destination, capacity, cost=0)

<!-- !! processed by numpydoc !! -->

#### create_hub(name, region, data=None)

<!-- !! processed by numpydoc !! -->

#### create_region(name, parent=None, data=None)

<!-- !! processed by numpydoc !! -->

#### delete(thing)

<!-- !! processed by numpydoc !! -->

#### load_hubs()

<!-- !! processed by numpydoc !! -->

#### recursive_region_generation(df, parent)

<!-- !! processed by numpydoc !! -->

#### test()

<!-- !! processed by numpydoc !! -->

#### visualize()

<!-- !! processed by numpydoc !! -->

#### write_data()

<!-- !! processed by numpydoc !! -->

## src.models.hydrogen.network.grid_data module

<!-- !! processed by numpydoc !! -->

### *class* src.models.hydrogen.network.grid_data.GridData(data_folder: Path)

Bases: `object`

<!-- !! processed by numpydoc !! -->

## src.models.hydrogen.network.hub module

### HUB CLASS

class objects are individual hubs, which are fundamental units of production in
the model. Hubs belong to regions, and connect to each other with transportation
arcs.

> name - str name of hub (from input data or aggregated)
> region - region located in
> data - data object that stores hub-specific parameters
> outbound - dict of arcs outbound from hub, with destination hub name:destination hub object format
> inbound - dict of arcs inbound to hub, with origin hub name: origin hub object format
> x,y - location coordinates (will deprecate)

> change_region - region arg becomes hub’s region and hub is added to args hublist
> display_outbound - print outbound arcs
> display_inbound - print inbound arcs
> add_outbound - add arc arg as an outbound arc
> add_inbound - add arc arg as an inbound arc
> remove_outbound - remove an outbound arc
> remove_inbound - remove an inbound arc
> get_data - pass the name of a parameter in data as arg, and receive the value.
> cost - temp cost function, to be deprecated
<!-- !! processed by numpydoc !! -->

### *class* src.models.hydrogen.network.hub.Hub(name, region, data=None)

Bases: `object`

### Methods

| **add_inbound**      |    |
|----------------------|----|
| **add_outbound**     |    |
| **change_region**    |    |
| **cost**             |    |
| **display_outbound** |    |
| **get_data**         |    |
| **remove_inbound**   |    |
| **remove_outbound**  |    |
<!-- !! processed by numpydoc !! -->

#### add_inbound(arc)

<!-- !! processed by numpydoc !! -->

#### add_outbound(arc)

<!-- !! processed by numpydoc !! -->

#### change_region(new_region)

<!-- !! processed by numpydoc !! -->

#### cost(technology, year)

<!-- !! processed by numpydoc !! -->

#### display_outbound()

<!-- !! processed by numpydoc !! -->

#### get_data(quantity)

<!-- !! processed by numpydoc !! -->

#### remove_inbound(arc)

<!-- !! processed by numpydoc !! -->

#### remove_outbound(arc)

<!-- !! processed by numpydoc !! -->

## src.models.hydrogen.network.region module

<!-- !! processed by numpydoc !! -->

### *class* src.models.hydrogen.network.region.Region(name, grid=None, kind=None, data=None, parent=None)

Bases: `object`

### Methods

| **absorb_subregions**        |    |
|------------------------------|----|
| **absorb_subregions_deep**   |    |
| **add_hub**                  |    |
| **add_subregion**            |    |
| **aggregate_subregion_data** |    |
| **create_subregion**         |    |
| **delete**                   |    |
| **display_children**         |    |
| **display_hubs**             |    |
| **get_data**                 |    |
| **remove_hub**               |    |
| **remove_subregion**         |    |
| **update_data**              |    |
| **update_parent**            |    |
<!-- !! processed by numpydoc !! -->

#### absorb_subregions()

<!-- !! processed by numpydoc !! -->

#### absorb_subregions_deep()

<!-- !! processed by numpydoc !! -->

#### add_hub(hub)

<!-- !! processed by numpydoc !! -->

#### add_subregion(subregion)

<!-- !! processed by numpydoc !! -->

#### aggregate_subregion_data(subregions)

<!-- !! processed by numpydoc !! -->

#### assigned_names *= {}*

#### create_subregion(name, data=None)

<!-- !! processed by numpydoc !! -->

#### delete()

<!-- !! processed by numpydoc !! -->

#### display_children()

<!-- !! processed by numpydoc !! -->

#### display_hubs()

<!-- !! processed by numpydoc !! -->

#### get_data(quantity)

<!-- !! processed by numpydoc !! -->

#### remove_hub(hub)

<!-- !! processed by numpydoc !! -->

#### remove_subregion(subregion)

<!-- !! processed by numpydoc !! -->

#### update_data(df)

<!-- !! processed by numpydoc !! -->

#### update_parent(new_parent)

<!-- !! processed by numpydoc !! -->

## src.models.hydrogen.network.registry module

### REGISTRY CLASS

> This class is the central registry of all objects in a grid. It preserves them
> in dicts of object-name:object so that they can be looked up by name.
> it also should serve as a place to save data in different configurations for
> faster parsing - for example, depth is a dict that organizes regions according to
> their depth in the region nesting tree.

> regions - dict of region name:region object
> hubs - dict of hub name:hub object
> arcs - dict of arc name:arc object
> depth - dict of ints and lists of regions with int n:list of regions at that depth
> max_depth - the max depth in the tree

> add - generic method to add something to the registry. Depending on the type
> : thing, it adds it to the appropriate variable and adjusts others as necessary

> remove - generic method to remove something from the registry. Depending on the
> : type of thing, it removes it from the appropriate variable and adjusts
>   others as necessary.

> update_levels - updates the level counts (such as when you aggregate and a region
> : changes level)
<!-- !! processed by numpydoc !! -->

### *class* src.models.hydrogen.network.registry.Registry

Bases: `object`

### Methods

| **add**           |    |
|-------------------|----|
| **remove**        |    |
| **update_levels** |    |
<!-- !! processed by numpydoc !! -->

#### add(thing)

<!-- !! processed by numpydoc !! -->

#### remove(thing)

<!-- !! processed by numpydoc !! -->

#### update_levels()

<!-- !! processed by numpydoc !! -->

## src.models.hydrogen.network.transportation_arc module

### TRANSPORTATION ARC CLASS

> objects in this class represent individual transportation arcs. An arc can
> exist with zero capacity, so they only represent *possible* arcs.

> name - the name used by the registry. Unlike regions and hubs, arc names are
> : fully determined. They are tuples of origin hub name and dest hub name.

> origin - pointer to origin hub object
> destination - pointer to destination hub object
> capacity - base capacity
> cost - generic cost parameter (to be deprecated)

> change_origin - changes the origin hub and name to reflect that
> chage_destination - changes the destination hub and name to reflect that
> disconnect - removes itself from the inbound and outbound hubs’ arc lists.
<!-- !! processed by numpydoc !! -->

### *class* src.models.hydrogen.network.transportation_arc.TransportationArc(origin, destination, capacity, cost=0)

Bases: `object`

### Methods

| **change_destination**   |    |
|--------------------------|----|
| **change_origin**        |    |
| **disconnect**           |    |
<!-- !! processed by numpydoc !! -->

#### change_destination(new_destination)

<!-- !! processed by numpydoc !! -->

#### change_origin(new_origin)

<!-- !! processed by numpydoc !! -->

#### disconnect()

<!-- !! processed by numpydoc !! -->

## Module contents

<!-- !! processed by numpydoc !! -->
