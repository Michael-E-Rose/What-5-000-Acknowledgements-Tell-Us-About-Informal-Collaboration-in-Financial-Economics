#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Creates ranking tables by year comparing commenter and author network,
as well as figures depicting Spearman correlations over time.
"""

from configparser import ConfigParser
import pandas as pd
from collections import defaultdict

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
from pybliometrics.scopus import AuthorRetrieval

SOURCE_FILE = "./880_person_sample/network.csv"
OUTPUT_FOLDER = "./990_output/"

_rank_cols = {'com_given': "Thanks",
              'com_eigenvector_rank': 'Eigenvector cent. rank (com)',
              'com_betweenness_rank': 'Betweenness cent. rank (com)',
              'auth_eigenvector_rank': 'Eigenvector cent. rank (auth)',
              'auth_betweenness_rank': 'Betweenness cent. rank (auth)'}
_tups = [('Network of informal collaboration', 'Thanks'),
         ('Network of informal collaboration', 'Eigenvector centrality'),
         ('Network of informal collaboration', 'Betweenness centrality'),
         ('Co-author network', 'Eigenvector centrality'),
         ('Co-author network', 'Betweenness centrality')]
_labels = {'euclid': "Euclidean Index of Citations", 'com_given': "Number of Thanks",
           'auth_betweenness_rank': 'Betweenness centrality rank (co-author)',
           'auth_eigenvector_rank': 'Eigenvector centrality rank (co-author)',
           'com_betweenness_rank': 'Betweenness centrality rank (informal)',
           'com_eigenvector_rank': 'Eigenvector centrality rank (informal)'}

pd.set_option('display.max_colWIDTH', None)
config = ConfigParser()
config.optionxform = str
config.read("./graphs.cfg")
plt.rcParams['font.family'] = config["styles"]["font"]
sns.set(style=config["styles"]["style"], font=config["styles"]["font"],
        palette="deep")
mpl.rcParams['axes.unicode_minus'] = False
var_colors = dict(config["colors"])


def make_name(s, euclid=True):
    """Format name for display: Lastname, Initial (euclid)."""
    au = AuthorRetrieval(s.name, refresh=False)
    initials = " ".join([x[0] + "." for x in au.given_name.split()])
    last = au.surname.replace("*", "")
    label = ", ".join([last, initials])
    if euclid:
        label += f"({s.euclid:.1f})"
    return label


def make_multilineplot(df, fname, x, y, hue, ylabel):
    """Create lineplot facet depicting correlations over time."""
    g = sns.relplot(kind="line", data=df, x=x, y=y, height=3.7,
                    style=hue, hue_order=_labels.values(), hue=hue,
                    col="source", col_order=_labels.keys(), col_wrap=2)
    # Add each plot separately
    xlim = (df[x].min(), df[x].max())
    for ax in g.axes:
        title = ax.get_title()
        var = title.split("= ")[-1]
        label = _labels.get(var, var)
        ax.set(title=label, ylabel=ylabel, xlabel="", xlim=xlim, ylim=(-1, 1))
    # Remove legend title
    g._legend.set_title("")
    # Save
    sns.despine()
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def make_ranking(df, fname, top=30, euclid=True):
    """Create five-column ranking and output as latex file."""
    out = pd.DataFrame()
    for col in _rank_cols.keys():
        if col != 'com_given':
            tops = df.sort_values(col)
        else:
            tops = df.sort_values(col, ascending=False)
        names = tops.head(top).apply(
            lambda s: make_name(s, euclid), axis=1)
        out[col] = names.tolist()
    out.columns = pd.MultiIndex.from_tuples(_tups)
    out.index = out.index+1
    out.to_latex(fname, column_format="l"+"r"*out.shape[1],
                 multicolumn_format="c", sparsify=True)


def main():
    cols = ['scopus_id', 'year', 'euclid'] + list(_rank_cols.keys())
    df = pd.read_csv(SOURCE_FILE, index_col=0, usecols=cols)

    # Create lists and get correlations
    corrs = defaultdict(lambda: pd.DataFrame(columns=['Year', 'var', 'Spearman']))
    for year in df['year'].unique():
        subset = df[df['year'] == year].copy().drop('year', axis=1)
        # Correlations
        cur_corr = subset.corr(method='spearman').round(2)
        for col in cur_corr.columns:
            new = cur_corr[col].to_frame().drop(col).reset_index()
            new = new.rename(columns={'index': 'var', col: 'Spearman'})
            new['Year'] = year
            corrs[col] = corrs[col].append(new, sort=False)

    # Average ranks
    avg_cols = ['auth_betweenness_rank', 'auth_eigenvector_rank',
       'com_betweenness_rank', 'com_eigenvector_rank', 'com_given']
    avg = df.reset_index().groupby('scopus_id')[avg_cols].mean()
    fname = OUTPUT_FOLDER + "/Tables/rank_short_all.tex"
    make_ranking(avg, fname, euclid=False)

    # Plot correlations
    out = pd.DataFrame()
    for label, df in corrs.items():
        df["source"] = label
        out = out.append(df)
    out["var"] = out["var"].replace(_labels)
    fname = OUTPUT_FOLDER + "Figures/person_correlation.pdf"
    ylabel = "Spearman Correlation Coefficient"
    make_multilineplot(out, fname, x="Year", y="Spearman", ylabel=ylabel,
                       hue="var")
 

if __name__ == '__main__':
    main()
