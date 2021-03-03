#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Creates master file for full sample, used for replication regression
and descriptives.
"""

from glob import glob

import numpy as np
import pandas as pd

from _005_create_bibliography import standardize
from _116_list_informal_pairs import read_ack_file
from _200_build_networks import write_stats
from _313_compute_author_metrics import explode

SCOPUS_FILE = "./005_bibliometric_information/Scopus.csv"
METRICS_FILE = "./313_author_metrics/metrics.csv"
CENTR_FOLDER = "./205_centralities/"
TARGET_FILE = "./580_paper_sample/master.csv"
OUTPUT_FOLDER = "./990_output/"


def aggregate(df, data, col, label=None, merge_cols=['scopus_id', 'year']):
    """Explode rows containing multiple individuals and merge on them."""
    label = label or col
    temp = explode(df, col, "scopus_id")
    data = data.set_index(merge_cols)
    return (temp.set_index(merge_cols)
                .join(data, how="left")
                .groupby(["simple_title"]).sum()
                .add_prefix(label + "_"))


def clean_jel_codes(entries):
    """Get clean JEL codes from string and return as list."""
    def is_jel_code(item):
        return item[0].isalpha() and not item[1].isalpha()

    try:
        return [i.strip() for i in entries if is_jel_code(i)]
    except TypeError:
        return None


def count(s):
    """Count explicit or implicit amount of informal collaboration."""
    if s is not np.nan:
        try:
            return len(s)
        except TypeError:
            if s:
                return s
            else:
                return 2


def custom_pivot(df, id_var, var_name, unstack_by):
    """Reshape DataFrame organized in years as columns
    to years in one column.
    """
    df = df.melt(id_vars=[id_var] + [unstack_by], var_name=var_name)
    df = df.set_index([id_var] + [var_name] + [unstack_by]).unstack()
    df.columns = df.columns.get_level_values(1)
    return df.dropna(how='all').reset_index()


def get_jel_categories(s):
    """Return set of jel categories."""
    cats = set()
    try:
        cats.update([j[0] for j in s["jel"] if j[0].isalpha()])
    except TypeError:
        pass
    try:
        cats.update([j[0] for j in s["jel3"] if j[0].isalpha()])
    except TypeError:
        pass
    return list(cats)


def read_centrality_file(f):
    """Read file with centralities and add prefixes."""
    from os.path import basename, splitext
    df = pd.read_csv(f, low_memory=False)
    net = splitext(basename(f))[0].split("_")[2]
    df['centrality'] = net + "_" + df['centrality']
    df['node'] = df['node'].astype(str)
    return df[df['node'].str.isnumeric().fillna(True)]


def main():
    # Read acknowledgements
    acks = read_ack_file()
    drops = ['prev', 'misc', 'order', 'ra', 'ind', 'data', 'editor', 'ref']
    acks = acks.drop(drops, axis=1)

    # Count JEL codes
    for col in ['jel', 'jel3']:
        acks[col] = acks[col].apply(clean_jel_codes)
    acks['num_jel'] = (acks['jel'].str.len().fillna(0) +
                       acks['jel3'].str.len().fillna(0))
    acks['num_jel'] = acks['num_jel'].astype("int8")

    # Merge with Scopus
    acks.index = acks['title'].apply(standardize)
    scopus_df = pd.read_csv(SCOPUS_FILE, index_col=0, encoding="utf8")
    df = (scopus_df.drop(["title", "journal", "year"], axis=1)
                   .join(acks, how="inner"))
    df.index.name = "simple_title"

    # Count informal collaboration
    ack_cols = ['coms', 'con', 'sem']
    for col in ack_cols:
        df['num_' + col] = df[col].apply(count)
    df["num_coms"] = df["num_coms"].replace(0, np.nan)

    # Mean values of informal collaboration
    count_cols = ["num_" + c for c in ack_cols]
    temp = df[count_cols + ["top"]]
    grouped = temp.groupby("top")[count_cols].agg(["sum", "count"])
    print("Average intensive margin of inf. collab. by journal class:")
    for c in count_cols:
        print(c)
        print(grouped[c]["sum"]/grouped[c]["count"])

    # Set to 0 for papers with acknowledgement
    papers_with = df[count_cols].fillna(0).sum(axis=1) > 0
    df['with'] = papers_with.astype(int)
    df.loc[papers_with, count_cols] = df.loc[papers_with, count_cols].fillna(0)

    # Add metrics for authors and commenters
    df = df.reset_index().set_index(["simple_title", "year"])
    dtypes = {'scopus_id': 'str', 'year': 'uint16'}
    metrics = pd.read_csv(METRICS_FILE, encoding="utf8", dtype=dtypes)
    metrics = metrics.drop(columns=['yearly_pubs', 'yearly_wpubs'], axis=1)
    metrics["cumcites"] = metrics.groupby("scopus_id")["yearly_cites"].cumsum()
    metrics['year'] = metrics['year'] + 1  # Use previous year's values
    auth_metrics = aggregate(df, metrics, "auth")
    coms_metrics = aggregate(df, metrics, "coms")
    del metrics

    # Add centralities for authors and commenters
    files = sorted(glob(CENTR_FOLDER + "*.csv"))
    centr = pd.concat([read_centrality_file(f) for f in files], axis=0, sort=True)
    centr = custom_pivot(centr, id_var='node', var_name='year', unstack_by='centrality')
    centr = centr.rename(columns={"node": "scopus_id"})
    centr['year'] = centr['year'].astype('uint16') + 1  # Previous year's values
    for netw in ("com", "auth"):
        centr[netw + "_giant"] = (~centr[netw + '_eigenvector'].isnull())*1
    fill_cols = [c for c in centr if "rank" not in c]
    centr[fill_cols] = centr[fill_cols].fillna(0)
    auth_centr = aggregate(df, centr, "auth")
    coms_centr = aggregate(df, centr, "coms")

    # Combine and fill missings
    df = df.reset_index(level=1)
    df = pd.concat([df, auth_metrics, coms_metrics, auth_centr, coms_centr],
                   axis=1, sort=True)
    for c in df.columns:
        if "giant" in c:
            df[c] = df[c].clip(upper=1)
    fill_cols = list(coms_metrics.columns) + list(coms_centr.columns)
    df.loc[papers_with, fill_cols] = df.loc[papers_with, fill_cols].fillna(0)

    # Write out
    drops = ['title', 'auth', 'coms', 'sem', 'con', 'jel', 'jel3']
    df = df.drop(drops, axis=1)
    df.to_csv(TARGET_FILE, index_label="title")

    # Analyze JEL codes
    acks['jel_cat'] = acks.apply(get_jel_categories, axis=1)
    temp = explode(acks, col="jel_cat")
    dummies = pd.get_dummies(temp.set_index("title"))
    dummies = dummies.groupby(dummies.index).sum()
    print(">>> Distribution of papers to JEL categories:\n", dummies.sum(axis=0))
    print(">>> Shares of papers with either G or E:")
    print(pd.crosstab(dummies["jel_cat_G"], dummies["jel_cat_E"],
                      margins=True, normalize=True))

    # Statistics
    jel_counter = {v: acks[v].notnull().sum() for v in ('jel', 'jel3')}
    s = {'N_of_JEL_all': jel_counter['jel'] + jel_counter['jel3'],
         'N_of_JEL_added': jel_counter["jel3"]}
    write_stats(s)


if __name__ == '__main__':
    main()
