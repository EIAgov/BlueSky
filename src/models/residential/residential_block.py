"""
The purpose of this module is to buid and hold a persistent residential model in ConcreteModel format
This block can be updated/interrogated to update pricing & load in an iterative solve
Or can be passed on as a block to a unified model
"""

from collections.abc import Iterable
import logging
import pandas as pd
from pyomo.environ import Block, ConcreteModel, Constraint, Var, Param, Set, value, NonNegativeReals  # type: ignore

from src.integrator.utilities import EI
from src.models.residential.scripts.residential import residentialModule

logger = logging.getLogger(__name__)


class ResidentialBlock(ConcreteModel):
    def __init__(self, load_index: Iterable[EI]):
        """Make a new Block that is initialized with the Electricity Indices provided

        Parameters
        ----------
        load_index : Iterable[EI]
            a container of EI tuples which are (region, year, hour)
        """
        ConcreteModel.__init__(self)

        # make a fake baseload table until the reader is ready...
        # TODO:  Remove this fake data
        records = [(ei.region, ei.year, ei.hour, 10) for ei in load_index]
        load_df = pd.DataFrame.from_records(records, columns=['r', 'y', 'hr', 'load']).set_index(
            ['r', 'y', 'hr']
        )
        self.res_mod = residentialModule(load_df=load_df)

        self.load_idx = Set(initialize=sorted(load_index))

        self.base_load = Param(self.load_idx, initialize=0.0, mutable=True)
        self.Load = Var(self.load_idx, within=NonNegativeReals)

        # Create constraints that restrict the Load variable to the newly calculated values
        @self.Constraint(self.load_idx)
        def create_load(self, r, y, hr):
            return self.Load[r, y, hr] == self.base_load[r, y, hr]

    def update_load(self, prices, price_index):
        """a quick relay to the residential module updating routines"""
        # calculate the lew loads from prices/indices
        updated_load = self.res_mod.update_load(prices, price_index)
        # update the parameter (which is linked to the load var)
        self.base_load.store_values(updated_load)

    def poll_load(self) -> dict[EI, float]:
        """
        A quick pull of the parameter data for use in iterative solving
        """
        loads = {EI(k): v for k, v in self.base_load.extract_values()}
        avg_load = sum(loads.values()) / len(loads)
        logger.debug('The grand average of new load is: %0.2f', avg_load)

        return loads
