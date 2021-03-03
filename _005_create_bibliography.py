#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Combines all relevant data from Scopus records."""

import pandas as pd
from numpy import cumsum
from pybliometrics.scopus import AbstractRetrieval, CitationOverview, ScopusSearch

SOURCE_FILE = "./001_journal_IDs/Scopus.csv"
TARGET_FILE = "./005_bibliometric_information/Scopus.csv"

YEARS = (1997, 2011)
TOP_JOURNALS = ('JF', 'RFS', 'JFE')
DOCTYPES = ("ar", "re", "cp", "ip", "no", "sh")


def parse_abstract(pub, refresh=350):
    """Extract bibliometric information and add yearly citations."""
    # Basic bibliometric information
    s = pd.Series()
    s['title'] = pub.title
    s['eid'] = pub.eid
    pubyear = int(pub.coverDate.split("-")[0])
    s['year'] = str(pubyear)
    try:
        pages = pub.pageRange.split("-")
    except AttributeError:
        ab = AbstractRetrieval(pub.eid, view="FULL")
        pages = ab.pageRange.split("-")
    s['num_pages'] = int(pages[1]) - int(pages[0])
    s['num_auth'] = pub.author_count
    s['authors'] = pub.author_ids
    # Yearly cumulated citations
    co = CitationOverview(pub.eid, start=pubyear, end=2020, refresh=refresh)
    s['total_citations'] = sum([int(t[1]) for t in co.cc])
    lags = [f"citcount_{y-pubyear}" for y, _ in co.cc]
    citations = cumsum([int(t[1]) for t in co.cc])
    s = s.append(pd.Series(citations, index=lags))
    return s


def standardize(ds):
    """Remove interpunctuation and whitespaces from a string."""
    from string import punctuation
    from unicodedata import category, normalize
    ss = ''.join(s for s in normalize('NFD', ''.join(ds.split()))
                 if category(s) != 'Mn')
    manually = (('“', '"'), ('”', '"'), ("(TM)", ""), ("(R)", ""))
    for old, new in manually:
        ss = ss.replace(old, new)
    return ss.translate(str.maketrans({k: "" for k in punctuation + '®™–'}))


def main():
    # Read in
    journals = pd.read_csv(SOURCE_FILE, index_col=0, encoding="utf8")

    # Get article information
    print(">>> Querying publications for:")
    d = []
    for idx, row in journals.iterrows():
        print("...", idx)
        for year in range(YEARS[0], YEARS[1]+1):
            q = f'SOURCE-ID({row.source_id}) AND PUBYEAR IS {year}'
            s = ScopusSearch(q, refresh=30)
            for pub in s.results:
                if pub.subtype not in DOCTYPES:
                    continue
                s = parse_abstract(pub)
                s["journal"] = row.Abbreviation
                d.append(s)
    print(f">>> Found {len(d):,} publications")

    # Turn to DataFrame
    df = pd.DataFrame.from_records(d)
    print(">>> Correcting some titles")
    repl = {"&amp;": "&", "<sup>": "", "</sup>": "", "<inf>": "", "</inf>": ""}
    for old, new in repl.items():
        df['title'] = df['title'].str.replace(old, new)
    df['simple_title'] = df['title'].apply(standardize).str.upper()
    df['top'] = df['journal'].isin(TOP_JOURNALS)*1

    # Add citation counts of reprints to original paper
    print(">>> Dropping reprints and duplicates")
    df = df.sort_values(['simple_title', 'year'])
    grouped = df.groupby('simple_title')
    left = grouped[[c for c in df.columns if "cit" not in c]].first()
    right = grouped[[c for c in df.columns if "cit" in c]].sum(min_count=1)
    df = pd.concat([left, right], axis=1)

    # Write out
    print(f">>> Saving {df.shape[0]:,} observations")
    df.set_index('simple_title').to_csv(TARGET_FILE, encoding="utf8")


if __name__ == '__main__':
    main()
