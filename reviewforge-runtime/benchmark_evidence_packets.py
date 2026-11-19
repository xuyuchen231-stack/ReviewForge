"""Replay existing manuscript writer requests offline, without sending to a provider."""
import argparse,hashlib,json
from pathlib import Path
import tiktoken
from evidence_transport import encode_context_payload,decode_context_payload
from reviewforge import encode_model_payload
from reviewforge_v4 import extract_sections,split_safe_blocks,write_section

class Capture:
    def __init__(self): self.calls=[]
    def chat(self,system,user,role='writer'):
        self.calls.append((system,user,role))
        return 'OFFLINE_CAPTURE_ONLY'

def benchmark(manuscript, workspace, output):
    raw=manuscript.read_bytes(); text=raw.decode('utf-8')
    papers=json.loads((workspace/'literature.json').read_text(encoding='utf-8'))
    if isinstance(papers,dict): papers=papers.get('papers',papers.get('results',[]))
    encoders={name:tiktoken.get_encoding(name) for name in ('cl100k_base','o200k_base')}
    rows=[]
    import reviewforge_v4 as v4
    original=v4.client_chat
    captured=[]
    def capture(api,system,payload,role='writer',**kwargs):
        captured.append((system,payload,role))
        return original(api,system,payload,role,**kwargs)
    v4.client_chat=capture
    try:
        for heading,start,end in extract_sections(text):
            for number,body in enumerate(split_safe_blocks(text[start+len(heading):end]),1):
                if not body.strip(): continue
                api=Capture(); captured.clear()
                write_section(api,text,heading,body,papers,workspace=workspace)
                assert len(api.calls)==1 and len(captured)==1
                system,payload,role=captured[0]
                old=encode_context_payload(payload,use_packet=False)
                new=api.calls[0][1]
                assert decode_context_payload(new)==payload, 'Evidence roundtrip failed'
                assert encode_context_payload(payload)==new
                wires={'uncompressed':encode_model_payload(payload),'previous_transport':old,'packet_transport':new}
                counts={name:{variant:len(enc.encode(system))+len(enc.encode(wire)) for variant,wire in wires.items()} for name,enc in encoders.items()}
                rows.append({'heading':heading,'block':number,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),
                    'evidence_rows':len(payload['evidence_context'].get('entries',[])),
                    'canonical_rows':len(payload['evidence_context'].get('canonical_facts',[])),
                    'full_payload_roundtrip_equal':True,'api_calls_per_case':1,'tokens':counts,
                    'chars':{k:len(system)+len(v) for k,v in wires.items()}})
                print('captured',len(rows),flush=True)
    finally: v4.client_chat=original
    totals={name:{v:sum(r['tokens'][name][v] for r in rows) for v in ('uncompressed','previous_transport','packet_transport')} for name in encoders}
    for values in totals.values():
        values['saved_vs_previous_percent']=round(100*(1-values['packet_transport']/values['previous_transport']),2)
        values['saved_vs_uncompressed_percent']=round(100*(1-values['packet_transport']/values['uncompressed']),2)
    report={'manuscript':str(manuscript.resolve()),'manuscript_sha256':hashlib.sha256(raw).hexdigest(),
        'workspace':str(workspace.resolve()),'benchmark':'Actual write_section and client_chat code with Capture API; all current manuscript blocks; no before=after synthetic review cases.',
        'billing':'Exact local tiktoken counts for two encodings, including system and serialized user text; excludes provider chat wrappers/cache billing. Not measured provider usage or latency.',
        'new_provider_requests':0,'new_review_rounds':0,'cases':len(rows),'all_payloads_roundtrip_equal':all(r['full_payload_roundtrip_equal'] for r in rows),
        'totals':totals,'rows':rows}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(rows),'totals':totals},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manuscript',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); benchmark(a.manuscript,a.workspace,a.output)
