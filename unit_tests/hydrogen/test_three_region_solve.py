import pytest
from pyomo.environ import value

from definitions import PROJECT_ROOT
from src.models.hydrogen.model import actions

import logging

logger = logging.getLogger(__name__)


@pytest.mark.skip('not ready:  costing needs work in dataset')
def test_three_reg_solve():
    # run the model
    HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
    data_path = HYDROGEN_ROOT / 'inputs/three_region'

    grid_data = actions.load_data(data_path)
    grid = actions.build_grid(grid_data=grid_data)
    model = actions.build_model(grid=grid)
    sol = actions.solve_it(model)

    # pull the objective value out for examination...
    obj_val = value(model.cost_expression)
    assert obj_val == pytest.approx(2671.56), "objective value doesn't match"
