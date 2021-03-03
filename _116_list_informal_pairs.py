#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Indicates pairs of formal and informal collaboration by year."""

from itertools import product

import pandas as pd

TARGET_FILE = "./116_informal_collaboration_pairs/pairs.csv"


def read_ack_file():
    """Read acknowledgement json, remove editors and transform to DataFrame."""
    from json import loads
    from urllib.request import urlopen

    def get_persons(item):
        """Extract Scopus ID (alternatively: name) from a list of dicts."""
        try:
            return [c.get('scopus_id', c['label']) for c in item]
        except TypeError:
            return []

    def get_phd(item):
        """Extract Scopus ID (alternatively: name) from a list of nested dicts."""
        return [p.get('scopus_id', p['label']) for x in item
                for p in x.get('phd', [])]

    def filter_editors(item):
        """Remove commenters that are editors."""
        return [c for c in item['com'] if c not in item['editors']]

    def flatten(item):
        """Collapse lists from DataFrame columns."""
        return [e for p in item for e in p]

    # Read from web
    ACK_FILE = "https://raw.githubusercontent.com/Michael-E-Rose/CoFE/"\
               "master/acks_min.json"
    EDITOR_FILE = "../InfCor_data/020_editor_tenures/list.csv"
    data = loads(urlopen(ACK_FILE).read().decode("utf-8"))['data']
    acks = pd.DataFrame(data)
    acks['phd'] = acks['authors'].apply(get_phd)
    for col in ['com', 'dis']:
        acks[col] = acks[col].apply(get_persons)
    acks['auth'] = acks['authors'].apply(get_persons)
    # Remove editors of this and previous year
    eds = pd.read_csv(EDITOR_FILE).dropna(subset=['scopus_id'])
    eds = eds[eds['managing_editor'] == 1]
    eds['scopus_id'] = eds['scopus_id'].astype(int).astype(str) + " "
    grouped = eds.groupby(['journal', 'year'])['scopus_id'].sum().reset_index()
    grouped['editors'] = grouped['scopus_id'].str.split()
    grouped = grouped[['journal', 'year', 'editors']]
    acks = acks.merge(grouped, "left", on=['journal', 'year'])
    grouped['year'] = grouped['year'] + 1
    acks = acks.merge(grouped, "left", on=['journal', 'year'],
                      suffixes=['_this', '_prev'])
    acks['editors'] = acks[['editors_this', 'editors_prev']].apply(flatten, axis=1)
    acks['com'] = acks.apply(filter_editors, axis=1)
    acks['coms'] = acks[['com', 'phd', 'dis']].apply(flatten, axis=1)
    drops = ['authors', 'com', 'phd', 'dis', 'editors_this', 'editors_prev', 'editors']
    return acks.drop(drops, axis=1)


def main():
    # Informal collaboration
    acks = read_ack_file()

    # Get combinations year-wise
    authcom_collabs = []
    for year in acks['year'].unique():
        subset = acks[acks['year'] == year]
        for auth, com in zip(subset['auth'], subset['coms']):
            new_links = product(auth, com)
            authcom_collabs.extend([(x[0], x[1], year) for x in new_links])

    # Write out
    out = pd.DataFrame(authcom_collabs, columns=['author', 'commenter', 'year'])
    out = out.sort_values(['year', 'author', 'commenter']).drop_duplicates()
    out.to_csv(TARGET_FILE, index=False)


if __name__ == '__main__':
    main()
