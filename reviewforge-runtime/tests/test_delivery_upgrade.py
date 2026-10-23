import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import reviewforge_v4 as rf


class TranslationTests(unittest.TestCase):
    def test_external_body_include_cannot_pass_untranslated(self):
        from translation_pipeline import translate_document, TranslationError
        tex=r'\documentclass{article}\begin{document}\input{results}\end{document}'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(TranslationError,'Flatten'):
                translate_document(tex,tmp,lambda *a:self.fail('Should reject before API'))
            self.assertEqual(json.loads((Path(tmp)/'reports/translation_gate.json').read_text())['status'],'FAILED')

    def test_partial_caption_and_short_sentence_rejected(self):
        from translation_pipeline import mask_tex, validate_unit
        masked,_=mask_tex(r'\section{Methods}\caption{Comparison of model predictions} Results show improved performance.')
        self.assertFalse(validate_unit(masked,masked.replace('Methods','方法'))[0])

    def test_legacy_math_and_comment_separated_citation_are_opaque(self):
        from translation_pipeline import mask_tex, TOKEN
        source='\\cite %keep\n {Smith2024} '+r'\ensuremath{velocity=2}\begin{eqnarray}velocity &=& speed\end{eqnarray}'
        masked,_=mask_tex(source)
        self.assertFalse(TOKEN.sub('',masked).strip())

    def test_windows_newlines_translation_audit(self):
        from translation_pipeline import translate_document
        from delivery_checks import delivery_audit
        tex='\\documentclass{article}\n\\begin{document}\nEnglish words.\n\\end{document}'
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)
            (ws/'review_en.tex').write_bytes(tex.replace('\n','\r\n').encode())
            zh=translate_document((ws/'review_en.tex').read_text(encoding='utf-8'),ws,lambda text,feedback:text.replace('English words.','中文文本。'))
            (ws/'review_zh.tex').write_bytes(zh.replace('\n','\r\n').encode())
            self.assertTrue(delivery_audit(ws)['translation_pass'])

    def test_float_options_spaced_cites_and_column_specs_are_opaque(self):
        from translation_pipeline import mask_tex, TOKEN
        source = r'\begin{figure}[htbp]Caption \citep [see] {key}\end{figure} \multicolumn{2}{lp{3cm}}{Group}'
        masked, saved = mask_tex(source)
        prose = TOKEN.sub('',masked)
        self.assertNotIn('htbp',prose)
        self.assertNotIn('key',prose)
        self.assertNotIn('3cm',prose)
        self.assertIn('Group',prose)

    def test_malformed_heading_is_rejected_before_api(self):
        from translation_pipeline import mask_tex, TranslationError
        with self.assertRaises(TranslationError): mask_tex(r'\subsection{Broken] Text')

    def test_math_citations_captions_table_and_resume(self):
        from translation_pipeline import translate_document, TOKEN
        tex = r'''\documentclass[11pt]{article}
\title{Battery models}
\begin{document}
\section{Methods}
Model results \citep[see]{key} with $x=2$.

\begin{equation}x=2\end{equation}
\begin{figure}\includegraphics[width=\linewidth]{my_file.png}\caption{Model results}\label{fig:a}\end{figure}
\begin{table}\begin{tabular}{ll}Method & Error \\ Hybrid & 0.2\end{tabular}\caption{Comparison}\end{table}
\end{document}'''
        def ask(text, feedback):
            return TOKEN.sub(lambda m:m.group(), text).replace('Battery models','电池模型').replace('Methods','方法').replace('Model results','模型结果').replace('with','其中').replace('Method','方法').replace('Error','误差').replace('Hybrid','混合').replace('Comparison','对比')
        with tempfile.TemporaryDirectory() as tmp:
            result = translate_document(tex, tmp, ask)
            self.assertIn(r'\citep[see]{key}', result)
            self.assertIn(r'$x=2$', result)
            self.assertIn(r'\begin{equation}x=2\end{equation}', result)
            self.assertIn(r'\caption{模型结果}', result)
            self.assertIn(r'\begin{tabular}{ll}方法 & 误差', result)
            self.assertEqual(result, translate_document(tex, tmp, lambda *a: self.fail('Cache missed')))
            report = json.loads((Path(tmp)/'reports/translation_gate.json').read_text())
            self.assertEqual(report['status'], 'PASS')

    def test_dropped_token_and_partial_english_are_rejected(self):
        from translation_pipeline import validate_unit
        self.assertFalse(validate_unit('Result RFPROTECT000000TOKEN', '结果')[0])
        self.assertFalse(validate_unit('This is English.', '这是中文 this is an entire English sentence which the translator did not translate at all')[0])

    def test_deadline_persists_failed_report(self):
        from translation_pipeline import translate_document, TranslationError
        tex = r'\begin{document}English text\end{document}'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(TranslationError):
                translate_document(tex, tmp, lambda *a: self.fail('Expired request'), deadline=0)
            self.assertEqual(json.loads((Path(tmp)/'reports/translation_gate.json').read_text())['status'], 'FAILED')

    def test_untranslated_response_must_not_return_success(self):
        tex = '\\documentclass{article}\n\\begin{document}\n\\section{Methods}\nThis is a complete English paragraph.\n\\end{document}'
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(rf, 'client_chat', side_effect=lambda api, system, payload, **kw: payload.get('body', payload.get('text', 'English'))):
                with self.assertRaises(rf.GateError):
                    rf.generate_chinese_body(None, tex, [], Path(tmp))

    def test_translation_preserves_layout_and_title_is_not_hardcoded(self):
        tex = '\\documentclass[11pt,onecolumn]{article}\n\\title{Battery models}\n\\begin{document}\n\\section{Methods}\nModel results.\n\\end{document}'
        def translate(api, system, payload, **kw):
            text = payload.get('text', payload.get('body', ''))
            return text.replace('Battery models', '电池模型').replace('Methods', '方法').replace('Model results.', '模型结果。')
        with tempfile.TemporaryDirectory() as tmp, patch.object(rf, 'client_chat', side_effect=translate):
            result = rf.generate_chinese_body(None, tex, [], Path(tmp))
            self.assertIn('[11pt,onecolumn]', result)
            self.assertIn('电池模型', result)
            self.assertNotIn('微生物发酵', result)


class ContextTests(unittest.TestCase):
    def test_new_citations_need_registered_key_and_supplied_excerpt(self):
        from evidence_context import candidate_evidence_gate
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)
            (ws/'references.bib').write_text('@article{k, title={Study}}')
            self.assertFalse(candidate_evidence_gate('Old',r'New \cite{k}',ws,'Methods')[0])
            (ws/'evidence_ledger.json').write_text(json.dumps({'entries':[{'claim':'Result','citekey':'k','source_id':'source','locator':'p.4','excerpt':'Primary result','section':'Methods'}]}))
            self.assertTrue(candidate_evidence_gate('Old',r'New \cite{k}',ws,'Methods')[0])
            self.assertFalse(candidate_evidence_gate('Old',r'New \cite{invented}',ws,'Methods')[0])

    def test_changed_bib_invalidates_build(self):
        from delivery_checks import input_digests, build_is_current
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'output').mkdir()
            (ws/'paper.tex').write_bytes(b'source'); (ws/'output/paper.pdf').write_bytes(b'pdf')
            (ws/'references.bib').write_text('old')
            report={'status':'PASS','source_sha256':hashlib.sha256(b'source').hexdigest(),'pdf_sha256':hashlib.sha256(b'pdf').hexdigest(),'inputs':input_digests(ws,'paper')}
            self.assertTrue(build_is_current(ws,'paper',report))
            (ws/'references.bib').write_text('new')
            self.assertFalse(build_is_current(ws,'paper',report))

    def test_writer_and_reviewer_receive_same_source_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws/'evidence_ledger.json').write_text(json.dumps({'entries':[{
                'claim':'Observed result', 'citekey':'k', 'source_id':'paper',
                'locator':'p.4', 'excerpt':'Exact primary result', 'verification_status':'source_located'}]}))
            with patch.object(rf, 'client_chat', return_value='{"accept":true}') as chat:
                rf.write_section(None, '', 'Methods', r'Text \cite{k}', [], workspace=ws)
                writer = chat.call_args.args[2]
                rf.review_section(None, 'Methods', r'Text \cite{k}', r'New text \cite{k}', workspace=ws)
                reviewer = chat.call_args.args[2]
            self.assertEqual(writer['evidence_context'], reviewer['evidence_context'])
            self.assertIn('Exact primary result', str(writer['evidence_context']))


class BuildTests(unittest.TestCase):
    def test_only_final_latex_pass_controls_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'paper.tex').write_text('source')
            def compile(*args, **kwargs):
                (ws/'output/paper.pdf').write_bytes(b'%PDF-test')
                (ws/'output/paper.log').write_text('Output written on paper.pdf; final pass clean.')
                from types import SimpleNamespace
                return SimpleNamespace(returncode=0,stdout="Reference `eq:a' on page 1 undefined on input line 4.",stderr='')
            with patch.object(rf.shutil,'which',return_value='tool'),patch.object(rf.subprocess,'run',side_effect=compile):
                result=rf.compile_tex(ws,'paper')
            self.assertEqual(result['layout_status'],'PASS')

    def test_resume_reuses_current_pdf_and_visual_approval(self):
        from delivery_checks import input_digests
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'output').mkdir(); (ws/'reports').mkdir()
            (ws/'paper.tex').write_text('source'); (ws/'output/paper.pdf').write_bytes(b'pdf')
            digest=hashlib.sha256(b'pdf').hexdigest()
            report={'status':'PASS','layout_status':'PASS', 'source_sha256':hashlib.sha256(b'source').hexdigest(),
                    'pdf_sha256':digest,'inputs':input_digests(ws,'paper'),
                    'rendered':{'status':'PASS','pdf_sha256':digest,'pages':[{'page':1}]}}
            (ws/'reports/paper_build.json').write_text(json.dumps(report))
            (ws/'reports/paper_visual_review.json').write_text(json.dumps({'pdf_sha256':digest,'reviewed_pages':[1], 'reviewer':'reader','approved':True}))
            with patch.object(rf.subprocess,'run',side_effect=AssertionError('Unexpected rebuild')):
                result=rf.compile_tex(ws,'paper',reuse=True)
            self.assertTrue(result['delivery_ready'])

    def test_unresolved_multiline_citation_diagnostic(self):
        from delivery_checks import layout_diagnostics
        log = "Package natbib Warning: Citation `LongKey' on page 1 undefined on input line 3.\nMissing character: There is no 字 in font X!"
        self.assertEqual(layout_diagnostics(log)['status'], 'FAILED')

    def test_stale_visual_approval_is_rejected(self):
        from delivery_checks import visual_status
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp); (ws/'reports').mkdir()
            (ws/'reports/paper_visual_review.json').write_text(json.dumps({'pdf_sha256':'old', 'approved':True, 'reviewer':'reader','reviewed_pages':[1]}))
            self.assertEqual(visual_status(ws, 'paper', {'status':'PASS','pdf_sha256':'new','pages':[{}]}), 'PENDING')

    def test_real_pdf_preview(self):
        try: import fitz
        except ImportError: self.skipTest('optional PyMuPDF not installed')
        from delivery_checks import render_preview
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)
            with fitz.open() as doc:
                doc.new_page().insert_text((50, 50), 'ReviewForge preview test')
                doc.save(ws/'test.pdf')
            result=render_preview(ws/'test.pdf',ws/'preview')
            self.assertEqual(result['status'],'PASS')
            self.assertTrue((ws/'preview/page-001.png').is_file())
            self.assertEqual(result['visual_status'],'PENDING')

    def test_successful_compile_with_overflow_is_not_layout_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws/'paper.tex').write_text(r'\documentclass{article}\begin{document}Text\end{document}')
            def compile(*args, **kwargs):
                (ws/'output'/'paper.pdf').write_bytes(b'%PDF-test')
                from types import SimpleNamespace
                return SimpleNamespace(returncode=0, stdout='Overfull \\hbox (15.0pt too wide) in paragraph at lines 2--3', stderr='')
            with patch.object(rf.shutil, 'which', return_value='tool'), patch.object(rf.subprocess, 'run', side_effect=compile):
                result = rf.compile_tex(ws, 'paper')
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result.get('layout_status'), 'FAILED')
            self.assertFalse(result.get('delivery_ready', True))


class ResearchWorkflowTests(unittest.TestCase):
    def test_score_gain_without_issue_resolution_is_rejected(self):
        from quality_loop import improve
        calls=[]
        def ask(prompt,payload):
            calls.append(prompt)
            if not prompt.startswith('Independent'): return 'Revised text'
            score=10 if len(calls)==1 else 15
            return json.dumps({'scores':dict.fromkeys(['depth','evidence','synthesis','critical_analysis','clarity'],score),
                              'major_issues':['Missing comparison'], 'unsupported_claims':[], 'revision_actions':[]})
        result=improve(ask, lambda *a:(True,''), 'Methods','Original text',max_rounds=1)
        self.assertEqual(result['text'],'Original text')

    def test_coverage_flags_missing_counterevidence_and_figure_brief(self):
        from research_planning import coverage_report, figure_inventory
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)
            (ws/'coverage_matrix.json').write_text(json.dumps({'questions':[{'id':'q1','question':'Does it generalize?', 'supporting_keys':['k'], 'counterevidence_keys':[], 'unresolved':'External validation missing'}]}))
            report=coverage_report(ws,r'Result \cite{k}')
            self.assertIn('counterevidence_search_not_documented', report['questions'][0]['gaps'])
            self.assertFalse(report['complete'])
            figs=figure_inventory(r'\begin{figure}\caption{Method}\label{fig:a}\end{figure}')
            self.assertEqual(figs[0]['label'],'fig:a')
            self.assertEqual(figs[0]['status'],'NEEDS_DESIGN_REVIEW')


if __name__ == '__main__':
    unittest.main()
