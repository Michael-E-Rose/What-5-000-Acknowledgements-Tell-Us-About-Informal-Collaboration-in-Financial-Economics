#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Describes global network structure and computes
centralities for all nodes of a given network.
"""

from glob import glob
from operator import itemgetter
from os.path import basename, splitext

import networkx as nx
import pandas as pd
from scipy.stats import spearmanr

from _200_build_networks import year_name, write_stats

NETWORK_FOLDER = "./200_yearly_networks/"
TARGET_FOLDER = "./205_centralities/"
OUTPUT_FOLDER = "./990_output/"


def compute_centralities(H, G):
    """Return DataFrame with node-wise network measures."""
    df = pd.DataFrame(index=sorted(H.nodes()))
    df['giant'] = df.index.map(lambda x: int(str(x) in G))
    try:
        df["in_degree"] = pd.Series(dict(H.in_degree))
        df["out_degree"] = pd.Series(dict(H.out_degree))
    except AttributeError:  # Undirected network
        df["degree"] = pd.Series(dict(H.degree))
    df["num_2nd_neighbors"] = pd.Series(
        {n: num_sec_neigh(n, H) for n in H.nodes()})
    df["betweenness"] = pd.Series(
        nx.betweenness_centrality(G.to_undirected(), weight="weight"))
    df['closeness'] = pd.Series(nx.closeness_centrality(G))
    df["eigenvector"] = pd.Series(
        nx.eigenvector_centrality_numpy(G, weight="weight"))
    return df


def giant(H):
    """Return giant component of a network."""
    try:
        components = nx.connected_components(H)
    except nx.NetworkXNotImplemented:  # Directed network
        components = nx.weakly_connected_components(H)
    return H.subgraph(sorted(components, key=len, reverse=True)[0])


def p_to_stars(p, thres=(0.1, 0.05, 0.01)):
    """Return stars for significance values."""
    stars = []
    for t in thres:
        if p < t:
            stars.append("*")
    return "".join(stars)


def global_analysis(H, G):
    """Return Series with network descriptives."""
    s = pd.Series()
    G = G.to_undirected()
    s["Nodes"] = nx.number_of_nodes(H)
    s["Links"] = nx.number_of_edges(H)
    s['Avg. clustering'] = round(nx.average_clustering(H.to_undirected()), 3)
    try:
        s["Components"] = nx.number_weakly_connected_components(H)
    except nx.NetworkXNotImplemented:  # Undirected network
        s["Components"] = nx.number_connected_components(H)
    s["Giant"] = nx.number_of_nodes(G)
    s["Density"] = round(nx.density(G), 4)
    s["Avg. path length"] = nx.average_shortest_path_length(G)
    s["Diameter"] = nx.diameter(G)
    return s


def num_sec_neigh(node, G):
    """Return number of unique second-order neighbors."""
    neigh_sec_order = nx.single_source_shortest_path_length(G, node, cutoff=2)
    return sum(1 for x in neigh_sec_order.values() if x == 2)


def main():
    auth = pd.DataFrame(columns=['index', 'centrality'])
    com = pd.DataFrame(columns=['index', 'centrality'])
    global_auth = pd.DataFrame()
    global_com = pd.DataFrame()
    print(">>> Now working on:")
    for file in sorted(glob(NETWORK_FOLDER + "*.gexf")):
        # Read in
        n_id = basename(splitext(file)[0])
        year = n_id[:4]
        print("...", n_id)
        H = nx.read_gexf(file)
        G = giant(H)

        # Clustering of random network
        avg_degree = sum(dict(G.degree()).values())/nx.number_of_nodes(G)
        exp_clustering = avg_degree/nx.number_of_nodes(G)
        print(f"    expected clustering of random network: {exp_clustering:,}")

        # Compute centralities
        new = compute_centralities(H, G)
        for col in ["eigenvector", "betweenness"]:
            new[col + "_rank"] = new[col].rank(method="min", ascending=False)

        # Global measures
        s = global_analysis(H, G)
        rho = spearmanr(new["betweenness"], new["eigenvector"], nan_policy='omit')
        s['rho'] = f"{rho[0]:.2f}{p_to_stars(rho[1])}"

        # Add to DataFrame
        new = (new.reset_index()
                  .melt(id_vars=['index'], var_name='centrality',
                        value_name=year))
        if n_id.endswith('auth'):
            auth = auth.merge(new, "outer", on=['index', 'centrality'])
            global_auth[year] = s
        elif n_id.endswith('com'):
            com = com.merge(new, "outer", on=['index', 'centrality'])
            global_com[year] = s

        # Statistics
        ident = "_".join([n_id[5:], year_name(year, -2)])
        stats = {f"N_of_nodes_{ident}": nx.number_of_nodes(H),
                 f"N_of_nodes_{ident}_giant": nx.number_of_nodes(G)}
        write_stats(stats)

    # WRITE OUT
    t = [('Overall', k) for k in ['Size', 'Links', 'Avg. clustering', 'Components']]
    t.extend([('Giant', k) for k in
             ['Size', 'Density', "Avg. path length", "Diameter", "rho"]])
    networks = [('auth', auth, global_auth), ('com', com, global_com)]
    for label, df1, df2 in networks:
        # Centralities
        df1 = df1.sort_values(['index', 'centrality']).set_index('index')
        fname = f"{TARGET_FOLDER}yearly_centr_{label}.csv"
        df1.to_csv(fname, index_label="node", encoding="utf8")
        # Global statistics
        df2 = df2.T
        df2['Avg. path length'] = df2['Avg. path length'].astype(float).round(2)
        df2.columns = pd.MultiIndex.from_tuples(t)
        fname = f"{OUTPUT_FOLDER}Tables/network_{label}.tex"
        df2.to_latex(fname, multicolumn_format='c', column_format='lrrrr|rrrrr')


if __name__ == '__main__':
    main()
