import pandas as pd


def to_table(df):
    df['Report'] = df['APN'].apply(
        lambda x: f"<a href= 'doc/{x}.pdf'> {x}</a>")
    df = df.sort_values('BA>75%,SLOPE<15%', ascending=False)
    df = df.reset_index(drop=True)
    df = df.drop('geometry', axis=1)
    html = df.to_html(render_links=True, escape=False)
    with open('../table.html', 'w') as dst:
        dst.write(html)
    return


if __name__ == "__main__":
    df = pd.DataFrame({
        'APN': ["011180014"],
        'BA>75%,SLOPE<15%': [2.3],
    })
    to_table(df)
