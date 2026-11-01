import json
import tempfile
import unittest
from pathlib import Path
from editorial_quality import notation_audit, citation_context, review_citations, acceptance_report


class EditorialQualityTests(unittest.TestCase):
    def test_explicit_symbol_conflict_is_located_not_blindly_renamed(self):
        source=r'The state vector $x$ describes the reactor. The biomass concentration $x$ is measured.'
        result=notation_audit(source)
        self.assertTrue(result['conflicts'])
        self.assertEqual(result['conflicts'][0]['symbol'],'x')
        self.assertEqual(result['source_modified'],False)
        self.assertFalse(notation_audit(r'The state vector $x$ and biomass concentration $X$ differ.')['conflicts'])
        self.assertTrue(notation_audit(r'Denote by $x(t)$ the reactor state. The biomass concentration $x$ is measured.')['conflicts'])

    def test_acronym_expansion_conflicts_and_first_use(self):
        source='MPC is applied. Model predictive control (MPC) follows. Maximum production capacity (MPC) is another meaning.'
        result=notation_audit(source)
        self.assertIn('MPC',[r['acronym'] for r in result['late_definitions']])
        self.assertIn('MPC',[r['acronym'] for r in result['acronym_conflicts']])

    def test_citation_context_is_bounded_and_missing_evidence_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'evidence_ledger.json'
            entry={'citekey':'A','claim':'Improved fitting','source_id':'doi:A','locator':'Abstract','excerpt':'A model improved fitting on training trajectories.','verification_status':'unverified','source_type':'abstract_only'}
            p.write_text(json.dumps([entry]),encoding='utf-8')
            result=citation_context(folder,r'Control improves 20 percent \cite{A,B}.',budget=1000)
            self.assertEqual(result['missing_citekeys'],['B'])
            self.assertLessEqual(len(json.dumps(result['anchors'],ensure_ascii=False)),1000)
            self.assertFalse(result['semantic_verification'])

    def test_model_cannot_invent_a_pass_or_omit_selected_keys(self):
        context={'selected_citekeys':['A'],'anchors':[{'citekey':'A'}],'missing_citekeys':[]}
        self.assertFalse(review_citations({'citation_checks':[]},context)['complete'])
        result=review_citations({'citation_checks':[{'citekey':'A','status':'supported','reason':'fit only'}]},context)
        self.assertTrue(result['complete'])
        self.assertFalse(review_citations({'citation_checks':[{'citekey':'A','status':'supported','reason':'claim'}]},dict(context,anchors=[],missing_citekeys=['A']))['complete'])

    def test_build_and_page_goal_are_separate_from_scientific_approval(self):
        result=acceptance_report(r'\documentclass[twocolumn]{article}\begin{document}Text.\end{document}',{'status':'PASS','layout_status':'PASS'},{'status':'PASS'},pages=83)
        self.assertTrue(result['technical_ready'])
        self.assertFalse(result['page_target_met'])
        self.assertFalse(result['submission_ready'])
        self.assertFalse(result['delivery_ready'])
        self.assertFalse(acceptance_report(r'\documentclass[twocolumn]{article}',{'status':'PASS','layout_status':'PASS','visual_status':'FAILED'},{'status':'PASS'},pages=25)['technical_ready'])
        self.assertFalse(acceptance_report('Text',{'status':'FAIL'},{'status':'PASS'},pages=25)['technical_ready'])


if __name__=='__main__':unittest.main()
