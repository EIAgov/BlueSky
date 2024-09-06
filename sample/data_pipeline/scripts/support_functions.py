import pandas as pd
import sqlite3
from time import time
import datetime
from pathlib import Path
import sys
import datetime
from datetime import datetime as dt

# def _parse_sql(sql: str) -> str:
#     """Properly interprets sql as file or query then processes"""

#     if ".sql" == str(sql)[-4:]:
#         if Path(sql).is_file():
#             open_query = open(sql, "r")
#             sql = open_query.read()
#         else:
#             raise ValueError(
#                 f"File not found at {sql}. "
#                 "If not a file, make sure your script doesn't end in .sql"
#             )

#     # pd.read_sql cannot handle semi colons
#     sql = sql.replace(";", "")

#     return sql

# def sql_run(connection, sql, lower_cols=False, verbose=True) -> pd.DataFrame:
#     """
#     :description: Use db connection created to query
#                   database with a single .sql file or string containing sql
#                   query. Can handle comments and ';' character.

#     :param connection: db connection 
#     :type connection: cx_Oracle.Connection; sqlite
#     :param sql: .sql file or string containing query you want to run
#     :type sql: str
#     :param lower_cols: convert column names to lowercase, by default False
#     :type lower_cols: bool
#     :param verbose: print sql run time, by default True
#     :type verbose: bool

#     :returns:  pd.DataFrame of queried data
#     """
#     t0 = time()
#     df = pd.read_sql(_parse_sql(sql), connection)
#     t1 = time()

#     if lower_cols:
#         df.columns = df.columns.str.lower()

#     # Print query run time
#     if verbose:
#         print(str(datetime.timedelta(seconds=round(t1 - t0))))
        
#     return df

def log_output(path):
    current_date = dt.now().strftime("%Y%m%d")
    log_file = open(f"{path}log_{current_date}.txt", "w")
    sys.stdout = log_file
    return log_file