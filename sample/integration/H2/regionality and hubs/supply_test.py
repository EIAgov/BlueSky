# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 09:28:58 2024

@author: JNI
"""

import pandas as pd
import random as rnd
import regions


'''
THIS IS A SIMPLE SCRIPT THAT USES A MADE UP DEMAND CURVE TO ITERATE WITH HMM

take the dataframe grid.model.h2_price and input it into the function interchange()
along with the desired number of iterations, and it will pass values back and forth.

'''

grid = regions.Grid(regions.Data())
grid.build_grid()
grid.test()


def demand_curve(h2_price_data, iteration = 1):
    
    h2_price_data['demand_' + str(iteration)] = (1 - h2_price_data['price'] /  (30*1.05**(h2_price_data['year']-2024)))*500000*1.2**(h2_price_data['year']-2024)
    return h2_price_data



def interchange(data, iterations = 1):
    
    data.rename(columns = {'price':'price_0'}, inplace = True)
    
    for iteration in range(iterations):
        data['demand_' + str(iteration)] = (1 - data['price_' + str(iteration)] /  (30*1.05**(data['year']-2024)))*500000*1.1**(data['year']-2024)
        new_demand = {(region,year): data[(data['region'] == region) & (data['year'] == year )].iloc[0]['demand_' + str(iteration)] for region in data['region'].unique().tolist() for year in data['year'].unique().tolist()}
        grid.model.resolve(new_demand)
        data['price_' + str(iteration+1)] = grid.model.h2_price['price']
    
    return data

