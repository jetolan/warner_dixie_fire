import pandas as pd
import shutil


def to_table(df):
    df['Report'] = df['APN'].apply(
        lambda x: f"<a href= 'doc/{x}.pdf'> {x}</a>")
    df = df.sort_values('BA>75 All Slopes', ascending=False)
    df = df.reset_index(drop=True)
    df = df.drop('geometry', axis=1)

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
    with open('../table.html', 'w') as f:
        f.write(html_string.format(table=df.to_html(
            classes='mystyle', render_links=True, escape=False)))
    shutil.copyfile('df_style.css', '../df_style.css')
    df = df.drop('Report', axis=1)
    df.to_csv('../table.csv')
    return


if __name__ == "__main__":
    df = pd.DataFrame({
        'APN': ["011180014"],
        'BA>75 All Slopes': 98,
        'BA>75 and S>30': 542,
        'BA>75 and 30>S>15': 778,
        'BA>75 and S<15': 64,
        'BA<75,BA>50  and S>30': 12467,
        'BA<75,BA>50 and 30>S>15': 1245,
        'BA<75,BA>50 and S<15': 1255,
        'BA<50,BA>25 and S>30': 355,
        'BA<50,BA>25 and 30>S>15': 345,
        'BA<50,BA>25 & S<15': 44,
        'BA<25 and S>30': 12,
        'BA<25 and 30>S>15': 34,
        'BA<25 and S<15': 12,
        'geometry': 3,
    })
    to_table(df)
