
####################################################################################################################
#Setup

#Import pacakges
import pandas as pd
import pyomo.environ as pyo
from datetime import datetime
import os

####################################################################################################################
####################################################################################################################
#POST-PROCESSING
####################################################################################################################
####################################################################################################################
#Review: sets, variables, parameters, constraints

#Sets
#for set in mod.component_objects(pyo.Set, active=True):set.pprint()

#Variables, Parameters, Constraints
def component_objects_to_df(mod_object):
    name = str(mod_object)
    #print(name)

    #creating a dataframe that reads in the paramater info
    df = pd.DataFrame()
    df['Key'] = [str(i) for i in mod_object]
    df[name] = [pyo.value(mod_object[i]) for i in mod_object]

    if not df.empty:
        #breaking out the data from the mod_object info into multiple columns
        df['Key'] = df['Key'].str.replace('(', '',regex=False).str.replace(')', '',regex=False)
        temp = df['Key'].str.split(', ', expand=True)
        for col in temp.columns: temp.rename(columns={col:'i_'+str(col)}, inplace=True)
        df = df.join(temp, how='outer')
    
    return df

##################################################################################################################
#Main Project Execution
def make_output_dir():
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    hour = now.strftime("%H")
    min = now.strftime("%M")
    dir = '../output/d'+year+month+day+hour+min+'/'
    
    if not os.path.exists(dir):
        os.makedirs(dir)
        os.makedirs(dir+'variables/')
        os.makedirs(dir+'parameters/')
        os.makedirs(dir+'constraints/')
    
    return dir

def main(instance,cols_dict):
    
    dir = make_output_dir()

    for variable in instance.component_objects(pyo.Var, active=True): 
        df = component_objects_to_df(variable)
        df.columns = ['Key'] + cols_dict[str(variable)]
        df.to_csv(dir+'variables/'+str(variable)+'.csv',index=False)

    for parameter in instance.component_objects(pyo.Param, active=True): 
        df = component_objects_to_df(parameter)
        df.columns = ['Key'] + cols_dict[str(parameter)]
        df.to_csv(dir+'parameters/'+str(parameter)+'.csv',index=False)

    for constraint in instance.component_objects(pyo.Constraint, active=True): 
        component_objects_to_df(constraint).to_csv(dir+'constraints/'+str(constraint)+'.csv',index=False)
