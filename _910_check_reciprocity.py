#!/usr/bin/env python3
"""Computes estimates of reciprocity in our network.

Reciprocity is the sum of papers that acknowledge at least one co-author
or at least one researcher that acknowledges one of the original authors
on his papers.
"""

from collections import defaultdict
from glob import glob
from os.path import basename, splitext

import networkx as nx
import pandas as pd

from _116_list_informal_pairs import read_ack_file
from _200_build_networks import write_stats
from _313_compute_author_metrics import explode

NETWORK_FOLDER = "./200_yearly_networks/"
AFFILIATION_FILE = "./312_author_data/pub_list.csv"
OUTPUT_FOLDER = "./990_output/"

PLATFORMS = {"60016621", "60020337", "60007893"}


def count_coll_com(s):
    """Count how many commenters are colleagues."""
    auth = set([a for a in s["auth"] if a])
    coms = [set(c.strip("-").split("-")) for c in s["coms"]
            if c and c not in ("?", "nan")]
    if not coms:
        return None
    return len([c for c in coms if len(c.intersection(auth))])


def group_affiliations(group, acks, affiliations, year_correction=0):
    """Aggregate affiliations of researchers (author or commenters) on
    a paper level, possibly using past affiliations instead.
    """
    temp = explode(acks, group, "scopus_id").set_index("title")
    temp = temp.join(acks[["year"]])
    temp["year"] = temp["year"]-year_correction
    affs = (temp.reset_index()
                .merge(affiliations, "left", on=["scopus_id", "year"]))
    affs["aff_ids"] = affs["aff_ids"].astype(str) + "|"
    grouped = affs.groupby(["title", "year"])["aff_ids"].sum()
    grouped.name = group
    return grouped


def read_affiliations(max_year=2011):
    """Read and compile yearly affiliations of researchers, where missing
    information are forward-filled.
    """
    cols = ["scopus_id", "years", "aff_ids"]
    df = pd.read_csv(AFFILIATION_FILE, usecols=cols, index_col=0, encoding="utf8")
    df = df.dropna(subset=["aff_ids"])
    # Remove platform affiliations
    for platform in PLATFORMS:
        df["aff_ids"] = df["aff_ids"].str.replace(platform, "")
    # Create long list
    for col in df.columns:
        df[col] = df[col].str.split("|")
    years = explode(df, "years", "year").drop("scopus_id", axis=1)
    affs = explode(df, "aff_ids")
    out = pd.concat([affs, years], axis=1)
    # Combine multiple affiliation information
    out["aff_ids"] = out["aff_ids"].str.strip("-")
    out = out[~(out["aff_ids"].isin(("?", "")))]
    out = out.drop_duplicates(["scopus_id", "year", "aff_ids"])
    out["aff_ids"] = out["aff_ids"] + "|"
    out = out.groupby(["scopus_id", "year"])["aff_ids"].sum().reset_index()
    out["aff_ids"] = (out["aff_ids"].str.strip("|")
                                    .str.replace("|", "-")
                                    .str.replace("--", "-"))
    # Forward-fill missing years
    out["year"] = out["year"].astype(int)
    extension_range = range(out["year"].min(), max_year+1)
    data = {"year": list(extension_range)*affs["scopus_id"].nunique(),
            "scopus_id": sorted(list(affs["scopus_id"].unique())*len(extension_range))}
    dummies = pd.DataFrame(data)
    out = dummies.merge(out, "left", on=["year", "scopus_id"])
    out["aff_ids"] = out["aff_ids"].fillna(method="ffill")
    out["scopus_id"] = out["scopus_id"].astype(str)
    return out.dropna()


def realized_reciprocity(s, direction=('coms', 'auth'), G=None, mapping=None):
    """Check whether any commenter either acknowledges any of the authors on
    her work, or whether she is a co-author of any of the authors.
    """
    status = False
    for p in s[direction[0]]:
        if G:
            neighbors = G.neighbors(p)
        else:
            neighbors = mapping.get(p, [])
        status = max(status, any(c in neighbors for c in s[direction[1]]))
    return status


def potential_reciprocity(s, G):
    """For authors, check whether an acknowledged commenter is author and
    has coauthors; for commenters, check whether she is author and has papers
    without authors of the paper she is acknowledged on.
    """
    if isinstance(s, list):
        return any(c in G.nodes() and len(list(G.neighbors(c))) > 0 for c in s)
    else:
        authors = set(s['auth'])
        return any(c in G.nodes() and
                   len(set(G.neighbors(c)) - authors) > 0 for c in s['coms'])


def split(entry, delim):
    """Split a string representing a list."""
    if len(entry) > 0:
        return entry[0].split(delim)
    else:
        return entry


def main():
    # Read acknowledgements and networks
    acks = read_ack_file()
    G = defaultdict(lambda: nx.Graph())
    for fname in glob(NETWORK_FOLDER + '*.gexf'):
        net_type = splitext(basename(fname))[0][5:]
        H = nx.read_gexf(fname).to_undirected()
        G[net_type] = nx.compose(G[net_type], H)

    # Dictionary mapping authors and their commenters
    auth_com_map = {n: [] for n in G['auth'].nodes()}
    for row in acks.itertuples(index=False):
        for author in row.auth:
            auth_com_map[author].extend(row.coms)

    # Reciprocity among coauthors
    acks['r_auth'] = acks[['auth', 'coms']].apply(
        lambda s: realized_reciprocity(s, ('auth', 'coms'), G=G['auth']), axis=1)
    acks['r_auth_p'] = acks['coms'].apply(
        lambda s: potential_reciprocity(s, G['auth']))

    # Reciprocity among commenters
    acks['r_com'] = acks[['auth', 'coms']].apply(
        lambda s: realized_reciprocity(s, mapping=auth_com_map), axis=1)
    acks['r_com_p'] = acks[['auth', 'coms']].apply(
        lambda s: potential_reciprocity(s, G['auth']), axis=1)

    # Read affiliation information
    affs = read_affiliations()

    # Reciprocity among colleagues
    acks = acks.set_index("title")
    auth_aff = group_affiliations("auth", acks, affs, year_correction=1)
    com_aff = group_affiliations("coms", acks, affs, year_correction=1)
    both_aff = pd.concat([auth_aff, com_aff], axis=1).reset_index()
    both_aff = both_aff.dropna(subset=["coms"])
    both_aff["auth"] = both_aff["auth"].str.replace("-", "|")
    for c in ("auth", "coms"):
        both_aff[c] = both_aff[c].str.strip("|").str.strip("-").str.split("|")
    both_aff["com_coll"] = both_aff.apply(count_coll_com, axis=1)
    both_aff = both_aff.dropna(subset=["com_coll"])
    print(">>> Distribution of the number of commenters that are colleagues")
    print(both_aff["com_coll"].value_counts()/both_aff.shape[0])
    acks = acks.merge(both_aff.drop(["year", "auth", "coms"], axis=1),
                      "left", on="title")
    acks["r_coll"] = acks["com_coll"].fillna(0) > 0
    acks["r_coll_p"] = acks["com_coll"].notnull()

    # Statistics
    stats = {'reci_auth_real': acks['r_auth'].sum(),
             'reci_auth_pot': acks['r_auth_p'].sum(),
             'reci_com_real': acks['r_com'].sum(),
             'reci_com_pot': acks['r_com_p'].sum(),
             'reci_coll_real': acks['r_coll'].sum(),
             'reci_coll_pot': acks['r_coll_p'].sum(),
             'reci_any_real': sum(acks[['r_auth', 'r_com', 'r_coll']].any(axis=1)),
             'reci_any_pot': sum(acks[['r_auth_p', 'r_com_p', 'r_coll_p']].any(axis=1))}
    write_stats(stats)

    print(">>> Papers with commenting co-authors: "
          f"{stats['reci_auth_real']:,} (of {stats['reci_auth_pot']:,})")
    print(">>> Papers with authors commenting on their commenters' "
          f"work: {stats['reci_com_real']:,} (of {stats['reci_com_pot']:,})")
    print(">>> Papers with commenters that are colleagues: "
          f"{stats['reci_coll_real']:,} (of {stats['reci_coll_pot']:,})")
    print(">>> Papers with either form of reciprocity: "
          f"{stats['reci_any_real']:,} (of {stats['reci_any_pot']:,})")


if __name__ == '__main__':
    main()
