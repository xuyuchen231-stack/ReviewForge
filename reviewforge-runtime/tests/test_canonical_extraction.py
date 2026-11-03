import tempfile
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from canonical_extraction import ensure_card
from study_registry import FIELDS
from test_study_registry import packet


class CanonicalExtractionTests(unittest.TestCase):
    def test_reported_unknown_is_metadata_not_a_positive_source_fact(self):
        from canonical_extraction import normalize_card
        from study_registry import empty_registry,ingest_card,study_view
        card={'fields':{'domain':{'status':'reported','value':'unknown','evidence_ids':['s0']},'study_type':{'status':'reported','value':'unknown','evidence_ids':['s0']}}}
        fixed,changes=normalize_card(card);r=empty_registry();ingest_card(r,packet(),fixed)
        self.assertTrue(changes)
        for name in ('domain','study_type'):
            self.assertEqual(study_view(r,'A')['facts'][name]['status'],'unknown')
            self.assertIsNone(fixed['fields'][name]['value'])

    def test_semantic_rejection_repairs_only_failed_field_and_records_review(self):
        review_calls=[];repair_calls=[]
        def ask(system,payload,required,role):
            if required=='fields' and 'repair_fields' in payload:
                repair_calls.append(payload);return {'fields':{'sample_size':{'status':'reported','value':230,'evidence_ids':['s0']}}}
            if required=='fields':return {'fields':{f:({'status':'reported','value':'240 batches','evidence_ids':['s0']} if f=='sample_size' else {'status':'unknown','value':None}) for f in FIELDS}}
            review_calls.append(payload)
            return {'facts':[{'fact_id':f['id'],'status':'fail' if len(review_calls)==1 else 'pass','reason':'Wrong batch count' if len(review_calls)==1 else 'Correct count in source.'} for f in payload['facts']]}
        with tempfile.TemporaryDirectory() as d:
            view=ensure_card(d,packet(),ask,lambda p:p)
            self.assertEqual(view['facts']['sample_size']['value'],230)
            self.assertEqual(len(review_calls),2);self.assertEqual(repair_calls[0]['repair_fields'],['sample_size'])
            saved=json.loads(next((Path(d)/'canonical_cards').glob('*.draft.json')).read_text())
            self.assertEqual(saved['review_history'][0]['review']['facts'][0]['status'],'fail')

    def test_quote_limit_prompt_update_reuses_previously_accepted_cards(self):
        import canonical_extraction as module
        old=module.EXTRACT.replace('Every reported field needs exact supplied evidence IDs. Prefer a few precise spans, but retain all distinct complementary spans needed for a compound field;', 'Every reported field needs exact supplied evidence IDs, preferably up to three and no more than eight complementary spans;')
        calls=[]
        def ask(system,payload,required,role):
            calls.append(required)
            if required=='fields':return {'fields':{f:{'status':'unknown','value':None} for f in FIELDS}}
            return {'facts':[]}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(module,'EXTRACT',old):ensure_card(d,packet(),ask,lambda p:p)
            before=len(calls);ensure_card(d,packet(),ask,lambda p:p);self.assertEqual(len(calls),before)

    def test_review_field_can_retain_thirteen_valid_distinct_spans(self):
        from study_registry import empty_registry,ingest_card,study_view
        p=packet();p['evidence_spans']=[{'id':'s'+str(i),'text':'Organism '+str(i),'locator':'p1'} for i in range(13)]
        r=empty_registry();ingest_card(r,p,{'fields':{'organism':{'status':'reported','value':['several reviewed organisms'],'evidence_ids':['s'+str(i) for i in range(13)]}}})
        self.assertEqual(len(study_view(r,'A')['facts']['organism']['anchors']),13)

    def test_bad_field_is_repaired_without_resending_the_full_document(self):
        calls=[]
        def ask(system,payload,required,role):
            calls.append(payload)
            if required=='fields' and 'repair_fields' in payload:
                return {'fields':{'sample_size':{'status':'reported','value':230,'evidence_ids':['s0']}}}
            if required=='fields':return {'fields':{f:({'status':'reported','value':230,'evidence_ids':['bad']} if f=='sample_size' else {'status':'unknown','value':None}) for f in FIELDS}}
            return {'facts':[{'fact_id':f['id'],'status':'pass','reason':'Count matches primary source.'} for f in payload['facts']]}
        with tempfile.TemporaryDirectory() as d:
            view=ensure_card(d,packet(),ask,lambda p:p)
            self.assertEqual(view['facts']['sample_size']['value'],230)
            self.assertEqual(len(calls),3)
            self.assertEqual(calls[1]['repair_fields'],['sample_size'])
            self.assertNotIn('source',calls[1])

    def test_observed_status_aliases_and_classification_are_normalized_without_dropping_quotes(self):
        from canonical_extraction import normalize_card
        card={'fields':{'domain':{'status':'mixed','value':['mammalian_culture','general_methods'],'evidence_ids':['s0']},'study_type':{'status':'empirical','value':'empirical','evidence_ids':['s0']},'hardware':{'status':'not_inspected_material','value':None,'evidence_ids':[]},'software':{'status':'reported','value':'six reported components','evidence_ids':['s'+str(i) for i in range(6)]}}}
        normalized,changes=normalize_card(card)
        self.assertEqual(normalized['fields']['domain']['value'],'mixed')
        self.assertEqual(normalized['fields']['domain']['status'],'reported')
        self.assertEqual(normalized['fields']['hardware']['status'],'not_in_inspected_material')
        self.assertEqual(normalized['fields']['study_type']['status'],'reported')
        self.assertEqual(len(normalized['fields']['software']['evidence_ids']),6)
        self.assertEqual(card['fields']['domain']['status'],'mixed')
        self.assertTrue(changes)

    def test_all_six_complementary_source_spans_are_retained(self):
        from study_registry import empty_registry,ingest_card,study_view
        p=packet();p['evidence_spans']=[{'id':'s'+str(i),'text':'Component '+str(i),'locator':'p1'} for i in range(6)]
        r=empty_registry();ingest_card(r,p,{'fields':{'software':{'status':'reported','value':'six components','evidence_ids':['s'+str(i) for i in range(6)]}}})
        self.assertEqual(len(study_view(r,'A')['facts']['software']['anchors']),6)

    def test_invalid_extraction_is_saved_before_validation(self):
        calls=[]
        def ask(system,payload,required,role):
            calls.append(required)
            return {'fields':{f:({'status':'reported','value':230,'evidence_ids':['missing']} if f=='sample_size' else {'status':'unknown','value':None}) for f in FIELDS}}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):ensure_card(d,packet(),ask,lambda p:p)
            drafts=list((Path(d)/'canonical_cards').glob('*.draft.json'))
            self.assertEqual(len(drafts),1)
            self.assertEqual(json.loads(drafts[0].read_text())['card']['fields']['sample_size']['evidence_ids'],['missing'])

    def test_same_source_extraction_upgrade_reviews_only_current_card(self):
        structured=[False]
        def ask(system,payload,required,role):
            if required=='fields':return {'fields':{f:({'status':'reported','value':{'batches':230} if structured[0] else 230,'evidence_ids':['s0']} if f=='sample_size' else {'status':'unknown','value':None}) for f in FIELDS}}
            if required=='resolution':return {'resolution':{'selected_fact_id':next(f['id'] for f in payload['alternatives'] if isinstance(f['value'],dict)),'reason':'The structured extraction preserves the same verified cohort count while explicitly identifying its units.'}}
            return {'facts':[{'fact_id':f['id'],'status':'pass','reason':'Primary count and units agree.'} for f in payload['facts']]}
        with tempfile.TemporaryDirectory() as d:
            ensure_card(d,packet(),ask,lambda p:p);structured[0]=True
            with patch('canonical_extraction.EXTRACT','Upgraded extraction schema'):
                view=ensure_card(d,packet(),ask,lambda p:p)
            self.assertFalse(view['conflicts']);self.assertEqual(view['facts']['sample_size']['value'],{'batches':230})

    def test_cached_card_reuses_both_calls_and_source_upgrade_invalidates(self):
        calls=[]
        def ask(system,payload,required,role):
            calls.append(required)
            if required=='fields':return {'fields':{f:({'status':'reported','value':230,'evidence_ids':['s0']} if f=='sample_size' else {'status':'unknown','value':None}) for f in FIELDS}}
            return {'facts':[{'fact_id':f['id'],'status':'pass','reason':'Primary quote agrees.'} for f in payload['facts']]}
        with tempfile.TemporaryDirectory() as d:
            p=packet();ensure_card(d,p,ask,lambda p:p);ensure_card(d,p,ask,lambda p:p)
            self.assertEqual(calls,['fields','facts'])
            p={**p,'source_sha256':'new-source'};ensure_card(d,p,ask,lambda p:p)
            self.assertEqual(len(calls),4)

    def test_incomplete_review_or_rejected_cache_not_accepted(self):
        def ask(system,payload,required,role):
            if required=='fields':return {'fields':{f:({'status':'reported','value':230,'evidence_ids':['s0']} if f=='sample_size' else {'status':'unknown','value':None}) for f in FIELDS}}
            return {'facts':[]}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):ensure_card(d,packet(),ask,lambda p:p)
