#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Merges person-related information with centralities and with measures of
informal collaboration.
"""

from glob import glob

import pandas as pd

from _580_create_paper_sample import custom_pivot, read_centrality_file

COMMENTS_FILE = "./115_collaboration_counts/person.csv"
CENTR_FOLDER = "./205_centralities/"
METRICS_FILE = "./313_author_metrics/metrics.csv"
GENDER_FILE = "./350_gender_estimates/genderize.csv"
NETWORK_FILE = "./880_person_sample/network.csv"
PAPER_FILE = "./880_person_sample/paper.csv"

EXP_CUTOFF = 10  # Diagnostics to detect suspiciously young nodes


def main():
    # Read centrality
    files = glob(CENTR_FOLDER + "yearly*.csv")
    centr = pd.concat([read_centrality_file(f) for f in files], axis=0, sort=True)
    centr = custom_pivot(centr, id_var='node', var_name='year',
                         unstack_by='centrality')
    centr = centr.rename(columns={"node": "scopus_id"})
    centr["year"] = centr["year"].astype(int)

    # Merge with gender
    gender = pd.read_csv(GENDER_FILE, usecols=["ID", "gender"], index_col=0)
    netw = centr.join(gender, on='scopus_id')
    del centr
    gender_unknown = netw.loc[netw["gender"].isna(), "scopus_id"].unique()
    print(f">>> {len(gender_unknown)} researchers w/o gender estimate")
    netw = netw.dropna(subset=['gender'])

    # Merge with author metrics
    metrics = pd.read_csv(METRICS_FILE, dtype={"scopus_id": str})
    rename = {"yearly_cites": "citation_stock", "yearly_pubs": "pub_stock",
              "yearly_wpubs": "weigh_pub_stock"}
    m_cumul = (metrics.drop(["euclid", "year"], axis=1)
                      .fillna(0)
                      .groupby("scopus_id").cumsum()
                      .rename(columns=rename))
    m_comb = pd.concat([metrics, m_cumul], axis=1)
    del m_cumul
    netw = netw.merge(m_comb, 'left', on=['scopus_id', 'year'])

    # Merge with cumulated comments
    comments = pd.read_csv(COMMENTS_FILE, low_memory=False)
    c_cumul = (comments.set_index(['node', 'variable'])
                       .fillna(0)
                       .rolling(window=3, axis=1).sum()
                       .drop(['1997', '1998'], axis=1)
                       .reset_index())
    c_cumul = custom_pivot(c_cumul, id_var='node', var_name='year',
                           unstack_by='variable')
    c_cumul = c_cumul.rename(columns={"node": "scopus_id"})
    c_cumul["year"] = c_cumul["year"].astype(int)
    netw = netw.merge(c_cumul, 'left', on=['scopus_id', 'year'])

    # Compute experience
    netw = netw.set_index("scopus_id")
    first_pub_year = metrics.groupby("scopus_id")["year"].first()
    netw["first_pub_year"] = first_pub_year
    netw['experience'] = netw['year'] - netw['first_pub_year']

    # Diagnostics
    netw = netw.reset_index()
    low_exp = list(netw[netw['experience'] < -EXP_CUTOFF]['scopus_id'].unique())
    print(f">>> {len(low_exp)} researchers with experience less than {EXP_CUTOFF} years:")
    print("; ".join(low_exp))
    cols = ['pub_stock', 'weigh_pub_stock', 'citation_stock', 'euclid',
            'com_out_degree', 'com_in_degree']
    netw[cols] = netw[cols].fillna(0)

    # Compute more variables
    netw['experience'] = netw['experience'].apply(lambda x: max(0, x))
    netw['gender_num'] = (netw['gender'] == "female").astype(int)
    netw['auth_giant'] = (~netw['auth_betweenness_rank'].isnull()).astype(int)

    # Write network file
    netw = netw.sort_values(['scopus_id', 'year'])
    netw.to_csv(NETWORK_FILE, index=False)
    del netw

    # Create paper file
    cols = ('node', 'year', 'num_paper', 'num_com_n', 'num_con_n',
            'num_sem_n', 'num_auth')
    comments = comments[comments["variable"].isin(cols)]
    comments = custom_pivot(comments, id_var='node', var_name='year',
                            unstack_by='variable')
    comments["num_auth"] = comments["num_auth"]-1
    comments["year"] = comments["year"].astype("int32")
    comments = comments.rename(columns={"node": "scopus_id"})
    paper = comments.merge(metrics, "inner", on=["scopus_id", "year"])
    paper = paper.sort_values(["scopus_id", "year"]).set_index("scopus_id")
    paper['first_pub_year'] = first_pub_year
    paper["experience"] = paper['year'] - paper['first_pub_year']
    for c in cols[2:]:
        new = c.replace("num", "avg")
        paper[new] = paper[c]/paper["num_paper"]
    paper.to_csv(PAPER_FILE)


if __name__ == '__main__':
    main()
