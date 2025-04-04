"""autoMOO Utilities"""

import csv
import ast
import argparse
import configparser
import dash
from dash import html
from dash import dcc
from dash import dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objs as go
import numpy as np
import hiplot as hip


def input_parser():
    """
    This function parses the command line arguments and config file

    Returns
    -------
    data_file: str
        Data file pulled from config file
    cor_colormap : str
        string that dictates correlation matrix colors
    """
    # Parse command line arguments
    my_parser = argparse.ArgumentParser()

    my_parser.add_argument(
        '-c',
        '--config',
        type=str,
        action='store',
        help="This is the config file that" +
        " stores the preferences and paths",
        required=False
    )

    # Parse config file contents
    config_inputs = my_parser.parse_args()
    if config_inputs.config is None:
        raise TypeError('Please include config file to create dashboard')
    elif config_inputs.config is not None:
        my_config = configparser.ConfigParser()
        my_config.read(config_inputs.config)
        if my_config['FILES']['input'] is None:
            raise TypeError(
                'Missing data file path. Please add this to your config file'
            )
        if my_config['FILES']['input'] is None:
            raise TypeError(
                'Missing data file path. Please add this to your config file'
            )
        elif my_config['PREFERENCES']['correlation_colormap'] is None:
            raise TypeError(
                'Missing correlation colormap. Please add this to your config'
                ' file'
            )
        else:
            data_file = my_config['FILES']['input']
            cor_colormap = my_config['PREFERENCES']['correlation_colormap']
            return data_file, cor_colormap


def file_reader(path):
    """
    Read contents of Comma Separated Values (CSV) files

    TODO it is faster to guess the datatypes initially instead of for every
    row with the underlying assumption is that each column will have a
    consistent datatype

    Parameters
    ----------
    path: str
        Path to file

    Returns
    -------
    data: list
        List of dictionaries containing the contents of dataset stored in
        `path`. This has the form
        [
            {col1: val1, col2: val1},
            {col1: val2, col2: val2}
            ...
        ]
    """
    with open(path, 'r') as read_obj:
        data = []
        dict_reader = csv.DictReader(read_obj, skipinitialspace=True)
        for row in dict_reader:
            data.append({k: ast.literal_eval(v) for k, v in row.items()})

    return data


def correlation_matrix(
        data: list,
        colormap=px.colors.diverging.RdBu
):
    """
    This function creates correlation matrices.

    Parameters
    ----------
    data: list
        List of dictionaries containing the contents of dataset
    colormap: list
        List of plotly colormap

    Returns
    -------
    correlations: numpy array
        array which holds correlations
    correlation_visual: plotly.graph_objs._figure.Figure
        Plotly figure of column correlations
    """
    # Initialize vars
    correlations = []

    # Get column information
    num_cols = len(data[0])

    # Column correlation information
    for i in range(num_cols):
        col_cors = []
        for j in range(num_cols):
            x = [row[list(row.keys())[i]] for row in data]
            y = [row[list(row.keys())[j]] for row in data]
            cor = np.corrcoef(x, y)[0][1]
            col_cors.append(cor)
        correlations.append(col_cors)

    # Creates a heatmap visualization that can be used by researcher
    correlation_visual = go.Figure(
        go.Heatmap(
            z=correlations,
            x=list(data[0].keys()),
            y=list(data[0].keys()),
            colorscale=colormap,
            showscale=True,
            ygap=1,
            xgap=1
        )
    )

    return correlations, correlation_visual


def group_columns(
    data: list,
    cors: list,
    cor_threshold
):
    """
    Grouping columns

    Parameters
    ----------
    data: list
        List of dictionaries containing the contents of dataset
    cors: list
        List of lists containing column correlations
    cor_threshold: float
            Current correlation threshold selected by the user

    Returns
    -------
    data_grouped: dict
        List of dictionaries containing the grouped dataset based on
        `cor_threshold`
    group_labels_with_columns: dict
        Updated `group_labels_with_columns` based on `cor_threshold`. Keys are
        each group and contents are a list of columns in that group
    """
    # Initialization
    group_label = 0
    val = -1
    init_group = 'Group 1'
    group_labels_with_columns = {init_group: []}  # initialize empty dictionary
    data_grouped = []
    for _ in data:
        data_grouped.append({init_group: []})

    col_list = list(data[0].keys())  # create list of column labels
    for col in col_list:
        val = val + 1  # iterable value for correlation check

        # List currently grouped columns
        group_cols = sorted(
            {x for v in group_labels_with_columns.values() for x in v}
        )

        # If group label not included in grouped columns already
        if col not in group_cols:
            group_label = group_label + 1
            group_name = 'Group ' + str(group_label)

            # Store previous label in new group
            group_labels_with_columns[group_name] = [col]

            # Add column data to grouped data
            group_vals = [row[list(row.keys())[val]] for row in data]
            for i, group_val in enumerate(group_vals):
                data_grouped[i][group_name] = group_val

            # Remaining column labels
            for leftover in range(val+1, len(col_list), 1):
                # Pull correlation value
                correlation_val = cors[val][leftover]

                if correlation_val > cor_threshold:  # if higher than threshold
                    stor = col_list[leftover]  # get name of column
                    # store name of column in group
                    group_labels_with_columns[group_name].append(stor)
                else:
                    pass

    return data_grouped, group_labels_with_columns


def create_parallel(data):
    """
    Create hiplot interactive parallel plot and return as html

    Parameters
    ----------
    data: list
        List of dictionaries containing the contents of dataset

    Returns
    -------
    srcdoc: str
        String of html file
    """
    # Create plot
    exp = hip.Experiment.from_iterable(data)
    exp.display_data(hip.Displays.PARALLEL_PLOT).update({'hide': ['uid']})
    exp.display_data(hip.Displays.TABLE).update({'hide': ['uid', 'from_uid']})

    # Saving plot
    srcdoc = exp.to_html()  # Store html as string
    return srcdoc


def create_dashboard(
        data,
        cor_colormap,
):
    """
    Create dash app

    Parameters
    ----------
    data: list
        List of dictionaries containing the contents of dataset. Has form:
        [
            {col1: val1, col2: val1 ...},
            {col1: val2, col2: val2 ...}
            ...
        ]
    cor_colormap: str
        Plotly diverging colormap

    Returns
    -------
    app: Dash
        AutoMOO dashboard
    """
    # Initialize app
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # Correlation matrix
    cors, cor_fig = correlation_matrix(
        data=data,
        colormap=getattr(px.colors.diverging, cor_colormap)
    )

    app.layout = dbc.Container(
        [
            dbc.Row(dbc.Col(html.H1('AutoMOO'))),
            dbc.Row(
                dbc.Col(
                    [
                        html.Label(
                            [
                                'Select Correlation Threshold',
                                dcc.Input(
                                    id='cor_threshold',
                                    type='number'
                                )
                            ]
                        ),
                        html.Button(
                            id='update_button',
                            n_clicks=0,
                            children='Update Plot'
                        )
                    ]
                )
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(id='correlation_matrix', figure=cor_fig)
                    ),
                    dbc.Col(
                        dash_table.DataTable(
                            id='group_table',
                            columns=[
                                {'name': 'Group', 'id': 'Group'},
                                {'name': 'Columns', 'id': 'Columns'}
                            ],
                            style_data={
                                'whiteSpace': 'normal',
                                'height': 'auto',
                            },
                            style_cell_conditional=[
                                {'if': {'column_id': 'Group'},
                                 'width': '20%'}
                            ]
                        )
                    )
                ]
            ),
            dbc.Row(
                dbc.Col(
                    html.Div(
                        html.Iframe(
                            id='parallel',
                            style={'width': '100%', 'height': '1080px'}
                        )
                    ),
                )
            ),
            dcc.Store(
                id='memory',
                data={
                    'data': data,
                    'cors': cors,
                }
            )
        ]
    )

    @app.callback(
        Output('parallel', 'srcDoc'),
        Output('group_table', 'data'),
        Input('update_button', 'n_clicks'),
        State('cor_threshold', 'value'),
        State('group_table', 'data'),
        State('memory', 'data'),
    )
    def update_dashboard(
            n_clicks,
            cor_threshold,
            group_table_data,
            memory_data
    ):
        """
        Update parallel axis plots and group table

        Parameters
        ----------
        n_clicks: int
            Number of times button pressed
        cor_threshold: float
            Current correlation threshold selected by the user
        group_table_data: dict
            Group labels and columns within each group
        memory_data: dict
            Data stored in memory

        Returns
        -------
        srcdoc: str
            html rendering as string
        group_table_data: dict
            Data for the group_table display
        """
        # Unpack memory data
        data = memory_data['data']
        cors = memory_data['cors']

        if n_clicks == 0:
            srcdoc = create_parallel(data)
        else:
            data_grouped, group_labels_with_columns = group_columns(
                data=data,
                cors=cors,
                cor_threshold=cor_threshold,
            )

            # Update parallel plot
            srcdoc = create_parallel(data_grouped)

            # Update group table
            group_table_data = []
            for key, value in group_labels_with_columns.items():
                group_table_data.append(
                    {'Group': key, 'Columns': ', '.join(value)}
                )

        return srcdoc, group_table_data

    return app
