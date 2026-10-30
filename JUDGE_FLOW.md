# FreightSwitch: reproducible judge flow

**Development revision, not the previously recorded frozen build.** Synthetic only; no account, API key, package installation, carrier connection or live inference is needed. Python 3.9+ runs the app. Installed Node is used for optional JavaScript logic regressions; skipped checks are reported, never counted as a browser pass.

## One-command verification

```sh
python3 judge_check.py --output .runtime/judge-report.json
python3 server.py --port 8909
```

Use a new output filename when re-running: existing verification evidence is never overwritten. The check runs development tests (including local HTTP), six authored state scenarios and integrity checks over the frozen historical evaluation. It reports **zero new model calls and no fresh model-accuracy score**. Loopback socket access is required.

Open http://127.0.0.1:8909/ and try this approximately 90-second path:

| Step | Inspect | Expected result |
| --- | --- | --- |
| Initial change | Click source `m07` and the driver's old confirmation | Receipt is not acceptance; proposed v2 cannot replace the driver's v1 instruction. |
| Explicit confirmation | Select the complete-confirmation stage | All three confirm the same full address/time; agreement is recorded, not dispatched. |
| Withdrawal | Select the withdrawn-request stage | A late reply cannot revive the withdrawn request. |
| New agreement | Select the final recovery stage | All three explicitly confirm v4. Prior warning and original/resolution sources remain visible. |
| Human review | Expand “Try your own synthetic message”; save, create offline mock, inspect quote/hash, enter reason and approve interpretation | Append-only interpretation audit; agreement remains unchanged. Editing a source invalidates its old review. |
| Evidence | Export evidence; compare `buildId` and `sourceDigest` to `/api/health` | Export is tied to the actual source build and scenario. Hashes show integrity, not identity. |

“Inspect legacy NVIDIA review” is the recorded October 28 result. It makes no new request and does **not** demonstrate the revised model contract. Frozen v2 remains **4/12 complete cases versus 10/12 fixed-rule baseline**. Do not claim those numbers improved because development tests pass.

## What the revision actually improves

- Confirmed acceptance sources are preserved when later messages reject or revoke the instruction. Current validity is separate from historical evidence.
- An older contradiction can close only through a strictly newer, later proposal with complete current confirmation from all parties. Partial/receipt-only or late conflicting responses do not clear it.
- The proposed new AI boundary binds the full original source, literal version and SHA-256 itself, rather than asking the model to reproduce them. The strict action-evidence gate is unchanged. New inference is still required to test semantic coverage.
- Rapid navigation cannot render an older response over a newer selection. Source fields are locked while a review operation is pending. These are logic-regression-tested, not full browser visual QA.

This is a complete working local test build. See README.md for the public source repository and measured validation summary. Judge-accessible hosting, public video and formal submission are separate deliverables; this source tree does not establish their completion. The separate human-review panel offers authored mock examples only, not a private diagnostic replay.
