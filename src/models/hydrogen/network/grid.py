"""GRID CLASS
~~~~~~~~~~~

    This is the central class that binds all the other classes together. No class
    instance exists in a reference that isn't fundamentally contained in a grid.
    The grid is used to instantiate a model, read data, create the regionality
    and hub / arc network within that regionality, assign data to objects and more.

    notably, the grid is used to coordinate internal methods in various classes to
    make sure that their combined actions keep the model consistent and accomplish
    the desired task.

    class variables:
    ~~~~~~~~~~~~~~~

    data = this is a data object

    class methods:
    ~~~~~~~~~~~~~


"""

import time
from matplotlib import pyplot as plt
import networkx as nx
import pandas as pd

from src.models.hydrogen.network.grid_data import GridData
from src.models.hydrogen.network.registry import Registry
from src.models.hydrogen.network.hub import Hub
from src.models.hydrogen.network.region import Region
from src.models.hydrogen.network.transportation_arc import TransportationArc


class Grid:
    def __init__(self, data: GridData | None = None):
        if data != None:
            self.data = data
        self.registry: Registry | None = (
            None  # good practice to declare all instance vars in __init__
        )

    def build_grid(self, vis=True):
        self.registry = Registry()
        self.world = Region('world', grid=self, data=self.data.regions)

        self.recursive_region_generation(self.data.regions, self.world)
        self.load_hubs()
        self.arc_generation(self.data.arcs)
        if vis:
            self.visualize()

    def visualize(self):
        G = nx.DiGraph()
        positions = {}
        for hub in self.registry.hubs.values():
            if hub.region.depth == 1:
                color = 'green'
                size = 100
            elif hub.region.depth == 2:
                color = 'red'
                size = 50

            else:
                color = 'blue'
                size = 30

            G.add_node(hub.name, pos=(hub.x, hub.y), color=color)
            positions[hub.name] = (hub.x, hub.y)
        edges = [arc for arc in self.registry.arcs.keys()]

        G.add_edges_from(edges)

        node_colors = [G.nodes[data]['color'] for data in G.nodes()]

        nx.draw(G, positions, with_labels=False, node_size=50, node_color=node_colors)
        plt.show()

    """
    Creation methods for region, hub, and arc.
    
    All classes should refer to these methods when creating instances so that everything
    is centralized. The methods will have return values so they can also be accessed during creation
    within their class. In some cases, the natural procedure should be to initiate the creation within
    another instance of the class so that the return value can be taken advantage of.
    
    
    """

    def create_region(self, name, parent=None, data=None):
        if parent == None:
            return self.registry.add_region(Region(name, parent=parent, grid=self, data=data))
        else:
            parent.add_subregion(
                (self.registry.add(Region(name, parent=parent, grid=self, data=data)))
            )

    def create_arc(self, origin, destination, capacity, cost=0):
        self.registry.add(TransportationArc(origin, destination, capacity, cost))
        origin.add_outbound(self.registry.arcs[(origin.name, destination.name)])
        destination.add_inbound(self.registry.arcs[(origin.name, destination.name)])

    def create_hub(self, name, region, data=None):
        region.add_hub(self.registry.add(Hub(name, region, data)))

    """
    delete function (works on arcs, hubs, and regions)
    """

    def delete(self, thing):
        if type(thing) == Region:
            thing.delete()
            self.registry.remove(thing)

        if type(thing) == Hub:
            for arc in list(thing.outbound.values()):
                self.delete(arc)
            for arc in list(thing.inbound.values()):
                self.delete(arc)

            thing.region.remove_hub(thing)
            self.registry.remove(thing)

        if type(thing) == TransportationArc:
            thing.disconnect()
            self.registry.remove(thing)

    def recursive_region_generation(self, df, parent):
        if df.columns[0] == 'data':
            for index, row in df.iterrows():
                # print(row[1:])
                parent.update_data(row[1:])

                """
                if type(row.hub) == str: 
                    self.create_hub(row.hub, parent,self.data.hubs.loc[self.data.hubs.hub == row.hub][self.data.hubs.columns[1:]])
                    parent.update_data(df[df.columns[1:]])
                """
        else:
            for region in df.iloc[:, 0].unique():
                if type(region) is not None:
                    # print(df.columns[0]+':',region)
                    parent.create_subregion(region)
                    self.recursive_region_generation(
                        df[df[df.columns[0]] == region][df.columns[1:]], parent.children[region]
                    )
                elif region == 'None':
                    self.recursive_region_generation(
                        df[df[df.columns[0]].isna()][df.columns[1:]], parent
                    )

                else:
                    self.recursive_region_generation(
                        df[df[df.columns[0]].isna()][df.columns[1:]], parent
                    )

    def arc_generation(self, df):
        for index, row in df.iterrows():
            self.create_arc(
                self.registry.hubs[row.origin], self.registry.hubs[row.destination], row['capacity']
            )
            # self.registry.add(TransportationArc(self.registry.hubs[row.origin],self.registry.hubs[row.destination],row['capacity']))
            # self.registry.hubs[row.origin].add_outbound(self.registry.arcs[(row.origin,row.destination)])
            # self.registry.hubs[row.destination].add_inbound(self.registry.arcs[(row.origin,row.destination)])

    def connect_subregions(self):
        for hub in self.registry.hubs.values():
            if hub.region.children == {}:
                for parent_hub in hub.region.parent.hubs.values():
                    self.create_arc(hub, parent_hub, 10000000)

    def load_hubs(self):
        for index, row in self.data.hubs.iterrows():
            # print(row['hub'], row['region'])
            # print(row[2:], type(row[2:]))
            self.create_hub(
                row['hub'],
                self.registry.regions[row['region']],
                data=pd.DataFrame(row[2:]).transpose().reset_index(),
            )

    def aggregate_hubs(self, hublist, region):
        temp_hub_data = pd.concat([hub.data for hub in hublist])
        new_data = pd.DataFrame(columns=self.data.summable['hub'] + self.data.meanable['hub'])

        for column in temp_hub_data.columns:
            if column in self.data.summable['hub']:
                new_data[column] = [temp_hub_data[column].sum()]
            if column in self.data.meanable['hub']:
                new_data[column] = [temp_hub_data[column].mean()]

        name = '_'.join([hub.name for hub in hublist])
        self.create_hub(name, region, new_data)

        inbound = {}
        outbound = {}

        for hub in hublist:
            for arc in hub.inbound.values():
                if arc.origin not in hublist:
                    if arc.origin.name not in inbound.keys():
                        inbound[arc.origin.name] = [arc]
                    else:
                        inbound[arc.origin.name].append(arc)
            for arc in hub.outbound.values():
                if arc.destination not in hublist:
                    if arc.destination.name not in outbound.keys():
                        outbound[arc.destination.name] = [arc]
                    else:
                        outbound[arc.destination.name].append(arc)

        for origin in list(inbound.keys()):
            self.combine_arcs(inbound[origin], self.registry.hubs[origin], self.registry.hubs[name])
        for destination in list(outbound.keys()):
            self.combine_arcs(
                outbound[destination], self.registry.hubs[name], self.registry.hubs[destination]
            )

        del inbound
        del outbound

        for hub in hublist:
            self.delete(hub)

        del hublist

    def combine_arcs(self, arclist, origin, destination):
        capacity = sum([arc.capacity for arc in arclist])
        cost = sum([arc.cost * arc.capacity for arc in arclist]) / capacity

        self.create_arc(origin, destination, capacity, cost)

        for arc in arclist:
            self.delete(arc)

    def write_data(self):
        hublist = [hub for hub in list(self.registry.hubs.values())]
        hubdata = pd.concat(
            [
                pd.DataFrame({'hub': [hub.name for hub in hublist]}),
                pd.concat([hub.data for hub in hublist]).reset_index(),
            ],
            axis=1,
        )
        hubdata.to_csv('saveddata.csv', index=False)

        regionlist = [
            region for region in list(self.registry.regions.values()) if not region.data is None
        ]
        regiondata = pd.concat(
            [
                pd.DataFrame({'region': [region.name for region in regionlist]}),
                pd.concat([region.data for region in regionlist], axis=1).transpose().reset_index(),
            ],
            axis=1,
        )
        regiondata = regiondata[
            ['region'] + self.data.summable['region'] + self.data.meanable['region']
        ]
        regiondata.to_csv('regiondatasave.csv', index=False)

        arclist = [arc for arc in list(self.registry.arcs.values())]
        arcdata = pd.DataFrame(
            {
                'origin': [arc.origin.name for arc in arclist],
                'destination': [arc.destination.name for arc in arclist],
                'capacity': [arc.capacity for arc in arclist],
                'cost': [arc.cost for arc in arclist],
            }
        )
        arcdata.to_csv('arcdatasave.csv', index=False)

    def collapse(self, region_name):
        self.registry.regions[region_name].absorb_subregions_deep()
        self.aggregate_hubs(
            list(self.registry.regions[region_name].hubs.values()),
            self.registry.regions[region_name],
        )
        self.registry.update_levels()
        self.visualize()

    # def build_model(self, mode = 'standard'):

    #     self.model = Model(self, mode)

    def test(self):
        start = time.time()

        self.build_model()
        self.model.start_build()
        self.model.solve(self.model.m)

        end = time.time()

        print(end - start)

    def collapse_level(self, level):
        for region in self.registry.depth[level]:
            self.collapse(region)
