"""

Created on:  7/26/24
"""

from region_network.context import Context
from region_network.region_data import RegionData


class Hub:
    """
    an H2 hub in the network
    """

    def __init__(self, name: str):
        self.name = name
        self.region_data: dict[Context, RegionData] = {}

    def add_region_data(self, context: Context, region_data: RegionData):
        self.region_data[context] = region_data

    def __repr__(self):
        return self.name
