"""

Created on:  7/26/24
"""

from region_network.arc import Arc
from region_network.context import Context
from region_network.hub import Hub
from region_network.network import Network
from region_network.region_data import RegionData

# make some fake data (read-in in future)
rd1 = RegionData('CA', 100000)
rd2 = RegionData('TX', 50000)
rd3 = RegionData('MD', 2000)

# make some hubs
h1 = Hub('west')
h1.add_region_data(context=Context.ELEC, region_data=rd1)

h2 = Hub('south')
h2.add_region_data(context=Context.ELEC, region_data=rd2)

h3 = Hub('east')
h3.add_region_data(context=Context.ELEC, region_data=rd3)

# build the network

network = Network()
network.add_connection(Arc(h1, h2, 5, 3))
network.add_connection(Arc(h2, h3, 6, 1.5))

# inspect...
print(network.all_connections())
