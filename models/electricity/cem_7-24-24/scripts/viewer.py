
####################################################################################################################
#Setup

#Import pacakges
import pandas as pd
import pyomo.environ as pyo
import os

from dash import Dash, html, dcc, html, Input, Output
import plotly.express as px

# *temporary* function for renaming any df from .csv with index names
def renamecol(df,ls):
    # check if list and # of columns match
    check = len(ls) == len(df.columns)-2
    if check == True:
        for i in list(range(0,len(df.columns)-2)):
            df = df.rename(columns={'i_'+str(i):ls[i]})
    else:
        diff = len(ls) - len(df.columns)-2
        print("number of columns are not equal, difference between input list and dataframe columns is " + str(diff))
    return df

# change directory to output
# the if statement is because dash goes through the whole code when it refreshes data, so the directory path will keep updating
# the if statement is to say if it's in the variables folder, do not change directory, otherwise go to the variables folder
if os.path.basename(os.getcwd()) == 'variables':
    pass
else:
    dir_output = os.path.join(os.path.normpath(os.getcwd() +os.sep +os.pardir) + "\\output\\variables\\")
    #Note: dir should work but wasn't working so I hard coded my dir for testing purposes
    os.chdir('D:\\Users\\CEM\\Desktop\\git\\electricity_dispatch\\output\\variables\\')

# read the generation.csv 
df_generation = pd.read_csv('Generation.csv')
df_capacitybuilds = pd.read_csv('CapacityBuilds.csv')
df_capacityretire = pd.read_csv('CapacityRetirements.csv')
df_capacitytotal = pd.read_csv('TotalCapacity.csv')
df_storagelevel = pd.read_csv('Storage_level.csv')
df_storageinflow = pd.read_csv('Storage_inflow.csv')
df_storageoutflow = pd.read_csv('Storage_outflow.csv')
df_trade = pd.read_csv('TradeToFrom.csv')
df_tradecan = pd.read_csv('TradeToFromCan.csv')
df_unmetload = pd.read_csv('unmet_Load.csv')

# *temporary* code to rename columns for Generation
# somehow get the indexnames for generation 
ls_genindexname = ['pt','y','r','steps','hr']
df_generation = renamecol(df_generation, ls_genindexname)
df_storagelevel = renamecol(df_storagelevel, ls_genindexname)
df_storageinflow = renamecol(df_storageinflow, ls_genindexname)
df_storageoutflow = renamecol(df_storageoutflow, ls_genindexname)
ls_capbuildsindexname = ['r','pt','y','steps']
df_capacitybuilds = renamecol(df_capacitybuilds, ls_capbuildsindexname)
ls_capretireindexname = ['pt','y','r','steps']
df_capacityretire = renamecol(df_capacityretire, ls_capretireindexname)
ls_cuvindexname = ['r','s','pt','steps','y']
df_capacitytotal = renamecol(df_capacitytotal, ls_cuvindexname)
ls_tradeindexname = ['r','r1','y','hr']
df_trade = renamecol(df_trade, ls_tradeindexname)
ls_tradecanindexname = ['r','r1','y','steps','hr']
df_tradecan = renamecol(df_tradecan, ls_tradecanindexname)
ls_unmetindexname = ['r','y','hr']
df_unmetload = renamecol(df_unmetload, ls_unmetindexname)

# sum the steps in the generation table
df_generation = df_generation[['pt','r','y','hr','Generation']]
df_generation = df_generation.groupby(['pt','r','y','hr']).Generation.sum().reset_index()

# sum the steps in the storage tables
df_storagelevel = df_storagelevel[['pt','r','y','hr','Storage_level']]
df_storagelevel = df_storagelevel.groupby(['pt','r','y','hr']).Storage_level.sum().reset_index()
df_storageinflow = df_storageinflow[['pt','r','y','hr','Storage_inflow']]
df_storageinflow = df_storageinflow.groupby(['pt','r','y','hr']).Storage_inflow.sum().reset_index()
df_storageoutflow = df_storageoutflow[['pt','r','y','hr','Storage_outflow']]
df_storageoutflow = df_storageoutflow.groupby(['pt','r','y','hr']).Storage_outflow.sum().reset_index()

# sum the steps in capacity tables
df_capacitybuilds = df_capacitybuilds[['pt','r','y','CapacityBuilds']]
df_capacitybuilds = df_capacitybuilds.groupby(['pt','r','y']).CapacityBuilds.sum().reset_index()
df_capacityretire = df_capacityretire[['pt','r','y','CapacityRetirements']]
df_capacityretire = df_capacityretire.groupby(['pt','r','y']).CapacityRetirements.sum().reset_index()

# assume that all season have the same capacity, do the max, then sum the steps 
df_capacitytotal = df_capacitytotal[['pt','r','y','steps','TotalCapacity']]
df_capacitytotal = df_capacitytotal.groupby(['pt','r','y','steps']).TotalCapacity.max().reset_index()
df_capacitytotal = df_capacitytotal[['pt','r','y','TotalCapacity']]
df_capacitytotal = df_capacitytotal.groupby(['pt','r','y']).TotalCapacity.sum().reset_index()

# sum th steps in the trade to Canada
df_tradecan = df_tradecan[['r','r1','y','hr','TradeToFromCan']]
df_tradecan = df_tradecan.groupby(['r','r1','y','hr']).TradeToFromCan.sum().reset_index()

# create unique list of indexes
regions = pd.unique(df_generation['r'])
technologies = pd.unique(df_generation['pt'])
years = pd.unique(df_generation['y'])
canregions = pd.unique(df_tradecan['r1'])

app = Dash(__name__)

# defines the layout of the app
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Generation', children=[
            html.Div(children=[
                html.Div(children=[
                    html.Label("Region: "),
                    dcc.Dropdown(
                        id='genregion',
                        options=[
                            {"label" : genregion, "value": genregion}
                            for genregion in regions
                        ],
                        className = "dropdown"
                    ),
                ], style = {'flex': 1} ),
                html.Div(children=[
                    html.Label("Year: "),
                    dcc.Dropdown(
                        id="genyear",
                        options=[
                            {"label": genyear, "value": genyear}
                            for genyear in years
                        ],
                        className="dropdown"
                    ),
                ], style = {'flex': 1}),
            ], style = {'padding': 20, 'display': 'flex', 'flexDirection': 'row'}),
            html.H1("Generation Chart"),
            dcc.Graph(id="gen_graph"),
            html.H1("Storage Level Chart"),
            dcc.Graph(id='storage_level_graph'),
            html.Div(children=[
                html.Div(children=[
                    html.H1("Storage Inflow Chart"),
                    dcc.Graph(id='storage_inflow_graph'),
                ], style = {'flex': 1}),
                html.Div(children=[
                    html.H1("Storage Outflow Chart"),
                    dcc.Graph(id='storage_outflow_graph'),
                ], style = {'flex': 1}),
            ], style = {'display': 'flex', 'flexDirection': 'row'}),
            html.H1("Unmet Load Chart"),
            dcc.Graph(id="unmet_graph"),
        ]),
        dcc.Tab(label='Capacity', children=[
            html.Div(children=[
                html.Div(children=[
                    html.Label("Region: "),
                    dcc.Dropdown(
                        id='capregion',
                        options=[
                            {"label" : capregion, "value": capregion}
                            for capregion in regions
                        ],
                        className = "dropdown"
                    ),
                ], style = {'flex': 1}),
            ], style = {'padding': 20, 'display': 'flex', 'flexDirection': 'row'}),
            html.H1("Capacity Total"),
            dcc.Graph(id="cap_total_graph"),
            html.Div(children=[
                html.Div(children=[
                    html.H1("Capacity Builds"),
                    dcc.Graph(id="cap_build_graph"),
                ], style = {'flex': 1}),
                html.Div(children=[
                    html.H1("Capacity Retirements"),
                    dcc.Graph(id='cap_retire_graph'),
                ], style = {'flex': 1}),
            ], style = {'display': 'flex', 'flexDirection': 'row'}),
        ]),
        dcc.Tab(label='Trade', children=[
            html.Div(children=[
                html.Div(children=[
                    html.Label("Region Supply: "),
                    dcc.Dropdown(
                        id='supregion',
                        options=[
                            {"label" : supregion, "value": supregion}
                            for supregion in regions
                        ],
                        className = "dropdown"
                    ),
                ], style = {'flex': 1}),
                html.Div(children=[
                    html.Label("Year: "),
                    dcc.Dropdown(
                        id="trdyear",
                        options=[
                            {"label": trdyear, "value": trdyear}
                            for trdyear in years
                        ],
                        className="dropdown"
                    ),
                ], style = {'flex': 1}),
            ], style = {'padding': 20, 'display': 'flex', 'flexDirection': 'row'}),
            html.H1("Region Trade"),
            dcc.Graph(id="trade_graph"),
            html.H1("Region Trade Canada"),
            dcc.Graph(id="tradecan_graph"),
        ]),
    ])
])

# each callback and update_figure correspond to the graph id for each chart to be updated by the filter

@app.callback(
    Output("gen_graph", "figure"),
    Input("genregion", "value"),
    Input("genyear", "value"),
    )

def update_figure(genregion, genyear):

    filtered_df_gen = df_generation[(df_generation.r == genregion) & (df_generation.y == genyear)]

    fig_gen = px.area(
        filtered_df_gen, x='hr', y='Generation', color='pt')
    return fig_gen

@app.callback(
    Output("storage_level_graph", "figure"),
    Input("genregion", "value"),
    Input("genyear", "value")
    )

def update_figure(genregion, genyear):

    filtered_df_storagelevel = df_storagelevel[(df_storagelevel.r == genregion) & (df_storagelevel.y == genyear)]

    fig_storagelevel = px.area(
        filtered_df_storagelevel, x='hr', y='Storage_level', color='pt')
    return fig_storagelevel

@app.callback(
    Output("storage_inflow_graph", "figure"),
    Input("genregion", "value"),
    Input("genyear", "value")
    )

def update_figure(genregion, genyear):

    filtered_df_storageinflow = df_storageinflow[(df_storageinflow.r == genregion) & (df_storageinflow.y == genyear)]

    fig_storageinflow = px.area(
        filtered_df_storageinflow, x='hr', y='Storage_inflow', color='pt')
    return fig_storageinflow

@app.callback(
    Output("storage_outflow_graph", "figure"),
    Input("genregion", "value"),
    Input("genyear", "value")
    )

def update_figure(genregion, genyear):

    filtered_df_storageoutflow = df_storageoutflow[(df_storageoutflow.r == genregion) & (df_storageoutflow.y == genyear)]

    fig_storageoutflow = px.area(
        filtered_df_storageoutflow, x='hr', y='Storage_outflow', color='pt')
    return fig_storageoutflow

@app.callback(
    Output("unmet_graph", "figure"),
    Input("genregion", "value"),
    Input("genyear", "value")
    )

def update_figure(genregion, genyear):

    filtered_df_unmetload = df_unmetload[(df_unmetload.r == genregion) & (df_unmetload.y == genyear)]

    fig_unmetload = px.area(
        filtered_df_unmetload, x='hr', y='unmet_Load')
    return fig_unmetload

@app.callback(
    Output("cap_total_graph", "figure"),
    Input("capregion", "value")
    )

def update_figure(capregion):

    filtered_df_capacitytotal = df_capacitytotal[(df_capacitytotal.r == capregion)]

    fig_capacitytotal = px.bar(
        filtered_df_capacitytotal, x='y', y='TotalCapacity', color ='pt')
    return fig_capacitytotal

@app.callback(
    Output("cap_build_graph", "figure"),
    Input("capregion", "value")
    )

def update_figure(capregion):

    filtered_df_capacitybuilds = df_capacitybuilds[(df_capacitybuilds.r == capregion)]

    fig_capacitybuilds = px.area(
        filtered_df_capacitybuilds, x='y', y='CapacityBuilds', color='pt')
    return fig_capacitybuilds

@app.callback(
    Output("cap_retire_graph", "figure"),
    Input("capregion", "value")
    )

def update_figure(capregion):

    filtered_df_capacityretire = df_capacityretire[(df_capacityretire.r == capregion)]

    fig_capacityretire = px.area(
        filtered_df_capacityretire, x='y', y='CapacityRetirements', color='pt')
    return fig_capacityretire

@app.callback(
    Output("trade_graph", "figure"),
    Input("supregion", "value"),
    Input("trdyear","value")
    )

def update_figure(supregion, trdyear):

    filtered_df_trade = df_trade[(df_trade.r == supregion) & (df_trade.y == trdyear)]

    fig_trade = px.area(
        filtered_df_trade, x='hr', y='TradeToFrom', color = 'r1')
    return fig_trade

@app.callback(
    Output("tradecan_graph", "figure"),
    Input("supregion", "value"),
    Input("trdyear","value")
    )

def update_figure(supregion, trdyear):

    filtered_df_tradecan = df_tradecan[(df_tradecan.r == supregion) & (df_tradecan.y == trdyear)]

    fig_tradecan = px.area(
        filtered_df_tradecan, x='hr', y='TradeToFromCan', color = 'r1')
    return fig_tradecan

# when running, ctrl+click on the http://127.0.0.1:8050/ which opens a broswer 
app.run_server(debug=True)