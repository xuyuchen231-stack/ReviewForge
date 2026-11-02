import tempfile
import unittest
from unittest.mock import patch
from canonical_extraction import ensure_card
from study_registry import FIELDS
from test_study_registry import packet


class CanonicalExtractionTests(unittest.TestCase):
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
