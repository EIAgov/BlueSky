####################################################################################################################
####################################################################################################################
#DATABASE CODE
####################################################################################################################
####################################################################################################################

#import packages
import preprocessor as pp
import pandas as pd
from pyomo.common.timing import TicTocTimer
timer = TicTocTimer()
timer.tic('start')

####################################################################################################################
####################################################################################################################
#PREPROCESSOR CODE
####################################################################################################################
####################################################################################################################

all_frames = {}
dir = '../input/temp'
# add csv input files to all frames 
all_frames = pp.readin_csvs(dir, all_frames)

####################################################################################################################
####################################################################################################################
#DEFINITIONS CODE
####################################################################################################################
####################################################################################################################

def create_pkindx_col(df):
    df = df.reset_index()
    df = df.rename(columns={'index': 'id'})
    df_final = df.set_index('id')
    return df_final

for key, df in all_frames.items():
    try:
        all_frames[key] = create_pkindx_col(df)
    except Exception as e:
        print(f"error with {key}: {str(e)}")
        continue

#declare dicitonary of dataframes
dataframes = all_frames


#import packages
import pandas as pd
from textwrap import dedent
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def generate_class_definition(table_name, df):
    class_name = table_name
    index_col = df.index.name
    fields = []

    if index_col is not None:
        dtype = 'Integer'
        if pd.api.types.is_float_dtype(df.index.dtype):
            dtype = 'Float'
        elif pd.api.types.is_string_dtype(df.index.dtype):
            dtype = 'String'
        fields.append(f"{index_col} = Column({dtype}, primary_key=True)")

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            fields.append(f"{col} = Column(DateTime)")
        elif pd.api.types.is_float_dtype(df[col].dtype):
            fields.append(f"{col} = Column(Float)")
        elif pd.api.types.is_integer_dtype(df[col].dtype):
            fields.append(f"{col} = Column(Integer)")
        else:
            fields.append(f"{col} = Column(String)")

    fields_str = "\n    ".join(fields)
    class_definition = f"""
class {class_name}(Base):
    __tablename__ = '{table_name}'
    {fields_str}
    """
    return class_definition

# Write definitions to a .py file
with open('cem_db_definitions.py', 'w') as f:
    f.write("from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime\n")
    f.write("from sqlalchemy.orm import sessionmaker, declarative_base\n")
    f.write("Base = declarative_base()\n\n")

    for table_name, df in dataframes.items():
        class_def = generate_class_definition(table_name, df)
        f.write(dedent(class_def))

    # f.write("\n# Database setup\n")
    # f.write("engine = create_engine('sqlite:///../input/cem_inputs_database.db')\n")
    # f.write("Base.metadata.create_all(engine)\n\n")
    # f.write("# If you need to interact with the database\n")
    # f.write("Session = sessionmaker(bind=engine)\n")
    # f.write("session = Session()\n\n")
    # f.write("# Add data handling below as required\n")
    # f.write("session.close()\n")

####################################################################################################################
####################################################################################################################
#WRITE DATA CODE
####################################################################################################################
####################################################################################################################

#import packages
import inspect
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import cem_db_definitions  # Import your module with table definitions
from cem_db_definitions import Base

def create_table_mapping(module):
    """
    Creates a mapping of table names to their SQLAlchemy class definitions
    found in the given module. Assumes that each table class inherits from `Base`
    and that the primary key column is named 'id'.

    Args:
    - module: A module containing SQLAlchemy table class definitions.

    Returns:
    - A dictionary mapping table class names to their class definitions.
    """
    mapping = {}
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, Base) and hasattr(obj, '__tablename__'):
            mapping[obj.__tablename__] = obj
    return mapping


def prepare_dates(df):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col]).dt.date
    return df

def load_data_to_db(session, table_class, dataframe):
    dataframe = prepare_dates(dataframe)
    for index, row in dataframe.iterrows():
        data_dict = row.to_dict()
        if dataframe.index.name:
            data_dict[dataframe.index.name] = index

        # Check for existence using the primary key (id), avoiding the costly query operation
        obj = table_class(**data_dict)
        session.merge(obj)  # `merge` instead of `add` will check and update if exists, otherwise insert

    try:
        session.commit()  # Commit all the operations as a batch
    except IntegrityError:
        session.rollback()

# Initialize database and session
engine = create_engine('sqlite:///../input/cem_inputs_database.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Use the function to create the table mapping
table_mapping = create_table_mapping(cem_db_definitions)

timer.toc('setup')
# Load data using the mapping
for table_name, table_class in table_mapping.items():
    dataframe = dataframes[table_name]
    load_data_to_db(session, table_class, dataframe)
    timer.toc(table_name)

session.close()
print("Data has been loaded into the database.")