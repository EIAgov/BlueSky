"""

Created on:  7/26/24
"""

from enum import Enum, unique


@unique
class Context(Enum):
    """
    usage contexts
    """

    ELEC = (1,)
    GAS = (2,)
    RESIDENTIAL = (3,)
