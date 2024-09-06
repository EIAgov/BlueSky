from logging import getLogger
import pytest
from pyomo.environ import value

from definitions import PROJECT_ROOT
from src.models.hydrogen.model import actions

logger = getLogger(__name__)


# @pytest.mark.skip('skipping single')
def test_solve():
    logger.info('Starting the single region test')

    # run the model
    HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
    data_path = HYDROGEN_ROOT / 'inputs/single_region'

    grid_data = actions.load_data(data_path)
    grid = actions.build_grid(grid_data=grid_data)
    model = actions.build_model(grid=grid)
    sol = actions.solve_it(model)

    # pull the objective value out for examination...
    obj_val = value(model.cost_expression)
    model.display()
    assert obj_val == pytest.approx(1163149.9), "objective value doesn't match"
