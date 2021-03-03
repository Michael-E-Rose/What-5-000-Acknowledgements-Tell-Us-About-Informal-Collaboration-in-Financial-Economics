#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Quantifies informal collaboration behavior on a yearly basis."""

from collections import defaultdict
from json import loads
from urllib.request import urlopen

import pandas as pd

ACK_FILE = "https://raw.githubusercontent.com/Michael-E-Rose/CoFE/master/acks_min.json"
TARGET_FOLDER = "./115_collaboration_counts/"


def add_subdict(d, persons, key, value):
    """Add nested subdict to person entry in a dict if it exists,
    otherwise create.
    """
    for p in persons:
        try:
            try:
                d[p][key] += value
            except KeyError:
                d[p].update({key: value})
        except KeyError:
            d[p] = {key: value}
    return d


def count(data, key):
    """Count explicit or implicit amount of informal collaboration."""
    try:
        return len(data.get(key, []))
    except TypeError:
        return data[key]


def main():
    acks = loads(urlopen(ACK_FILE).read().decode("utf-8"))['data']

    person = defaultdict(dict)
    for item in acks:
        pub_year = item['year']
        d = person[pub_year]
        # Persons
        auths = [a.get('scopus_id', a['label']) for a in item['authors']]
        dis = [c.get('scopus_id', c['label']) for c in item.get('dis', [])]
        coms = [c.get('scopus_id', c['label']) for c in item.get('com', [])]
        coms.extend(dis)
        coms.extend([p.get('scopus_id', p['label']) for x in item['authors']
                     for p in x.get('phd', [])])
        # Meta information
        has_ack = (len(coms) > 0 or 'sem' in item or 'con' in item)
        if not has_ack:
            continue
        # Numbers
        counts = {'num_auth': len(auths), 'num_com': len(coms),
                  'num_dis': len(dis), 'num_con': count(item.copy(), 'con'),
                  'num_sem': count(item.copy(), 'sem'), 'num_paper': 1}
        for col in ['com', 'dis', 'con', 'sem']:
            key = f"num_{col}_n"
            counts[key] = counts['num_' + col]/counts['num_auth']
        # Author information: informal collaboration
        for label, val in counts.items():
            d = add_subdict(d, auths, label, val)
        # Commenter information: given comments
        d = add_subdict(d, coms, 'com_given', 1)
        # Discussant information: given discussions
        d = add_subdict(d, dis, 'dis_given', 1)

    # Person information
    df = pd.DataFrame(columns=['index', 'variable'])
    for year in sorted(person.keys()):
        new = pd.DataFrame.from_dict(person[year]).T.reset_index()
        new = new.melt(id_vars='index', value_name=year)
        df = df.merge(new, 'outer', on=['index', 'variable'])
    df = df.sort_values(['index', 'variable']).rename(columns={'index': 'node'})
    df.to_csv(TARGET_FOLDER + "person.csv", index=False)


if __name__ == '__main__':
    main()
