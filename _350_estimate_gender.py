#!/usr/bin/env python3
# Author:  Michael E. Rose <michael.ernst.rose@gmail.com>
"""Collect gender estimates from genderize.io.

This script was written for free usage of genderize, which
allows 1000 requests/day.  Run this script continuously on separate days
to obtain all the information.
"""

import pandas as pd
import genderize
from numpy import nan
from tqdm import tqdm

from _200_build_networks import write_stats

PERSON_FILE = "https://raw.githubusercontent.com/Michael-E-Rose/CoFE/master/"\
              "data/persons.csv"
TARGET_FILE = "./350_gender_estimates/genderize.csv"


def clean_name(s):
    """Strip accents and remove interpunctuation."""
    import unicodedata
    new = s.split("-")[0]
    return ''.join(c for c in unicodedata.normalize('NFD', new)
                   if unicodedata.category(c) != 'Mn')


def get_firstname(s):
    """Return first name."""
    if "," in s["label"]:
        firstnames = s["label"].split(", ", 1)[1]
        new = clean_name(firstnames)
        firsts = [part for part in new.split() if
                  len(part) > 1 and not part.endswith(".")]
        try:
            return firsts[0].upper()
        except IndexError:
            return None
    else:
        return s["label"].split()[0]


def main():
    # Read all researchers
    cols = ["scopus_id", "label"]
    df = pd.read_csv(PERSON_FILE, usecols=cols)[cols]
    df['scopus_id'] = df['scopus_id'].fillna(df['label'])
    df = df.drop_duplicates(subset="scopus_id").set_index("scopus_id")
    df.index = df.index.map(lambda x: str(int(x)) if isinstance(x, float) else x)

    # Skip persons that already have estimates
    try:
        collected = pd.read_csv(TARGET_FILE, index_col=0, na_values="",
                                keep_default_na=False)
        collected = collected[collected.index.isin(df.index.tolist())]
        collected = collected.dropna(subset=["gender"])
        df = df.drop(collected.index, errors='ignore')
    except FileNotFoundError:
        collected = pd.DataFrame()

    # Prepare names
    df["first"] = df.apply(get_firstname, axis=1)
    before = df.shape[0]
    df = df.dropna(subset=["first"])
    name_invalid = before-df.shape[0]
    if name_invalid:
        print(f">>> Dropping {name_invalid:,} researchers w/o valid name")

    # Get gender estimates
    estimates = {}
    total = df['first'].nunique()
    print(f">>> Searching for {total} new names...")
    for name in tqdm(df["first"].unique()):
        try:
            resp = genderize.Genderize().get([name])
            estimates[name] = resp[0]
        except Exception as e:  # Daily Quota exceeded
            print("... Quota exceeded, try again tomorrow")
            break

    # Write out
    if estimates:
        new = pd.DataFrame(estimates).T
        new["count"] = new["count"].astype(float)
        df = df.join(new, how="right", on="first")
        df = df[["count", "gender", "name", "probability"]]
        collected = pd.concat([collected, df]).sort_index()
        nans = collected["gender"] == ""
        collected.loc[nans, ["count", "gender", "probability"]] = nan
        collected.to_csv(TARGET_FILE, index_label="ID")

    # Statistics
    print(">>> Distribution of gender:")
    print(pd.value_counts(collected["gender"]))
    n_missing = collected["gender"].isna().sum() + name_invalid
    write_stats({"N_of_researcher_nogender": n_missing})
    share = n_missing/(float(collected.shape[0])+name_invalid)
    print(f">>> No estimates for {n_missing:,} out of {collected.shape[0]:,} "
          f"({share:,.2%}) researchers w/ valid names")


if __name__ == '__main__':
    main()
