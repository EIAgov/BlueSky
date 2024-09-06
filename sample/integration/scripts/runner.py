import sys
import os
import logging
import argparse as ap

### Setup Logging

# Delete old log
try:
    os.remove('../output/debug.log')
except:
    pass

# Configure Logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig( level=logging.DEBUG,
                    format='[%(asctime)s][%(name)s]' +
                           '[%(funcName)s][%(levelname)s]  :: |%(message)s|',
                    handlers=[logging.FileHandler("../output/debug.log"),
                              logging.StreamHandler()])

logger = logging.getLogger('ccats.py')
logger.info('logger.info All Model System Paths')
logger.info(sys.path)

# Import Module
import electricity_model as electricity_model
import preprocessor as preprocessor
import postprocessor as postprocessor

#Build inputs used for model
all_frames = preprocessor.preprocessor(preprocessor.Sets())

electricity_model.run_model()

