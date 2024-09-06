"""

Created on:  7/26/24
"""

from region_network.hub import Hub


class Arc:
    """
    A directed arc on a graph with capacity and cost
    """

    def __init__(self, s: Hub, t: Hub, capacity, cost):
        """
        An arc between two hubs
        :param s: start hub
        :param t: terminal hub
        :param capacity: the capacity
        :param cost: usage cost
        """
        self.s = s
        self.t = t
        self.capacity = capacity
        self.cost = cost

    def __repr__(self):
        return f'{self.s} ---(cost: {self.cost} | cap: {self.capacity})---> {self.t}'
