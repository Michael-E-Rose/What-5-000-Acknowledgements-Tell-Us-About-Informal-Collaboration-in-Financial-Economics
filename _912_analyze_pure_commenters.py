#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Analyzes pure commenters."""

from glob import glob

import pandas as pd
import networkx as nx

DATA_FILE = "./312_author_data/data.csv"
NETWORKS_FOLDER = "./200_yearly_networks/"
METRICS_FILE = "./313_author_metrics/metrics.csv"
GENDER_FILE = "./350_gender_estimates/genderize.csv"


def find_main_field(field_str):
    """Find main (most frequent) field of a researcher."""
    from collections import Counter

    try:
        fields = field_str.split("|")
        return Counter(fields).most_common(1)[0][0]
    except AttributeError:
        return None


def main():
    # Split researchers
    authors = set()
    for f in glob(NETWORKS_FOLDER + "*auth.gexf"):
        authors.update(nx.read_gexf(f).nodes())
    commenters = set()
    for f in glob(NETWORKS_FOLDER + "*com.gexf"):
        commenters.update(nx.read_gexf(f).nodes())
    pure_com = pd.DataFrame(index=(commenters - authors))
    pure_auth = pd.DataFrame(index=(authors - commenters))

    # Merge with gender
    gender = pd.read_csv(GENDER_FILE, usecols=["ID", "gender"], index_col=0)
    pure_com = pure_com.join(gender)
    pure_auth = pure_auth.join(gender)

    # Merge with author data
    data = pd.read_csv(DATA_FILE, index_col=0)
    data.index = data.index.astype(str)
    data["main_field"] = data["fields"].apply(find_main_field)
    data = data.drop("fields", axis=1)
    pure_com = pure_com.join(data)
    pure_auth = pure_auth.join(data)
    print(">>> Distribution of main fields:\n... authors:")
    print(pure_auth["main_field"].value_counts()/pure_auth.shape[0])
    print("... commenters:")
    print(pure_com["main_field"].value_counts()/pure_com.shape[0])


if __name__ == '__main__':
    main()
