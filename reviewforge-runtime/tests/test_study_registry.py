import json
from pathlib import Path
import tempfile
import unittest
from study_registry import empty_registry,ingest_card,study_view,registry_digest,overlay_matrix,record_fact_review,resolve_conflict,eligible_facts


def packet(text='The study used 230 batches. Hardware was reported.',key='A',sha='source-a'):
    return {'citekey':key,'source_sha256':sha,'source_type':'full_text_excerpt','document_access':'full_text',
            'inspection_coverage':'selected_excerpt','source_text_file':'source.txt','evidence_spans':[{'id':'s0','text':text,'locator':'p2'}]}


class StudyRegistryTests(unittest.TestCase):
    def test_unknown_cannot_overwrite_reported_fact(self):
        r=empty_registry();p=packet()
        ingest_card(r,p,{'fields':{'sample_size':{'status':'reported','value':230,'evidence_ids':['s0']}}})
        ingest_card(r,p,{'fields':{'sample_size':{'status':'unknown','value':None}}})
        self.assertEqual(study_view(r,'A')['facts']['sample_size']['value'],230)

    def test_conflicting_positive_facts_are_not_last_write_wins(self):
        r=empty_registry();p=packet()
        for value in [230,240]:
            p=packet(text='The study used '+str(value)+' batches.',sha='source-'+str(value))
            ingest_card(r,p,{'fields':{'sample_size':{'status':'reported','value':value,'evidence_ids':['s0']}}})
        self.assertEqual(study_view(r,'A')['facts']['sample_size']['status'],'conflict')

    def test_partial_access_cannot_prove_not_reported(self):
        with self.assertRaises(ValueError):
            ingest_card(empty_registry(),packet(),{'fields':{'hardware':{'status':'not_reported','value':None}}})

    def test_subset_digest_and_matrix_project_current_facts(self):
        r=empty_registry();p=packet()
        ingest_card(r,p,{'fields':{'hardware':{'status':'reported','value':'workstation','evidence_ids':['s0']}}})
        fact=study_view(r,'A')['facts']['hardware'];record_fact_review(r,'A',{'facts':[{'fact_id':fact['id'],'status':'pass','reason':'Exact source confirms hardware.'}]})
        before=registry_digest(r,{'A'})
        ingest_card(r,packet(key='B',sha='source-b'),{'fields':{'hardware':{'status':'reported','value':'other','evidence_ids':['s0']}}})
        self.assertEqual(before,registry_digest(r,{'A'}))
        matrix=overlay_matrix({'studies':[{'citekey':'A','source_type':'abstract_only','fields':{'hardware':{'status':'not_accessible','value':'not reported'}}}]},r)
        self.assertEqual(matrix['studies'][0]['fields']['hardware']['value'],'workstation')
        self.assertEqual(matrix['studies'][0]['source_type'],'full_text_excerpt')

    def test_current_full_text_overrides_old_abstract_ledger_label(self):
        from autonomous_review import source_packet
        with tempfile.TemporaryDirectory() as folder:
            ws=Path(folder);source=ws/'primary_sources/a';source.mkdir(parents=True);(source/'source.txt').write_text('Current full source. Training data and hardware described.')
            run=ws/'run';run.mkdir()
            p=source_packet(ws,run,{'citekey':'A','source_type':'abstract_only','source_directory':'primary_sources/a'},'hardware')
            self.assertEqual(p['source_type'],'full_text_excerpt')
            self.assertEqual(p['document_access'],'full_text')

    def test_failed_fact_cannot_supply_evidence(self):
        r=empty_registry();ingest_card(r,packet(),{'fields':{'hardware':{'status':'reported','value':'workstation','evidence_ids':['s0']}}})
        fact=study_view(r,'A')['facts']['hardware'];record_fact_review(r,'A',{'facts':[{'fact_id':fact['id'],'status':'fail','reason':'Does not establish this hardware.'}]})
        self.assertFalse(eligible_facts(r))
        result=overlay_matrix({'studies':[{'citekey':'A','fields':{}}]},r)
        self.assertEqual(result['studies'][0]['fields']['hardware']['status'],'not_accessible')

    def test_source_snapshots_are_immutable_versions(self):
        from autonomous_review import source_packet
        with tempfile.TemporaryDirectory() as folder:
            ws=Path(folder);src=ws/'src';src.mkdir();run=ws/'run';run.mkdir()
            file=src/'source.txt';file.write_text('Version one source.')
            a=source_packet(ws,run,{'citekey':'A','source_directory':'src'},'')
            file.write_text('Version two source.')
            b=source_packet(ws,run,{'citekey':'A','source_directory':'src'},'')
            self.assertNotEqual(a['source_text_file'],b['source_text_file'])
            self.assertEqual((run/a['source_text_file']).read_text(),'Version one source.')

    def test_explicit_resolution_keeps_history(self):
        r=empty_registry()
        for v in (230,240):ingest_card(r,packet(text=str(v),sha=str(v)),{'fields':{'sample_size':{'status':'reported','value':v,'evidence_ids':['s0']}}})
        ids=list(r['studies']['A']['observations']['sample_size'])
        record_fact_review(r,'A',{'facts':[{'fact_id':i,'status':'pass','reason':'Source-bound observation.'} for i in ids]})
        resolve_conflict(r,'A','sample_size',ids[0],'The primary full-text cohort definition confirms this count; alternate extraction was erroneous.')
        self.assertEqual(study_view(r,'A')['facts']['sample_size']['value'],230)
        self.assertEqual(len(r['studies']['A']['observations']['sample_size']),2)
