#!/usr/bin/Rscript
setwd("/home/panther/Science/Projects/acknowledgements/")

#
# Variables
#
masterfile = "./880_person_sample/network.csv"
out_folder = "./990_output/"

font = "Utopia"  # For graphs
style = "qje"  # For tables
omit_stats = c("chi2", 'll', 'theta', 'ser', 'f', 'rsq')  # Drop summary stats

var = list()
var$node = c("euclid", "pub_stock", "citation_stock", "gender_num",
             "experience", "experiencesq", "com_given")
attr(var$node, "names") = c("Euclid. Index", "Publications", "Citations",
                            "Female", "Experience", "ExperienceSQ", "No. of Thanks")
var$auth = c("auth_giant", "auth_degree", "auth_eigenvector_rank",
             "auth_betweenness_rank")
attr(var$auth, "names") = c("Giant membership (co-author)", "Degree (co-author)",
                            "Eigenvector centrality rank (co-author)",
                            "Betweenness centrality rank (co-author)")
var$com = c("com_given", "com_out_degree", "com_eigenvector_rank",
            "com_betweenness_rank")
attr(var$com, "names") = c("No. of Thanks", "Out-Degree",
                           "Eigenvector centrality rank (informal)",
                           "Betweenness centrality rank (informal)")

#
# Load packages
#
suppressPackageStartupMessages({
  require(Hmisc)
  require(stargazer)
  require(lfe)
  require(arm)
  require(extrafont)
  require(mfx)
})

#
# Functions
#
# Create summary statistics
get_summary = function(x){
  do.call(data.frame,
          list(N=apply(x, 2, function(x) length(which(!is.na(x)))),
               Mean=round(apply(x, 2, mean, na.rm=T), 1),
               Median=round(apply(x, 2, median, na.rm=T), 0),
               "Std Dev."=round(apply(x, 2, sd, na.rm=T), 2),
               Min=round(apply(x, 2, min, na.rm=T), 0),
               Max=round(apply(x, 2, max, na.rm=T), 0)))}


#
# Read in
#
Master = read.csv(masterfile, stringsAsFactors=T)
Master$com_given[is.na(Master$com_given)] = 0
Master = within(Master, {
  year = as.factor(year)
  year = relevel(year, ref='2011')
  scopus_id = as.factor(scopus_id)})
Master["experiencesq"] = Master["experience"]**2

#
# Summary statistics
#
sum_vars = c(var$node[1:(length(var$node)-2)], var$com, var$auth)
temp = Master[, sum_vars]
summary_com = get_summary(temp)
pos = list()
covariate_labels = attr(sum_vars, "names")
covariate_labels[1] = paste0("\\textbf{Researcher Characteristics}\\\\\n",
                             covariate_labels[1])
pos$com = length(var$node) - 1
covariate_labels[pos$com] = paste0("\\midrule\\textbf{Network Centralities}\\\\\n",
                                   covariate_labels[pos$com])
rownames(summary_com) = covariate_labels
# # Print
w = latex(summary_com, file=paste0(out_folder, "Tables/sum_person.tex"),
          center="none", where="ht", rowlabel.just="l", rowlabel="",
          booktabs=T, dcolumns=T, multicol=F, table.env=F)
# !!! Add giant membership in co-author network manually
print(mean(temp[["auth_giant"]]))

#
# Correlations
#
corr_vars = c(var$node[1:(length(var$node)-2)], var$com, var$auth[2:length(var$auth)])
temp = Master[, corr_vars]
corr_matrix = cor(temp, use="pairwise.complete.obs", method="spearman")
rownames(corr_matrix) = colnames(corr_matrix) = attr(corr_vars, "names")
corr_matrix[upper.tri(corr_matrix)] = NA
diag(corr_matrix) = NA
w = latex(corr_matrix, file=paste0(out_folder, "Tables/corr_person.tex"),
          center="none", table.env=F, booktabs=T, dec=2, rowlabel.just="l|",
          multicol=F, numeric.dollar=F, dcolumns=T, colheads=F, where="ht",
          rgroup=c("Researcher Characteristics", "Network Centralities"),
          n.rgroup=c(length(var$node)-2, length(var$com) + length(var$auth)-1))

#
# Regression
#
Master = within(Master, {
  gender_num = as.factor(gender_num)
  gender_num = relevel(gender_num, ref='0')
  gender = relevel(gender, ref='male')})
base = paste(var$node[1:length(var$node)-1], collapse="+")

# Commenter
# # Negative Bininomial with cluster
est_com = list()
for (r_var in var$com[1:2]) {
  f = paste(r_var, base, sep="~")
  est_com[[r_var]] = negbinmfx(f, data=Master, clustervar1="scopus_id")$fit
  f = paste(f, "year", sep="+")
  est_com[[paste0(r_var, "y")]] = negbinmfx(f, data=Master, clustervar1="scopus_id")$fit
}
# # Write out
lines = list(c('Year fixed effects', rep(c("", "\\checkmark"), length(est_com)/2)))
fname = paste0(out_folder, "Tables/reg_person_informal.tex")
stargazer(est_com, out=fname, header=F,
          omit.stat=omit_stats, omit.table.layout="n", omit=c("year"),
          covariate.labels=attr(var$node[1:(length(var$node)-1)], "names"),
          dep.var.labels=attr(var$com[1:2], "names"), add.lines=lines,
          model.numbers=T, align=T, float=F, column.sep.width="0pt", style=style)

Master[["experience"]] = as.factor(Master[["experience"]])
reg_vars = var$node[1:(length(var$node)-3)]
base = paste(reg_vars, collapse="+")
com = paste(c(reg_vars, var$com[1]), collapse="+")
suffix = "|year+experience|0|scopus_id"
base = paste0(base, suffix)
com = paste0(com, suffix)

# # OLS with cluster
est_com = list()
for (r_var in var$com[3:4]) {
  f = paste(r_var, base, sep="~")
  est_com[[r_var]] = felm(eval(parse(text=f)), data=Master)
  f = paste(r_var, com, sep="~")
  est_com[[paste0(r_var, "2")]] = felm(eval(parse(text=f)), data=Master)
}
# # Write out
lines = list(c('Year fixed effects', rep("\\checkmark", length(est_com))),
             c('Experience fixed effects', rep("\\checkmark", length(est_com))))
fname = paste0(out_folder, "Tables/reg_person_centr-com.tex")
stargazer(est_com, out=fname, header=F,
          omit.stat=omit_stats, omit.table.layout="n", omit=c("experience", "year"),
          covariate.labels=attr(c(reg_vars, var$com[1]), "names"), add.lines=lines,
          align=T, model.numbers=T, float=F, style=style, column.sep.width="0pt")

# Coauthor
# # OLS with cluster
est_auth = list()
for (r_var in var$auth[2:length(var$auth)]) {
  f = paste0(r_var, "~", base)
  est_auth[[r_var]] = felm(eval(parse(text=f)), data=Master)
}
# # Write out
lines = list(c('Year fixed effects', rep("\\checkmark", length(est_auth))),
             c('Experience fixed effects', rep("\\checkmark", length(est_auth))))
fname = paste0(out_folder, "Tables/reg_person_centr-coauth.tex")
stargazer(est_auth, out=fname, header=F,
          omit.stat=omit_stats, omit.table.layout="n", omit="experience",
          covariate.labels=attr(reg_vars, "names"), column.sep.width="0pt",
          model.numbers=T, align=T, float=F, style=style, add.lines=lines)
# !!! Change dep. var. labels manually
