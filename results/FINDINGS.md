# Findings from the observed sample

The project answers a bounded question about observed commenting and explicit tagging activity. It provides a working minimum SNA, rather than an estimate of all interactions on Facebook.

## Main variant: two community groups, 2026

The study interval runs from 1 January through 13 October 2026 in Europe/Warsaw. The selected sources are WEBC and Expats in Warsaw, Poland. Both a parent post and its event timestamp must fall in the interval.

There are 24 posts, 6 comments and 3 mention events. The directed combined graph has **27 actors, 9 edges, 9 non-loop events and 17 isolates**. Ten actors have at least one observed non-loop connection. There are 19 weak components: two nontrivial components of sizes 7 and 3, plus 17 singletons. Density including isolates is approximately **0.01282**. The largest observed total degree is 5, for pseudonym A044. This is a sample statistic, not evidence of influence.

The participation graph has 27 total nodes (actors plus groups), 25 observed actor-group pairs and 30 post/comment activity events. Its node universe differs from the interaction graph because mentioned targets without authored activity do not become participation actors.

## Sensitivity analysis

| Variant | Posts | Comments | Mentions | Actors | Edges | Isolates | Weak components | Largest component |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Full sample | 63 | 25 | 5 | 73 | 26 | 43 | 48 | 13 |
| Two community groups, all years | 27 | 9 | 5 | 31 | 12 | 17 | 20 | 7 |
| Two community groups, 2026 | 24 | 6 | 3 | 27 | 9 | 17 | 19 | 7 |

The full sample contains 30 raw interaction events, including 3 self-loop events. Removing those leaves 27 events across 26 directed pairs. The two-community all-years variant removes one self-loop event, leaving 13 events across 12 pairs. No self-loops occur in the main 2026 variant.

The full sample mixes different source roles and publication years. A larger observed graph does not demonstrate a more connected population. Density depends on the retained isolates and the sampling process.

## What can be concluded

The captured records support reproducible graph construction, descriptive degree/strength/component statistics and a comparison of source/time selections. Posts and comments also support observed participation analysis. The sparse main network demonstrates the complete analytical workflow.

The sample does not support estimates of group membership, friendship networks, complete reaction/share networks, population-level influence or stable community structure. Comment coverage is incomplete; no verified nested replies were captured. The 133 engagement rows are repeated snapshots and must not be summed as independent user actions. Seven actors are group-scoped anonymous profiles; three display names are missing. Pseudonyms do not remove the source identifiers from the dataset.

A stronger next study should define the groups, time interval and sampling rule before collection, collect comparable comments and verified replies, and repeat captures to measure missingness. Preserve source evidence and deduplicate by exact IDs before creating a new frozen snapshot.
