
####################################################################################################################
#Setup

#Import pacakges
import pandas as pd
import pyomo.environ as pyo

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

def main(instance):
    for constraint in instance.component_objects(pyo.Var, active=True): 
        component_objects_to_df(constraint).to_csv('../output/variables/'+str(constraint)+'.csv',index=False)

    for parameter in instance.component_objects(pyo.Param, active=True): 
        component_objects_to_df(parameter).to_csv('../output/parameters/'+str(parameter)+'.csv',index=False)

    for constraint in instance.component_objects(pyo.Constraint, active=True): 
        component_objects_to_df(constraint).to_csv('../output/constraints/'+str(constraint)+'.csv',index=False)

