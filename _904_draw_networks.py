#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Draws networks according to Fruchterman-Reingold algorithm."""

from glob import glob
from os.path import basename, splitext

import matplotlib.pyplot as plt
import networkx as nx

from _005_create_bibliography import TOP_JOURNALS

NETWORK_FOLDER = "./200_yearly_networks/"
OUTPUT_FOLDER = "./990_output/"


def get_edge_color(G):
    """Return a list of edge colors depending on journal where edges occur."""
    color_list = []
    for s, t, data in G.edges(data=True):
        journals = list(set(data['journal'].split('; ')))
        if all(journal in TOP_JOURNALS for journal in journals):
            color_list.append("red")
        elif all(journal not in TOP_JOURNALS for journal in journals):
            color_list.append("blue")
        else:
            color_list.append("purple")
    return color_list


def main():
    print(">>> Now working on:")
    for netf in glob(NETWORK_FOLDER + "*.gexf"):
        # Read in
        ident = splitext(basename(netf))[0]
        print("..." + ident)
        H = nx.to_undirected(nx.read_gexf(netf))

        # Calculate positions
        pos = nx.nx_agraph.pygraphviz_layout(H)

        # Plot
        edge_color = get_edge_color(H)
        plt.figure(3, figsize=(100, 100))
        nx.draw(H, font_size=15, with_labels=False, vmin=0.0, vmax=1.0, pos=pos,
                nodelist=H.nodes(), node_color='black', edge_color=edge_color)

        # Save graph
        fname = f"{OUTPUT_FOLDER}Figures/network_{ident}.pdf"
        plt.savefig(fname, bbox_inches="tight")
        plt.close()


if __name__ == '__main__':
    main()
