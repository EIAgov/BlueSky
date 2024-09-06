"""
A sequencer for actions in the model.
This may change up a bit, but it is a place to assert control of the execution sequence for now
"""

from pathlib import Path
from logging import getLogger

from src.models.hydrogen.model.h2_model import solve, H2Model
from src.models.hydrogen.network.grid_data import GridData
from src.models.hydrogen.network.grid import Grid

from pyomo.opt import SolverResults, check_optimal_termination


logger = getLogger(__name__)


def load_data(path_to_input: Path, **kwds) -> GridData:
    gd = GridData(data_folder=path_to_input, **kwds)  # default build
    logger.info('Grid Data built.')
    return gd


def build_grid(grid_data: GridData) -> Grid:
    grid = Grid(grid_data)
    grid.build_grid(vis=False)
    logger.info(
        f'Grid built from Data with {len(grid.registry.arcs)} and {len(grid.registry.hubs)} hubs'
    )
    return grid


def build_model(grid: Grid, **kwds) -> H2Model:
    hm = H2Model(grid, **kwds)
    logger.info('model built')
    return hm


def solve_it(hm: H2Model) -> SolverResults:
    res = solve(hm=hm)
    logger.info('model solved')

    return res


def quick_summary(solved_hm: H2Model) -> None:
    res = (
        f'********** QUICK SUMMARY *************\n'
        f'  Production Cost: {value(solved_hm.total_cost):0.3f}\n'
        f'  Production Cap Cost: {value(solved_hm.prod_capacity_expansion_cost):0.3f}\n'
        f'  Transpo Cost: {value(solved_hm.transportation_cost):0.3f}\n'
        f'  Transpo Cap Expansion Cost: {value(solved_hm.trans_capacity_expansion_cost):0.3f}\n\n'
        f'  Total Cost: {value(solved_hm.cost_expression):0.3f}'
    )
    print(res)
