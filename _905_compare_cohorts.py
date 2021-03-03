#!/usr/bin/env python3
# Author:   Nurzhan Sapargali <nurzh.sapargali@gmail.com>
#           Michael E. Rose <michael.ernst.rose@gmail.com>
"""Compares informal collaboration by cohort of researchers and publication
year of papers.
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from _205_compute_centralities import p_to_stars

OUTPUT_FOLDER = "./990_output/Figures/"

PERSON = {"groups": [0, 1970, 1980, 1990, 2000, 2020],
          "labels": ["<1970", "1970-1979", "1980-1989", "1990-1999", ">=2000"],
          "var": "first_pub_year", "name": "person"}
PAPER = {"groups": [1997, 2002, 2007, 2020],
         "labels": ["1997-2001", "2002-2006", "2007-2011"],
         "var": "year", "name": "paper"}
DEP_VARS = {'num_com_n': {"title": "Average number of commenters per author",
                          "ylabel": "No. of commenters per author"},
            'num_con_n': {"title": "Average number of conferences per author",
                          "ylabel": "No. of conferences per author"},
            'num_sem_n': {"title": "Average number of seminars per author",
                          "ylabel": "No. of seminars per author"},
            'num_auth': {"title": "Average number of co-authors",
                         "ylabel": "No. of co-authors"}}


def add_plot(data, mat, var, ax, scale, ylabel=None, title=None, lw=1.5,
             arrowheight=0.05):
    """Add plot with bars and t-test indicators to a specific ax."""
    # Start plot showing means and error bars
    sns.barplot(y=var, x='cohort', data=data, ax=ax)
    # Aesthetics
    ax.set(ylabel=ylabel, xlabel="")
    ax.set_title(title, pad=15)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    # Parameters
    distance = ax.patches[1].get_bbox().x1 - ax.patches[0].get_bbox().x0
    arrow = {"arrowstyle": f'-[, widthB={distance*scale[0]}, lengthB={scale[1]}',
             "lw": lw, "color": 'black'}
    # Draw bracket spanning neighboring bars with significance stars
    for idx in range(mat.shape[0]-1):
        stars = mat.iloc[idx][idx+1]
        if stars:
            x0 = ax.patches[idx].get_bbox().x0
            x1 = ax.patches[idx+1].get_bbox().x1
            y = max([ax.lines[idx].get_ydata()[-1],
                     ax.lines[idx+1].get_ydata()[-1]])
            height = y*(1 + arrowheight)
            ax.annotate(stars, xytext=((x0+x1)/2, height), arrowprops=arrow,
                        xy=((x0+x1)/2, height), va='bottom', ha='center')


def compare_means(group_1_years, group_2_years, year_column, var, df):
    """Compares means in y for two cohorts defined by year ranges via
    Welch's t-test.
    """
    from scipy.stats import ttest_ind
    group1 = df[(df[year_column].isin(group_1_years))]
    group2 = df[(df[year_column].isin(group_2_years))]
    ttest = ttest_ind(group1[var], group2[var], equal_var=False)
    return ttest


def compute_tstats(data, ranges, var, by_var, verbose=True):
    """Compute lower triangular matrix of significance levels of
    pairwise t-tests.
    """
    if verbose:
        print(f"...{var}:")
    mat = pd.DataFrame(columns=ranges, index=ranges)
    for idx1, r1 in enumerate(ranges):
        for idx2 in range(idx1+1, len(ranges)):
            r2 = ranges[idx2]
            ttest = compare_means(r1, r2, by_var, var, data)
            stars = p_to_stars(ttest[1])
            if verbose and stars:
                print(f"...{r1} vs. {r2}: {ttest[1]:.2}")
            mat.iloc[idx1][idx2] = mat.iloc[idx2][idx1] = stars
    return mat


def read_paper_file():
    """Read file with paper-specific information."""
    PAPER_FILE = "./580_paper_sample/master.csv"
    columns = ["year", "with", "num_auth", "num_coms", "num_con", "num_sem"]
    df = pd.read_csv(PAPER_FILE, usecols=columns, encoding="utf8")
    df = df[df["with"] == 1].drop("with", axis=1).fillna(0)
    for c in columns[-3:]:
        label = c + "_n"
        df[label] = df[c]/df["num_auth"]
    rename = {"num_coms": "num_com", "num_coms_n": "num_com_n"}
    return df.rename(columns=rename)


def read_person_file():
    """Read file with person-specific information."""
    PERSON_FILE = './880_person_sample/paper.csv'
    columns = list(DEP_VARS.keys()) + ['scopus_id', 'first_pub_year', 'num_auth']
    df = pd.read_csv(PERSON_FILE, usecols=columns, encoding="utf8")
    df.columns = [c.replace("avg_", "num_") for c in df.columns]
    return df


def main():
    # Read values of informal collaboration
    PERSON["data"] = read_person_file()
    PAPER["data"] = read_paper_file()

    samples = [(PERSON, "Year of first publication"), (PAPER, "Publication year")]
    for d, xlabel in samples:
        print(f">>> Working on graph for '{d['name']}' sample...")
        # Create cohorts
        d["data"]["cohort"] = pd.cut(d["data"][d["var"]], bins=d["groups"],
                                     right=False, labels=d["labels"],
                                     include_lowest=True)
        ranges = [range(y, d["groups"][idx+1]) for idx, y
                  in enumerate(d["groups"][:-1])]
        n_groups = len(d["groups"]) - 1
        # Initiate figure
        figsize = (11, 5)
        fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=True)
        fig.tight_layout(pad=4)
        scale = ((figsize[0]/2)/(0.6*n_groups), (figsize[1]/2)/(5*n_groups))
        # Add plots
        prev = 0
        for idx, (var, labels) in enumerate(DEP_VARS.items()):
            x = min(max(idx, 1), prev)
            y = idx % 2
            stars = compute_tstats(d["data"], ranges, var, d["var"], verbose=False)
            prev = min(idx, 1)
            add_plot(d["data"], stars, var, ax=axes[x, y], scale=scale,
                     ylabel=labels["ylabel"], title=labels["title"])
        # Aesthetics
        axes[1, 1].set(xlabel=xlabel)
        axes[1, 0].set(xlabel=xlabel)
        # Save graph
        fname = f"{OUTPUT_FOLDER}barcomparison_{d['name']}.pdf"
        fig.savefig(fname, bbox_inches="tight")
        plt.clf()


if __name__ == '__main__':
    main()
