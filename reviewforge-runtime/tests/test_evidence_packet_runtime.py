import copy,json,unittest
from evidence_transport import encode_context_payload
from evidence_packet_runtime import expand_packet, packet_view

class PacketRuntimeTests(unittest.TestCase):
 def payload(self):
  quote='Exact source result with units, operating conditions and limitations. '*80
  return {'body':'Manuscript remains literal', 'evidence_context':{'entries':[
   {'citekey':str(i),'locator':'p.'+str(i),'excerpt':quote,'qualification':'limited to fed-batch','source_sha256':'hash-'+str(i)} for i in range(8)]}}
 def test_roundtrip_all_evidence(self):
  p=self.payload(); original=copy.deepcopy(p)
  packet=packet_view(p)
  self.assertIn('_exact_evidence_packet',packet)
  self.assertEqual(expand_packet(packet),p)
  self.assertEqual(p,original)
 def test_actual_encoder_uses_packet(self):
  p=self.payload(); p['canonical_studies']=[{'facts':{'result':{'value':p['evidence_context']['entries'][0]['excerpt']}}} for _ in range(8)]; wire=json.loads(encode_context_payload(p))
  self.assertIn('_exact_evidence_packet',wire)
  self.assertEqual(expand_packet(wire)['body'],p['body'])
 def test_no_gain_or_collision_leaves_original(self):
  p={'body':'plain','evidence_context':{'excerpt':'short'}}
  self.assertEqual(packet_view(p),p)
  p['_exact_evidence_packet']={'user':'data'}
  self.assertEqual(packet_view(p),p)
 def test_tamper_rejected(self):
  wire=packet_view(self.payload())
  first=next(iter(wire['_exact_evidence_packet']['texts'].values()))
  first['text']+='altered'
  with self.assertRaises(ValueError): expand_packet(wire)
 def test_no_evidence_no_change(self):
  p={'body':'a'*3000,'before':'a'*3000}
  self.assertEqual(packet_view(p),p)
 def test_provider_route_sends_once_and_keeps_all_values(self):
  from major_revision import provider_request
  from evidence_transport import decode_context_payload
  payload=self.payload()
  payload['canonical_studies']=[{'citekey':str(i),'facts':{'result':{'value':payload['evidence_context']['entries'][0]['excerpt'],'qualification':'one condition'}}} for i in range(8)]
  class API:
   calls=0
   last_finish_reason=None
   def chat(self,system,user,role):
    self.calls+=1
    self.decoded=decode_context_payload(user)
    return 'unchanged result'
  api=API()
  self.assertEqual(provider_request(api,'system',payload,None,'writer'),'unchanged result')
  self.assertEqual(api.calls,1)
  self.assertEqual(api.decoded['evidence_context'],payload['evidence_context'])
  self.assertEqual(api.decoded['body'],payload['body'])
 def test_nonidentical_qualifications_never_coalesced(self):
  p=self.payload()
  p['evidence_context']['entries'][0]['excerpt']+=' DIFFERENT LIMITATION'
  self.assertEqual(expand_packet(packet_view(p)),p)
if __name__=='__main__': unittest.main()
