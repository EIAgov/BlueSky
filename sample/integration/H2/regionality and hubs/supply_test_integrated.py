# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 09:28:58 2024

@author: JNI
"""

import pandas as pd
import random as rnd
import regions_integrated 
from pyomo.environ import *

'''
THIS IS A SIMPLE SCRIPT THAT USES A MADE UP DEMAND AND PRICES

it imports the region class, generates a grid, creates a model object running
in 'integrated' mode with the price and demand as inputs, builds the model and
saves the return value as copied model
'''


# generate some price and demand data

def demand_curve(h2_price_data, iteration = 1):   
    h2_price_data['demand_' + str(iteration)] = (1 - h2_price_data['price'] /  (30*1.05**(h2_price_data['year']-2024)))*500000*1.2**(h2_price_data['year']-2024)
    return h2_price_data

# read a csv file for demand as a df and append prices to it
data_price = demand_curve(pd.read_csv('C:/Users/MLJ/Downloads/H2/regionality and hubs/h2_price.csv'))

#convert the df into dicts
price = {(region,year): data_price[(data_price['region'] == region) & (data_price['year'] == year)].iloc[0]['price']*.04 for region in data_price['region'].unique() for year in data_price['year'].unique()}
demand = {(region,year): data_price[(data_price['region'] == region) & (data_price['year'] == year)].iloc[0]['demand_1'] for region in data_price['region'].unique() for year in data_price['year'].unique()}

#create a grid instance loading from data, and build it
grid = regions_integrated.Grid(regions_integrated.Data())
grid.build_grid()

# create a model instance that takes the grid as input, runs in integrated mode
# and takes demand and electricity_price as inputs. 
# 
model = regions_integrated.Model(grid, mode = 'integrated', demand = demand, electricity_price = price)

# start_build builds a pyomo block and returns it as a value saved as copied_model
copied_model = model.start_build()

# big model is a concrete model, and we attach the block copied_model to it as little
bigmodel = ConcreteModel()
bigmodel.little = copied_model

# solve bigmodel and it solves little

solver = SolverFactory('appsi_highs')
solver.solve(bigmodel,tee=True).write()



