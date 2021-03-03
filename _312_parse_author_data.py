#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Lists publication and individual information for each matched researcher."""

from glob import glob

import pandas as pd
from pybliometrics.scopus import AuthorRetrieval, AffiliationRetrieval,\
    ScopusSearch
from tqdm import tqdm

TARGET_FOLDER = "./312_author_data/"
MAX_YEAR = "2015"  # Year beyond which we're not interested in publications
RESEARCH_TYPES = ("ar", "re", "cp", "sh")
PLATFORMS = {"60016621", "60020337", "60007893"}


def get_affiliation(p, auth_id):
    """"""
    try:
        auth_idx = p.author_ids.split(";").index(str(auth_id))
    except ValueError:  # Author lists of pubs with > 100 authors not complete
        return "?"
    try:
        return p.author_afids.split(";")[auth_idx] or "?"
    except (AttributeError, IndexError):
        return "?"


def get_aff_type(affiliations):
    """Get the type of current affiliation of an author."""
    try:
        aff_ids = [aff.id for aff in affiliations if aff.id not in PLATFORMS]
        return AffiliationRetrieval(aff_ids[0]).org_type
    except (IndexError, TypeError):
        return None


def get_scopus_nodes(G):
    """Return set of nodes whose ID is a number."""
    return set([str(n) for n in G if n.isdigit()])


def parse_publications(res, *args):
    """Return EIDs, publication name (source) and publication year."""
    return [(p.eid, p.source_id, p.coverDate[:4], p.author_ids,
             get_affiliation(p, *args))
            for p in res
            if p.coverDate[:4] <= MAX_YEAR and p.subtype in RESEARCH_TYPES]


def perform_query(auth_id, refresh=100, fields=["eid", "title"]):
    """Access ScopusSearch API to retrieve EIDs, sources and
    publication years.
    """
    q = f"AU-ID({auth_id})"
    try:
        res = ScopusSearch(q, refresh=refresh, integrity_fields=fields).results
        info = parse_publications(res, auth_id)
    except (AttributeError, KeyError, TypeError):
        res = ScopusSearch(q, refresh=True).results
        info = parse_publications(res, auth_id)
    if not info:
        return None, None, None, None, None
    return zip(*info)


def read_nodes():
    """Read all nodes from the networks if they are identified."""
    import networkx as nx
    scopus_nodes = set()
    for file in glob("./200_yearly_networks/*.gexf"):
        G = nx.read_gexf(file)
        scopus_nodes.update(get_scopus_nodes(G))
    return scopus_nodes


def main():
    scopus_nodes = read_nodes()
    print(f">>> Looking up {len(scopus_nodes):,} researchers")

    # Parse publication lists
    pubs = {}
    data = {}
    missing = []
    for node in tqdm(scopus_nodes):
        # Document information
        eids, sources, years, coauthors, affs = perform_query(node)
        if not eids or not sources or not years:
            missing.append(node)
            continue
        sources = [s or "-" for s in sources]  # Replace missing journal names
        # Author information
        au = AuthorRetrieval(node, refresh=200)
        try:
            fields = [f.abbreviation for f in au.subject_areas if f]
        except Exception as e:
            fields = []
        try:
            aff_type = get_aff_type(au.affiliation_current)
        except Exception as e:
            au = AuthorRetrieval(node, refresh=10)
            try:
                aff_type = get_aff_type(au.affiliation_current)
            except Exception as e:
                pass
        # Add to storage
        data[node] = {"current_aff_type": aff_type, "fields": "|".join(fields)}
        pubs[node] = {"eids": "|".join(eids), "sources": "|".join(sources),
                      "years": "|".join(years), "aff_ids": "|".join(affs),
                      "coauthors": "|".join(coauthors)}
    if missing:
        print(f">>> {len(missing)} researchers w/o research publication "
              f"before {MAX_YEAR}:\n{','.join(missing)}")

    # Write out
    data = pd.DataFrame(data).T.sort_index()
    data.to_csv(TARGET_FOLDER + "data.csv", index_label="scopus_id")
    pubs = pd.DataFrame(pubs).T.sort_index()
    pubs.to_csv(TARGET_FOLDER + "pub_list.csv", index_label="scopus_id")


if __name__ == '__main__':
    main()
