"""
REGISTRY CLASS
~~~~~~~~~~~~~~

    This class is the central registry of all objects in a grid. It preserves them
    in dicts of object-name:object so that they can be looked up by name.
    it also should serve as a place to save data in different configurations for
    faster parsing - for example, depth is a dict that organizes regions according to
    their depth in the region nesting tree.

    class variables:
    ~~~~~~~~~~~~~~~

    regions - dict of region name:region object
    hubs - dict of hub name:hub object
    arcs - dict of arc name:arc object
    depth - dict of ints and lists of regions with int n:list of regions at that depth
    max_depth - the max depth in the tree


    class methods:
    ~~~~~~~~~~~~~

    add - generic method to add something to the registry. Depending on the type
          thing, it adds it to the appropriate variable and adjusts others as necessary
    remove - generic method to remove something from the registry. Depending on the
             type of thing, it removes it from the appropriate variable and adjusts
             others as necessary.
    update_levels - updates the level counts (such as when you aggregate and a region
                    changes level)


"""

from src.models.hydrogen.network.hub import Hub
from src.models.hydrogen.network.region import Region
from src.models.hydrogen.network.transportation_arc import TransportationArc


class Registry:
    def __init__(self):
        self.regions: dict[str, Region] = {}
        self.depth = {i: [] for i in range(10)}
        self.hubs: dict[str, Hub] = {}
        self.arcs = {}
        self.max_depth = 0

    def add(self, thing):
        if type(thing) == Hub:
            self.hubs[thing.name] = thing
            return thing
        elif type(thing) == TransportationArc:
            self.arcs[thing.name] = thing
            return thing
        elif type(thing) == Region:
            self.regions[thing.name] = thing
            self.depth[thing.depth].append(thing.name)
            if thing.depth > self.max_depth:
                self.max_depth = thing.depth
            return thing

    def remove(self, thing):
        if type(thing) == Hub:
            del self.hubs[thing.name]
        elif type(thing) == Region:
            # self.depth[thing.depth] = self.depth[thing.depth].remove(thing.name)
            del self.regions[thing.name]

        elif type(thing) == TransportationArc:
            del self.arcs[thing.name]

    def update_levels(self):
        self.depth = {i: [] for i in range(10)}
        for region in self.regions.values():
            self.depth[region.depth].append(region.name)
        pass
