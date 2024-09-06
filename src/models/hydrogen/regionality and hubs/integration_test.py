# -*- coding: utf-8 -*-
"""
Created on Fri Jul 12 14:49:56 2024

@author: JNI
"""

from pyomo.environ import *
import pandas as pd
import random as rnd
# import regions


class My_Block(Block):
    def __init__(self, params, *args, **kwargs):
        self.p = params
        super(My_Block, self).__init__()
        self.generate_sets()

    def generate_sets(self):
        self.S = Set(initialize=self.p[0])


model = ConcreteModel()
model.myblock = My_Block([1, 2, 3])
