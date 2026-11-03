import unittest
from prose_quality import prose_diagnostics


class ProseQualityTests(unittest.TestCase):
    def test_writing_context_excludes_unknown_fact_ids_and_reviewer_boilerplate(self):
        from study_registry import empty_registry,ingest_card,study_view,record_fact_review,facts_for_prose
        from test_study_registry import packet
        r=empty_registry();ingest_card(r,packet(),{'fields':{'sample_size':{'status':'reported','value':230,'evidence_ids':['s0']},'hardware':{'status':'unknown','value':None}}})
        f=study_view(r,'A')['facts']['sample_size'];record_fact_review(r,'A',{'facts':[{'fact_id':f['id'],'status':'qualified','reason':'Count applies to the reported cohort only.'}]})
        context=facts_for_prose(r,{'A'})[0]
        self.assertNotIn('hardware',context['facts']);self.assertIn('hardware',context['unknown_fields'])
        self.assertEqual(context['facts']['sample_size']['id'],f['id'])
        self.assertIn('reported cohort',context['facts']['sample_size']['qualification'])
        self.assertNotIn('fact_ids',context['facts']['sample_size'])

    def test_synthesis_cache_invalidates_when_shared_prose_rules_change(self):
        from unittest.mock import patch
        import synthesis_pipeline as module
        plan={'units':[]};matrix={'studies':[]};evidence={}
        before=module.contract_digest(plan,matrix,evidence)
        with patch.object(module,'PROSE_CONTRACT',module.PROSE_CONTRACT+' Require new argumentative content.'):
            self.assertNotEqual(before,module.contract_digest(plan,matrix,evidence))

    def test_repeated_claim_with_new_citation_still_flagged(self):
        sentence='An accurate historical fit cannot establish reliable prediction under a changed feed trajectory'
        result=prose_diagnostics(sentence+r' \cite{A}.'+'\n\n'+sentence+r' \cite{B}.')
        self.assertEqual(len(result['repeated_sentences']),1)
        self.assertFalse(result['automatic_deletion_allowed'])

    def test_distinct_quantitative_results_and_mathematics_not_collapsed(self):
        result=prose_diagnostics('The held-out prediction error was 0.12 for the first model.\n\nThe held-out prediction error was 0.35 for the second model.\n\n'+r'\begin{equation}x=y+z\end{equation}'+'\n\n'+r'\begin{equation}x=y+z\end{equation}')
        self.assertFalse(result['repeated_sentences']);self.assertFalse(result['similar_paragraphs'])

    def test_repeated_generic_caveats_are_advisory_not_a_word_ban(self):
        result=prose_diagnostics('The accessible abstract does not establish a prospective result.\n\nThe accessible abstract does not establish hardware requirements.\n\nThe accessible abstract does not establish this split.')
        self.assertTrue(result['repeated_meta_phrases'])
        self.assertEqual(result['status'],'REVIEW_HINTS_ONLY')
