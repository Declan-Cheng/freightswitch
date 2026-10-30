"""Development regressions for immutable confirmations and conflict recovery.

These authored typed events are not a model or held-out accuracy evaluation.
"""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from domain import evaluate
from fixtures import events,message,NEW,OLD,LATE


def contradiction():
    return events()[:11]+[message('driver-reject','reject','driver',17,'v2',ref='m05')]


def replacement():
    return [message('new-request','propose','customer',24,'v4',LATE),
            message('new-customer','accept','customer',25,'v4',LATE,'new-request'),
            message('new-dispatch','accept','dispatcher',26,'v4',LATE,'new-request'),
            message('new-driver','accept','driver',27,'v4',LATE,'new-request')]


class AgreementHistoryTests(unittest.TestCase):
    def test_rejection_cannot_rewrite_original_confirmation_evidence(self):
        before=evaluate(events()[:11])
        reject=message('later-rejection','reject','driver',17,'v2',ref='m05',supersedes='m11')
        result=evaluate(events()[:11]+[reject])
        self.assertEqual(result['agreement']['parties'],before['agreement']['parties'])
        self.assertEqual(result['agreement']['details'],before['agreement']['details'])
        self.assertEqual(result['agreement']['confirmationMessageId'],'m11')
        self.assertEqual(result['agreement']['parties']['driver']['evidence'][0]['messageId'],'m11')
        self.assertEqual(result['proposed']['parties']['driver']['status'],'rejected')
        self.assertEqual(result['agreementValidity']['status'],'disputed')
        self.assertTrue(result['agreementValidity']['instructionRiskOpen'])

    def test_withdrawal_is_current_annotation_not_a_rewrite_of_confirmation(self):
        before=evaluate(events()[:11])
        result=evaluate(events()[:11]+[message('cancel','withdraw','customer',17,'v2',ref='m05')])
        self.assertEqual(result['agreement']['parties'],before['agreement']['parties'])
        self.assertEqual(result['agreement']['confirmedAt'],before['agreement']['confirmedAt'])
        self.assertTrue(result['agreement']['revoked'])
        self.assertEqual(result['agreement']['withdrawal']['messageId'],'cancel')
        self.assertEqual(result['agreementValidity']['status'],'revoked')

    def test_original_agreement_retains_first_confirmation(self):
        before=evaluate(events()[:4])['originalAgreement']
        reject=message('old-reject','reject','driver',18,'v1',ref='m01',supersedes='m04')
        result=evaluate(events()[:11]+[reject])
        self.assertEqual(result['originalAgreement'],before)
        self.assertEqual(result['originalAgreement']['parties']['driver']['status'],'accepted')

    def test_old_return_before_final_party_prevents_new_agreement_until_reconfirmed(self):
        rows=events()[:8]+[
            message('driver-new','accept','driver',14,'v2',NEW,'m05'),
            message('driver-old','accept','driver',15,'v1',OLD,'m01'),
            message('dispatch-final','accept','dispatcher',16,'v2',NEW,'m05')]
        result=evaluate(rows)
        self.assertEqual(result['status'],'AT_RISK')
        self.assertEqual(result['agreement']['version'],'v1')
        self.assertEqual(result['latestAcknowledgments']['driver']['version'],'v1')
        self.assertFalse(any(t['type']=='confirmed' and t['version']=='v2' for t in result['transitions']))
        fresh=message('driver-current','accept','driver',17,'v2',NEW,'m05')
        recovered=evaluate(rows+[fresh])
        self.assertEqual(recovered['status'],'ALIGNED')
        self.assertEqual(recovered['agreement']['version'],'v2')
        self.assertEqual(recovered['agreement']['confirmationMessageId'],'driver-current')
        self.assertEqual(recovered['agreementValidity']['status'],'current')

    def test_same_version_reconfirmation_updates_last_not_initial_snapshot(self):
        before=evaluate(events()[:4])
        repeat=message('driver-reconfirm','accept','driver',4,'v1',OLD,'m01')
        result=evaluate(events()[:4]+[repeat])
        self.assertEqual(result['originalAgreement'],before['originalAgreement'])
        self.assertEqual(result['agreement']['confirmationMessageId'],'driver-reconfirm')
        self.assertEqual(result['agreement']['confirmedAt'],repeat['sentAt'])
        self.assertEqual(result['agreement']['parties']['driver']['evidence'][0]['messageId'],'driver-reconfirm')

    def test_new_complete_agreement_resolves_old_conflict_with_both_source_chains(self):
        original=contradiction()+replacement();unchanged=copy.deepcopy(original)
        result=evaluate(original)
        self.assertEqual(original,unchanged)
        self.assertEqual(result['status'],'ALIGNED')
        self.assertEqual(result['agreementValidity']['status'],'current')
        warning=next(w for w in result['warningHistory'] if w['code']=='CONTRADICTION')
        self.assertEqual(warning['status'],'resolved')
        self.assertEqual(warning['version'],'v2')
        self.assertEqual(warning['sentAt'],'2026-10-27T08:17:00-04:00')
        self.assertEqual([e['messageId'] for e in warning['evidence']],['m11','driver-reject'])
        self.assertEqual([e['messageId'] for e in warning['resolution']['evidence']],
                         ['new-request','new-customer','new-dispatch','new-driver'])
        self.assertEqual(result['risks'],[])
        old=next(v for v in result['versions'] if v['version']=='v2')
        self.assertEqual(old['parties']['driver']['status'],'conflict')

    def test_unresolved_conflict_has_one_source_bound_warning_not_empty_duplicate(self):
        result=evaluate(contradiction())
        warnings=[w for w in result['warningHistory'] if w['code']=='CONTRADICTION']
        risks=[r for r in result['risks'] if r['code']=='CONTRADICTION']
        self.assertEqual(len(warnings),1);self.assertEqual(len(risks),1)
        self.assertEqual(risks[0]['evidence'],warnings[0]['evidence'])
        self.assertEqual(len(risks[0]['evidence']),2)

    def test_partial_new_confirmation_cannot_resolve_conflict(self):
        for count in (1,2,3):
            with self.subTest(count=count):
                result=evaluate(contradiction()+replacement()[:count])
                self.assertNotEqual(result['status'],'ALIGNED')
                self.assertEqual(result['resolvedWarnings'],[])

    def test_received_is_not_full_reconfirmation(self):
        new=replacement()[:3]+[message('new-receipt','received','driver',27,'v4',ref='new-request')]
        result=evaluate(contradiction()+new)
        self.assertNotEqual(result['status'],'ALIGNED');self.assertEqual(result['resolvedWarnings'],[])

    def test_late_old_conflicting_acknowledgment_reopens_warning(self):
        late=message('late-old','accept','driver',28,'v2',NEW,'m05')
        result=evaluate(contradiction()+replacement()+[late])
        self.assertEqual(result['status'],'CLARIFY')
        self.assertEqual(result['agreement']['version'],'v4')
        self.assertEqual(result['agreement']['parties']['driver']['evidence'][0]['messageId'],'new-driver')
        warning=next(w for w in result['warningHistory'] if w['code']=='CONTRADICTION')
        self.assertEqual(warning['status'],'open')
        self.assertEqual(warning['evidence'][-1]['messageId'],'late-old')

    def test_new_proposal_must_postdate_conflict_not_only_final_acceptance(self):
        new=[message('n','propose','customer',16,'v4',LATE),
             message('nc','accept','customer',18,'v4',LATE,'n'),
             message('nd','accept','dispatcher',19,'v4',LATE,'n'),
             message('nr','accept','driver',20,'v4',LATE,'n')]
        result=evaluate(contradiction()+new)
        self.assertEqual(result['status'],'CLARIFY');self.assertEqual(result['resolvedWarnings'],[])

    def test_identity_uncertainty_is_not_retired_with_old_conflict(self):
        unknown=message('unknown','accept','driver',23,'v2',NEW,'m05');unknown['identityVerified']=False
        result=evaluate(contradiction()+[unknown]+replacement())
        self.assertEqual(result['status'],'CLARIFY')
        self.assertTrue(any(r['code']=='IDENTITY' for r in result['risks']))
        self.assertTrue(any(w['code']=='CONTRADICTION' and w['status']=='resolved' for w in result['warningHistory']))

    def test_same_version_explicit_correction_can_establish_new_complete_snapshot(self):
        correction=message('correction','accept','driver',18,'v2',NEW,'m05',supersedes='driver-reject')
        result=evaluate(contradiction()+[correction])
        self.assertEqual(result['status'],'ALIGNED')
        self.assertEqual(result['agreement']['confirmationMessageId'],'correction')
        self.assertEqual(result['agreement']['parties']['driver']['evidence'][0]['messageId'],'correction')
        self.assertEqual(result['originalAgreement']['parties']['driver']['evidence'][0]['messageId'],'m04')


if __name__=='__main__':unittest.main(verbosity=2)
