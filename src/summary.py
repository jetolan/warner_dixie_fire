import pandas as pd
import json


def owners():

    owners_file = 'apns.json'
    with open(owners_file) as src:
        owners = json.load(src)
    # owners = pd.read_json(owners_file)
    df = pd.read_csv("../table.csv")

    usfs = df[df['APN'].isin(owners['USFS'])]
    usfs_out = usfs.sum().to_frame().transpose().drop(
        ['APN', 'Unnamed: 0'], axis=1)
    usfs_out['owner'] = 'USFS'

    nps = df[df['APN'].isin(owners['NPS'])]
    nps_out = nps.sum().to_frame().transpose().drop(
        ['APN', 'Unnamed: 0'], axis=1)
    nps_out['owner'] = 'NPS'

    cdfw = df[df['APN'].isin(owners['CDFW'])]
    cdfw_out = cdfw.sum().to_frame().transpose().drop(
        ['APN', 'Unnamed: 0'], axis=1)
    cdfw_out['owner'] = 'CDFW'

    private = df[~df['APN'].isin(owners['USFS']+owners['NPS']+owners['CDFW'])]
    private_out = private.sum().to_frame().transpose().drop(
        ['APN', 'Unnamed: 0'], axis=1)
    private_out['owner'] = 'PRIVATE'

    out = pd.concat([usfs_out, nps_out, cdfw_out, private_out])
    out = out.set_index('owner')
    out = out.sort_values('BA>75 All Slopes', ascending=False)
    out = out.astype(float).round(2)

    pd.set_option('colheader_justify', 'center')   # FOR TABLE <th>
    html_string = '''
    <html>
    <head><title>WARNER PARCELS</title></head>
    <link rel="stylesheet" type="text/css" href="df_style.css"/>
    <body>
    {table}
    </body>
    </html>.
    '''

    # OUTPUT AN HTML FILE
    with open('../summary.html', 'w') as f:
        f.write(html_string.format(table=out.to_html(
            classes='mystyle', render_links=True, escape=False)))

    return out


if __name__ == "__main__":
    out = owners()
