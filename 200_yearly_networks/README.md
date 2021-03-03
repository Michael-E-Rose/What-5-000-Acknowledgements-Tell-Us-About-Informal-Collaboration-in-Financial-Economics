Directed and weighted networks of informal collaboration consisting all nodes nodes.

`auth` networks: Every node represents a Scopus author profile. Edges represent co-authorship. Edges are unweighted.

`com` networks: Every node represents either an author, or an acknowledged commenter (including PhD advisers and discussants), or both. Edges represent co-authorship, or an acknowledgment, or both. Edges are weighted to reflect type and frequency of exchange: Edges between authors equal to 1; edges between authors and acknowledged commenters equal to 1/n where n is the number of authors on the paper. Edge weight increases by this number if the edge has existed before.
