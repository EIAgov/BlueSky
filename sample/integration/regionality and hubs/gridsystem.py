import numpy as np
from pyomo.environ import *
import highspy as hp
import pandas as pd
import plotly
import plotly.express as px
import matplotlib
import networkx as nx
import matplotlib.pyplot as plt
import weakref as wr

class Grid:

    
    def __init__(self, name):
        self.name = name
        self.registry = Registry(self)
        
        
    def create_region(self,name,parent = None, data = None):
        
        self.registry.add_region(Region(name,parent = parent,grid = self,data = data))
        
    def create_hub(self, name, region, data = None):
        
        
        self.registry.add_hub(Hub(name,self,region,data=None))
        region.add_hub()
    
        
class Registry:
    
    def __init__(self, grid):
        
        self.grid = grid
        self.regions = {}
        self.hubs = {}
        self.arcs = {}
        
    def add_region(self,region):
            
        self.regions[region.name] = region
    
    def add_hub(self,hub):
        
        self.hubs[hub.name] = hub
        
    def add_arc(self,arc):
        
        self.arcs[arc.name] = arc
        
    def remove_region(self,region):
        
        if type(region) == str: del self.regions[region]
        else: del self.regions[region.name]
        
    def remove_hub(self,hub):
        
        if type(hub) == str: del self.hubs[hub]
        else: del self.hubs[hub.name] 
        
    def remove_arc(self,arc):
        
        if type(arc) == tuple: del self.arcs[arc]
        else: del self.arcs[arc.name]
        
    

class Region:
    
    def __init__(self,name, parent = None, grid = None, data = None):
        
        self.name = name
        
        if parent != None:
            self.parent = parent
        else: self.parent = None
        
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
    
    def create_hub(self,name,data=None):
        
        self.hubs[name] = self.grid.create_hub(name, region = self, data = data)

class Hub:
    
    def __init__(self,name, grid, region, data = None):
        
        self.name = name        
        self.region = region
        self.data = data
        
    def add_hub(self,name):

        pass

class Arc:
    
    def __init__(self,origin, destination, capacity, data = None):

        self.name = (origin,destination)
        self.origin = origin
        self.destination = destination
        self.capacity = capacity
        
        

class Data():
    
    def __init__(self,path):
        self.path = path
        
        
H = Grid('grid')
H.create_region('world')