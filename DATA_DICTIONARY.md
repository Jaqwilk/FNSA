# Data dictionary

Read identifiers as **strings**, not floating-point numbers. Empty cells mean unavailable/not served, not zero. Timestamps are timezone-aware ISO 8601 values. `timestamp` is publication/event time; `collected_at` is retrieval time. Join actors by ID and scope, not display name. Original text and names have not been translated.

| Table | Rows | Meaning and key fields |
| --- | ---: | --- |
| `posts.csv` | 63 | Unique `post_id`; `author_id`, `group_id`, exact `timestamp`, `source_url`, `collected_at`. |
| `comments.csv` | 25 | Unique `comment_id`; `author_id`, `post_id`, `parent_comment_id`, `timestamp`, `parent_relation_verified`, provenance. No verified nested replies are present. |
| `actors.csv` | 73 | `actor_id`, explicitly served `actor_type`, optional `display_name` and `username`, `identity_scope`, `evidence_roles`. A missing username/name does not remove an actor. |
| `groups.csv` | 7 | `group_id`, original `name`, `study_role`, public `url`. Study roles guide cohort selection. |
| `mentions.csv` | 5 | Structured source/target actor IDs and target type; containing record type/ID, post/group/time, tagged label and UTF-16 text offsets. A mention is not a friendship. |
| `participation.csv` | 71 | Observed `group_id` + `actor_id` pair; post/comment/activity counts, first/last activity times and evidence type. This is not a member list. |
| `interaction_events.csv` | 30 | Unique `event_id`; interaction type, source/target actor IDs, group/post/comment IDs, event timestamp and URL. Includes self-loop source events. |
| `served_text.csv` | 82 | Record type/ID, post ID, served text, completeness flag and provenance. A served snippet may be incomplete. |
| `engagement_observations.csv` | 133 | Post ID, served reaction/share/comment totals at retrieval, URL and original source file. Multiple rows can be successive snapshots of the same post. |

## Graph identifiers and outputs

A served `User` keeps its source actor ID. A `GroupAnonAuthorProfile` becomes `anonymous:<group_id>:<actor_id>` so its identity does not imply a known person or a cross-group match. There are 7 such profiles. Three display names are unavailable.

`results/node_mapping.csv` maps node IDs to A### pseudonyms. Pseudonyms are stable within this frozen project, including across its three variants. Source identifiers remain present in data and GraphML, so this is not an anonymized public dataset.

`*_events.csv` adds `source_node`, `target_node` and `self_loop` to selected source events. `*_edges.csv` aggregates non-loop events into directed actor pairs. `weight` is event frequency. `*_interactions.graphml` is the combined comments-and-mentions graph. `*_participation.graphml` is the bipartite activity graph. `node_metrics.csv` includes in/out-degree, in/out-strength and directed unweighted betweenness. `summary_networks.csv` reports comments, mentions and combined networks with the same node universe within each variant.

The collection summary JSON preserves an earlier graph convention with interaction endpoints only. Use **`results/summary.json`** for this project's analysis, which retains all observed authors and isolates and removes self-loops. Different conventions explain different node counts; they are not additional collected records.

`collection_validation.json` records original collection checks. `results/validation.json` records final project checks. `sources.json` records cohort roles and sampling scope.
