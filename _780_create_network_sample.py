#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Creates master file for network sample."""
# Code of original paper drops researchers with 5 or fewer observations, but
# not indicated in the paper

from glob import glob
from os.path import basename, splitext

import networkx as nx
import numpy as np
import pandas as pd

from _580_create_paper_sample import custom_pivot

NETWORK_FOLDER = "./200_yearly_networks/"
CENTR_FOLDER = "./205_centralities/"
METRICS_FILE = "./313_author_metrics/metrics.csv"
NEIGHBOR_FILE = "./770_network_neighbor_productivity/both.csv"
METRIC_FILE = "./313_author_metrics/metrics.csv"
TARGET_FILE = "./780_network_master/network_sample.csv"


def get_neighbors(net_type):
    """Return DataFrames with yearly direct and indirect get_neighbors"""
    neigh_1st = {}
    for file in sorted(glob(NETWORK_FOLDER + f"*{net_type}.gexf")):
        G = nx.read_gexf(file)
        year = int(basename(file)[:4])
        neigh = {n: set([k for k in G[n].keys() if k.isdigit()])
                 for n in G.nodes() if n.isdigit()}
        neigh_1st[year] = neigh
    df = pd.DataFrame.from_dict(neigh_1st)
    df.index.name = 'scopus_id'
    return df


def is_top_author(s, tops):
    """Whether any member of `s` is member of `tops`."""
    try:
        s = set([int(a) for a in s])
        return int(len(s.intersection(tops)) > 0)
    except TypeError:
        return 0


def process_centrality_file(fname):
    """Read and process centrality file (melting, dropping)."""
    label = splitext(basename(fname))[0].split("_")[-1]
    df = pd.read_csv(fname, low_memory=False)
    df = custom_pivot(df, id_var="node", var_name='year', unstack_by='centrality')
    # Drop unmatched obs
    df['node'] = pd.to_numeric(df['node'], errors='coerce')
    df = df.dropna(subset=['node'])
    # Transform variables
    df['closeness'] = np.log(1 + df['closeness'].fillna(0))
    df['betweenness'] = np.log(1 + df['betweenness'].fillna(0))
    df["year"] = df["year"].astype("uint32")
    # Rename variables
    rename = {label + '_node': 'scopus_id', label + '_year': 't'}
    return df.add_prefix(label + '_').rename(columns=rename)


def main():
    # READ IN
    cols = ["scopus_id", "year", "yearly_wpubs"]
    w_pubs = pd.read_csv(METRICS_FILE, usecols=cols, index_col=[0, 1],
                         encoding="utf8")
    w_pubs = w_pubs.unstack()
    w_pubs.columns = w_pubs.columns.droplevel()

    # CONSTRUCT VARIABLES
    # Future output (t1 till t3)
    y = w_pubs.rolling(3, min_periods=0, axis=1).sum().reset_index()
    y = y.melt(id_vars='scopus_id', var_name='t', value_name='y')
    y['y'] = np.log(1 + y['y'].fillna(0))
    y['t'] = y['t'].astype(int) - 3

    # Past output (t-n until t-5)
    qc = w_pubs.cumsum(axis=1).reset_index()
    qc = qc.melt(id_vars='scopus_id', var_name='t', value_name='qc')
    qc['t'] = qc['t'].astype(int)
    qc['t'] = qc['t'] + 5

    # Current past output (t-4 until t)
    qr = w_pubs.rolling(5, min_periods=0, axis=1).sum().reset_index()
    qr = qr.melt(id_vars='scopus_id', var_name='t', value_name='qr')
    qr['qr'] = np.log(1 + qr['qr'].fillna(0))
    qr['t'] = qr['t'].astype(int)

    # Number of years without publication after first publication year
    temp1 = w_pubs.cumsum(axis=1).replace(0, np.nan)
    temp2 = temp1.copy()
    temp2.columns = [y+1 for y in temp2.columns]
    temp1 = temp1.drop(temp1.columns[0], axis=1)
    temp2 = temp2.drop(temp2.columns[-1], axis=1)
    r = temp1 == temp2  # Compare values of t and t+1
    r = r.astype(int).cumsum(axis=1).reset_index()
    r = r.melt(id_vars='scopus_id', var_name='t', value_name='r')
    r['t'] = r['t'].astype(int)

    # Publication year (for c)
    pubs = pd.read_csv(METRIC_FILE, index_col=0)
    first_pub = pubs.groupby("scopus_id")["year"].first()
    first_pub.name = "t0"

    # Centralities
    auth = process_centrality_file(CENTR_FOLDER + "yearly_centr_auth.csv")
    com = process_centrality_file(CENTR_FOLDER + "yearly_centr_com.csv")

    # Top coauthor and top commenter
    auth_1st = get_neighbors("auth")
    com_1st = get_neighbors("com")
    for col in auth_1st.columns:
        cutoff = w_pubs[col].quantile(0.99)
        tops = set(w_pubs[w_pubs[col] >= cutoff].index)
        auth_1st[col] = auth_1st[col].apply(lambda s: is_top_author(s, tops))
        com_1st[col] = com_1st[col].apply(lambda s: is_top_author(s, tops))
    melt_params = {"id_vars": 'scopus_id', "var_name": 't',
                   "value_name": 'top_auth'}
    cols = ['scopus_id', 't']
    auth_1st = auth_1st.reset_index().melt(**melt_params)
    auth_1st[cols] = auth_1st[cols].astype(int)
    melt_params.update({"value_name": 'top_com'})
    com_1st = com_1st.reset_index().melt(**melt_params)
    com_1st[cols] = com_1st[cols].astype(int)

    # Coauthor and commenter productivity
    qi = pd.read_csv(NEIGHBOR_FILE)
    for col in qi.columns[-4:]:
        qi[col] = np.log(1 + qi[col].fillna(0))

    # COMBINE VARIABLES
    # Author network
    df = auth.copy()
    # Log of future output
    df = df.merge(y, 'left', on=['t', 'scopus_id'])
    # Career time
    df = df.merge(first_pub, 'left', on='scopus_id')
    df['c'] = df['t'] - df['t0']
    df['c'] = df['c'].clip(0)
    # Past output
    df = df.merge(qc, 'left', on=['t', 'scopus_id'])
    # Recent past output
    df = df.merge(qr, 'left', on=['t', 'scopus_id'])
    # Years w/o publications
    df = df.merge(r, 'left', on=['t', 'scopus_id'])
    # Coauthor and commenter productivity
    df = df.merge(qi, "left", on=['t', 'scopus_id'])
    # Top coauthor
    df = df.merge(auth_1st, "left", on=['t', 'scopus_id'])
    # Top commenter
    df = df.merge(com_1st, "left", on=['t', 'scopus_id'])
    # Commenter network
    df = df.merge(com, "left", on=['t', 'scopus_id'])

    # WRITE OUT
    df = df.fillna(0).sort_values(["scopus_id", "t"])
    df.to_csv(TARGET_FILE, index=False, encoding="utf8")


if __name__ == '__main__':
    main()
