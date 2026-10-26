"""Render explicit figure specifications; no model-generated code or invented data."""
import argparse,hashlib,json,math,shutil,subprocess,textwrap,uuid
from pathlib import Path
from reviewforge import atomic_json

def topology_dot(spec):
    nodes=spec.get('nodes',[]);edges=spec.get('edges',[])
    if not isinstance(nodes,list) or not 1<=len(nodes)<=40:raise ValueError('Topology requires 1..40 nodes')
    ids=[node.get('id') for node in nodes]
    if any(not isinstance(key,str) or not key for key in ids) or len(set(ids))!=len(ids):raise ValueError('Invalid topology IDs')
    lookup={key:'n'+str(index) for index,key in enumerate(ids)}
    lines=['digraph review {','graph [rankdir=LR, splines=ortho, nodesep=0.5, ranksep=0.8, bgcolor="white"];','node [shape=box, style="rounded,filled", fillcolor="#e8f1f7", color="#315b75", fontname="Arial", fontsize=11, margin="0.16,0.12"];','edge [color="#526675", arrowsize=0.7];']
    for node in nodes:
        label=node.get('label')
        if not isinstance(label,str) or not label.strip():raise ValueError('Node needs a label')
        lines.append(lookup[node['id']]+' [label='+json.dumps(textwrap.fill(label,26),ensure_ascii=False)+'];')
    for edge in edges:
        if edge.get('source') not in lookup or edge.get('target') not in lookup:raise ValueError('Unknown topology edge target')
        lines.append(lookup[edge['source']]+' -> '+lookup[edge['target']]+';')
    return '\n'.join(lines+['}'])

def validate_quantitative(spec):
    if not isinstance(spec.get('unit'),str) or not spec['unit'].strip() or not spec.get('comparison_group'):raise ValueError('Define units and a comparable protocol/task before plotting')
    items=spec.get('items',[])
    if not isinstance(items,list) or not 1<=len(items)<=12:raise ValueError('Use 1..12 labeled items per panel')
    for item in items:
        value=item.get('value');sources=item.get('source_ids')
        if not isinstance(item.get('label'),str) or not item['label'].strip() or type(value) not in (float,int) or not math.isfinite(value):raise ValueError('Invalid quantitative datum')
        if not isinstance(sources,list) or not sources or any(not isinstance(source,str) or not source.strip() for source in sources):raise ValueError('Every datum needs explicit source IDs')
        if item.get('comparison_group',spec['comparison_group'])!=spec['comparison_group'] or item.get('unit',spec['unit'])!=spec['unit']:raise ValueError('Heterogeneous tasks/units need separate panels; do not imply a ranking')
    return True

def render(spec,output):
    if spec.get('kind')=='topology':topology_dot(spec)
    elif spec.get('kind')=='bar':validate_quantitative(spec)
    else:raise ValueError('Supported figure kinds: topology, bar')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    existing=[output/name for name in ('figure.dot','figure.pdf','figure.png','figure_manifest.json') if (output/name).is_file()]
    if existing:
        stale=output/'stale_outputs'/uuid.uuid4().hex;stale.mkdir(parents=True)
        for path in existing:path.replace(stale/path.name)
    report={'semantic_verification':False,'visual_status':'PENDING','spec_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'kind':spec.get('kind')}
    if spec.get('kind')=='topology':
        dot=topology_dot(spec);source=output/'figure.dot';source.write_text(dot,encoding='utf-8');engine=shutil.which('dot')
        if not engine:report.update(status='UNAVAILABLE',reason='Graphviz dot is not installed; topology source saved; no rendered figure claimed.')
        else:
            subprocess.run([engine,'-Tpdf',str(source),'-o',str(output/'figure.pdf')],check=True,timeout=60)
            subprocess.run([engine,'-Tpng',str(source),'-o',str(output/'figure.png')],check=True,timeout=60)
            report['status']='RENDERED'
    elif spec.get('kind')=='bar':
        validate_quantitative(spec)
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'text.usetex':False}):
            fig,ax=plt.subplots(figsize=(max(5.5,len(spec['items'])*.8),3.8),layout='constrained')
            labels=[textwrap.fill(item['label'],16).replace('$',r'\$') for item in spec['items']]
            ax.bar(range(len(labels)),[item['value'] for item in spec['items']],color='#0072B2',width=.65)
            ax.set_xticks(range(len(labels)),labels);ax.set_ylabel(spec['unit']);ax.set_title(spec.get('title',''));ax.set_axisbelow(True);ax.grid(axis='y',alpha=.18)
            fig.savefig(output/'figure.pdf');fig.savefig(output/'figure.png',dpi=300);plt.close(fig)
        report.update(status='RENDERED',source_ids=sorted({source for item in spec['items'] for source in item['source_ids']}))
    else:raise ValueError('Supported figure kinds: topology, bar')
    report['outputs']={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir() if path.name in ('figure.dot','figure.pdf','figure.png') and path.is_file()}
    atomic_json(output/'figure_manifest.json',report);return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('spec');parser.add_argument('--output',required=True);args=parser.parse_args()
    print(json.dumps(render(json.loads(Path(args.spec).read_text(encoding='utf-8')),args.output),ensure_ascii=False))
