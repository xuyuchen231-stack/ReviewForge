import tempfile
import unittest
import json
import subprocess
import sys
from pathlib import Path
from editorial_refinement import audit, split_document, preservation_errors, refine


class EditorialRefinementTests(unittest.TestCase):
    def approval(self):
        return '{"accept":true,"scope_preserved":true,"quantities_preserved":true,"uncertainty_preserved":true,"no_new_claims":true,"editorial_goal_met":true,"explanation":"Meaning and necessary scope preserved."}'

    def test_forward_reference_is_not_missing(self):
        result = audit(r'Budget \eqref{eq:t}. Later \begin{equation}t=1\label{eq:t}\end{equation}')
        self.assertEqual(result['missing_references'], [])
        self.assertEqual(result['forward_references'], ['eq:t'])

    def test_split_preserves_document_and_large_protected_environment(self):
        source = r'\documentclass{article}\begin{document}' + '\n\n'.join(['A sentence. '*100]*8) + r'\begin{equation}' + 'x'*3000 + r'\end{equation}\end{document}'
        prefix, chunks, suffix = split_document(source, 2000)
        self.assertEqual(prefix + ''.join(chunks) + suffix, source)
        self.assertTrue(any('x'*3000 in c for c in chunks))

    def test_critical_content_cannot_disappear_or_be_invented(self):
        old = r'Result 12.5\% \cite{A}. \begin{equation}x=1\label{e}\end{equation}'
        self.assertTrue(preservation_errors(old, old.replace('12.5', '15.5')))
        self.assertTrue(preservation_errors(old, old.replace(r'\cite{A}', r'\cite{B}')))
        self.assertTrue(preservation_errors(old, old.replace('x=1', 'x=2')))
        self.assertEqual(preservation_errors(old, old), [])
        self.assertTrue(preservation_errors('A $$x+y$$ result.', 'A $$x-y$$ result.'))
        self.assertTrue(preservation_errors(r'\begin{multline}x+y\end{multline}', r'\begin{multline}x-y\end{multline}'))
        self.assertEqual(preservation_errors(r'Claim \cite{A}. Repeated claim \cite{A}.',r'Claim \cite{A}.'), [])
        self.assertTrue(preservation_errors(r'Claim \cite{A}.',r'Claim \\cite{A}.'))

    def test_dollars_inside_environment_do_not_swallow_following_prose(self):
        text = r'\begin{document}\begin{figure}Caption $x$.\end{figure}' + '\n\n'.join(['Dense prose $y$ and interpretation. '*40]*20) + r'\end{document}'
        prefix, chunks, suffix = split_document(text, 2000)
        self.assertEqual(prefix+''.join(chunks)+suffix, text)
        self.assertLess(max(map(len,chunks)), 4000)

    def test_narrative_environments_can_edit_prose_but_not_math_or_boundaries(self):
        before=r'\begin{abstract}Repeated background $x+y$.\end{abstract}'
        self.assertEqual(preservation_errors(before,before.replace('Repeated background','Clear background')),[])
        self.assertTrue(preservation_errors(before,before.replace('x+y','x-y')))
        self.assertTrue(preservation_errors(before,before.replace('abstract','quote')))

    def test_comment_commands_do_not_create_false_unclosed_environments(self):
        text='Text.\n% '+r'\begin{equation}'+'\nMore text.'
        prefix,chunks,suffix=split_document(text)
        self.assertEqual(prefix+''.join(chunks)+suffix,text)
        self.assertEqual(preservation_errors(text,text),[])

    def test_rejected_or_interrupted_stage_does_not_publish_clean_version(self):
        source = r'\begin{document}The accessible abstract does not establish a split.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            def chat(system, payload, role):
                return payload['body'] if role == 'writer' else '{"accept":false}'
            result = refine(source, Path(folder), chat)
            self.assertEqual(result['status'], 'PAUSED')
            self.assertFalse((Path(folder)/'full_cleaned.tex').exists())
            self.assertTrue(list((Path(folder)/'raw').glob('*.tex')))

    def test_resume_reuses_reviewed_chunks_and_preserves_raw(self):
        source = r'\begin{document}Original scientific result.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            def chat(system, payload, role):
                calls.append(role)
                return payload['body'] if role == 'writer' else '{"accept":true,"scope_preserved":true,"quantities_preserved":true,"uncertainty_preserved":true,"no_new_claims":true,"editorial_goal_met":true,"explanation":"No redundancy; preserve the result."}'
            result = refine(source, Path(folder), chat)
            self.assertEqual(result['status'], 'COMPLETE')
            before = len(calls)
            self.assertEqual(refine(source, Path(folder), chat)['status'], 'COMPLETE')
            self.assertEqual(len(calls), before)
            self.assertEqual(Path(result['versions']['clean']['path']).read_text(encoding='utf-8'), source)

    def test_review_outage_keeps_writer_draft_for_resume(self):
        source=r'\begin{document}Scientific result.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            writers=[]
            def outage(system,payload,role):
                if role=='reviewer':raise TimeoutError('unavailable')
                writers.append(role);return payload['body']
            self.assertEqual(refine(source,folder,outage)['status'],'PAUSED')
            def resumed(system,payload,role):
                if role=='writer':writers.append(role);return payload['body']
                return self.approval()
            self.assertEqual(refine(source,folder,resumed)['status'],'COMPLETE')
            self.assertEqual(len(writers),2)  # Original clean draft reused; only condense writes anew.

    def test_new_source_pause_does_not_mix_completed_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            def chat(system,payload,role):return payload['body'] if role=='writer' else self.approval()
            a=refine(r'\begin{document}First source.\end{document}',folder,chat)
            def paused(system,payload,role):
                if payload['stage']=='condense':raise TimeoutError('pause')
                return chat(system,payload,role)
            b=refine(r'\begin{document}Second source.\end{document}',folder,paused)
            self.assertEqual(b['status'],'PAUSED');self.assertIn('clean',b['versions'])
            self.assertNotEqual(a['versions']['clean']['path'],b['versions']['clean']['path'])
            self.assertFalse((Path(folder)/'refined.tex').exists())

    def test_cache_paths_fit_windows_without_long_path_support(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)/('d'*100)
            def chat(system,payload,role):return payload['body'] if role=='writer' else self.approval()
            result=refine(r'\begin{document}Scientific result.\end{document}',directory,chat)
            self.assertEqual(result['status'],'COMPLETE')
            self.assertLess(max(len(str(p)) for p in directory.rglob('*')),260)

    def test_structured_latex_is_decoded_once(self):
        source=r'\begin{document}Scientific claim \cite{A}.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            def chat(system,payload,role):
                return json.dumps({'latex':payload['body']}) if role=='writer' else self.approval()
            self.assertEqual(refine(source,folder,chat)['status'],'COMPLETE')

    def test_long_paragraph_diagnostics_have_a_bounded_runtime(self):
        script="from editorial_refinement import audit; audit('A clear scientific sentence. '*20000)"
        subprocess.run([sys.executable,'-c',script],timeout=8,check=True,capture_output=True)


if __name__ == '__main__':
    unittest.main()
