import pandas as pd
import shutil


def to_table(df):
    df['Report'] = df['APN'].apply(
        lambda x: f"<a href= 'doc/{x}.pdf'> {x}</a>")
    df = df.sort_values('BA>75% & S<15', ascending=False)
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
        'BA>75% & <15': [2.3],
        'geometry': 3,
    })
    to_table(df)
