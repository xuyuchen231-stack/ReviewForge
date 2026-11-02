import tempfile
import unittest
from pathlib import Path
from study_registry import empty_registry,ingest_card,study_view,record_fact_review
from scientific_quality import passages,validate_review,review_manuscript
from test_study_registry import packet


def registry():
    r=empty_registry();ingest_card(r,packet(),{'fields':{'sample_size':{'status':'reported','value':230,'evidence_ids':['s0']}}})
    f=study_view(r,'A')['facts']['sample_size'];record_fact_review(r,'A',{'facts':[{'fact_id':f['id'],'status':'pass','reason':'The source reports this count.'}]})
    return r,f['id']


def verdict(items,fid):
    return {'passages':[{'id':p['id'],'status':'pass','reason':'Compared with source facts.','all_substantive_claims_examined':True,
                        'claims':[{'unit_id':u['id'],'text':u['text'],'kind':'empirical','citekeys':['A'],'fact_ids':[fid],'status':'pass','reason':'Source cohort count agrees.'} for u in p['units']]} for p in items]}


class ScientificQualityTests(unittest.TestCase):
    def test_every_occurrence_reviewed_beyond_eight_citations(self):
        r,fid=registry();text='\n\n'.join('Study '+str(i)+r' reported 230 independent batches in the supplied cohort \cite{A}.' for i in range(11))
        calls=[]
        def ask(system,payload,required,role):
            calls.append(required)
            if required=='examined_passage_ids':return {'examined_passage_ids':[p['id'] for p in payload['passages']],'status':'pass','reason':'Consistent counts.','conflicts':[]}
            return verdict(payload['passages'],fid)
        with tempfile.TemporaryDirectory() as d:
            result=review_manuscript(text,r,ask,d,batch_chars=200)
            self.assertEqual(result['reviewed_passages'],11)
            self.assertEqual(result['cross_section_studies_reviewed'],1)
            self.assertEqual(result['status'],'PROVISIONAL_MODEL_PASS')
            before=len(calls);review_manuscript(text,r,ask,d,batch_chars=200);self.assertEqual(before,len(calls))
            review_manuscript(text+'\n\nA further study reported 230 independent batches in this cohort \\cite{A}.',r,ask,d,batch_chars=200)
            self.assertGreater(len(calls),before)

    def test_omitted_sentence_or_substituted_claim_rejected(self):
        r,fid=registry();items=passages(r'The study reported 230 independent batches \cite{A}. Hardware was measured in this experimental study.')
        report=verdict(items,fid);report['passages'][0]['claims'].pop()
        with self.assertRaises(ValueError):validate_review(items,report,r)
        report=verdict(items,fid);report['passages'][0]['claims'][0]['text']='A harmless analytic statement.'
        with self.assertRaises(ValueError):validate_review(items,report,r)

    def test_background_cannot_bypass_empirical_fact_requirement(self):
        r,fid=registry();items=passages(r'The study reported 230 independent industrial batches in this cohort \cite{A}.')
        report=verdict(items,fid);claim=report['passages'][0]['claims'][0];claim.update(kind='background',fact_ids=[])
        with self.assertRaises(ValueError):validate_review(items,report,r)

    def test_cross_study_and_failed_facts_rejected(self):
        r,fid=registry();items=passages(r'The study reported 230 independent industrial batches in this cohort \cite{B}.')
        report=verdict(items,fid);report['passages'][0]['claims'][0]['citekeys']=['B']
        with self.assertRaises(ValueError):validate_review(items,report,r)
        items=passages(r'The study reported 230 independent industrial batches in this cohort \cite{A}.')
        record_fact_review(r,'A',{'facts':[{'fact_id':fid,'status':'fail','reason':'Incorrect extraction.'}]})
        with self.assertRaises(ValueError):validate_review(items,verdict(items,fid),r)

    def test_cross_batch_conflict_blocks_pass(self):
        r,fid=registry();text=r'The first study reported 230 independent batches in this cohort \cite{A}.'+'\n\n'+r'The same study reported a different cohort in its experiment \cite{A}.'
        def ask(system,payload,required,role):
            if required=='examined_passage_ids':
                ids=[p['id'] for p in payload['passages']];return {'examined_passage_ids':ids,'status':'fail','reason':'Conflicting cohort descriptions.','conflicts':[{'passage_ids':ids,'reason':'Same cohort differs.'}]}
            return verdict(payload['passages'],fid)
        with tempfile.TemporaryDirectory() as d:self.assertEqual(review_manuscript(text,r,ask,d,batch_chars=100)['status'],'NEEDS_REVISION')
