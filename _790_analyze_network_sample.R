#!/usr/bin/Rscript
setwd("/home/panther/Science/Projects/acknowledgements")
#
# Variables
#
masterfile = "./780_network_master/network_sample.csv"
out_folder = "./990_output/"

font = "Utopia"  # For graphs
style = "qje"  # For tables

var = list()
var$dep = "y"
attr(var$dep, "names") = "Future productivity"
var$x = c("qc", "r", "c", "t")
attr(var$x, "names") = c("Past output", "Years w/o publication",
                         "Career time", "Year")
var$y = "qr"
attr(var$y, "names") = "Recent past output"
var$auth = c("auth_degree", "auth_num_2nd_neighbors", "auth_giant",
             "auth_closeness", "auth_betweenness",
             "qit1_a", "qit2_a", "top_auth")
attr(var$auth, "names") = c("Degree", "Degree of order 2",
                            "Giant component",
                            "Closeness centrality",
                            "Betweenness centrality",
                            "Coauthors' productivity",
                            "Indirect Coauthors' productivity",
                            "Working with top 1")
var$com = c("com_in_degree", "com_num_2nd_neighbors", "com_giant",
            "com_closeness", "com_betweenness",
            "qit1_c", "qit2_c", "top_com")
attr(var$com, "names") = c("Degree", "Degree of order 2",
                           "Giant component",
                           "Closeness centrality",
                           "Betweenness centrality",
                           "Commenters' productivity",
                           "Indirect Commenters' productivity",
                           "Working with top 1")

#
# Load packages
#
suppressPackageStartupMessages({
  require(Hmisc)
  require(plyr)
  require(stringi)
  require(stargazer)
  require(stats)
  require(forecast)
})

#
#  Read in
#
Master = read.csv(masterfile)
Master = within(Master, {
  t = as.factor(t)
  t = relevel(t, ref='2009')
  c = as.factor(c)
  c = relevel(c, ref='0')})

#
# Regress
#
base = paste(var$dep, '~', paste(var$x, collapse="+"))
form = list()
form['1'] = paste(base)
form['2'] = paste(base, var$y, sep="+")
form['3'] = paste(base, paste(c(var$auth), collapse="+"), sep="+")
form['4'] = paste(base, paste(c(var$com), collapse="+"), sep="+")
form['5'] = paste(base, paste(c(var$auth, var$com), collapse="+"), sep="+")
form['6'] = paste(base, paste(c(var$y, var$auth, var$com), collapse="+"), sep="+")
est = list()
rsq = list()
for (name in names(form)) {
  formula = form[[name]]
  reg = lm(formula, data=Master)
  est[[name]] = reg
  rsq[[name]] = round(summary(reg)$adj.r.squared, 2)
}
labels = c(attr(var$x, "names")[1:2], "delete",
           attr(var$y, "names"), attr(var$auth, "names"),
           attr(var$com, "names"))
stargazer(est, type="html", header=F,
          out=paste0(out_folder, "Tables/coauthor_replication.htm"),
          #omit=c(4:67),
          omit.stat=c("ser", "f"),
          #covariate.labels=labels, column.sep.width="0pt",
          omit.table.layout="n", dep.var.labels=attr(var$dep, "names"),
          model.numbers=T, align=T, float=F, style=style)

#
# RMSE Comparison
#
errors = list()
rmse = list()
diffs = list()
for (name in names(est)) {
  preds = predict(est[[name]])
  error = Master[var$dep] - preds
  errors[[name]] = error
  rmse[[name]] = round(sqrt(mean(error$y^2)), 2)
  diff = abs((rmse[[name]]-rmse[['1']])/rmse[['1']])
  diffs[[name]] = round(diff*100, 2)
}
m = matrix(c(unlist(rsq), unlist(rmse), unlist(diffs)), length(rsq))
m[1,3] = NaN
rownames(m) = c("Benchmark", "Recent past output",
                "Author network variables",
                "Commenter network variables",
                "Auth. net. and com. net. variables",
                "All")
colnames(m) = c("Adj. R${^2}$", "RMSE", "RMSE Differential")
w = latex(m,
      file=paste0(out_folder, "Tables/forecast_person.tex"),
      center="none", where="ht", rowlabel.just="l", rowlabel="",
      booktabs=T, dcolumns=T, multicol=F, table.env=F)
# Add significance levels manually
dm.test(unlist(errors['1']), unlist(errors['2']))$p.value
dm.test(unlist(errors['1']), unlist(errors['3']))$p.value
dm.test(unlist(errors['1']), unlist(errors['4']))$p.value
dm.test(unlist(errors['1']), unlist(errors['5']))$p.value
dm.test(unlist(errors['1']), unlist(errors['6']))$p.value
