import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from astroquery.simbad import Simbad
from toco.toco import Target, get_tic_name
from astropy.coordinates import SkyCoord, get_constellation
from astropy import units as u
import warnings
warnings.filterwarnings('ignore', category=UserWarning, append=True)

app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY])
server = app.server

def print_results(tic=12350):
    print_str = ""
    try:
        tic = int(tic)
    except ValueError:
        return (None, "Not a valid TIC number")

    target = Target(tic)


    catalogData = target.query().to_pandas()

    catalogData['ra'] = catalogData['ra'].round(5)
    catalogData['dec'] = catalogData['dec'].round(5)
    catalogData['eclong'] = catalogData['eclong'].round(5)
    catalogData['eclat'] = catalogData['eclat'].round(5)
    catalogData['pmRA'] = catalogData['pmRA'].round(2)
    catalogData['pmDEC'] = catalogData['pmDEC'].round(2)
    catalogData['Tmag'] = catalogData['Tmag'].round(2)
    catalogData['Vmag'] = catalogData['Vmag'].round(2)
    catalogData['Kmag'] = catalogData['Kmag'].round(2)

    output_table = catalogData[['ID', 'ra', 'dec', 'pmRA', 'pmDEC',
                                'eclong', 'eclat', 'Tmag', 'Vmag',
                                'Kmag', 'Teff',
                                'rad', 'mass', 'd', ]].iloc[0:1]

    skobj = SkyCoord(ra=catalogData['ra'] * u.degree,
                     dec=catalogData['dec'] * u.degree,
                     frame='icrs')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')

        customSimbad = Simbad()
        customSimbad.add_votable_fields(
            'ra(2;A;ICRS;J2000;2000)', 'dec(2;D;ICRS;J2000;2000)')
        customSimbad.remove_votable_fields('coordinates')

        # try different search radii, be fast if possible
        for i in [5, 10, 20]:
            result_table = customSimbad.query_region(
                skobj, radius=i * u.arcsec)
            if result_table is None:
                continue
            else:
                break

    if result_table is None:
        print_str += "\n\n"
        print_str += "No Simbad target resolved\n\n"
    else:
        print_str += "Target name: {}\n\n".format(
            result_table['MAIN_ID'][0])
    print_str += "The target is in constellation {}\n\n".format(
        get_constellation(skobj)[0])

    obs_sectors = target.get_obs()
    obs2, obsffi, obs20 = obs_sectors

    print_str += 'FFI data at MAST for sectors:      {}\n\n'.format(
        str(sorted(list(set(obsffi)))).replace("[", r"\[").replace("]", r"\]"))
    print_str += '2-min data at MAST for sectors:    {}\n\n'.format(
        str(sorted(list(set(obs2)))).replace("[", r"\[").replace("]", r"\]"))
    print_str += '20-s data at MAST for sectors:     {}\n\n'.format(
        str(sorted(list(set(obs20)))).replace("[", r"\[").replace("]", r"\]"))
    return output_table, print_str




jumbotron = dbc.Jumbotron(
    [
        html.H1("toco in the browser - like magic", className="display-3"),
        html.P(dcc.Markdown(
            "Based on [toco](https://github.com/tessgi/toco), a "
            "tool for quickly finding information on TESS sources"),
            className="lead",
        ),
        html.Hr(className="my-2"),
    ]
)

name_form = dbc.Form(
    [
        dbc.FormGroup(
            [
                dbc.Label("Target Name:", className="mr-2"),
                dbc.Input(type="text", placeholder="Star Name", id="my-input-name",
                          ),
            ],
            className="mr-3",
        ),
        dbc.Button("Submit", color="primary", id="submit-val-name"),
    ],
    inline=True,
)

tic_form = dbc.Form(
    [
        dbc.FormGroup(
            [
                dbc.Label("TIC number:", className="mr-2"),
                dbc.Input(type="text", placeholder="TIC Number",
                          id="my-input-tic"),
            ],
            className="mr-3",
        ),
        dbc.Button("Submit", color="primary", id="submit-val-tic"),
    ],
    inline=True,
)

app.layout = dbc.Container(
    [
        jumbotron,
        name_form,
        html.Br(),
        tic_form,
        html.Br(),
        dbc.Spinner(id="loading-1", type="grow",
                    children=[html.Div(id='my-output-table')]),
        html.Br(),
        html.Div(dcc.Markdown(id='my-output-text')),
        html.Footer(dcc.Markdown("Build by [Tom Barclay](tombarclay.com). "
            "Checkout the code on [GitHub](https://github.com/mrtommyb/toco-online)."))
    ],
    fluid=True,
)


@app.callback(
    [Output(component_id='my-output-table', component_property='children'),
        Output(component_id='my-output-text', component_property='children')],
    [Input("submit-val-name", "n_clicks"),
     Input(component_id='my-input-name', component_property='value'),
     Input("submit-val-tic", "n_clicks"),
     Input(component_id='my-input-tic', component_property='value')])
def update_output(n_clicks_name, input_value_name, n_clicks_tic,
                  input_value_tic):

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if "submit-val-name" in changed_id:

        tic = get_tic_name(input_value_name)
        df, print_str = print_results(tic=tic)
        if df is None:
            return None, print_str
        else:
            tbl = dash_table.DataTable(
                id='my-output',
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict('records'),
                style_table={
                    'width': '80%',
                }
            )
        return tbl, print_str

    elif "submit-val-tic" in changed_id:
        tic = input_value_tic
        df, print_str = print_results(tic=tic)
        if df is None:
            return [None, print_str]
        else:
            tbl = dash_table.DataTable(
                id='my-output',
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict('records'),
                style_table={
                    'width': '80%',
                }
            )
        return tbl, print_str
    else:
        return [None, None]


if __name__ == '__main__':
    app.run_server(debug=True)
