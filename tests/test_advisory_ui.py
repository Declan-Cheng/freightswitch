"""Post-hoc UI logic checks only; no model accuracy or real browser claim."""
from pathlib import Path
import shutil
import subprocess
import unittest

@unittest.skipUnless(shutil.which('node'),'Installed Node required for UI logic checks')
class AdvisoryUIRegressionTests(unittest.TestCase):
    def case(self,name):
        result=subprocess.run(['node',str(Path(__file__).with_name('advisory_ui_harness.js')),name],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_initial_load_is_read_only_and_original_score_visible(self):self.case('initialReadOnly')
    def test_unsupported_suggestion_retains_exact_unverified_evidence(self):self.case('unsupportedSuggestionRetained')
    def test_supported_review_is_source_bound_interpretation_only(self):self.case('supportedReviewIsBound')
    def test_model_acceptance_cannot_be_directly_promoted(self):self.case('acceptsNeverPromote')
    def test_human_assessment_does_not_rewrite_model_label(self):self.case('separateHumanReadingKeepsModel')
    def test_stale_source_preserved_but_all_decisions_disabled(self):self.case('staleSourceCannotDecide')
    def test_tampered_quote_binding_fails_closed(self):self.case('tamperedBindingFailsClosed')
    def test_pending_request_blocks_double_click(self):self.case('busyBlocksDuplicateLoad')
    def test_review_requires_nonblank_reason(self):self.case('reasonRequired')
    def test_failed_request_has_no_automatic_retry(self):self.case('noAutomaticRetry')
    def test_sender_authentication_cannot_be_inferred(self):self.case('falseIdentityClaimRejected')

    def test_accept_requires_every_unchecked_confirmation(self):self.case('acceptRequiresEveryConfirmation')
    def test_accept_rejects_false_or_truthy_nonboolean_checkbox_state(self):self.case('acceptRequiresStrictBooleanState')
    def test_human_accept_binds_source_and_preserves_unverified_model_audit(self):self.case('humanAcceptBoundAudit')
    def test_accept_mode_switch_clears_confirmations(self):self.case('acceptModeSwitchClears')
    def test_accept_source_switch_clears_reason_and_confirmations(self):self.case('acceptSourceSwitchClears')
    def test_accept_stale_refresh_clears_and_disables(self):self.case('acceptStaleRefreshClears')
    def test_accept_missing_version_blocks(self):self.case('acceptMissingVersionBlocked')
    def test_accept_unresolved_version_origin_blocks(self):self.case('acceptCompetingVersionBlocked')
    def test_accept_inflight_double_click_is_one_write(self):self.case('acceptDoubleClickBlocked')
    def test_accept_requires_meaningful_reason(self):self.case('acceptShortReasonBlocked')
    def test_accept_failed_write_clears_without_retry(self):self.case('acceptFailedWriteClears')
    def test_accept_unexpected_authenticated_response_fails_closed(self):self.case('acceptWrongAuthorityFailsClosed')
    def test_authored_practice_is_explicit_mock_with_bound_human_path(self):self.case('authoredPracticeExplicit')
    def test_authored_practice_rejects_false_provenance(self):self.case('practiceFalseProvenanceRejected')

    def test_accept_rejects_falsely_authenticated_reviewer(self):self.case('acceptFalseReviewerAuthenticationBlocked')
    def test_accept_rejects_operational_authority_claim(self):self.case('acceptFalseOperationalAuthorityBlocked')

if __name__=='__main__':unittest.main(verbosity=2)
