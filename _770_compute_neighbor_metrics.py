#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Computes measures of productivity for network neighbors
based on journal impact factors.
"""

from glob import glob

import networkx as nx
import pandas as pd

from _313_compute_author_metrics import explode, read_jif

JIF_FILE = "./751_Journal_Impact_Factors/JIFs.csv"
PUBLICATION_LIST = "./312_author_data/pub_list.csv"
NETWORK_FOLDER = "./200_yearly_networks/"
TARGET_FILE = "./770_network_neighbor_productivity/both.csv"


def compute_first_neigh_prod(neigh, wpubs, window=5):
    """Compute the productivity of first neighbors excluding joint
    publications.
    """
    # Add years prior to actual observation
    neigh = neigh.sort_values(["index", "t", "scopus_id"])
    temp = neigh.copy()
    for lag in range(1, window):
        new = temp.copy()
        new["t"] = new["t"]-lag
        neigh = neigh.append(new)
    neigh = neigh.drop_duplicates()
    del temp, new
    # Add neighbors' publications' JIF and exclude joint publications
    neigh = neigh.merge(wpubs, "left", on=["scopus_id", "t"])
    neigh = neigh[neigh.apply(find_coauthor, axis=1)].drop("authors", axis=1)
    return neigh.groupby(["index", "t"])["SJR"].sum().reset_index()


def find_coauthor(s):
    """Whether `s["index"]` is not in `s["authors"]`."""
    try:
        return s["index"] not in s["authors"]
    except TypeError:  # Coauthors missing for some strange reason
        return True


def get_neighbors(files):
    """Return DataFrames with yearly direct and indirect neighbors"""
    from os.path import basename
    neigh_1st = {}
    neigh_2nd = {}
    for file in files:
        G = nx.read_gexf(file)
        year = basename(file)[:4]
        neigh = {n: list(set([k for k in G[n].keys() if k.isdigit()]))
                 for n in G.nodes() if n.isdigit()}
        neigh_1st[year] = neigh
        indir = {}
        for node, neighs in neigh.items():
            lst = [set(G[n].keys()) for n in neighs]
            new = set([n for sl in lst for n in sl if n.isdigit()])
            indir[node] = list(new - set(neighs))
        neigh_2nd[year] = indir
    first = pd.DataFrame.from_dict(neigh_1st).reset_index()
    first = transform(first, "scopus_id")
    second = pd.DataFrame.from_dict(neigh_2nd).reset_index()
    second = transform(second, "scopus_id")
    return first, second


def cumulate_productivity(df, window=5):
    """Compute productivity over current and past 4 years."""
    return (df.pivot(index="scopus_id", columns="t", values="SJR")
              .fillna(0).rolling(window, min_periods=1, axis=1).sum()
              .reset_index().melt(id_vars="scopus_id", value_name="SJR"))


def transform(df, value_name):
    """Melt and explode DataFrame of neighbors."""
    df = df.melt(id_vars="index", var_name="t", value_name=value_name)
    df = df.dropna().set_index(["index", "t"])
    df = explode(df, value_name, value_name)
    df[value_name] = df[value_name].astype(int)
    df["t"] = df["t"].astype("uint")
    return df


def main():
    # Read in
    cols = ["scopus_id", "years", "sources", "coauthors"]
    pubs = pd.read_csv(PUBLICATION_LIST, index_col=0, usecols=cols)
    for c in pubs.columns:
        pubs[c] = pubs[c].str.split("|")

    # Weigh publications
    print(">>> Weighting publications...")
    dfs = [explode(pubs, "years", "t"),
           explode(pubs, "sources", "source").drop("scopus_id", axis=1),
           explode(pubs, "coauthors", "authors").drop("scopus_id", axis=1)]
    wpubs = pd.concat(dfs, axis=1)
    wpubs["t"] = wpubs["t"].astype("uint")
    jif = read_jif().drop_duplicates(subset="source").drop("year", axis=1)
    wpubs = wpubs.merge(jif, "left", on="source").drop("source", axis=1)

    # Read neighbors
    print(">>> Reading network files...")
    auth_1st, auth_2nd = get_neighbors(glob(NETWORK_FOLDER + "*auth.gexf"))
    com_1st, com_2nd = get_neighbors(glob(NETWORK_FOLDER + "*com.gexf"))

    # Compute first neighbors' productivity (account for joint publications)
    print(">>> Computing first neighbors' productivity...")
    wpubs["authors"] = wpubs["authors"].str.split(";")
    auth1 = compute_first_neigh_prod(auth_1st, wpubs)
    auth1 = auth1.rename(columns={'SJR': 'qit1_a', 'index': 'scopus_id'})
    auth1["scopus_id"] = auth1["scopus_id"].astype(int)
    com1 = compute_first_neigh_prod(com_1st, wpubs)
    com1 = com1.rename(columns={'SJR': 'qit1_c', 'index': 'scopus_id'})
    com1["scopus_id"] = com1["scopus_id"].astype(int)

    # Compute second neighbors' productivity
    print(">>> Computing second neighbors' productivity...")
    wpubs = wpubs.groupby(["scopus_id", "t"])["SJR"].sum().reset_index()
    wpubs = cumulate_productivity(wpubs)
    params = {"right": wpubs, "how": "left", "on": ["scopus_id", "t"]}
    auth2 = (auth_2nd.merge(**params)
                     .groupby(["scopus_id", "t"])["SJR"].sum()
                     .reset_index()
                     .rename(columns={"SJR": 'qit2_a'}))
    com2 = (com_2nd.merge(**params)
                   .groupby(["scopus_id", "t"])["SJR"].sum()
                   .reset_index()
                   .rename(columns={"SJR": 'qit2_c'}))

    # Write out
    print(">>> Writing out...")
    out = (auth1.merge(auth2, "outer", on=['scopus_id', 't'])
                .merge(com1, "outer", on=['scopus_id', 't'])
                .merge(com2, "outer", on=['scopus_id', 't'])
                .sort_values(['scopus_id', 't']))
    out.to_csv(TARGET_FILE, index=False)


if __name__ == '__main__':
    main()
