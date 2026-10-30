# FreightSwitch — source-bound human review

Created by **Ziyou Cheng**.

A synthetic shipment-change confirmation workbench: keep the old agreement visible, inspect a proposed address/time, distinguish receipt from acceptance, and trace withdrawal and explicit reconfirmation to exact source messages.

**Prototype, not shipment authorization.** No carrier connection, dispatch action, verified real-world identity or physical-delivery claim. The three-party agreement display uses authored fixtures. Separate human assessments never change that agreement. Optional model suggestions are fallible and remain UNVERIFIED even after a separate bounded local interpretation is recorded; that interpretation is not authenticated counterparty acceptance.

## Public browser demo

**[Open the public interactive demo](https://freightswitch-review-preview.quailsemp.chatgpt.site)** — no login or API key required.

The hosted demo is a **browser-local recorded-output preview**, not the Python/SQLite server and not live inference. It replays authored shipment-state outputs and supports bounded local human interpretations using scripted synthetic examples. Review history stays in that browser's local storage, survives reload there, and can be changed or deleted by its owner; it is not a shared or tamper-proof audit. Counterparty identity is not authenticated, and no human interpretation changes a shipment agreement or dispatches anything.

The complete deployed implementation, all nine exact static assets, source generator, captured synthetic outputs and adapter tests are included in [`preview/`](preview/README.md). Preview identity is `FS-BROWSER-PREVIEW-88f736ed8f28`; the reference core remains `FS-1.6-public-22bb8d9b977b`. The adapter passed **86 checks**, including **43 differential request cases**. Earlier actual internal-preview browser QA reported **23 UI checks**; a separate anonymous public v6 interpretation/reload/export smoke test also passed. These are engineering checks, not model-accuracy results, and CSS viewport tests are not native mobile-device tests. The Python application's **201 tests and six authored scenes** remain separate.

## Run the complete local test build

Python 3.9+ standard library; no dependency installation, account or API key is needed for the offline app.

```sh
python3 server.py --port 8909
```

Open <http://127.0.0.1:8909/>. `/api/health` returns `FS-1.6-public-<source digest>` and the complete source digest. This digest identifies source files, not process attestation. Use fictional messages only. Local review history is stored in `.runtime/`, which is excluded from version control. The server intentionally binds only to loopback; it is not a public hosting server.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 judge_check.py --output .runtime/judge-report.json
python3 evaluate.py
```

Choose a new output filename on each judge-check run; existing reports are preserved. Local socket permission is needed for HTTP tests. Installed Node enables the JavaScript logic tests; skips are reported explicitly, not counted as browser checks. See [JUDGE_FLOW.md](JUDGE_FLOW.md) for a reproducible walkthrough and `verification/public-check-summary.json` for this public candidate's measured checks. Regression tests and six authored scenes are **not model accuracy**.

## What to try

1. **Initial change:** customer requests v2, driver confirms v1; receipt leaves the mismatch unresolved.
2. **Complete confirmation:** all parties confirm the same full version/address/time; an agreement is recorded, not dispatched.
3. **Withdrawal:** a late acknowledgement cannot revive the withdrawn request.
4. **New agreement:** complete v4 confirmation resolves the warning but preserves the earlier sources and resolution history.
5. **Editable synthetic-source workspace:** save a fictional source, generate a scripted mock, inspect the entire quote/version/hash, and approve, reject or request clarification with a reason. Editing the source makes earlier reviews stale.
6. **Separate human-review panel:** load either an authored review example or authored acceptance practice. Both are explicitly scripted mocks, not model responses. A human-reported accept interpretation requires a current sole version, a meaningful reason and three explicit confirmations. It never promotes model acceptance or changes the shipment agreement. See [HUMAN_ACCEPT_WORKFLOW.md](HUMAN_ACCEPT_WORKFLOW.md).
7. **Legacy NVIDIA review:** inspect the already-public recorded October 28 response. It makes no new call. Export the evidence or local interpretation audit.

## NVIDIA Nemotron and Nebius Token Factory

The implemented provider adapter is in `provider.py`. Historical synthetic requests used Nebius Token Factory with `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` to propose wording classifications. Deterministic code binds evidence and maintains the agreement state. No model weights are trained, modified or bundled: inference was performed by the provider, not a local weight file.

The revised wire contract asks for semantic labels and source-specific clarification. The application binds the complete original source, SHA-256, codepoint span and sole literal version to the outbound snapshot. A missing or competing version remains unresolved. Exact binding establishes integrity, not correct semantics or sender identity. There is no guessed action, silent model retry or live-to-mock fallback.

**No new live call is made by the web UI or test suite.** The historical time-limited paid-call authorization has expired; the live CLI is intentionally paused. Keys are not bundled. Configuration flags do not authorize spending. Any new live run requires separately approved credentials, budget and protocol. Frozen v1.4 settings were temperature 0, max_tokens 1800, `chat_template_kwargs.enable_thinking=false`, no response_format. Acceptance of that parameter does not establish internal model behavior.

## Honest model evidence and limitations

Historical summaries report 34 synthetic requests: four early probes, 18 v1 evaluation requests and 12 v2 evaluation requests. The public detailed files retain all 30 frozen evaluation attempts and one early recorded probe; the other early probes are represented only in the aggregate summaries. Calculated cumulative token-rate cost was US$0.00730644, not a tax-inclusive invoice or production estimate.

| Frozen set | Complete cases | Complete observations | Fixed-rule baseline |
| --- | --- | --- | --- |
| v1 | 0/18 | 0/28 | 15/18 cases; 25/28 observations |
| v2 | 4/12 | 6/18 | 10/12 cases; 16/18 observations |

These are different fixed synthetic sets, not evidence of general improvement. v1 had inadequate version-only quotes, three truncations and one validation rejection, including an unsafe ambiguous-OK false acceptance. v2 returned seven evidence-valid observations, rejected seven cases and misclassified one receipt as unclear. No observed false acceptance among returned v2 observations is not a safety guarantee; coverage was low. The baseline is narrow, authored code rather than general language understanding.

**A separate, later frozen v1.5 twelve-case evaluation reported raw semantic results of 7/12 complete cases and 30/36 source labels, but 0/12 strict integrated cases.** This is not the v2 result above. Its underlying fresh-set inputs, labels and private audit are not included in this public release; these aggregate figures are reported, not independently reproduced here. The post-hoc v1.6 public human-review candidate has **no fresh independent model evaluation**. Retaining a suggestion or adding human review does not repair a benchmark score. The now-known evaluation set must not be reused as unseen evidence.

`evaluation/` and `evidence/live-probes-20261028/risk.json` retain the previously public synthetic evidence byte-for-byte. `evaluation_audit.py` checks archived input/attempt hashes and inventories failures without rescoring. Gold labels and the independent scorer are not distributed. Rejected raw model contents are absent, so some exact failure mechanisms cannot be reconstructed. The current validator is not the frozen validator for those evaluations. Do not rescore old attempts as new performance.

The public human-review panel uses newly authored mocks only; the private post-hoc diagnostic replay is deliberately not distributed or served. There is no private evaluation data, secret, usage ledger or model-weight requirement to run this test build.

## Release and competition status

Public source repository: <https://github.com/Declan-Cheng/freightswitch>. This tree provides the complete local Python test build and complete source of the [public browser demo](https://freightswitch-review-preview.quailsemp.chatgpt.site). Anonymous access and the bounded public workflow were verified. Public YouTube video URL: **pending**. Formal competition submission is tracked separately; neither a live demo nor this source tree establishes submission acceptance.

The intended competition track is **Best Apps and Agents**, using Nemotron through Nebius Token Factory. The [official rules](https://nebiusglobalaihackathon.devpost.com/rules) require a working demo/application/test-build URL, public open-source repository and a public YouTube demonstration under three minutes. Judging access must remain available through **December 23, 2026, 20:00 UTC** (12:00 Pacific Standard Time), not December 15. The entry deadline is October 30, 2026, 17:00 UTC. These requirements do not establish eligibility, submission acceptance or any prize outcome.

MIT licensed; see [LICENSE](LICENSE). No AI-superiority, production-safety, real-customer or prize claim.
