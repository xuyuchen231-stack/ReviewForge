import tempfile
import unittest
import json
import subprocess
import sys
from pathlib import Path
from editorial_refinement import audit, split_document, preservation_errors, refine


class RequestDiagnosticTests(unittest.TestCase):
    def test_classifies_only_known_failure_markers_without_leaking_payload(self):
        from editorial_refinement import request_failure
        result = request_failure(RuntimeError('API attempts failed: critic: TimeoutError secret-key private body'))
        self.assertEqual(result['category'], 'connection_failure')
        self.assertNotIn('secret-key', json.dumps(result))
        self.assertNotIn('private body', json.dumps(result))

    def test_rate_limit_is_not_permanent_exhaustion(self):
        from editorial_refinement import request_failure
        result = request_failure(RuntimeError('Provider rate limit (429); respect Retry-After: 3600'))
        self.assertEqual(result['category'], 'rate_limit')
        self.assertEqual(result['retry_after_seconds'], 3600)

    def test_unknown_runtime_error_is_not_guessed_to_be_network(self):
        from editorial_refinement import request_failure
        self.assertEqual(request_failure(RuntimeError('unknown secret'))['category'], 'unknown')


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
        self.assertEqual(preservation_errors('Measured on 18 batches.','Measured on 18 batches; these 18 batches define the dataset.'),[])

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

    def test_caption_wording_can_change_but_table_data_and_caption_math_cannot(self):
        old=r'\begin{table}\caption{Evidence boundary for 12 runs. Access status is recorded in the ledger. $x+y$}\label{tab:a}\begin{tabular}{cc}A&12\\B&15\end{tabular}\end{table}'
        new=old.replace(' Access status is recorded in the ledger.','')
        self.assertEqual(preservation_errors(old,new),[])
        self.assertTrue(preservation_errors(old,new.replace('x+y','x-y')))
        self.assertTrue(preservation_errors(old,new.replace('A&12','A&15')))
        self.assertTrue(preservation_errors(old,new.replace('12 runs','15 runs')))

    def test_old_caption_rejection_resumes_with_review_without_rewriting(self):
        from editorial_refinement import _process_chunk,sha
        body=r'\begin{table}\caption{Evidence. Access is recorded.}\begin{tabular}{c}12\end{tabular}\end{table}'
        candidate=body.replace(' Access is recorded.','')
        with tempfile.TemporaryDirectory() as folder:
            cache=Path(folder)/'cache.json'
            cache.write_text(json.dumps({'source_sha256':sha(body),'binding_sha256':'test','attempt':1,'accepted':False,'pending_review':False,'candidate':candidate,'errors':['Protected mathematical/environment inventory changed']}),encoding='utf-8')
            def chat(system,payload,role):
                self.assertEqual(role,'reviewer');return self.approval()
            self.assertTrue(_process_chunk(body,'clean',chat,cache,None,binding='test')['accepted'])

    def test_old_quote_transport_failure_resumes_as_exact_span_id_review(self):
        from editorial_refinement import _process_chunk,sha
        body=r'A specific scientific fitting result \cite{A}.'
        with tempfile.TemporaryDirectory() as folder:
            cache=Path(folder)/'cache.json';review=json.loads(self.approval())
            cache.write_text(json.dumps({'source_sha256':sha(body),'binding_sha256':'test','attempt':1,'accepted':False,'candidate':body,'errors':[],'review':review,'citation_audit':{'complete':False,'unsupported':[]}}),encoding='utf-8')
            def chat(system,payload,role):
                self.assertEqual(role,'reviewer')
                result=json.loads(self.approval());result['citation_checks']=[{'citekey':'A','status':'supported','reason':'Fitting only','passage_id':payload['citation_passage_options'][0]['id']}]
                return json.dumps(result)
            context={'selected_citekeys':['A'],'anchors':[{'citekey':'A'}],'missing_citekeys':[]}
            self.assertTrue(_process_chunk(body,'clean',chat,cache,None,context,'test')['accepted'])

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

    def test_quality_context_is_shared_and_citation_findings_are_saved(self):
        source=r'\begin{document}A reported fitting result \cite{A}.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder)/'run';run.mkdir()
            (run/'evidence_ledger.json').write_text(json.dumps([{'citekey':'A','claim':'Fit','source_id':'A','locator':'abstract','excerpt':'The model fitted the training trajectories.'}]),encoding='utf-8')
            contexts=[]
            def chat(system,payload,role):
                contexts.append(payload['citation_context'])
                if role=='writer':return json.dumps({'latex':payload['body']})
                review=json.loads(self.approval());review['citation_checks']=[{'citekey':'A','status':'qualified','reason':'Training fit only','passage':'reported fitting result'}]
                return json.dumps(review)
            result=refine(source,Path(folder)/'editorial',chat,quality_workspace=run)
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(contexts[0],contexts[1])
            self.assertTrue(result['citation_audit']['sampled_checks'])
            original_clean=Path(result['versions']['clean']['path'])
            original_bytes=original_clean.read_bytes()
            ledger=run/'evidence_ledger.json'
            entries=json.loads(ledger.read_text(encoding='utf-8'));entries[0]['excerpt']='The model fitted a second set of training trajectories.'
            ledger.write_text(json.dumps(entries),encoding='utf-8')
            def paused(system,payload,role):
                if payload['stage']=='condense':raise TimeoutError('Provider unavailable')
                return chat(system,payload,role)
            updated=refine(source,Path(folder)/'editorial',paused,quality_workspace=run)
            self.assertEqual(updated['status'],'PAUSED')
            self.assertNotEqual(original_clean,Path(updated['versions']['clean']['path']))
            self.assertEqual(original_clean.read_bytes(),original_bytes)

    def test_semantic_rejection_gets_one_targeted_repair_without_restarting(self):
        source=r'\begin{document}A scientific result.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            calls=[];rejected=False
            def chat(system,payload,role):
                nonlocal rejected
                calls.append(role)
                if role=='writer':return payload['body']
                if not rejected:rejected=True;return '{"accept":false,"explanation":"Remove redundant transition."}'
                return self.approval()
            result=refine(source,folder,chat)
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(calls.count('writer'),3)

    def test_exhausted_rejection_is_not_retried_forever_on_resume(self):
        source=r'\begin{document}A scientific result.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            calls=[]
            def chat(system,payload,role):
                calls.append(role)
                return payload['body'] if role=='writer' else '{"accept":false}'
            self.assertEqual(refine(source,folder,chat)['status'],'PAUSED')
            before=len(calls)
            self.assertEqual(refine(source,folder,chat)['status'],'PAUSED')
            self.assertEqual(len(calls),before)

    def test_repeated_access_boilerplate_cannot_increase_despite_model_approval(self):
        source=r'\begin{document}A scientific result.\end{document}'
        with tempfile.TemporaryDirectory() as folder:
            reviewers=[]
            def chat(system,payload,role):
                if role=='writer':return payload['body']+' The accessible abstract does not establish this. The accessible abstract does not establish that.'
                reviewers.append(role);return self.approval()
            self.assertEqual(refine(source,folder,chat)['status'],'PAUSED')
            self.assertEqual(reviewers,[])


if __name__ == '__main__':
    unittest.main()
