# common entry point at top level

import argparse
import logging
from pathlib import Path
import tomllib

from definitions import PROJECT_ROOT, OUTPUT_ROOT
from src.integrator.utilities import make_output_dir, setup_logger
from src.integrator.runner import run_elec_solo, run_h2_solo
from src.integrator.gs_elec_hyd_res import run_gs_combo
from src.integrator.unified_elec_hyd_res import run_unified_res_elec_h2

# Specify config path
default_config_path = Path(PROJECT_ROOT, 'src/integrator', 'run_config.toml')

if __name__ == '__main__':
    # Initial setup of output directory and logger
    OUTPUT_ROOT = make_output_dir(OUTPUT_ROOT)
    logger = setup_logger(OUTPUT_ROOT)
    logger = logging.getLogger(__name__)
    logger.info('Starting Logging')

    # Parse the args to get selected mode if one is provided
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='description:\n'
        '\tBuilds and runs models based on user inputs set in src/integrator/run_config.toml\n'
        '\tMode argument determines which models are run and how they are integrated and solved\n'
        '\tUniversal and module-specific options contained within run_config.toml\n'
        '\tUser can specify regions, time periods, solver options, and mode in run_config\n'
        '\tUsers can also specify the mode via command line argument or run_config.toml',
    )
    parser.add_argument(
        '--mode',
        choices=[
            'elec',
            'h2',
            'unified-combo',
            'gs-combo',
        ],
        dest='op_mode',
        help='The mode to run:\n\n'
        'elec:  run the elec model solo\n'
        'h2:  run the h2 model solo\n'
        'unified-combo:  run unified optimization method to solve h2 + ele + res models iteratively\n'
        'gs-combo:  run gauss-seidel method to solve h2 + elec + res models iteratively\n\n'
        'Mode can be set either via --mode command or in run_config.toml.\n'
        'If no --mode option is provided, default_mode in run_config.toml is used.',
    )
    parser.add_argument('--debug', action='store_true', help='set logging level to DEBUG')

    args = parser.parse_args()

    # Set logging level to DEBUG if --debug flag is provided
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug('Logging level set to DEBUG')

    # If no mode is specified read in the default mode from the run config TOML file
    if not args.op_mode:
        print('No mode arg passed, therefore...')
        with open(default_config_path, 'rb') as src:
            config = tomllib.load(src)
        logger.info(f'Retrieved config data: {config}')
        args.op_mode = config['default_mode']
        print(f'using mode {args.op_mode} specified in run_config file')

    logger.info(f'Model running in: {args.op_mode} mode')

    # Match on the mode to run the appropriate function
    match args.op_mode:
        case 'elec':
            run_elec_solo(config_path=default_config_path)

        case 'h2':
            # lets try to run the H2 solo for 1 region
            #   it needs a path to a data folder...
            HYDROGEN_ROOT = PROJECT_ROOT / 'src/models/hydrogen'
            data_path = HYDROGEN_ROOT / 'inputs/single_region'

            # run H2 with config info for region & year...
            run_h2_solo(data_path=data_path, config_path=default_config_path)
            # could run with no config data
            # run_h2_solo(data_path=data_path)

        case 'gs-combo':
            run_gs_combo(config_path=default_config_path)

        case 'unified-combo':
            run_unified_res_elec_h2(config_path=default_config_path)

        case _:
            logger.error('Unkown op mode... exiting')
