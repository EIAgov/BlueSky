from pathlib import Path
from src.models.hydrogen.model import actions

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='h2.log', encoding='utf-8', level=logging.DEBUG, filemode='w')

logging.getLogger('pyomo').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

verbose = True

# run the model
# data_path = Path('inputs/single_region')
data_path = Path('inputs/three_region')

grid_data = actions.load_data(data_path)
grid = actions.build_grid(grid_data=grid_data)
model = actions.build_model(grid=grid)

sol = actions.solve_it(model)
if verbose:
    actions.quick_summary(model)
print('done!')
