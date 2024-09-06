from logging import getLogger
import pandas as pd

"""
Region class:
~~~~~~~~~~~~
    
    Class objects are regions, which have a natural tree-structure. Each region
    can have a parent region and child regions (subregions), a data object, and 
    a set of hubs.
  
    class variables:
    ~~~~~~~~~~~~  
    
    self.name = str of the regions name (from data file input)
    self.parent = pointer to the parent region object
    self.childrem = dict of subregions, with name:object format
    self.data = data object, which should contain region-specific parameters
    self.grid = the grid the region lies in (inherited from parent region)
    self.depth = distance from root of tree
    
    class methods:
    ~~~~~~~~~~~~  
    
    display_children - prints a list of subregions
    display_hubs - prints a list of hubs in the region
    update_parent - changes the parent region (used in aggregation)
    create_subregion - creates a subregion with given name and data
    add_subregion - takes an existing region as an arg and assigns it as a subregion
    remove_subregion - removes a subregion from list of subregions
    add_hub - adds an existing hub to region hubs
    remove_hub - removes a hub from region hubs
    delete - deletes the region. hubs and subregions are reassigned to parent
    absorb_subregions -  aggregates subregion data into region's data, then deletes them, 
                         inherits their subregions and hubs
    absorb_subregions_deep - recursively runs absorb_subregions on subregions, 
                             their subregions etc so that region is the bottom level
    update_data - replaces data object with arg
    aggregate_subregion_data - takes all subregions, and aggregates their data
                               based on whether they are summable or meanable 
    get_data - pass the name of a parameter in data as arg, and receive the value.
    
"""
logger = getLogger(__name__)


class Region:
    assigned_names = set()

    def __init__(self, name, grid=None, kind=None, data=None, parent=None):
        # check name for uniqueness
        if not name:
            raise ValueError('name cannot be None')
        if name in Region.assigned_names:
            logger.warning(f'region name {name} already exists')
        Region.assigned_names.add(name)
        self.name = name
        self.parent = parent
        self.children = {}
        self.hubs = {}
        self.data = data

        if self.parent != None:
            self.depth = self.parent.depth + 1
            self.grid = parent.grid

        else:
            self.depth = 0
            self.grid = grid

    def display_children(self):
        for child in self.children.values():
            print(child.name, child.depth)
            child.display_children()

    def display_hubs(self):
        for hub in self.hubs.values():
            print(hub.name)

    def update_parent(self, new_parent):
        if self.parent != None:
            del self.parent.children[self.name]
            self.parent = new_parent
            self.parent.add_subregion(self)
            self.depth = new_parent.depth + 1

        else:
            self.parent = new_parent
            self.parent.add_subregion(self)

    def create_subregion(self, name, data=None):
        self.grid.create_region(name, self, data)

    def add_subregion(self, subregion):
        self.children.update({subregion.name: subregion})

    def remove_subregion(self, subregion):
        self.children.pop(subregion.name)

    def add_hub(self, hub):
        self.hubs.update({hub.name: hub})

    def remove_hub(self, hub):
        del self.hubs[hub.name]

    def delete(self):
        for hub in self.hubs.values():
            hub.change_region(self.parent)

        for child in list(self.children.values()):
            child.update_parent(self.parent)
            self.parent.add_subregion(child)

        if self.name in self.parent.children.keys():
            self.parent.remove_subregion(self)

    def absorb_subregions(self):
        subregions = list(self.children.values())

        if self.data is None:
            self.aggregate_subregion_data(subregions)

        for subregion in subregions:
            self.grid.delete(subregion)

        del subregions

    def absorb_subregions_deep(self):
        subregions = list(self.children.values())
        # print([subregion.name for subregion in subregions])

        for subregion in subregions:
            # print(subregion.name)

            subregion.absorb_subregions_deep()

            print('deleting: ', subregion.name)

            if self.data is None:
                self.aggregate_subregion_data(subregions)
            self.grid.delete(subregion)

        del subregions

    def update_data(self, df):
        self.data = df

    def aggregate_subregion_data(self, subregions):
        temp_child_data = pd.concat([region.data for region in subregions], axis=1).transpose()
        # print(temp_child_data)
        new_data = pd.DataFrame(
            columns=self.grid.data.summable['region'] + self.grid.data.meanable['region']
        )

        for column in temp_child_data.columns:
            if column in self.grid.data.summable['region']:
                new_data[column] = [temp_child_data[column].sum()]
            if column in self.grid.data.meanable['region']:
                new_data[column] = [temp_child_data[column].mean()]

        self.update_data(new_data.squeeze())

    def get_data(self, quantity):
        if self.data is None:
            return 0
        else:
            return self.data[quantity]
