import unittest
import tempfile
from pathlib import Path
import json
from paragraph_review import paragraph_options,validate_paragraph_review


def keep(options):
    return {'paragraph_review':[{'paragraph_id':p['id'],'function':'comparison','decision':'keep','message':'Compares independent batch testing with measurement-updated prediction.','adds':'Explains the different information available in the two tests.','destination':'main','reason':'Needed to interpret the compared outcomes.'} for p in options]}


class ParagraphReviewTests(unittest.TestCase):
    def test_relocation_log_preserves_original_and_does_not_modify_prose(self):
        from paragraph_review import preserve_relocations
        text=r'An extended detail records the exact update schedule used in this study \cite{A}.'
        options=paragraph_options(text);report=keep(options);report['paragraph_review'][0].update(decision='move',destination='supplement')
        changes=validate_paragraph_review(text,report)
        with tempfile.TemporaryDirectory() as d:
            preserve_relocations(d,text,changes)
            data=json.loads((Path(d)/'paragraph_relocations.json').read_text())
            self.assertEqual(next(iter(data['records'].values()))['original_paragraph'],text)
            self.assertIn('not independent evidence',data['scope'])

    def test_heading_equation_and_figure_are_not_missing_prose(self):
        text=r'\section{Scope}'+'\n\n'+r'\begin{equation}a=b\end{equation}'+'\n\n'+r'The two studies test different forecasting tasks because one uses measurements acquired during prediction \cite{A,B}.'+'\n\n'+r'\begin{figure}caption text here\end{figure}'
        options=paragraph_options(text);self.assertEqual(len(options),1)
        self.assertFalse(validate_paragraph_review(text,keep(options)))

    def test_review_must_cover_each_real_paragraph_once(self):
        text='This paragraph describes the information provided at prediction time.\n\nThis paragraph compares the two reported validation procedures.'
        options=paragraph_options(text);report=keep(options);report['paragraph_review'].pop()
        with self.assertRaises(ValueError):validate_paragraph_review(text,report)
        report=keep(options);report['paragraph_review'][0]['paragraph_id']='stale'
        with self.assertRaises(ValueError):validate_paragraph_review(text,report)

    def test_proposed_relocation_or_deletion_prevents_automatic_acceptance(self):
        text='This paragraph repeats the previously established evidence boundary without adding a result.'
        options=paragraph_options(text);report=keep(options);report['paragraph_review'][0].update(decision='move',destination='evidence_matrix',reason='Access bookkeeping belongs in the shared matrix.')
        issues=validate_paragraph_review(text,report)
        self.assertEqual(issues[0]['paragraph_id'],options[0]['id'])
        self.assertEqual(issues[0]['decision'],'move')

    def test_equation_change_changes_bound_paragraph_identity(self):
        a='The prediction changes when the input $F_a(t)$ is perturbed while holding the initial conditions fixed.'
        b=a.replace('$F_a(t)$','$F_b(t)$')
        self.assertNotEqual(paragraph_options(a)[0]['id'],paragraph_options(b)[0]['id'])
