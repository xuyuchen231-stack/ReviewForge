"""Render authored, source-linked conceptual figure plans with no model/API calls."""
import hashlib,json,re,textwrap
from pathlib import Path
from reviewforge import atomic_json

def validate_plan(spec,known_keys):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{1,60}',spec.get('id','')):raise ValueError('Invalid figure ID')
    if not spec.get('source_keys') or set(spec['source_keys'])-set(known_keys):raise ValueError('Figure needs existing source identities')
    if len(spec.get('panels',[]))!=4:raise ValueError('This conceptual template requires four distinct panels')
    for panel in spec['panels']:
        if not panel.get('title') or not panel.get('note') or not 2<=len(panel.get('nodes',[]))<=4:raise ValueError('Incomplete conceptual panel')
        if any(not isinstance(n.get('text'),str) or not n['text'].strip() or len(n['text'])>64 for n in panel['nodes']):raise ValueError('Invalid node label')
    if not spec.get('caption') or not spec.get('after_heading') or not spec.get('lead_in'):raise ValueError('Specify scientific role, caption and insertion point')
    return True

def render_concept(spec,directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
    folder=Path(directory);folder.mkdir(parents=True,exist_ok=True)
    colors={'mechanism':('#EAF0F5','#284D68'),'learning':('#E7F3F1','#16746D'),'measurement':('#FAF0E1','#9B6923'),'decision':('#F0ECF5','#6B548A')}
    node_checks=[];text_boxes=[]
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','text.usetex':False}):
        fig,axes=plt.subplots(2,2,figsize=(7.05,3.9));fig.subplots_adjust(left=.025,right=.985,bottom=.035,top=.985,wspace=.12,hspace=.15)
        for i,(ax,panel) in enumerate(zip(axes.flat,spec['panels'])):
            ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
            ax.text(0,.98,'('+chr(97+i)+') '+textwrap.fill(panel['title'],39),ha='left',va='top',fontsize=8.7,fontweight='bold',color='#233F53',parse_math=False)
            nodes=panel['nodes'];width=.93/len(nodes)-.025;gap=(.96-len(nodes)*width)/(len(nodes)-1)
            for j,node in enumerate(nodes):
                x=.01+j*(width+gap);fill,edge=colors.get(node.get('kind'),colors['mechanism'])
                box=FancyBboxPatch((x,.40),width,.30,boxstyle='round,pad=0.008,rounding_size=0.02',facecolor=fill,edgecolor=edge,linewidth=.85);ax.add_patch(box)
                label=ax.text(x+width/2,.55,node['text'],ha='center',va='center',fontsize=7.6,color='#183143',linespacing=1.25,parse_math=False)
                text_boxes.append((label,box))
                if j:
                    ax.add_patch(FancyArrowPatch((x-gap+.012,.55),(x-.012,.55),arrowstyle='-|>',mutation_scale=8,linewidth=.9,color='#506575'))
            ax.text(0,.28,textwrap.fill(panel['note'],55),ha='left',va='top',fontsize=7.4,color='#415363',linespacing=1.25,parse_math=False)
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        for text,box in text_boxes:
            a=text.get_window_extent(renderer);b=box.get_window_extent(renderer)
            if a.x0<b.x0 or a.x1>b.x1 or a.y0<b.y0 or a.y1>b.y1:raise ValueError('Concept label exceeds its box; shorten label without shrinking type')
            node_checks.append({'contained':True,'font_pt':text.get_fontsize()})
        bounds=[list(ax.get_position().bounds) for ax in axes.flat]
        if max(b[2] for b in bounds)-min(b[2] for b in bounds)>1e-6 or max(b[3] for b in bounds)-min(b[3] for b in bounds)>1e-6:raise ValueError('Panel geometry differs')
        for suffix in ('pdf','svg','png'):fig.savefig(folder/(spec['id']+'.'+suffix),dpi=300)
        plt.close(fig)
    report={'kind':'conceptual_schematic','experimental_data':False,'source_keys':spec['source_keys'],'semantic_verification':False,'visual_status':'PENDING','spec_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'panel_bounds':bounds,'node_text_checks':node_checks,'font_floor_pt':7.4}
    atomic_json(folder/(spec['id']+'.manifest.json'),report);return report

def add_planned_figures(tex,plan,output):
    known=set(re.findall(r'\\bibitem(?:\[[^]]*\])?\{([^}]+)\}',tex));reports=[]
    if not isinstance(plan,dict) or not isinstance(plan.get('figures'),list):raise ValueError('Invalid publication figure plan')
    for spec in plan['figures']:
        validate_plan(spec,known)
        label='fig:rf-'+spec['id']
        if '\\label{'+label+'}' in tex:continue
        marker=spec['after_heading'];start=tex.find(marker)
        if start<0:raise ValueError('Figure insertion heading missing: '+marker)
        next_heading=re.search(r'(?m)^\\(?:section|subsection)\*?\{',tex[start+len(marker):])
        stop=start+len(marker)+next_heading.start() if next_heading else tex.find(r'\begin{thebibliography}')
        if stop<start:raise ValueError('Cannot place conceptual figure inside article')
        reports.append(render_concept(spec,Path(output)/'figures'))
        block='\n'+spec['lead_in'].replace('{FIG}',r'\ref{'+label+'}')+'\n\n'+r'\begin{figure*}[!t]'+'\n'+r'\centering'+'\n'+r'\includegraphics[width=\textwidth]{figures/'+spec['id']+'.pdf}\n'+r'\caption{'+spec['caption']+r'\cite{'+','.join(spec['source_keys'])+'}.}\n'+r'\label{'+label+'}\n'+r'\end{figure*}'+'\n\n'
        tex=tex[:stop]+block+tex[stop:]
    return tex,{'added':len(reports),'records':reports,'model_calls':0}
