import json
import tempfile
import unittest
from pathlib import Path
from major_revision import build,prepare,sections,CHECKS,provider_request,delivery_chat
from reviewforge import atomic_json
from test_scientific_quality import registry,verdict


class MajorRevisionTests(unittest.TestCase):
    def test_filler_review_failure_blocks_even_when_other_checks_pass(self):
        r,fid=registry()
        def ask(system,payload,required,role):
            if required=='latex':return {'latex':r'\section{Argument} '+('This abstract principle merits careful consideration in the broader methodological landscape. '*35)+r'\cite{A}', 'evidence_synthesis':[{'finding':'Cohort count reported.','citekeys':['A'],'fact_ids':[fid]}]}
            checks={c:True for c in CHECKS};checks['nonredundant_argument']=False
            return {'accepted':True,'checks':checks,'issues':['Repeated sentences add no comparison or result.']}
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);source=run/'source.tex';source.write_text('\n'.join('\\section{Old '+str(i)+'} original source evidence \\cite{A}.' for i in range(13)))
            atomic_json(run/'study_registry.json',r)
            with self.assertRaisesRegex(ValueError,'Section 1 needs'):build(source,run,ask)
            root=prepare(source,run)
            self.assertEqual(json.loads((root/'progress.json').read_text())['stage'],'reconstruction')

    def test_validation_failure_preserves_safe_reason_and_location(self):
        from major_revision import failure_record
        from study_registry import ingest_card,empty_registry
        from test_study_registry import packet
        try:ingest_card(empty_registry(),packet(),{'fields':{'hardware':{'status':'reported','value':'x','evidence_ids':['bad']}}})
        except ValueError as exc:report=failure_record(exc,Path('run'),{'stage':'facts','study':'A'})
        self.assertEqual(report['request_failure']['category'],'validation_failure')
        self.assertIn('Unanchored canonical fact',report['reason'])
        self.assertEqual(report['study'],'A')
        self.assertEqual(report['error_site']['file'],'study_registry.py')

    def test_real_translation_route_preserves_plain_text_response(self):
        from reviewforge_v4 import generate_chinese_body
        class Provider:
            last_finish_reason=None
            def chat(self,system,user,role):
                data=json.loads(user)
                if 'translation_request' in data:data=json.loads(data['translation_request'])
                return data['text'].replace('Results','\u7ed3\u679c').replace('Growth increases.','\u751f\u957f\u589e\u52a0\u3002')
        provider=Provider()
        def ask(system,payload,required,role):return provider_request(provider,system,payload,required,role)
        class API:
            def chat(self,system,user,role='writer'):return delivery_chat(ask,system,{'translation_request':user},role)
        with tempfile.TemporaryDirectory() as d:
            source=r'\documentclass{article}\begin{document}\section{Results} Growth increases.\end{document}'
            translated=generate_chinese_body(API(),source,[],Path(d))
            self.assertIn('\u751f\u957f\u589e\u52a0',translated)
            self.assertNotIn('Growth increases.',translated)

    def test_invalid_json_retried_within_the_same_request(self):
        from editorial_refinement import resilient_request
        class API:
            last_finish_reason=None
            def __init__(self):self.calls=0
            def chat(self,*args,**kwargs):
                self.calls+=1
                return '{broken' if self.calls==1 else '{"fields":{}}'
        api=API()
        result=provider_request(api,'system',{'source':'fixture'},'fields','writer',retry=lambda request,deadline:resilient_request(request,deadline,sleep=lambda _:None))
        self.assertEqual(api.calls,2);self.assertEqual(result,{'fields':{}})

    def test_rejected_cache_resumes_and_accepted_work_is_reused(self):
        r,fid=registry();allow=[False];calls=[]
        def ask(system,payload,required,role):
            calls.append(required)
            if required=='latex':
                prose=' '.join('Specific comparative evidence informs the stated modeling decision and its practical interpretation.' for _ in range(30))
                return {'latex':'\\section{'+payload['title']+'}\n'+prose+r' \cite{A}.','evidence_synthesis':[{'finding':'The source cohort count is explicit.','citekeys':['A'],'fact_ids':[fid]}],'removed_redundancy':['Repeated general warnings.']}
            if required=='accepted':return {'accepted':allow[0],'issues':[] if allow[0] else ['Need substantive synthesis.'],'checks':{c:allow[0] for c in CHECKS}}
            if required=='examined_passage_ids':return {'examined_passage_ids':[p['id'] for p in payload['passages']],'status':'pass','reason':'Consistent facts across sections.','conflicts':[]}
            return verdict(payload['passages'],fid)
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);source=run/'source.tex';original='\\documentclass{article}\n\\begin{document}\n'+'\n'.join('  \\section{Old '+str(i)+'} Old material with original primary evidence and meaningful explanation \\cite{A}.' for i in range(13))+'\n\\end{document}'
            source.write_text(original);atomic_json(run/'study_registry.json',r)
            self.assertEqual(len(sections(original)),13)
            with self.assertRaisesRegex(ValueError,'Section 1 needs'):build(source,run,ask)
            allow[0]=True;result=build(source,run,ask)
            self.assertEqual(result['status'],'PROVISIONAL_MODEL_PASS')
            self.assertEqual(source.read_text(),original)
            self.assertEqual(len(sections(Path(result['candidate']).read_text())),7)
            before=len(calls);build(source,run,ask);self.assertEqual(len(calls),before)
            self.assertFalse(result['submission_ready'])

    def test_prepare_does_not_call_models_or_claim_completion(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);source=run/'source.tex';source.write_text('\n'.join('\\section{Old '+str(i)+'} text' for i in range(13)))
            root=prepare(source,run)
            self.assertTrue((root/'original.tex').exists())
            self.assertFalse((root/'reconstructed.tex').exists())
            self.assertFalse(json.loads((root/'plan.json').read_text())['submission_ready'])
