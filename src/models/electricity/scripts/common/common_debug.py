# TODO: add docstrings


import os
import logging
from tabulate import tabulate

logger = logging.getLogger('common_debug.py')


def print_table(df, outputfilename=None):
    """prints a table for easy debugging.

    Parameters
    ----------
    df1: 2 dimensional dataframe
       restart variable table
    outputfilename: string
        name of output file
    """
    if outputfilename:
        fileparts = os.path.split(outputfilename)
        if fileparts[0]:
            outputfilename = fileparts[0] + r'\table_' + fileparts[1]
        outputfilename = outputfilename.replace('|', '_')
        if '.txt' not in outputfilename:
            outputfilename = outputfilename + '.txt'
    else:
        outputfilename = 'table_mytable.txt'
    with open(outputfilename, 'a+') as f:
        if os.path.exists(outputfilename):
            f.write('\n')
        f.write(tabulate(df, headers='keys', tablefmt='psql'))
