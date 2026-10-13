# Collection reliability: what our tests established

Scrapling was tested on 13 October 2026 using public, logged-out Facebook views. These were same-day pilots on one IP and two public groups, with selected fixed post threads. They do not establish long-term reliability or complete coverage of the final seven-group sample.

## Repeated observations

- In the initial three-round pilot, two fixed post permalinks returned matching post IDs, author IDs, group IDs and exact timestamps on all six visits. The selected commented post returned the same three comment IDs, authors and timestamps in all three rounds.
- Initial group discovery returned 12, 12 and 16 posts; only 10 IDs appeared in every round. Equal counts did not always mean identical records.
- In the options comparison, the primary group returned the same 12 IDs in all three rounds for each tested browser configuration. Its selected thread returned the same three comments and two explicit tag events across nine browser visits. Those two tag events represented one actor pair, not two different pairs.
- The second group returned 7, 16 and 7 posts. Only seven IDs were present in every round.
- Capturing the primary group's public page-triggered responses raised the structured extractor's yield from 4 HTML records to 12 records in each run. This improved recovery of data already served to the public page; it did not establish complete group coverage.
- Installed Chrome and StealthySession did not improve yield over the tested persistent DynamicSession configuration. The login prompt returned; complete history access was not established.

## Usable data types

**Core:** stable identifiers for served posts/authors/groups, exact publication times on tested direct links, and activity-derived profile-group participation.

**Public interactions when exposed:** comment IDs, authors, post links and exact times; explicit tagged actor IDs. Repeatability was verified on selected fixed threads, not on every thread in the final corpus. No verified nested replies were recovered.

**Optional context:** served post/comment text and exposed reaction/share/comment count snapshots. Text can be incomplete, counts can change, and some fields were missing from previews. Do not sum successive snapshots or infer user identities from totals.

**Not established:** complete member/friend lists, individual reacting/sharing profile lists, reliable usernames, verified nested-reply coverage or complete group history. Authenticated collection was not tested. A feature not established here is not proven impossible in every other setting.

## Implication for this analysis

The frozen dataset is made from the usable records actually recovered. Repeatable extraction of fields is different from repeatable discovery of all records. Therefore the analysis describes observed posting, comment-to-post-author links and explicit tags. It does not estimate all activity, relationships or membership in the groups.

Original trial reports and raw captures remain in the local collection workspace, outside the compact repository. This note summarizes FACEBOOK_CONSISTENCY_REPORT.md and SCRAPLING_OPTIONS_TEST_REPORT.md; the final data counts and graph conventions are recorded separately in data/ and results/.
