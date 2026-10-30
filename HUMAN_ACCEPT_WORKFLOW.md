# Bounded human-reported acceptance interpretation

This public candidate adds a local human assessment, not acceptance by a carrier, driver or customer. It does not authenticate reviewer or source author, modify the shipment agreement, send a message or dispatch anything. It does not improve a frozen model score. The separately reported pre-repair evaluation remains 0/12 strict integrated cases; raw semantics were 7/12 cases and 30/36 source labels. Its underlying private audit is not distributed here, and this candidate has no fresh independent model evaluation.

## Complete local practice flow

1. Run `python3 server.py --port 8909` and open <http://127.0.0.1:8909/>.
2. In the separate advisory panel choose **Load authored acceptance practice (no model)**. This is scripted synthetic data, not a provider prediction or benchmark. The other example button is also explicitly authored.
3. Inspect the full source, sole literal version, SHA-256, revision and unauthenticated sender label. The scripted/model label remains UNVERIFIED. Direct approval of an acceptance suggestion stays blocked.
4. Select your separate **accept** interpretation, enter a source-grounded reason, and explicitly confirm that you reviewed the complete source, checked quoted/negated/conditional context, and understand this is only your local interpretation, not verified counterparty agreement.
5. Record and export its separate human record. `humanKind=accept` and `humanReported=true` do not rewrite `modelKind`, authorize agreement or assert authenticated acceptance.
6. A source body or sender-label revision makes the old record historical/stale. Repeated or fresh acceptance against that old revision is rejected. Reload the audit before reviewing again; there is no automatic retry.

The authored three-party instruction view is not connected to these human assessments. The legacy NVIDIA review elsewhere in the app uses already-public recorded evidence. The private diagnostic replay is not distributed, and its former route returns 404.

## Source-bound request contract

`POST /api/advisory/assessment` requires explicit local Origin and exact fields:

- `actionId`, `proposalId`, `sourceRevision`, `sourceSHA256`, `version`, `quote`, `note`, `humanKind`.
- Only for `humanKind="accept"`: `sourceReviewed=true`, `conditionsQuotesChecked=true`, `localInterpretationOnlyAcknowledged=true` as literal JSON booleans. Missing, false, numeric or string equivalents are rejected.
- Full quote/hash/revision/version must match the current original source and stored mechanically bound suggestion. A sole literal version is mandatory for accept.
- The trimmed accept reason must contain 12–1000 characters. Duplicate JSON keys are rejected. Checkboxes are operator attestations, not proof of correct reading.

The audit is local and append-only. Scripted/model prediction, human interpretation, source identity and operational authority remain distinct. Mechanically exact evidence does not prove semantics or identity; humans can also be mistaken.

## Verification limits

Local regression, HTTP and JavaScript logic checks are reproducible via `judge_check.py`. JavaScript tests use DOM/fetch doubles and are not real-browser visual QA. Neither test counts nor source hashes demonstrate model quality. Public hosting adapters must be separately reviewed and must not claim Python-server identity unless they execute this exact source runtime. New model-accuracy claims require unseen independently authored cases, a new freeze and separately authorized paid calls.
