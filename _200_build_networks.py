#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Generates weighted yearly networks with formal collaboration only, and
informal collaboration only.
"""

from collections import Counter, defaultdict
from itertools import combinations, product
from json import loads
from urllib.request import urlopen

import networkx as nx
import pandas as pd
from num2words import num2words

ACK_FILE = "https://raw.githubusercontent.com/Michael-E-Rose/CoFE/"\
           "master/acks_min.json"
EDITOR_FILE = "./075_editor_tenures/list.csv"
TARGET_FOLDER = "./200_yearly_networks/"
OUTPUT_FOLDER = "./990_output/"

SPAN = 3  # number of years for each network
MAX_YEAR = 2011


def add_attribute(network, edges, val, attr='weight'):
    """Creates, appends or increases attribute of edges"""
    for entry in edges:
        d = network.edges[entry[0], entry[1]]
        try:
            if isinstance(d[attr], str):
                d[attr] += ";" + val  # append
            else:
                d[attr] += val  # increase
        except KeyError:
            d[attr] = val  # create


def write_stats(stat_dct):
    """Write out textfiles as "filename: content" pair."""
    for key, cont in stat_dct.items():
        fname = f"{OUTPUT_FOLDER}/Statistics/{key}.txt"
        with open(fname, "w") as out:
            out.write(f"{int(cont):,}")


def year_name(year, last_digits=None):
    """Turn numbers into words, as a fix for Latex."""
    return num2words(int(str(year)[last_digits:])).replace("-", '')


def main():
    # READ IN
    eds = pd.read_csv(EDITOR_FILE).dropna(subset=['scopus_id'])
    eds = eds[eds['managing_editor'] == 1]
    eds['scopus_id'] = eds['scopus_id'].astype(int).astype(str)
    acks = loads(urlopen(ACK_FILE).read().decode("utf-8"))['data']

    stats = {"N_of_articles": len(acks), "N_of_articles_with": 0}

    # GENERATE NETWORKS
    art_counter = []  # Count papers by year
    with_counter = []  # Count papers with acknowledgements by year
    all_authors = set()  # Count unique authors
    all_commenters = []  # Count unique and weighted number of commenters
    A = defaultdict(lambda: nx.Graph(name="auth"))
    C = defaultdict(lambda: nx.DiGraph(name="com"))
    for item in acks:
        pub_year = item['year']
        journal = item['journal']
        # Authors
        auths = [a.get('scopus_id', a['label']) for a in item['authors']]
        all_authors.update(auths)
        # Commenters
        coms = [c.get('scopus_id', c['label']) for c in item.get('com', [])]
        coms.extend([c.get('scopus_id', c['label']) for c in item.get('dis', [])])
        coms.extend([p.get('scopus_id', p['label']) for x in item['authors']
                     for p in x.get('phd', [])])
        # Remove editors of this and previous year
        eds_range = range(pub_year-1, pub_year+1)
        mask = (eds['year'].isin(eds_range)) & (eds['journal'] == item['journal'])
        cur_editors = set(eds[mask]['scopus_id'])
        coms = set(coms) - cur_editors
        has_ack = (coms or 'sem' in item or 'con' in item)
        if has_ack:
            stats["N_of_articles_with"] += 1
        all_commenters.extend([c for c in coms])
        # Add weighted links to this and the next LAG networks
        for cur_year in range(pub_year, pub_year+SPAN):
            if cur_year < 1997+SPAN-1 or cur_year > MAX_YEAR:
                continue
            art_counter.append(cur_year)
            auth_links = list(combinations(auths, 2))
            com_links = list(product(coms, auths))
            if has_ack:
                with_counter.append(cur_year)
            # Author network
            A[cur_year].add_nodes_from(auths)
            A[cur_year].add_edges_from(auth_links)
            add_attribute(A[cur_year], auth_links, 1.0)
            add_attribute(A[cur_year], auth_links, journal, 'journal')
            # Commenter network
            C[cur_year].add_nodes_from(coms)
            C[cur_year].add_edges_from(com_links)
            add_attribute(C[cur_year], com_links, 1/len(auths))
            add_attribute(C[cur_year], com_links, journal, 'journal')

    # WRITE OUT
    for label, d in [('auth', A), ('com', C)]:
        for year, G in d.items():
            assert(len(list(nx.selfloop_edges(G))) == 0)
            ouf = f"{TARGET_FOLDER}/{year}_{label}.gexf"
            nx.write_gexf(G, ouf)

    # SAVE STATISTICS
    stats.update({f"N_of_articles_{year_name(k, -2)}": v for k, v
                  in Counter(art_counter).items()})
    stats.update({f"N_of_articles_with_{year_name(k, -2)}": v for k, v
                  in Counter(with_counter).items()})
    all_persons = all_authors.union(all_commenters)
    all_comments = Counter(all_commenters)
    stats.update(
        {"N_of_authors_all": len(all_authors),
         "N_of_authors_scopus": sum([a.isdigit() for a in all_authors]),
         "N_of_commenters_all": len(set(all_commenters)),
         "N_of_commenters_scopus": sum([c.isdigit() for c in set(all_commenters)]),
         "N_of_comments_all": sum(all_comments.values()),
         "N_of_comments_scopus": sum([v for k, v in all_comments.items()if k.isdigit()]),
         "N_of_persons_all": len(all_persons),
         "N_of_persons_scopus": sum([p.isdigit() for p in all_persons])})
    write_stats(stats)


if __name__ == '__main__':
    main()
