"""

Created on:  7/26/24
"""

from collections import defaultdict
from itertools import chain

from region_network.arc import Arc
from region_network.hub import Hub


class Network:
    """
    A network of hubs & arcs for H2
    """

    def __init__(self):
        self.connections: dict[Hub, set[Arc]] = defaultdict(set)

    def add_connection(self, arc: Arc):
        """
        add an arc to the network
        :param arc: arc to add
        :return: None
        """
        self.connections[arc.s].add(arc)

    def all_connections(self) -> list[Arc]:
        """
        get a list of all arcs in the network
        :return:
        """
        return list(chain(*self.connections.values()))
