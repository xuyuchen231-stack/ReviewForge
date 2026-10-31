import json,unittest

class InputPayloadTests(unittest.TestCase):
 def test_wire_json_preserves_every_string_and_value(self):
  from reviewforge import encode_model_payload
  payload={"quote":"  Exact source.  ","latex":r"\cite{A,B} x_{2} ","unicode":"研究", "rows":[True,None,1.25,{"a":"line1\nline2"}]}
  encoded=encode_model_payload(payload)
  self.assertEqual(json.loads(encoded),payload)
  self.assertLess(len(encoded),len(json.dumps(payload,ensure_ascii=False)))
 def test_issue_dedup_keeps_changed_versions_and_order(self):
  from synthesis_pipeline import unique_issue_details
  original=[{"id":"M1","reason":"first"},{"reason":"first","id":"M1"},{"id":"M1","reason":"changed"},{"id":"M2","reason":"other"}]
  self.assertEqual(unique_issue_details(original),[original[0],original[2],original[3]])
  self.assertEqual(len(original),4)
