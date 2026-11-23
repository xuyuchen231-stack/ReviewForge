import copy,unittest
from editorial_scoped import scope_studies

class ScopedEvidenceTests(unittest.TestCase):
 def study(self):
  fields={name:{'id':name,'status':'reported','value':value,'semantic_status':'qualified','semantic_review':{'reason':'Only tested in one domain; not a transfer guarantee'},'anchors':[{'excerpt':'Exact '+name,'locator':'p2','source_sha256':'sha'}]} for name,value in {'study_type':'research','prediction_task':'predict biomass','mechanistic_structure':'balances and neural rates','learned_component':'rate','validation_split':'whole batches held out','sample_size':9,'quantitative_results':'23.2 percent MAPE','uncertainty':'single held-out process','failure_modes':'oxygen limitation','hardware':'GPU','computation_time':'120 seconds'}.items()}
  return {'citekey':'A','facts':fields,'sources':[{'source_sha256':'sha','source_id':'doi:A','document_access':'full_text','inspection_coverage':'complete'}]}
 def test_exact_values_qualifications_and_primary_quotes_survive(self):
  s=self.study();before=copy.deepcopy(s);out=scope_studies([s],r'Hybrid balance equations learn rates \cite{A}.')[0]
  self.assertEqual(s,before)
  for field,cell in out['facts'].items():self.assertEqual(cell,s['facts'][field])
  self.assertIn('mechanistic_structure',out['facts']);self.assertIn('uncertainty',out['facts'])
  self.assertIn('hardware',out['available_unselected_fields']);self.assertNotIn('hardware',out['facts'])
 def test_quantitative_claim_includes_design_results_and_limits(self):
  out=scope_studies([self.study()],r'Prediction MAPE was 23.2 percent on 9 batches \cite{A}.')[0]
  for field in ('quantitative_results','sample_size','validation_split','uncertainty'):self.assertIn(field,out['facts'])
 def test_unclassified_claim_falls_back_to_complete_study(self):
  s=self.study();out=scope_studies([s],r'A poorly classified assertion \cite{A}.')[0]
  self.assertEqual(out['facts'],s['facts']);self.assertEqual(out['selection_basis'],'full_unclassified_fallback')
 def test_cost_claim_cannot_omit_timing_hardware(self):
  out=scope_studies([self.study()],r'CPU runtime takes 120 seconds \cite{A}.')[0]
  self.assertIn('hardware',out['facts']);self.assertIn('computation_time',out['facts'])
 def test_other_citations_and_author_scope_do_not_expand_a_review_reference(self):
  s=self.study()
  text=r'Balance equations retain mass \cite{B}. General hybrid model reviews cover learning \cite{A}. This review compares CPU runtime of 120 seconds and 9 pilot batches.'
  out=scope_studies([s],text)[0]
  self.assertNotIn('hardware',out['facts']);self.assertNotIn('quantitative_results',out['facts'])
 def test_results_following_a_study_citation_are_still_in_scope(self):
  out=scope_studies([self.study()],r'The biomass predictor is tested \cite{A}. Its MAPE was 23.2 percent on 9 batches.')[0]
  self.assertIn('quantitative_results',out['facts']);self.assertIn('sample_size',out['facts'])
 def test_wire_packet_keeps_exact_values_and_qualifications(self):
  from editorial_scoped import source_packet
  study=scope_studies([self.study()],r'Biomass MAPE 23.2 percent on 9 batches \cite{A}.')[0]
  packet=source_packet([study],r'Biomass MAPE 23.2 percent on 9 batches \cite{A}.')[0]
  for name,cell in study['facts'].items():
   self.assertEqual(packet['facts'][name]['value'],cell['value'])
   self.assertEqual(packet['facts'][name]['source_check_note'],cell['semantic_review']['reason'])
  original=[a for cell in study['facts'].values() for a in cell.get('anchors',[])]
  self.assertTrue(all(a in original for a in packet['primary_spans'].values()))
 def test_all_conflicts_are_retained_and_never_sent_as_approved(self):
  from editorial_scoped import source_packet
  study=self.study();study['facts']['hardware']['status']='conflict'
  scoped=scope_studies([study],r'Hybrid predictor \cite{A}.')[0]
  self.assertIn('hardware',scoped['facts'])
  with self.assertRaises(ValueError):source_packet([scoped],r'Hybrid predictor \cite{A}.')
if __name__=='__main__':unittest.main()
