#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Creates LaTeX code for rank tables for use in appendix."""

from string import Template


latex = Template("""% Table::rank_short_$year
\\begin{table}[!ht]
 \caption{Ranking according to different centrality measures in the co-author and commenter networks for $year, ranks 1 through 30.\label{Table::rank_short_$year}}
 {\scriptsize \input{Tables/rank_short_$year}}
 \justify \small \\textit{Notes:} Table ranks researchers based on various measures derived from publications in six financial economics journals published between $prev and $year. See \\ref{Section::Data} for variable definition.
\end{table}

""")

out = []
for year in range(1999, 2011+1):
    out.append(latex.substitute(year=year, prev=year-2))

with open("latex_rank_code.txt", 'w') as ouf:
    ouf.writelines(out)
