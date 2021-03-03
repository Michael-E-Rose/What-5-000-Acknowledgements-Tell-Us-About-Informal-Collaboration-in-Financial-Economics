#!/usr/bin/Rscript
setwd("/home/panther/Science/Projects/acknowledgements/")

#
# Preparation
#
masterfile = "./580_paper_sample/master.csv"
out_folder = "./990_output/"
omit_stats = c("chi2", 'll', 'theta', 'ser', 'f', 'rsq')  # Drop summary stats

font = "Utopia"  # For graphs
style = "qje"  # For tables
colors.journal = c(JF="#DF0000", RFS="#DF3838", JFE="#DF7070",
                   JFI="#0070DF", JMCB="#388BDF", JBF="#70A7DF")
colors.journalgroup = c(Top="#DF0000", Other="#0070DF")

#
# Variables
#
var = list()
# Dependent variables
var$dep_count = "total_citations"
attr(var$dep_count, "names") = "Total citation count"
var$dep_logit = "top"
attr(var$dep_logit, "names") = "Top publication"
# Controls
var$paper = c("num_pages", "num_auth", "auth_euclid")
attr(var$paper, "names") = c("\\# of pages", "\\# of authors", "Auth. total Euclid")
# Informal
var$informal = c("num_sem", "num_con", "num_coms", "coms_euclid")
attr(var$informal, "names") = c("\\# of seminars", "\\# of conferences",
                                "\\# of commenters", "Com. total Euclid")
# Network
var$auth_auth = c("auth_auth_giant", "auth_auth_eigenvector", "auth_auth_betweenness")
attr(var$auth_auth, "names") = c("Auth. giant (co-author)", "Auth. eigenvector (co-author)",
                                 "Auth. betweenness (co-author)")
var$auth_com = c("auth_com_giant", "auth_com_eigenvector", "auth_com_betweenness")
attr(var$auth_com, "names") = c("Auth. giant (informal)", "Auth. eigenvector (informal)",
                                "Auth. betweenness (informal)")
var$com_auth = c("coms_auth_giant", "coms_auth_eigenvector", "coms_auth_betweenness")
attr(var$com_auth, "names") = c("Com. giant (co-author)", "Com. eigenvector (co-author)",
                                "Com. betweenness (co-author)")
var$com_com = c("coms_com_giant", "coms_com_eigenvector", "coms_com_betweenness")
attr(var$com_com, "names") = c("Com. giant (informal)", "Com. eigenvector (informal)",
                               "Com. betweenness (informal)")
# Other
var$other = c("journal", "year")

#
# Load packages
#
suppressPackageStartupMessages({
  require(data.table)
  require(dplyr)
  require(extrafont)
  require(ggplot2)
  require(gridExtra)
  require(mfx)
  require(rms)
  require(stringr)
  require(stargazer)
  require(VennDiagram)
})

#
# Functions
#
# Return legend
g_legend = function(p){
  tmp = ggplotGrob(p)
  leg = which(sapply(tmp$grobs, function(x) x$name)=="guide-box")
  legend = tmp$grobs[[leg]]
  return(legend)}
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
#  Read in
#
Master.full = read.csv(masterfile, stringsAsFactors=F)
Master.full = within(Master.full, {
  year = as.factor(year)
  year = relevel(year, ref='1997')
  num_coms_n = num_coms/num_auth
  num_con_n = num_con/num_auth
  num_sem_n = num_sem/num_auth
  journal = as.factor(journal)
  journal = relevel(journal, ref='JF')})
Master = Master.full[Master.full[["with"]] == 1,]

# ############ #
# DESCRIPTIVES #
# ############ #
#
# Summary statistics
#
sum_vars = c(var$dep_count, var$dep_logit, var$paper, var$informal,
             var$auth_auth, var$auth_com, var$com_com)
temp = Master[, sum_vars]
summary_com = get_summary(temp)
pos = list()
covariate_labels = attr(sum_vars, "names")
covariate_labels[1] = paste0("\\textbf{Academic success}\\\\\n",
                             covariate_labels[1])
pos$paper = 3
covariate_labels[pos$paper] = paste0("\\midrule\\textbf{Paper Characteristics}\\\\\n",
                                     covariate_labels[pos$paper])
pos$informal = pos$paper + length(var$paper)
covariate_labels[pos$informal] = paste0("\\midrule\\textbf{Informal collaboration}\\\\\n",
                                        covariate_labels[pos$informal])
pos$auth = pos$informal + length(var$informal)
covariate_labels[pos$auth] = paste0("\\midrule\\textbf{Authors' centralities}\\\\\n",
                                    covariate_labels[pos$auth])
pos$com = pos$auth + length(var$auth_auth) + length(var$auth_com)
covariate_labels[pos$com] = paste0("\\midrule\\textbf{Commenters' centralities}\\\\\n",
                                    covariate_labels[pos$com])
rownames(summary_com) = covariate_labels
# # Print
w = latex(summary_com, file=paste0(out_folder, "Tables/sum_paper.tex"),
          center="none", where="ht", rowlabel.just="l", rowlabel="",
          booktabs=T, dcolumns=T, multicol=F, table.env=F)
# !!! Add giant membership in largest component manually
print(mean(temp[["auth_auth_giant"]]), na.rm=T)
print(mean(temp[["auth_com_giant"]]), na.rm=T)
print(mean(temp[["coms_com_giant"]]), na.rm=T)

#
# Correlations
#
corr_vars = c(var$dep_count, var$dep_logit, var$paper, var$informal,
              var$auth_auth[2:length(var$auth_auth)], var$auth_com[2:length(var$auth_com)],
              var$com_com[2:length(var$com_com)])
temp = Master[, corr_vars]
corr_matrix = cor(temp, use="pairwise.complete.obs", method="spearman")
rownames(corr_matrix) = colnames(corr_matrix) = attr(corr_vars, "names")
corr_matrix[upper.tri(corr_matrix)] = NA
diag(corr_matrix) = NA
w = latex(corr_matrix, file=paste0(out_folder, "Tables/corr_paper.tex"),
          center="none", table.env=F, booktabs=T, dec=2, rowlabel.just="l|",
          multicol=F, numeric.dollar=F, dcolumns=T, colheads=F, where="ht")

#
# Count of papers with and without
#
temp = Master.full[, which(names(Master.full) %in% c("journal", "year", "with"))]
temp$Acknowledgements = ifelse(temp$with == 0, "without", "with")
temp = temp %>% group_by(year, journal, Acknowledgements) %>% summarise(count = n())
names(temp)[names(temp) == "journal"] <- "Journal"
temp$Journal = factor(temp$Journal, levels=c("JF", "RFS", "JFE", "JFI", "JMCB", "JBF"))
temp = temp[order(temp$Journal), ]
# Plot
plot = ggplot(temp, aes(x=year, y=count, group=Journal, colour=Journal)) +
  facet_grid(rows=vars(Acknowledgements)) + geom_line(aes(linetype=Journal)) +
  ylab("") + xlab("") + theme_bw() +
  scale_colour_manual(values=colors.journal, name="Journal",
                      guide=guide_legend(nrow=6, title.position="top")) +
  theme(legend.position="right", legend.key=element_blank(),
        strip.text.x=element_text(size=14),
        axis.text=element_text(colour="black", size=10),
        axis.text.x=element_text(angle=45, hjust=1),
        axis.ticks.x=element_blank(),
        panel.grid.minor.x=element_blank(),
        panel.grid.major.x=element_blank(),
        panel.grid.minor.y=element_blank())
ggsave(file=paste0(out_folder, "Figures/line_acknowledgement_status.pdf"),
       plot, width=8, height=5, family=font)

#
# Venn diagramme for extensive margin
#
pdf(paste0(out_folder, "Figures/venn_collaboration.pdf"), family=font)
draw.triple.venn(area1=sum(Master['num_coms'] > 0),
                 area2=sum(Master['num_sem'] > 0),
                 area3=sum(Master['num_con'] > 0),
                 n12=sum(Master['num_coms'] > 0 & Master['num_sem'] > 0),
                 n23=sum(Master['num_sem'] > 0 & Master['num_con'] > 0),
                 n13=sum(Master['num_coms'] > 0 & Master['num_con'] > 0),
                 n123=sum(Master['num_coms'] > 0 & Master['num_sem'] > 0 & Master['num_con'] > 0),
                 fill=c("#009431", "#FFA301", "#868484"),
                 category= c("Commenters", "Seminars", "Conferences"),
                 cat.pos=c(340, 19, 200), cat.dist=c(0.05, 0.05, 0.05),
                 alpha=0.5, lty=2, cex=2, cat.cex=2,
                 print.mode="percent", sigdigs=2)
dev.off()

# ###################### #
# REPLICATION REGRESSION #
# ###################### #
# Regress
est_repl = list()
# # Laband and Tollison (2000), Tab. 4, col. 1
f = as.formula('citcount_5~auth_cumcites+num_pages+num_coms')
est_repl[['one']] = lm(f, Master)
# # Laband and Tollison (2000), Tab. 4, col. 2
f = as.formula('citcount_5~auth_cumcites+num_pages+coms_cumcites')
est_repl[['two']] = lm(f, Master)
# # Laband and Tollison (2000), Tab. 4, col. 3
f = as.formula('citcount_5~auth_cumcites+num_pages+num_coms+coms_cumcites')
est_repl[['three']] = lm(f, Master)
# # Brown (2012), Tab. 8, panel B
f = as.formula('total_citations~num_auth+num_coms+num_sem+num_con+journal+year')
est_repl[['four']] = negbinmfx(f, Master, atmean=F)$fit
# # Write out
lines = list(c("Journal fixed effects", rep("", length(est_repl)-1), "\\checkmark"),
             c("Publication year fixed effects", rep("", length(est_repl)-1), "\\checkmark"))
var_labels = c("Authors' 5-year cites", 'No. of pages', 'No. of authors',
               'No. of commenters', "Commenters' 5-year cites",
               'No. of seminars', 'No. of conferences')
cov_labels = c('Six-year citations', 'Total citations')
stargazer(est_repl, header=F, out=paste0(out_folder, "Tables/reg_paper_replication.tex"),
          omit=c("journal", "year"), omit.stat=omit_stats, style=style,
          add.lines=lines, covariate.labels=var_labels, align=T, float=F,
          dep.var.labels=cov_labels, omit.table.layout="n", model.numbers=T,
          column.sep.width="0pt")


# ######################### #
# REGRESSION WITH INF. COR. #
# ######################### #
# Prepare
Master = within(Master, {
  num_auth = as.factor(num_auth)
  auth_auth_giant = as.factor(auth_auth_giant)
  auth_com_giant = as.factor(auth_com_giant)
  coms_com_giant = as.factor(coms_com_giant)})
Master["num_auth"] = factor(Master$num_auth)
Master$year = relevel(Master$year, ref='1997')
base = paste(c(var$paper, var$other[2], var$informal), collapse="+")
base_cit = paste(base, var$other[1], sep="+")

# Regressions
est = list()
logit_base = paste0(var$dep_logit, "~", base)
est[['base_logit']] = logitmfx(as.formula(logit_base), data=Master)$fit
negbin_base = paste0(var$dep_count, "~", base_cit)
est[['base_negbin']] = negbinmfx(as.formula(negbin_base), data=Master)$fit
negbin_base5 = str_replace(negbin_base, var$dep_count, "citcount_4")
est[['base_negbin5']] = negbinmfx(as.formula(negbin_base5), data=Master)$fit
negbin_base10 = str_replace(negbin_base, var$dep_count, "citcount_9")
est[['base_negbin10']] = negbinmfx(as.formula(negbin_base10), data=Master)$fit
# # Write out
dep_labels = c(attr(c(var$dep_logit, var$dep_count), "names"), "5-year citation count",
               "10-year citation count")
lines = list(c("Paper Characteristics", rep("\\checkmark", length(est))),
             c("Author group size fixed effects", rep("\\checkmark", length(est))),
             c("Publication year fixed effects", rep("\\checkmark", length(est))),
             c("Journal fixed effects", "", rep("\\checkmark", length(est)-1)))
fname = paste0(out_folder, "Tables/reg_paper_informal.tex")
stargazer(est, report="vc*p", header=F, out=fname,
          omit=c(var$paper, var$other), omit.stat=omit_stats[1:length(omit_stats)-1],
          omit.table.layout="n", add.lines=lines, model.numbers=T, align=T,
          float=F, style=style, column.sep.width="0pt", dep.var.labels=dep_labels,
          covariate.labels=attr(var$informal, "names"))


# ############################ #
# REGRESSION WITH CENTRALITIES #
# ############################ #
# Prepare
base = paste(var$paper, collapse="+")
omit_vars = c(var$paper, var$other, var$informal)
labels = attr(c(var$auth_auth, var$auth_com, var$com_com), "names")

# Toppublication regression
est = list()
logit_base = paste0(var$dep_logit, "~", base, "+", var$other[2])
est[['base']] = logitmfx(as.formula(logit_base), data=Master)$fit
logit_auth_auth = paste0(logit_base, "+", paste(var$auth_auth, collapse="+"))
est[['auth_auth']] = logitmfx(as.formula(logit_auth_auth), data=Master)$fit
logit_auth_com = paste0(logit_base, "+", paste(var$auth_com, collapse="+"))
est[['auth_com']] = logitmfx(as.formula(logit_auth_com), data=Master)$fit
logit_com_com = paste0(logit_base, "+", paste(var$com_com, collapse="+"))
est[['com_com']] = logitmfx(as.formula(logit_com_com), data=Master)$fit
logit_all = paste0(logit_base, "+", paste(c(var$auth_auth, var$auth_com, var$com_com), collapse="+"))
est[['all']] = logitmfx(as.formula(logit_all), data=Master)$fit
# # Write out
lines = list(c("Paper Characteristics", rep("\\checkmark", length(est))),
             c("Informal Collaboration", rep("\\checkmark", length(est))),
             c("Author group size fixed effects", rep("\\checkmark", length(est))),
             c("Publication year fixed effects", rep("\\checkmark", length(est))))
fname = paste0(out_folder, "Tables/reg_paper_centr-top.tex")
stargazer(est, report="vc*p", header=F, out=fname,
          omit=omit_vars, omit.stat=omit_stats[1:length(omit_stats)-1],
          omit.table.layout="n", add.lines=lines, model.numbers=T, align=T,
          float=F, style=style, column.sep.width="0pt", covariate.labels=labels,
          dep.var.labels=attr(var$dep_logit, "names"))

# Citations regression
est = list()
negbin_base = paste0(var$dep_count, "~", paste(c(base, var$other), collapse="+"))
est[['base']] = negbinmfx(as.formula(negbin_base), data=Master)$fit
negbin_auth_auth = paste0(negbin_base, "+", paste(var$auth_auth, collapse="+"))
est[['auth_auth']] = negbinmfx(as.formula(negbin_auth_auth), data=Master)$fit
negbin_auth_com = paste0(negbin_base, "+", paste(var$auth_com, collapse="+"))
est[['auth_com']] = negbinmfx(as.formula(negbin_auth_com), data=Master)$fit
negbin_com_com = paste0(negbin_base, "+", paste(var$com_com, collapse="+"))
est[['com_com']] = negbinmfx(as.formula(negbin_com_com), data=Master)$fit
negbin_all = paste0(negbin_base, "+", paste(c(var$auth_auth, var$auth_com, var$com_com), collapse="+"))
est[['all']] = negbinmfx(as.formula(negbin_all), data=Master)$fit
negbin_all = str_replace(negbin_all, "year", "")
negbin_all5 = str_replace(negbin_all, var$dep_count, "citcount_4")
est[['com_com5']] = negbinmfx(as.formula(negbin_all5), data=Master)$fit
negbin_all10 = str_replace(negbin_all, var$dep_count, "citcount_9")
est[['com_com10']] = negbinmfx(as.formula(negbin_all10), data=Master)$fit
# # Write out
lines = list(c("Paper Characteristics", rep("\\checkmark", length(est))),
             c("Author group size fixed effects", rep("\\checkmark", length(est))),
             c("Publication year fixed effects", rep("\\checkmark", length(est)-2), "", ""))
dep_labels = c(attr(var$dep_count, "names"), "5-year citation count",
               "10-year citation count")
fname = paste0(out_folder, "Tables/reg_paper_centr-citation.tex")
stargazer(est, report="vc*p", header=F, out=fname,
          omit=omit_vars, omit.stat=omit_stats, omit.table.layout="n",
          add.lines=lines, model.numbers=T, align=T, float=F, style=style,
          covariate.labels=labels, dep.var.labels=dep_labels,
          column.sep.width="0pt")
