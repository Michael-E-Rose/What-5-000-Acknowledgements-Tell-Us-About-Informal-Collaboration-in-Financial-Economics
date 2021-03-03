#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Crawls metrics for authors on a yearly basis: publications count, weighted
publication count, yearly citations and Euclidean index of citations.

You need a special API key by Scopus to access the citation view.
"""

import pandas as pd
from scholarmetrics import euclidean
from pybliometrics.scopus import CitationOverview
from tqdm import tqdm

from _005_create_bibliography import YEARS
from _312_parse_author_data import MAX_YEAR

SOURCE_FILE = "./312_author_data/pub_list.csv"
TARGET_FILE = "./313_author_metrics/metrics.csv"


def compute_euclid(df):
    """Return yearly Euclidean index except when all entries are nan."""
    return df.dropna(how="all", axis=1).cumsum(axis=1).apply(euclidean)


def explode(df, col, label=None):
    """Explode a DataFrame using Series stacking of column `col`."""
    label = label or col
    n_levels = len(df.index.names)
    return (df[col].apply(pd.Series)
              .stack()
              .reset_index(level=n_levels, drop=True)
              .reset_index()
              .rename(columns={0: label}))


def get_yearly_citations(eid, pubyear, refresh=False):
    """Return dict of yearly citations."""
    co = CitationOverview(eid, pubyear, refresh=refresh)
    return {y: int(c) for y, c in co.cc}


def nan_preserving_sum(df):
    """Sum values except when all entries are nan."""
    return df.dropna(how="all", axis=1).fillna(0).sum(axis=0)


def read_jif(asjc=(2000, 1400)):
    """Read file with Scimago Journal Impact Factors."""
    JIF_URL = "https://raw.githubusercontent.com/Michael-E-Rose/"\
              "ScimagoEconJournalImpactFactors/master/compiled/Scimago_JIFs.csv"
    dtypes = {"Sourceid": str, "year": "uint16", "SJR": "str", "field": "uint16"}
    jif = pd.read_csv(JIF_URL, usecols=dtypes.keys(), dtype=dtypes)
    jif = jif[jif["field"].isin(asjc)].drop("field", axis=1)
    jif = jif.drop_duplicates(subset=["Sourceid", "year"])
    jif["SJR"] = jif["SJR"].fillna(0).str.replace(",", ".").astype(float)
    return jif.rename(columns={"Sourceid": "source"})


def main():
    # Read in
    cols = ["scopus_id", "eids", "years", "sources"]
    df = pd.read_csv(SOURCE_FILE, index_col=0, usecols=cols, encoding="utf8")
    for col in df.columns:
        df[col] = df[col].str.split("|")

    # Inform about publications in study period
    years = explode(df, "years", "year")
    eids = explode(df, "eids", "eid")
    temp = pd.concat([eids, years], axis=1).drop_duplicates(subset="eid")
    temp["year"] = temp["year"].astype("uint32")
    pubs_within = temp["year"].between(int(YEARS[0]), int(YEARS[1])).sum()
    del temp
    print(f">>> Found {eids['eid'].nunique():,} publications overall, and "
          f"{pubs_within:,} between {YEARS[0]} and {YEARS[1]}")

    # Publication count
    print(">>> Counting publications...")
    pubs = (years.groupby(["scopus_id", "year"]).size()
                 .reset_index()
                 .rename(columns={0: "yearly_pubs"}))
    pubs["year"] = pubs["year"].astype("int32")

    # Weighted publication count
    print(">>> Counting JIF-weighted publications...")
    sources = explode(df, "sources", "source")
    temp = pd.concat([years, sources.drop("scopus_id", axis=1)], axis=1)
    temp['year'] = temp['year'].astype("int32")
    jif = read_jif()
    temp = temp.merge(jif, "left", on=['source', 'year'], indicator=True)
    mask_unmerged = temp["_merge"] == "left_only"
    unmerged = temp[mask_unmerged].drop(["SJR", "_merge"], axis=1)
    temp = temp[~mask_unmerged]
    jif_first = jif.drop_duplicates(subset=["source"]).drop("year", axis=1)
    new = unmerged.merge(jif_first, "left", on=["source"], indicator=True)
    del jif, jif_first, unmerged
    temp = pd.concat([temp, new], axis=0)
    unmerged = new[new["_merge"] == "left_only"]
    if not unmerged.empty:
        n_pub = unmerged.shape[0]
        source_missing = unmerged["source"].value_counts()
        print(f">>> {n_pub:,} unmatched publications out of "
              f"{temp.shape[0]:,} ({(n_pub/temp.shape[0]):.2%}) from "
              f"{source_missing.shape[0]:,} journals")
        print(f">>> Most common unmatched journals:\n{source_missing.head(10)}")
    temp = temp.drop("_merge", axis=1)
    wpubs = (temp.fillna(0)
                 .groupby(['scopus_id', 'year'])['SJR'].sum()
                 .reset_index()
                 .rename(columns={"SJR": "yearly_wpubs"}))
    del temp

    # Yearly citation count
    temp = pd.concat([eids, years["year"]], axis=1).reset_index(drop=True)
    total = temp.shape[0]
    print(f">>> Searching yearly citation counts for {total:,} articles")
    yearly_cites = {}
    for idx, row in tqdm(temp.iterrows(), total=temp.shape[0]):
        try:
            yearly_cites[row["eid"]] = get_yearly_citations(row["eid"], row["year"])
        except Exception as e:
            print("\n", e, row["eid"])
            continue
    print(">>> Computing citations and Euclidean index of citations")
    yearly_cites = pd.DataFrame(yearly_cites).T
    yearly_cites = yearly_cites[sorted(yearly_cites.columns)]
    eid_cites = eids.join(yearly_cites, how="left", on="eid")
    eid_cites = eid_cites.drop("eid", axis=1).set_index("scopus_id")
    grouped = eid_cites.groupby(eid_cites.index)
    cites = grouped.apply(nan_preserving_sum)
    cites = (cites.reset_index()
                  .rename(columns={"level_1": "year", 0: "yearly_cites"}))

    # Euclidean index of citations
    euclid = grouped.apply(compute_euclid)
    euclid = (euclid.reset_index()
                    .rename(columns={"level_1": "year", 0: "euclid"}))

    # Write out
    print(">>> Finishing up...")
    out = euclid.merge(cites, "left", on=["scopus_id", "year"])
    out = (out.merge(pubs, "left", on=["scopus_id", "year"])
              .merge(wpubs, "left", on=["scopus_id", "year"])
              .sort_values(['scopus_id', 'year']))
    out = out[out["year"] <= int(MAX_YEAR)]
    out.to_csv(TARGET_FILE, index=False, encoding="utf8")


if __name__ == '__main__':
    main()
