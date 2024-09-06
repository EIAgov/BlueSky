####################################################################################################################
# Setup

# Import pacakges
import pandas as pd
import pyomo.environ as pyo
import os

from dash import Dash, html, dcc, html, Input, Output
import plotly.express as px
import plotly as plotly

# setting up directories
dir_output = os.path.join(os.path.dirname(__file__))
# dir_inputs = os.path.join(dir_output, '..', 'src\\models\\electricity\\input')


# add a new index using a mapping dataframe and return a dataframe with the input index
def mapping(df, mapdf, col, indexes):
    df = pd.merge(df, mapdf, on=col, how='outer')
    df = df[indexes]
    df = df.dropna(how='any', axis=0)

    return df


# read the .csv while appending the dataframe to a list
def read_run_csv(csv, run, df_list):
    df = pd.read_csv(csv)
    df['run'] = run
    df_list.append(df)

    return df_list


# get all the electricity run names from the output file
os.chdir(dir_output)
all_runs = []
for root, dirs, files in os.walk(dir_output):
    if 'electricity' in dirs:
        all_runs.append(os.path.relpath(os.path.join(root, 'electricity')))

# empty dataframes for the variarables output
df_generation = []
df_capacitybuilds = []
df_capacityretire = []
df_capacitytotal = []
df_storagelevel = []
df_storageinflow = []
df_storageoutflow = []
df_trade = []
df_tradecan = []
df_unmetload = []

# a loop for reading each .csv of each run folder and appending them into the dataframe and adding the a column for their run name
for i in range(len(all_runs)):
    run_output = os.path.join(dir_output, all_runs[i])

    # switches to the variables folder
    run_variables = run_output + '\\variables'
    os.chdir(run_variables)

    # grabs the run name
    runname = all_runs[i]

    # the try and except is for when file is missing when happens if the model is turned off
    try:
        df_generation = read_run_csv('Generation.csv', runname, df_generation)
    except FileNotFoundError:
        pass

    try:
        df_capacitybuilds = read_run_csv('CapacityBuilds.csv', runname, df_capacitybuilds)
    except FileNotFoundError:
        pass

    try:
        df_capacityretire = read_run_csv('CapacityRetirements.csv', runname, df_capacityretire)
    except FileNotFoundError:
        pass

    try:
        df_capacitytotal = read_run_csv('TotalCapacity.csv', runname, df_capacitytotal)
    except FileNotFoundError:
        pass

    try:
        df_storagelevel = read_run_csv('Storage_level.csv', runname, df_storagelevel)
    except FileNotFoundError:
        pass

    try:
        df_storageinflow = read_run_csv('Storage_inflow.csv', runname, df_storageinflow)
    except FileNotFoundError:
        pass

    try:
        df_storageoutflow = read_run_csv('Storage_outflow.csv', runname, df_storageoutflow)
    except FileNotFoundError:
        pass

    try:
        df_trade = read_run_csv('TradeToFrom.csv', runname, df_trade)
    except FileNotFoundError:
        pass

    try:
        df_tradecan = read_run_csv('TradeToFromCan.csv', runname, df_tradecan)
    except FileNotFoundError:
        pass

    try:
        df_unmetload = read_run_csv('unmet_Load.csv', runname, df_unmetload)
    except FileNotFoundError:
        pass

# concat all the runs into one table, there a try statements here due to whether the dataframe has values in them
try:
    df_generation = pd.concat(df_generation)
except ValueError:
    print('Generation dataframe is empty.')
try:
    df_capacitybuilds = pd.concat(df_capacitybuilds)
except ValueError:
    print('Capacity build dataframe is empty.')
try:
    df_capacityretire = pd.concat(df_capacityretire)
except ValueError:
    print('Capacity retirement dataframe is empty.')
try:
    df_capacitytotal = pd.concat(df_capacitytotal)
except ValueError:
    print('Capacity total dataframe is empty.')
try:
    df_storagelevel = pd.concat(df_storagelevel)
except ValueError:
    print('Storage level dataframe is empty.')
try:
    df_storageinflow = pd.concat(df_storageinflow)
except ValueError:
    print('Storage inflow dataframe is empty.')
try:
    df_storageoutflow = pd.concat(df_storageoutflow)
except ValueError:
    print('Storage outflow dataframe is empty.')
try:
    df_trade = pd.concat(df_trade)
except ValueError:
    print('Trade dataframe is empty.')
try:
    df_tradecan = pd.concat(df_tradecan)
except ValueError:
    print('Canada trade dataframe is empty.')
try:
    df_unmetload = pd.concat(df_unmetload)
except ValueError:
    print('Unmet load dataframe is empty.')

# swithcing directory to inmport the pt mapping to tech and color
os.chdir(dir_output)
df_ptcolor = pd.read_csv('pt_colors.csv')

# loop to create a dictionary for inputting into dash plotly
colorsetting = {}
for i in range(len(df_ptcolor)):
    tech = df_ptcolor['tech'][i]
    color = df_ptcolor['hex'][i]
    colorsetting[tech] = color

# sum the steps in the generation table
try:
    df_generation = df_generation[['run', 'pt', 'r', 'y', 'hr', 'Generation']]
    df_generation = (
        df_generation.groupby(['run', 'pt', 'r', 'y', 'hr']).Generation.sum().reset_index()
    )
    df_generation = mapping(
        df_generation, df_ptcolor, 'pt', ['run', 'tech', 'r', 'y', 'hr', 'Generation']
    )
except TypeError:
    print('Generation dataframe is empty.')

# sum the steps in the storage tables
try:
    df_storagelevel = df_storagelevel[['run', 'pt', 'r', 'y', 'hr', 'Storage_level']]
    df_storagelevel = (
        df_storagelevel.groupby(['run', 'pt', 'r', 'y', 'hr']).Storage_level.sum().reset_index()
    )
    df_storagelevel = mapping(
        df_storagelevel, df_ptcolor, 'pt', ['run', 'tech', 'r', 'y', 'hr', 'Storage_level']
    )
except TypeError:
    print('Storage level dataframe is empty.')

try:
    df_storageinflow = df_storageinflow[['run', 'pt', 'r', 'y', 'hr', 'Storage_inflow']]
    df_storageinflow = (
        df_storageinflow.groupby(['run', 'pt', 'r', 'y', 'hr']).Storage_inflow.sum().reset_index()
    )
    df_storageinflow = mapping(
        df_storageinflow, df_ptcolor, 'pt', ['run', 'tech', 'r', 'y', 'hr', 'Storage_inflow']
    )
    df_storageinflow['Storage_flow'] = df_storageinflow['Storage_inflow'] * -1
except TypeError:
    print('Storage inflow dataframe is empty.')

try:
    df_storageoutflow = df_storageoutflow[['run', 'pt', 'r', 'y', 'hr', 'Storage_outflow']]
    df_storageoutflow = (
        df_storageoutflow.groupby(['run', 'pt', 'r', 'y', 'hr']).Storage_outflow.sum().reset_index()
    )
    df_storageoutflow = mapping(
        df_storageoutflow, df_ptcolor, 'pt', ['run', 'tech', 'r', 'y', 'hr', 'Storage_outflow']
    )
    df_storageoutflow['Storage_flow'] = df_storageoutflow['Storage_outflow']
except TypeError:
    print('Storage outflow dataframe is empty.')

df_storagecharge = pd.concat([df_storageinflow, df_storageoutflow])
df_storagecharge = df_storagecharge[['run', 'tech', 'r', 'y', 'hr', 'Storage_flow']]
df_storagecharge = (
    df_storagecharge.groupby(['run', 'tech', 'r', 'y', 'hr']).Storage_flow.sum().reset_index()
)

# sum the steps in capacity tables
try:
    df_capacitybuilds = df_capacitybuilds[['run', 'pt', 'r', 'y', 'CapacityBuilds']]
    df_capacitybuilds = (
        df_capacitybuilds.groupby(['run', 'pt', 'r', 'y']).CapacityBuilds.sum().reset_index()
    )
    df_capacitybuilds = mapping(
        df_capacitybuilds, df_ptcolor, 'pt', ['run', 'tech', 'r', 'y', 'CapacityBuilds']
    )
except TypeError:
    print('Capacity build dataframe is empty.')

try:
    df_capacityretire = df_capacityretire[['run', 'pt', 'r', 'y', 'CapacityRetirements']]
    df_capacityretire = (
        df_capacityretire.groupby(['run', 'pt', 'r', 'y']).CapacityRetirements.sum().reset_index()
    )
    df_capacityretire = mapping(
        df_capacityretire, df_ptcolor, 'pt', ['run', 'tech', 'r', 'y', 'CapacityRetirements']
    )
except TypeError:
    print('Capacity retirement dataframe is empty.')

# assume that all season have the same capacity, do the max, then sum the steps
try:
    df_capacitytotal = df_capacitytotal[['run', 'pt', 'r', 'y', 'steps', 'TotalCapacity']]
    df_capacitytotal = (
        df_capacitytotal.groupby(['run', 'pt', 'r', 'y', 'steps']).TotalCapacity.max().reset_index()
    )
    df_capacitytotal = df_capacitytotal[['run', 'pt', 'r', 'y', 'TotalCapacity']]
    df_capacitytotal = (
        df_capacitytotal.groupby(['run', 'pt', 'r', 'y']).TotalCapacity.sum().reset_index()
    )
    df_capacitytotal = mapping(
        df_capacitytotal, df_ptcolor, 'pt', ['run', 'tech', 'r', 'y', 'TotalCapacity']
    )
except TypeError:
    print('Capacity total dataframe is empty.')

# sum th steps in the trade to Canada
try:
    df_tradecan = df_tradecan[['run', 'r', 'r1', 'y', 'hr', 'TradeToFromCan']]
    df_tradecan = (
        df_tradecan.groupby(['run', 'r', 'r1', 'y', 'hr']).TradeToFromCan.sum().reset_index()
    )
except TypeError:
    print('Canada trade dataframe is empty.')

# create unique list of indexes
s_regions = pd.unique(df_generation['r'])
s_regions.sort()
s_technologies = pd.unique(df_capacitytotal['tech'])
s_years = pd.unique(df_generation['y'])
s_years.sort()
s_canregions = pd.unique(df_tradecan['r1'])
s_canregions.sort()
s_runs = pd.unique(df_generation['run'])
s_runs.sort()

# change directory back to the scripts folder (This is for the batch file to work.)
# os.chdir(dir_output)

app = Dash(__name__)

# defines the layout of the app
app.layout = html.Div(
    [
        html.Div(
            children=[
                html.H1(children='Electricity Model Viewer'),
            ],
            style={
                'textAlign': 'center',
                'padding': '2rem',
                'backgroundColor': 'rgb(166, 251, 255)',
                'boxShadow': '#e3e3e3 5px 5px 5px',
                'border-radius': '1px',
            },
        ),
        html.Div(
            children=[
                html.Label('Runs: ', style={'font-size': '17px'}),
                dcc.Dropdown(
                    id='run',
                    options=[{'label': run, 'value': run} for run in s_runs],
                    className='dropdown',
                    multi=True,
                ),
            ],
            style={'paddingTop': '2rem'},
        ),
        html.Div(
            children=[
                html.Label('Region: ', style={'font-size': '17px'}),
                dcc.Dropdown(
                    id='region',
                    options=[{'label': region, 'value': region} for region in s_regions],
                    className='dropdown',
                    multi=True,
                ),
            ],
            style={'paddingTop': '1rem', 'paddingBottom': '2rem'},
        ),
        dcc.Tabs(
            [
                dcc.Tab(
                    label='Generation',
                    style={'font-size': '20px', 'font-weight': 'bold'},
                    children=[
                        html.Div(
                            children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            children=[
                                                html.Label(
                                                    'Year: ',
                                                    style={'padding': '5rem', 'font-size': '17px'},
                                                ),
                                                dcc.Dropdown(
                                                    id='genyear',
                                                    options=[
                                                        {'label': genyear, 'value': genyear}
                                                        for genyear in s_years
                                                    ],
                                                    className='dropdown',
                                                ),
                                            ],
                                            style={'paddingTop': '2rem'},
                                        ),
                                        html.Div(
                                            children=[
                                                html.Label(
                                                    'Technology: ',
                                                    style={'padding': '5rem', 'font-size': '17px'},
                                                ),
                                                dcc.Checklist(
                                                    id='gentech',
                                                    options=[
                                                        {'label': gentech, 'value': gentech}
                                                        for gentech in s_technologies
                                                    ],
                                                ),
                                            ],
                                            style={'paddingTop': '2rem'},
                                        ),
                                    ],
                                    style={
                                        'padding': '3rem',
                                        'margin': '2rem',
                                        'backgroundColor': 'rgb(224, 224, 224)',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '3px',
                                        'marginTop': '2rem',
                                    },
                                ),
                                html.Div(
                                    children=[
                                        html.H2('Generation Area Charts'),
                                        dcc.Graph(id='gen_graph_area'),
                                        html.H2('Storage Level Area Charts'),
                                        dcc.Graph(id='storage_level_graph_area'),
                                        html.H2('Storage Flow Area Charts'),
                                        dcc.Graph(id='storage_flow_graph_area'),
                                        html.H2('Unmet Load Area Charts'),
                                        dcc.Graph(id='unmet_graph_area'),
                                    ],
                                    style={
                                        'padding': '0.3rem',
                                        'marginTop': '1rem',
                                        'marginLeft': '1rem',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '1px',
                                    },
                                ),
                            ],
                            style={'display': 'flex', 'flexDirection': 'row'},
                        ),
                        html.Div(
                            children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            children=[
                                                html.Label(
                                                    'Technology: ',
                                                    style={'padding': '5rem', 'font-size': '17px'},
                                                ),
                                                dcc.Dropdown(
                                                    id='gentech2',
                                                    options=[
                                                        {'label': gentech2, 'value': gentech2}
                                                        for gentech2 in s_technologies
                                                    ],
                                                ),
                                            ],
                                            style={'paddingTop': '2rem'},
                                        ),
                                    ],
                                    style={
                                        'padding': '3rem',
                                        'margin': '2rem',
                                        'backgroundColor': 'rgb(224, 224, 224)',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '3px',
                                        'marginTop': '2rem',
                                    },
                                ),
                                html.Div(
                                    children=[
                                        html.H2('Generation Line Charts'),
                                        dcc.Graph(id='gen_graph_line'),
                                        html.H2('Storage Level Line Charts'),
                                        dcc.Graph(id='storage_level_graph_line'),
                                        html.H2('Storage Flow Line Charts'),
                                        dcc.Graph(id='storage_flow_graph_line'),
                                        html.H2('Unmet Load Line Charts'),
                                        dcc.Graph(id='unmet_graph_line'),
                                    ],
                                    style={
                                        'padding': '0.3rem',
                                        'marginTop': '1rem',
                                        'marginLeft': '1rem',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '1px',
                                    },
                                ),
                            ],
                            style={'display': 'flex', 'flexDirection': 'row'},
                        ),
                    ],
                ),
                dcc.Tab(
                    label='Capacity',
                    style={'font-size': '20px', 'font-weight': 'bold'},
                    children=[
                        html.Div(
                            children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            children=[
                                                html.Label(
                                                    'Technology: ',
                                                    style={'padding': '5rem', 'font-size': '17px'},
                                                ),
                                                dcc.Checklist(
                                                    id='captech',
                                                    options=[
                                                        {'label': captech, 'value': captech}
                                                        for captech in s_technologies
                                                    ],
                                                ),
                                            ],
                                            style={'paddingTop': '2rem'},
                                        ),
                                    ],
                                    style={
                                        'padding': '3rem',
                                        'margin': '2rem',
                                        'backgroundColor': 'rgb(224, 224, 224)',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '3px',
                                        'marginTop': '2rem',
                                    },
                                ),
                                html.Div(
                                    children=[
                                        html.H2('Capacity Total Bar Charts'),
                                        dcc.Graph(id='cap_graph_bar'),
                                        html.H2('Capacity Builds Bar Charts'),
                                        dcc.Graph(id='cap_build_graph_bar'),
                                        html.H2('Capacity Retirements Bar Charts'),
                                        dcc.Graph(id='cap_retire_graph_bar'),
                                    ],
                                    style={
                                        'padding': '0.3rem',
                                        'marginTop': '1rem',
                                        'marginLeft': '1rem',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '1px',
                                    },
                                ),
                            ],
                            style={'display': 'flex', 'flexDirection': 'row'},
                        ),
                    ],
                ),
                dcc.Tab(
                    label='Trade',
                    style={'font-size': '20px', 'font-weight': 'bold'},
                    children=[
                        html.Div(
                            children=[
                                html.Div(
                                    children=[
                                        html.Div(
                                            children=[
                                                html.Label(
                                                    'Year: ',
                                                    style={'padding': '5rem', 'font-size': '17px'},
                                                ),
                                                dcc.Dropdown(
                                                    id='trdyear',
                                                    options=[
                                                        {'label': trdyear, 'value': trdyear}
                                                        for trdyear in s_years
                                                    ],
                                                    className='dropdown',
                                                ),
                                            ],
                                            style={'paddingTop': '2rem'},
                                        ),
                                    ],
                                    style={
                                        'padding': '3rem',
                                        'margin': '2rem',
                                        'backgroundColor': 'rgb(224, 224, 224)',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '3px',
                                        'marginTop': '2rem',
                                    },
                                ),
                                html.Div(
                                    children=[
                                        html.H2('Region Trade Charts'),
                                        dcc.Graph(id='trade_graph_area'),
                                        html.H2('Region Trade Canada Charts'),
                                        dcc.Graph(id='tradecan_graph_area'),
                                    ],
                                    style={
                                        'padding': '0.3rem',
                                        'marginTop': '1rem',
                                        'marginLeft': '1rem',
                                        'boxShadow': '#e3e3e3 1px 1px 1px',
                                        'border-radius': '1px',
                                    },
                                ),
                            ],
                            style={'display': 'flex', 'flexDirection': 'row'},
                        ),
                    ],
                ),
            ]
        ),
    ]
)

# each callback and update_figure correspond to the graph id for each chart to be updated by the filter


@app.callback(
    Output('gen_graph_area', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
    Input('gentech', 'value'),
)
def update_figure(region, genyear, run, gentech):
    filtered_df_gen = df_generation[(df_generation.y == genyear)]

    if region:
        filtered_df_gen = filtered_df_gen[filtered_df_gen['r'].isin(region)]
        filtered_df_gen = filtered_df_gen[['run', 'tech', 'y', 'hr', 'Generation']]
        filtered_df_gen = (
            filtered_df_gen.groupby(['run', 'tech', 'y', 'hr']).Generation.sum().reset_index()
        )
    else:
        filtered_df_gen = filtered_df_gen[['run', 'tech', 'y', 'hr', 'Generation']]
        filtered_df_gen = (
            filtered_df_gen.groupby(['run', 'tech', 'y', 'hr']).Generation.sum().reset_index()
        )

    if gentech:
        filtered_df_gen = filtered_df_gen[filtered_df_gen['tech'].isin(gentech)]

    if run:
        filtered_df_gen = filtered_df_gen[filtered_df_gen['run'].isin(run)]

    fig_gen = px.area(
        filtered_df_gen,
        x='hr',
        y='Generation',
        color='tech',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_gen


@app.callback(
    Output('storage_level_graph_area', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
)
def update_figure(region, genyear, run):
    filtered_df_storagelevel = df_storagelevel[(df_storagelevel.y == genyear)]

    if region:
        filtered_df_storagelevel = filtered_df_storagelevel[
            filtered_df_storagelevel['r'].isin(region)
        ]
        filtered_df_storagelevel = filtered_df_storagelevel[
            ['run', 'tech', 'y', 'hr', 'Storage_level']
        ]
        filtered_df_storagelevel = (
            filtered_df_storagelevel.groupby(['run', 'tech', 'y', 'hr'])
            .Storage_level.sum()
            .reset_index()
        )
    else:
        filtered_df_storagelevel = filtered_df_storagelevel[
            ['run', 'tech', 'y', 'hr', 'Storage_level']
        ]
        filtered_df_storagelevel = (
            filtered_df_storagelevel.groupby(['run', 'tech', 'y', 'hr'])
            .Storage_level.sum()
            .reset_index()
        )

    if run:
        filtered_df_storagelevel = filtered_df_storagelevel[
            filtered_df_storagelevel['run'].isin(run)
        ]

    fig_storagelevel = px.area(
        filtered_df_storagelevel,
        x='hr',
        y='Storage_level',
        color='tech',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_storagelevel


@app.callback(
    Output('storage_flow_graph_area', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
)
def update_figure(region, genyear, run):
    filtered_df_storagecharge = df_storagecharge[(df_storagecharge.y == genyear)]

    if region:
        filtered_df_storagecharge = filtered_df_storagecharge[
            filtered_df_storagecharge['r'].isin(region)
        ]
        filtered_df_storagecharge = filtered_df_storagecharge[
            ['run', 'tech', 'y', 'hr', 'Storage_flow']
        ]
        filtered_df_storagecharge = (
            filtered_df_storagecharge.groupby(['run', 'tech', 'y', 'hr'])
            .Storage_flow.sum()
            .reset_index()
        )
    else:
        filtered_df_storagecharge = filtered_df_storagecharge[
            ['run', 'tech', 'y', 'hr', 'Storage_flow']
        ]
        filtered_df_storagecharge = (
            filtered_df_storagecharge.groupby(['run', 'tech', 'y', 'hr'])
            .Storage_flow.sum()
            .reset_index()
        )

    if run:
        filtered_df_storagecharge = filtered_df_storagecharge[
            filtered_df_storagecharge['run'].isin(run)
        ]

    fig_storagecharge = px.area(
        filtered_df_storagecharge,
        x='hr',
        y='Storage_flow',
        color='tech',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_storagecharge


@app.callback(
    Output('unmet_graph_area', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
)
def update_figure(region, genyear, run):
    filtered_df_unmetload = df_unmetload[(df_unmetload.y == genyear)]

    if region:
        filtered_df_unmetload = filtered_df_unmetload[filtered_df_unmetload['r'].isin(region)]
        filtered_df_unmetload = filtered_df_unmetload[['run', 'y', 'hr', 'unmet_Load']]
        filtered_df_unmetload = (
            filtered_df_unmetload.groupby(['run', 'y', 'hr']).unmet_Load.sum().reset_index()
        )
    else:
        filtered_df_unmetload = filtered_df_unmetload[['run', 'y', 'hr', 'unmet_Load']]
        filtered_df_unmetload = (
            filtered_df_unmetload.groupby(['run', 'y', 'hr']).unmet_Load.sum().reset_index()
        )

    if run:
        filtered_df_unmetload = filtered_df_unmetload[filtered_df_unmetload['run'].isin(run)]

    fig_unmetload = px.area(
        filtered_df_unmetload, x='hr', y='unmet_Load', facet_col='run', width=1600, height=500
    )
    return fig_unmetload


@app.callback(
    Output('gen_graph_line', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
    Input('gentech2', 'value'),
)
def update_figure(region, genyear, run, gentech2):
    filtered_df_gen = df_generation[(df_generation.y == genyear) & (df_generation.tech == gentech2)]

    if region:
        filtered_df_gen = filtered_df_gen[filtered_df_gen['r'].isin(region)]

    if run:
        filtered_df_gen = filtered_df_gen[filtered_df_gen['run'].isin(run)]

    fig_gen = px.line(
        filtered_df_gen,
        x='hr',
        y='Generation',
        color='r',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_gen


@app.callback(
    Output('storage_level_graph_line', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
    Input('gentech2', 'value'),
)
def update_figure(region, genyear, run, gentech2):
    filtered_df_storagelevel = df_storagelevel[
        (df_storagelevel.y == genyear) & (df_storagelevel.tech == gentech2)
    ]

    if region:
        filtered_df_storagelevel = filtered_df_storagelevel[
            filtered_df_storagelevel['r'].isin(region)
        ]

    if run:
        filtered_df_storagelevel = filtered_df_storagelevel[
            filtered_df_storagelevel['run'].isin(run)
        ]

    fig_storagelevel = px.line(
        filtered_df_storagelevel,
        x='hr',
        y='Storage_level',
        color='r',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_storagelevel


@app.callback(
    Output('storage_flow_graph_line', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
    Input('gentech2', 'value'),
)
def update_figure(region, genyear, run, gentech2):
    filtered_df_storagecharge = df_storagecharge[
        (df_storagecharge.y == genyear) & (df_storagecharge.tech == gentech2)
    ]

    if region:
        filtered_df_storagecharge = filtered_df_storagecharge[
            filtered_df_storagecharge['r'].isin(region)
        ]

    if run:
        filtered_df_storagecharge = filtered_df_storagecharge[
            filtered_df_storagecharge['run'].isin(run)
        ]

    fig_storagecharge = px.line(
        filtered_df_storagecharge,
        x='hr',
        y='Storage_flow',
        color='r',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_storagecharge


@app.callback(
    Output('unmet_graph_line', 'figure'),
    Input('region', 'value'),
    Input('genyear', 'value'),
    Input('run', 'value'),
)
def update_figure(region, genyear, run):
    filtered_df_unmetload = df_unmetload[(df_unmetload.y == genyear)]

    if region:
        filtered_df_unmetload = filtered_df_unmetload[filtered_df_unmetload['r'].isin(region)]

    if run:
        filtered_df_unmetload = filtered_df_unmetload[filtered_df_unmetload['run'].isin(run)]

    fig_unmetload = px.line(
        filtered_df_unmetload,
        x='hr',
        y='unmet_Load',
        color='r',
        facet_col='run',
        width=1600,
        height=500,
    )
    return fig_unmetload


@app.callback(
    Output('cap_graph_bar', 'figure'),
    Input('region', 'value'),
    Input('run', 'value'),
    Input('captech', 'value'),
)
def update_figure(region, run, captech):
    filtered_df_capacitytotal = df_capacitytotal

    if region:
        filtered_df_capacitytotal = df_capacitytotal[df_capacitytotal['r'].isin(region)]
        filtered_df_capacitytotal = filtered_df_capacitytotal[['run', 'tech', 'y', 'TotalCapacity']]
        filtered_df_capacitytotal = (
            filtered_df_capacitytotal.groupby(['run', 'tech', 'y'])
            .TotalCapacity.sum()
            .reset_index()
        )
    else:
        filtered_df_capacitytotal = filtered_df_capacitytotal[['run', 'tech', 'y', 'TotalCapacity']]
        filtered_df_capacitytotal = (
            filtered_df_capacitytotal.groupby(['run', 'tech', 'y'])
            .TotalCapacity.sum()
            .reset_index()
        )

    if captech:
        filtered_df_capacitytotal = filtered_df_capacitytotal[
            filtered_df_capacitytotal['tech'].isin(captech)
        ]

    if run:
        filtered_df_capacitytotal = filtered_df_capacitytotal[
            filtered_df_capacitytotal['run'].isin(run)
        ]

    fig_capacitytotal = px.bar(
        filtered_df_capacitytotal,
        x='y',
        y='TotalCapacity',
        color='tech',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_capacitytotal


@app.callback(
    Output('cap_build_graph_bar', 'figure'),
    Input('region', 'value'),
    Input('run', 'value'),
    Input('captech', 'value'),
)
def update_figure(region, run, captech):
    filtered_df_capacitybuilds = df_capacitybuilds

    if region:
        filtered_df_capacitybuilds = df_capacitybuilds[df_capacitybuilds['r'].isin(region)]
        filtered_df_capacitybuilds = filtered_df_capacitybuilds[
            ['run', 'tech', 'y', 'CapacityBuilds']
        ]
        filtered_df_capacitybuilds = (
            filtered_df_capacitybuilds.groupby(['run', 'tech', 'y'])
            .CapacityBuilds.sum()
            .reset_index()
        )
    else:
        filtered_df_capacitybuilds = filtered_df_capacitybuilds[
            ['run', 'tech', 'y', 'CapacityBuilds']
        ]
        filtered_df_capacitybuilds = (
            filtered_df_capacitybuilds.groupby(['run', 'tech', 'y'])
            .CapacityBuilds.sum()
            .reset_index()
        )

    if captech:
        filtered_df_capacitybuilds = filtered_df_capacitybuilds[
            filtered_df_capacitybuilds['tech'].isin(captech)
        ]

    if run:
        filtered_df_capacitybuilds = filtered_df_capacitybuilds[
            filtered_df_capacitybuilds['run'].isin(run)
        ]

    fig_capacitybuilds = px.bar(
        filtered_df_capacitybuilds,
        x='y',
        y='CapacityBuilds',
        color='tech',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_capacitybuilds


@app.callback(
    Output('cap_retire_graph_bar', 'figure'),
    Input('region', 'value'),
    Input('run', 'value'),
    Input('captech', 'value'),
)
def update_figure(region, run, captech):
    filtered_df_capacityretire = df_capacityretire

    if region:
        filtered_df_capacityretire = df_capacityretire[df_capacityretire['r'].isin(region)]
        filtered_df_capacityretire = filtered_df_capacityretire[
            ['run', 'tech', 'y', 'CapacityRetirements']
        ]
        filtered_df_capacityretire = (
            filtered_df_capacityretire.groupby(['run', 'tech', 'y'])
            .CapacityRetirements.sum()
            .reset_index()
        )
    else:
        filtered_df_capacityretire = filtered_df_capacityretire[
            ['run', 'tech', 'y', 'CapacityRetirements']
        ]
        filtered_df_capacityretire = (
            filtered_df_capacityretire.groupby(['run', 'tech', 'y'])
            .CapacityRetirements.sum()
            .reset_index()
        )

    if captech:
        filtered_df_capacityretire = filtered_df_capacityretire[
            filtered_df_capacityretire['tech'].isin(captech)
        ]

    if run:
        filtered_df_capacityretire = filtered_df_capacityretire[
            filtered_df_capacityretire['run'].isin(run)
        ]

    fig_capacityretire = px.bar(
        filtered_df_capacityretire,
        x='y',
        y='CapacityRetirements',
        color='tech',
        facet_col='run',
        color_discrete_map=colorsetting,
        width=1600,
        height=500,
    )
    return fig_capacityretire


@app.callback(
    Output('trade_graph_area', 'figure'),
    Input('region', 'value'),
    Input('trdyear', 'value'),
    Input('run', 'value'),
)
def update_figure(region, trdyear, run):
    filtered_df_trade = df_trade[(df_trade.y == trdyear)]

    if region:
        filtered_df_trade = filtered_df_trade[filtered_df_trade['r'].isin(region)]
        filtered_df_trade = filtered_df_trade[['run', 'r1', 'y', 'hr', 'TradeToFrom']]
        filtered_df_trade = (
            filtered_df_trade.groupby(['run', 'r1', 'y', 'hr']).TradeToFrom.sum().reset_index()
        )
    else:
        filtered_df_trade = filtered_df_trade[['run', 'r1', 'y', 'hr', 'TradeToFrom']]
        filtered_df_trade = (
            filtered_df_trade.groupby(['run', 'r1', 'y', 'hr']).TradeToFrom.sum().reset_index()
        )

    if run:
        filtered_df_trade = filtered_df_trade[filtered_df_trade['run'].isin(run)]

    fig_trade = px.area(
        filtered_df_trade,
        x='hr',
        y='TradeToFrom',
        color='r1',
        facet_col='run',
        width=1600,
        height=500,
    )
    return fig_trade


@app.callback(
    Output('tradecan_graph_area', 'figure'),
    Input('region', 'value'),
    Input('trdyear', 'value'),
    Input('run', 'value'),
)
def update_figure(region, trdyear, run):
    filtered_df_tradecan = df_tradecan[(df_tradecan.y == trdyear)]

    if region:
        filtered_df_tradecan = filtered_df_tradecan[filtered_df_tradecan['r'].isin(region)]
        filtered_df_tradecan = filtered_df_tradecan[['run', 'r1', 'y', 'hr', 'TradeToFromCan']]
        filtered_df_tradecan = (
            filtered_df_tradecan.groupby(['run', 'r1', 'y', 'hr'])
            .TradeToFromCan.sum()
            .reset_index()
        )
    else:
        filtered_df_tradecan = filtered_df_tradecan[['run', 'r1', 'y', 'hr', 'TradeToFromCan']]
        filtered_df_tradecan = (
            filtered_df_tradecan.groupby(['run', 'r1', 'y', 'hr'])
            .TradeToFromCan.sum()
            .reset_index()
        )

    if run:
        filtered_df_tradecan = filtered_df_tradecan[filtered_df_tradecan['run'].isin(run)]

    fig_tradecan = px.area(
        filtered_df_tradecan,
        x='hr',
        y='TradeToFromCan',
        color='r1',
        facet_col='run',
        width=1600,
        height=500,
    )
    return fig_tradecan


# when running, ctrl+click on the http://127.0.0.1:8050/ which opens a broswer
app.run_server(debug=True)
