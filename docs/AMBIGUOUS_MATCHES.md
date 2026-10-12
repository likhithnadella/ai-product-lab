# Ambiguous entity matching

An exact identifier match is useful evidence, but it does not prove that the first record returned by a source is the correct person. Two distinct records may share an email or phone number. Previously, when both scored above the automatic-match threshold, input ordering decided which record won. That can silently merge identities.

The resolver now compares the top two distinct source identities. When the highest score is at least the review threshold but its lead is less than 0.05, it returns `review` rather than `matched`. Repeated copies of the same `(source, external_id)` are treated as one candidate. Candidates without an external ID remain distinct because we cannot establish that they are duplicates. A clear winner still follows the existing thresholds.

This margin is a conservative policy choice, not a calibrated probability or measured optimal threshold. It reduces one class of false merges at the cost of more manual reviews. Regression tests cover ties, near ties, clear winners, and repeated source records. A future labeled dataset should measure false-merge and review rates and tune the margin accordingly. Longer term, candidate identifiers should be source-qualified throughout the API; the current response exposes only `external_id`.
