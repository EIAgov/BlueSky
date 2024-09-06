"""
TRANSPORTATION ARC CLASS
~~~~~~~~~~~~~~~~~~~~~~~~

    objects in this class represent individual transportation arcs. An arc can
    exist with zero capacity, so they only represent *possible* arcs.

    class variables:
    ~~~~~~~~~~~~~~~

    name - the name used by the registry. Unlike regions and hubs, arc names are
           fully determined. They are tuples of origin hub name and dest hub name.
    origin - pointer to origin hub object
    destination - pointer to destination hub object
    capacity - base capacity
    cost - generic cost parameter (to be deprecated)

    class methods:
    ~~~~~~~~~~~~~

    change_origin - changes the origin hub and name to reflect that
    chage_destination - changes the destination hub and name to reflect that
    disconnect - removes itself from the inbound and outbound hubs' arc lists.

"""


class TransportationArc:
    def __init__(self, origin, destination, capacity, cost=0):
        self.name = (origin.name, destination.name)
        self.origin = origin
        self.destination = destination
        self.capacity = capacity
        self.cost = cost

    def change_origin(self, new_origin):
        self.name = (new_origin.name, self.name[1])
        self.origin = new_origin

    def change_destination(self, new_destination):
        self.name = (self.name[0], new_destination.name)
        self.destination = new_destination

    def disconnect(self):
        self.origin.remove_outbound(self)
        self.destination.remove_inbound(self)
