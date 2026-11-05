import unittest
from bounded_review import review_batches,combine_reviews
from efficient_payload import project_payload,encoded_size
from paragraph_review import paragraph_options

class BoundedReviewTests(unittest.TestCase):
 def test_unresolved_primary_requests_cannot_pass_after_resume(self):
  from major_revision import review_section,CHECKS
  body='The source reports 230 batches.';candidate={'latex':body};pid=paragraph_options(body)[0]['id'];saved=[]
  report={'accepted':True,'checks':{c:True for c in CHECKS},'issues':[],'evidence_requests':['f1'],'paragraph_review':[{'paragraph_id':pid,'function':'evidence','message':'Count.','adds':'Count.','decision':'keep','destination':'main','reason':'Count.'}]}
  calls=[]
  def ask(*args):calls.append(1);return report
  payload={'canonical_studies':[{'citekey':'A','facts':{'n':{'id':'f1','anchors':[{'excerpt':'230 batches'}]}}}]}
  for pending in (None,report):
   with self.assertRaises(ValueError):review_section(ask,payload,candidate,saved.append,pending=pending)
  self.assertEqual(len(calls),4)
  self.assertTrue(all(r.get('review_incomplete') and r['accepted'] is False for r in saved))
 def test_minor_style_is_optional_but_minor_factual_change_still_blocks(self):
  from paragraph_review import validate_paragraph_review
  body='The study reports 230 batches.';pid=paragraph_options(body)[0]['id']
  row={'paragraph_id':pid,'function':'evidence','message':'Reported cohort.','adds':'Cohort count.','decision':'revise','destination':'main','reason':'Revise.','severity':'minor','category':'style'}
  self.assertEqual(validate_paragraph_review(body,{'paragraph_review':[row]}),[])
  self.assertTrue(validate_paragraph_review(body,{'paragraph_review':[{**row,'category':'factual'}]}))
 def test_all_paragraphs_and_original_blocks_covered_with_bounded_calls(self):
  body='\n\n'.join(('Result '+str(i)+' '+('specific '*150)+r'\cite{'+key+'}.') for i,key in enumerate('ABCD'))
  original='\n\n'.join('Original evidence '+key+r'\cite{'+key+'}.' for key in 'ABCD')
  studies=[{'citekey':key,'facts':{'n':{'id':'f'+key,'value':230,'semantic_status':'pass','anchors':[{'excerpt':'exact source '*10000,'span_id':'s','source_sha256':'x','locator':'p1'}]}}} for key in 'ABCD']
  payload={'original_material':original,'canonical_studies':studies}
  batches=review_batches('review',payload,{'latex':body},12000,max_paragraphs=2)
  self.assertGreater(len(batches),1)
  self.assertTrue(all(encoded_size(project_payload(b))+len('review')<=12000 for b in batches))
  ids=[p['id'] for b in batches for p in b['paragraph_options']]
  self.assertEqual(ids,[p['id'] for p in paragraph_options(body)])
  self.assertEqual(sorted(x for b in batches for x in b['original_block_ids']),['b001','b002','b003','b004'])
 def test_one_rejected_batch_cannot_be_hidden_by_other_passes(self):
  rows=[{'accepted':True,'checks':{'facts':True},'issues':[],'paragraph_review':[]}, {'accepted':False,'checks':{'facts':False},'issues':['unsupported result'],'paragraph_review':[]}]
  result=combine_reviews(rows,['facts']);self.assertFalse(result['accepted']);self.assertFalse(result['checks']['facts'])
