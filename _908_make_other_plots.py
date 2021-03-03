#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Makes different plots related to the dataset: Barchart for the number
of researchers in the dataset, histogram for the number of comments per
researcher, linechart for the yearly number of comments by researcher,
and a heatmap for the relationship of experience of author and commenter.
"""

from collections import Counter
from configparser import ConfigParser
from glob import glob

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import seaborn as sns

from _200_build_networks import write_stats

config = ConfigParser()
config.optionxform = str
config.read("./graphs.cfg")
plt.rcParams['font.family'] = config["styles"]["font"]
sns.set(style=config["styles"]["style"], font=config["styles"]["font"],
        rc={"lines.linewidth": 0.5})
mpl.rcParams['axes.unicode_minus'] = False

PAIR_FILE = "./116_informal_collaboration_pairs/pairs.csv"
NETWORKS_FOLDER = "./200_yearly_networks/"
METRICS_FILE = "./313_author_metrics/metrics.csv"
PERSONNETWORK_FILE = "./880_person_sample/network.csv"
OUTPUT_FOLDER = "./990_output/"


def make_barchart(df):
    """Plot a horizontal stacked bar showing the number of pure authors,
    commenting authors and pure commenters.
    """
    # Count
    authors = set()
    for f in glob(NETWORKS_FOLDER + "*auth.gexf"):
        authors.update(nx.read_gexf(f).nodes())
    commenters = set()
    for f in glob(NETWORKS_FOLDER + "*com.gexf"):
        commenters.update(nx.read_gexf(f).nodes())
    # Prepare
    df['scopus_id'] = df['scopus_id'].astype(str)
    pure_com = (commenters - authors)
    pure_auth = set(df[df['com_out_degree'].fillna(0) == 0]['scopus_id'].unique())
    com_auth = (commenters - pure_auth - pure_com)
    print(f">>> {len(pure_auth):,} pure authors "
          f"({sum(x.isdigit() for x in pure_auth):,} w/ Scopus ID); "
          f"{len(pure_com):,} pure commenters "
          f"({sum(x.isdigit() for x in pure_com):,} w/ Scopus ID); "
          f"{len(com_auth):,} mixed types "
          f"({sum(x.isdigit() for x in com_auth):,} w/ Scopus ID)")
    out = pd.DataFrame(data=[len(pure_auth), len(com_auth), len(pure_com)],
                       index=['pure_auth', 'com_auth', 'pure_com'],
                       columns=['persons'])
    # Plot
    fig, ax = plt.subplots(figsize=(25, 4))
    out.T.plot(kind='barh', stacked=True, legend=False, ax=ax, colormap='PiYG',
               alpha=0.7)
    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)
    # Hatched area for commenting authors
    ax.patches[1].set(hatch="O", facecolor=ax.patches[0].get_facecolor(),
                      edgecolor=ax.patches[2].get_facecolor(), lw=0)
    # Add labels inside
    for p in ax.patches:
        ax.annotate(f"{int(p.get_width()):,}", fontsize=40,
                    xy=(p.get_x() + p.get_width()/3.1, -0.05))
    # Add bracket outside (set width manually)
    auth_cent = (len(authors)/out.sum())/2 - 0.01
    bbox = {"boxstyle": 'square', "fc": 'white'}
    arrowprops = {"arrowstyle": '-[, widthB=8.35, lengthB=1',
                  "lw": 2.0, "color": "black"}
    ax.annotate('Authors', xy=(auth_cent, 0.90), xytext=(auth_cent, 0.9),
                xycoords='axes fraction', ha='center', va='bottom',
                bbox=bbox, fontsize=35, arrowprops=arrowprops)
    com_cent = (len(commenters)/out.sum())/2 + auth_cent - 0.054
    arrowprops.update({"arrowstyle": '-[, widthB=12.73, lengthB=1'})
    ax.annotate('Commenters', xy=(com_cent, 0.10), xytext=(com_cent, 0),
                xycoords='axes fraction', ha='center', va='bottom',
                bbox=bbox, fontsize=35, arrowprops=arrowprops)
    # Save
    sns.despine(ax=None, top=True, right=True, left=True, bottom=True)
    fname = OUTPUT_FOLDER + "Figures/barh_persons.pdf"
    fig.savefig(fname, bbox_inches="tight")
    fname = OUTPUT_FOLDER + "Figures/barh_persons.png"
    fig.savefig(fname, bbox_inches="tight")
    plt.clf()
    # Write stats
    stats = {'N_of_Authors_pure': len(pure_auth),
             'N_of_Commenters_pure': len(pure_com),
             'N_of_Authors_commenting': len(com_auth)}
    write_stats(stats)


def make_histogram(df, col='com_given', label="Number"):
    """Make histogram of `col` versus experience with CDF."""
    # Add missing years
    years = range(int(df['experience'].min()), int(df['experience'].max()))
    miss = [e for e in years if e not in df['experience'].unique()]
    for exp in miss:
        df = df.append(pd.Series({'experience': exp, 'com_given': 0}),
                       ignore_index=True)
    # Aggregate
    cumul = df.groupby('experience')[col].sum().to_frame().sort_index()
    counts = df.groupby('experience')[col].count().to_frame().sort_index()
    # Percentage for CDF
    cumul['cumsum'] = cumul[col].cumsum()
    counts['cumsum'] = counts[col].cumsum()
    cumul['perc_comments'] = 100*cumul['cumsum']/cumul[col].sum()
    counts['perc_commenters'] = 100*counts['cumsum']/counts[col].sum()
    mode_com = df["experience"].value_counts().index[1]
    print(f">>> Mode positive experience of commenters: {int(mode_com)}")
    # Count values for histogram
    values = [int(t[1]) * [t[2]] for t in
              cumul.reset_index()[[col, 'experience']].itertuples()]
    values = [e for sl in values for e in sl]
    mod_com = Counter(values).most_common(2)[1][0]
    print(f">>> Mode experience of comments: {mod_com}")
    # Plot Histogram
    fig, ax1 = plt.subplots()
    sns.histplot(values, kde=False, ax=ax1, bins=cumul.shape[0],
                 color="#6087b5", label='Comments')
    sns.histplot(df.set_index(col)['experience'], ax=ax1, kde=False,
                 bins=cumul.shape[0], color="#d4916a", label='Commenters')
    plt.legend()
    ax2 = ax1.twinx()
    # Add CDF
    cumul['perc_comments'].plot(ax=ax2, grid=False, color="#6087b5")
    counts['perc_commenters'].plot(ax=ax2, grid=False, color="#d4916a")
    # Aesthetics
    ax1.set(xlabel='Experience (years since/until first publication)',
            ylabel=label)
    ax2.set(ylim=(0, 100), ylabel="Cumulative Density Funcation (in %)")
    # Save
    sns.despine(ax=ax1)
    fname = f"{OUTPUT_FOLDER}Figures/histogram_{col}.pdf"
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def make_jointkde():
    """Create a heatmap for experience of authors and commenters."""
    # Merge with year of first publication
    df = pd.read_csv(PAIR_FILE, encoding="utf8")
    df = df[df['commenter'].str.isdigit()]
    df['commenter'] = df['commenter'].astype(int)
    metrics = pd.read_csv(METRICS_FILE, usecols=["scopus_id", "year"], encoding="utf8")
    metrics = (metrics.drop_duplicates(subset='scopus_id')
                      .rename(columns={'year': 'first_pub_year'})
                      .set_index('scopus_id'))
    df = (df.join(metrics, on='author')
            .join(metrics, on='commenter', lsuffix='_author', rsuffix='_commenter'))
    # Compute experience
    for c in ['commenter', 'author']:
        col = "experience_" + c
        df[col] = df['year'] - df['first_pub_year_' + c]
        df.loc[df[col] < 0, col] = 0
    # Plot
    g = sns.jointplot(x=df["experience_commenter"], y=df["experience_author"],
                      kind='kde', marginal_kws={"shade": True}, space=0,
                      cmap='YlGnBu', joint_kws={"shade": True})
    g = g.set_axis_labels("Commenter experience", "Author experience",
                          fontsize=15)
    max_val = max(df["experience_commenter"].max(), df["experience_author"].max())
    g.ax_joint.set(xlim=(0, max_val), ylim=(0, max_val))
    lims = [0, max_val]
    g.ax_joint.plot(lims, lims, linewidth=2, linestyle='--', color="#d0865c")
    sns.despine()
    fname = OUTPUT_FOLDER + "Figures/jointkde_experience.pdf"
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def main():
    df = pd.read_csv(PERSONNETWORK_FILE, encoding="utf8")
    make_barchart(df.copy())
    make_histogram(df.copy())

    make_jointkde()


if __name__ == '__main__':
    main()
