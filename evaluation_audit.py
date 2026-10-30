"""Read-only historical evidence integrity and failure inventory. Never rescoring."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def audit_evaluation(folder):
    folder=Path(folder)
    manifest=json.loads((folder/'manifest.json').read_text())
    inputs_bytes=(folder/'inputs.jsonl').read_bytes();attempts_bytes=(folder/'attempts.jsonl').read_bytes()
    checks=dict(inputsSHA256Matches=hashlib.sha256(inputs_bytes).hexdigest()==manifest['inputSHA256'],
                attemptsSHA256Matches=hashlib.sha256(attempts_bytes).hexdigest()==manifest['attemptsSHA256'])
    inputs=[json.loads(line) for line in inputs_bytes.splitlines() if line.strip()]
    attempts=[json.loads(line) for line in attempts_bytes.splitlines() if line.strip()]
    input_ids=[r['case_id'] for r in inputs];attempt_ids=[r['case_id'] for r in attempts]
    checks['caseInventoryMatches']=len(input_ids)==len(set(input_ids))==len(attempt_ids)==len(set(attempt_ids))==manifest['inputCases'] and set(input_ids)==set(attempt_ids)
    checks['sourceHashesMatch']=all(hashlib.sha256(m['body'].encode()).hexdigest()==m['sha256'] for row in inputs for m in row['messages'])
    rejected=[r for r in attempts if r.get('rejected')]
    return dict(evaluation=folder.name,historicalBuildId=manifest['buildId'],integrityChecks=checks,integrityPassed=all(checks.values()),
        frozenIndependentScore=json.loads((folder/'independent-score.json').read_text()),
        originalAttempts=len(attempts),rejectedCases=len(rejected),
        failureInventory=dict(Counter(r.get('error_detail') or r.get('error_class') or 'unspecified' for r in rejected)),
        rejectedCasesWithoutStructuredOutput=sum(r.get('result') is None for r in rejected),
        scoreProvenance='Historical externally reported score file; gold labels/scorer absent, not recomputed or independently verifiable here.',
        diagnosisLimit='Rejected attempts retain response hashes, not raw model content; token/quote mismatch mechanisms cannot be reconstructed from these artifacts alone.',
        currentRevisionRescore=False,newModelCalls=0)


def report():
    return dict(format='freightswitch-historical-evidence-audit-v1',evaluations=[audit_evaluation(ROOT/'evaluation'/v) for v in ('v1','v2')],
        currentModelAccuracy=None,newModelCalls=0,notice='Integrity and failure inventory only. Original scores unchanged. No replay can establish fresh model performance.')

if __name__=='__main__':print(json.dumps(report(),indent=2))
