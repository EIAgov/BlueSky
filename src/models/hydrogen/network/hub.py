"""
HUB CLASS
~~~~~~~~~

class objects are individual hubs, which are fundamental units of production in
the model. Hubs belong to regions, and connect to each other with transportation
arcs.

    class variables:
    ~~~~~~~~~~~~~~~

    name - str name of hub (from input data or aggregated)
    region - region located in
    data - data object that stores hub-specific parameters
    outbound - dict of arcs outbound from hub, with destination hub name:destination hub object format
    inbound - dict of arcs inbound to hub, with origin hub name: origin hub object format
    x,y - location coordinates (will deprecate)

    class methods:
    ~~~~~~~~~~~~~

    change_region - region arg becomes hub's region and hub is added to args hublist
    display_outbound - print outbound arcs
    display_inbound - print inbound arcs
    add_outbound - add arc arg as an outbound arc
    add_inbound - add arc arg as an inbound arc
    remove_outbound - remove an outbound arc
    remove_inbound - remove an inbound arc
    get_data - pass the name of a parameter in data as arg, and receive the value.
    cost - temp cost function, to be deprecated
"""


class Hub:
    def __init__(self, name, region, data=None):
        self.name = name
        self.region = region
        self.data = data.infer_objects(copy=False).fillna(0)

        # outbound and inbound dictionaries mapping names of hubs to the arc objects
        self.outbound = {}
        self.inbound = {}

        self.x = data.iloc[0]['x']
        self.y = data.iloc[0]['y']

    def change_region(self, new_region):
        self.region = new_region
        new_region.add_hub(self)

    def display_outbound(self):
        for arc in self.outbound.values():
            print('name:', arc.origin.name, 'capacity:', arc.capacity)

    """
    Add and remove arc functions
    
    only modifies itself
    """

    def add_outbound(self, arc):
        self.outbound[arc.destination.name] = arc

    def add_inbound(self, arc):
        self.inbound[arc.origin.name] = arc

    def remove_outbound(self, arc):
        del self.outbound[arc.destination.name]

    def remove_inbound(self, arc):
        del self.inbound[arc.origin.name]

    def get_data(self, quantity):
        return self.data.iloc[0][quantity]

    def cost(self, technology, year):
        if technology == 'PEM':
            return self.region.data['electricity_cost'] * 45
        elif technology == 'SMR':
            return self.region.data['gas_cost']
        else:
            return 0
