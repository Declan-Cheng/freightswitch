# FreightSwitch

A synthetic shipment-change confirmation and stale-version workbench. One shipment, three fictional parties: preserve the old agreement, inspect the proposed address/time, distinguish receipt from acceptance, and follow revocation and explicit reconfirmation back to exact source messages.

**Prototype, not shipment authorization.** No carrier connection, dispatch action, verified real-world identity or physical-delivery claim. Model suggestions are optional and fallible. The default UI is offline and has no live-inference web route.

## Run

Python 3.9+ standard library; no dependency installation needed.

```sh
python3 server.py --port 8909
```

Open http://127.0.0.1:8909/. The source build identifier is `FS-1.4.1-b479055da0ae`; it is a source digest, not process attestation. Use fictional messages only. Review history is stored locally in `.runtime/` and excluded from version control. Approving an interpretation does not change the deterministic shipment agreement.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 evaluate.py --help
```

The reviewed candidate passed 94 development tests, including loopback HTTP tests and six new metadata-envelope regressions. Local socket permissions are required for HTTP tests. This count is not model accuracy.

## Try the workflow

1. Initial change: customer requests v2; driver still confirms v1; receipt leaves risk open.
2. Explicit confirmation: all parties confirm the same full version/address/time.
3. Withdrawn request: late acknowledgment cannot revive it.
4. New agreement: complete v4 confirmation resolves the warning while preserving its history.
5. Expand the editable synthetic-source workspace, save a source, create a scripted mock proposal, inspect the full quote/version/hash, and approve/reject/request clarification with a reason. Editing the source makes prior decisions stale.
6. Inspect the legacy NVIDIA response. It is visibly labeled recorded replay and makes no new call. Export evidence or interpretation audit.

## Actual model evidence and limitations

The historical provider was Nebius Token Factory, model `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. There were 34 real synthetic requests: four early probes, 18 frozen v1 evaluation requests, 12 fresh frozen v2 requests. Calculated token-rate cost: US$0.00730644, not a tax-inclusive invoice or production estimate.

| Frozen evaluation | Complete cases | Complete observations | Fixed rules baseline |
| --- | --- | --- | --- |
| v1 | 0/18 | 0/28 | 15/18 cases; 25/28 observations |
| v2 | 4/12 | 6/18 | 10/12 cases; 16/18 observations |

These are different fixed synthetic sets, not proof of general improvement. v1 supplied inadequate version-only quotes, had three truncations and one validation rejection, and included a dangerous ambiguous-OK false acceptance. v2 returned seven evidence-valid observations but rejected seven cases and misclassified one receipt as unclear. No observed false acceptance among returned v2 observations is not a safety guarantee; coverage is low. The rules baseline is narrow and authored for the fixed comparison, not general language understanding.

`evaluation/` preserves synthetic inputs, exact sanitized attempts and independently reported score summaries. Gold labels and the independent scorer are not distributed here; score reproduction therefore requires those separately. The current validator is not the frozen validator for either evaluation: do not rescore old attempts as new performance.

v1.4.1 supports only a fixed `Sent <timezone-aware ISO timestamp>. Customer|Dispatcher|Driver: <complete payload>` presentation envelope. It can omit that header only with the entire remaining payload quoted; qualifications, forwarded text, injection markers and competing versions remain checked. Role labels confer no identity authority. This repair has development regression coverage but no fresh independent model evaluation.

## Provider boundary

`provider.py` contains the adapter and structured evidence validation. Frozen v1.4 settings were temperature 0, max_tokens 1800, `chat_template_kwargs.enable_thinking=false`, and no response_format. Endpoint acceptance of the parameter is not proof of internal model behavior. No secret is bundled. Live CLI is intentionally paused; the historical time-limited budget has expired. Do not treat configuration flags or copied historical limits as permission to spend. Any new live run needs a separate budget and protocol.

## Delivery state

Local prototype and synthetic evidence only. Public repository publication, judge-accessible hosting through December 15, a recorded public video under three minutes and formal competition submission require separate completion. No hosted judge demo or public video is provided by this package. No AI-superiority, production-safety, real-customer or prize claim.

MIT licensed; see LICENSE.
