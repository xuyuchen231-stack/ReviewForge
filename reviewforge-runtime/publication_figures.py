"""Render authored, source-linked conceptual figure plans with no model/API calls."""
import hashlib,json,re,textwrap
from pathlib import Path
from reviewforge import atomic_json

def validate_plan(spec,known_keys):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{1,60}',spec.get('id','')):raise ValueError('Invalid figure ID')
    if not spec.get('source_keys') or set(spec['source_keys'])-set(known_keys):raise ValueError('Figure needs existing source identities')
    if spec.get('layout')=='research_diagram':
        if spec.get('diagram') not in ('overview','scale','uncertainty'):raise ValueError('Unknown research diagram')
        if spec.get('span','single') not in ('single','double'):raise ValueError('Invalid figure span')
        if not all(spec.get(k) for k in ('caption','after_heading','lead_in')):raise ValueError('Scientific role and insertion point required')
        return True
    if spec.get('layout')=='workflow':
        nodes=spec.get('nodes',[])
        if not 3<=len(nodes)<=8 or any(not isinstance(n,str) or not n.strip() or len(n)>150 for n in nodes):raise ValueError('Workflow needs 3-8 short authored nodes')
        if not spec.get('caption') or not spec.get('after_heading') or not spec.get('lead_in'):raise ValueError('Specify scientific role and insertion point')
        return True
    if len(spec.get('panels',[]))!=4:raise ValueError('This conceptual template requires four distinct panels')
    for panel in spec['panels']:
        if not panel.get('title') or not panel.get('note') or not 2<=len(panel.get('nodes',[]))<=4:raise ValueError('Incomplete conceptual panel')
        if any(not isinstance(n.get('text'),str) or not n['text'].strip() or len(n['text'])>64 for n in panel['nodes']):raise ValueError('Invalid node label')
    if not spec.get('caption') or not spec.get('after_heading') or not spec.get('lead_in'):raise ValueError('Specify scientific role, caption and insertion point')
    return True

def render_concept(spec,directory):
    if spec.get('layout')=='research_diagram':
        from review_overview_figure import render_overview
        report=render_overview(spec,directory)
        report['spec']=spec
        from figure_contract import require_vector_contract
        return require_vector_contract(Path(directory)/(spec['id']+'.pdf'),report,178 if spec.get('span')=='double' else 89)
    if spec.get('layout')=='workflow':return render_workflow(spec,directory)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
    folder=Path(directory);folder.mkdir(parents=True,exist_ok=True)
    colors={'mechanism':('#EAF0F5','#284D68'),'learning':('#E7F3F1','#16746D'),'measurement':('#FAF0E1','#9B6923'),'decision':('#F0ECF5','#6B548A')}
    node_checks=[];text_boxes=[]
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','text.usetex':False}):
        fig,axes=plt.subplots(2,2,figsize=(89/25.4,68/25.4));fig.subplots_adjust(left=.025,right=.985,bottom=.035,top=.985,wspace=.12,hspace=.15)
        for i,(ax,panel) in enumerate(zip(axes.flat,spec['panels'])):
            ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
            ax.text(0,.98,'('+chr(97+i)+') '+textwrap.fill(panel['title'],23),ha='left',va='top',fontsize=7,fontweight='bold',color='#233F53',parse_math=False)
            nodes=panel['nodes'];width=.93/len(nodes)-.025;gap=(.96-len(nodes)*width)/(len(nodes)-1)
            for j,node in enumerate(nodes):
                x=.01+j*(width+gap);fill,edge=colors.get(node.get('kind'),colors['mechanism'])
                box=FancyBboxPatch((x,.40),width,.30,boxstyle='round,pad=0.008,rounding_size=0.02',facecolor=fill,edgecolor=edge,linewidth=.85);ax.add_patch(box)
                label=ax.text(x+width/2,.55,textwrap.fill(node['text'],max(5,int(width*23))),ha='center',va='center',fontsize=7,color='#183143',linespacing=1.25,parse_math=False)
                text_boxes.append((label,box))
                if j and panel.get('connect',False):
                    ax.add_patch(FancyArrowPatch((x-gap+.012,.55),(x-.012,.55),arrowstyle='-|>',mutation_scale=8,linewidth=.9,color='#506575'))
            ax.text(0,.28,textwrap.fill(panel['note'],25),ha='left',va='top',fontsize=6.7,color='#415363',linespacing=1.25,parse_math=False)
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        for ax in axes.flat:
            region=ax.get_window_extent(renderer)
            extents=[text.get_window_extent(renderer) for text in ax.texts if text.get_text().strip()]
            if any(not region.contains(box.x0,box.y0) or not region.contains(box.x1,box.y1) for box in extents):
                plt.close(fig)
                raise ValueError('Panel text exceeds panel; shorten or reflow labels')
            if any(a.overlaps(b) for i,a in enumerate(extents) for b in extents[i+1:]):
                plt.close(fig)
                raise ValueError('Panel labels overlap; simplify panel content')
        for text,box in text_boxes:
            a=text.get_window_extent(renderer);b=box.get_window_extent(renderer)
            if a.x0<b.x0 or a.x1>b.x1 or a.y0<b.y0 or a.y1>b.y1:raise ValueError('Concept label exceeds its box; shorten label without shrinking type')
            node_checks.append({'contained':True,'font_pt':text.get_fontsize()})
        bounds=[list(ax.get_position().bounds) for ax in axes.flat]
        if max(b[2] for b in bounds)-min(b[2] for b in bounds)>1e-6 or max(b[3] for b in bounds)-min(b[3] for b in bounds)>1e-6:raise ValueError('Panel geometry differs')
        for suffix in ('pdf','svg'):fig.savefig(folder/(spec['id']+'.'+suffix),dpi=300)
        plt.close(fig)
    report={'kind':'conceptual_schematic','experimental_data':False,'source_keys':spec['source_keys'],'semantic_verification':False,'visual_status':'PENDING','spec_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'panel_bounds':bounds,'node_text_checks':node_checks,'font_floor_pt':6.7}
    report['spec']=spec
    from figure_contract import require_vector_contract
    return require_vector_contract(folder/(spec['id']+'.pdf'),report,178 if spec.get('span')=='double' else 89)


def render_workflow(spec,directory):
    """Authored classification or locked-protocol sequence, not a four-panel substitute."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    nodes=spec['nodes'];height=68/25.4
    with plt.rc_context({'font.family':'DejaVu Sans','pdf.fonttype':42,'svg.fonttype':'none'}):
        fig,ax=plt.subplots(figsize=(89/25.4,height));ax.set(xlim=(0,1),ylim=(0,len(nodes)));ax.axis('off')
        boxes=[]
        for i,node in enumerate(nodes):
            y=len(nodes)-i-.85
            box=FancyBboxPatch((.04,y),.92,.66,boxstyle='round,pad=0.01',facecolor='#EAF3F5',edgecolor='#28556A');ax.add_patch(box)
            label=ax.text(.50,y+.33,textwrap.fill(node,42),ha='center',va='center',fontsize=7,parse_math=False)
            boxes.append((label,box))
            if i and spec.get('connect',True):ax.annotate('',xy=(.5,y+.68),xytext=(.5,y+.96),arrowprops={'arrowstyle':'->','color':'#28556A'})
        fig.subplots_adjust(left=.015,right=.985,top=.99,bottom=.01);fig.canvas.draw()
        renderer=fig.canvas.get_renderer()
        for label,box in boxes:
            a=label.get_window_extent(renderer);b=box.get_window_extent(renderer)
            if a.x0<b.x0 or a.x1>b.x1 or a.y0<b.y0 or a.y1>b.y1:raise ValueError('Workflow label overflow')
        for suffix in ('pdf','svg'):fig.savefig(directory/(spec['id']+'.'+suffix),dpi=300)
        plt.close(fig)
    report={'kind':'conceptual_workflow','experimental_data':False,'source_keys':spec['source_keys'],'semantic_verification':False,'visual_status':'PENDING','spec_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'font_floor_pt':7}
    report['spec']=spec
    from figure_contract import require_vector_contract
    return require_vector_contract(directory/(spec['id']+'.pdf'),report,178 if spec.get('span')=='double' else 89)

def add_planned_figures(tex,plan,output):
    from bibliography_delivery import active_text
    known=set(re.findall(r'\\bibitem(?:\[[^]]*\])?\{([^}]+)\}',active_text(tex)));reports=[]
    if not isinstance(plan,dict) or not isinstance(plan.get('figures'),list):raise ValueError('Invalid publication figure plan')
    # Replace only explicitly owned generated illustrations, never author data plots.
    mappings={}
    for spec in plan['figures']:
        if not re.fullmatch(r'[a-z][a-z0-9_-]{1,60}',spec.get('id','')):raise ValueError('Invalid figure ID')
        if '\\label{fig:rf-'+spec['id']+'}' not in active_text(tex):validate_plan(spec,known)
        for old in spec.get('replaces',[]):
            if not re.fullmatch(r'[a-z][a-z0-9_-]{1,60}',old) or old==spec['id']:raise ValueError('Invalid superseded figure ID')
            mappings['fig:rf-'+old]='fig:rf-'+spec['id']
    for match in reversed(list(re.finditer(r'\\begin\{figure\*?\}(?:\[[^]]*\])?[\s\S]*?\\end\{figure\*?\}',active_text(tex)))):
        labels=re.findall(r'\\label\{([^}]+)\}',match.group(0));owned=set(labels)&set(mappings)
        if owned:
            if any(not label.startswith('fig:rf-') for label in labels):raise ValueError('Mixed author/generated figure labels require explicit review')
            graphics=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',match.group(0))
            expected={'figures/'+label[len('fig:rf-'):]+'.pdf' for label in owned}
            if not graphics or set(graphics)-expected:raise ValueError('Generated-figure replacement has ambiguous asset provenance')
            tex=tex[:match.start()]+tex[match.end():]
    for spec in plan['figures']:
        for lead in spec.get('superseded_lead_ins',[]):
            pattern=r'\s+'.join(re.escape(word) for word in lead.split())
            for match in reversed(list(re.finditer(pattern,active_text(tex)))):tex=tex[:match.start()]+tex[match.end():]
    from manuscript_integrity import REF
    for match in reversed(list(REF.finditer(active_text(tex)))):
        keys=[mappings.get(key.strip(),key.strip()) for key in match.group(1).split(',')]
        tex=tex[:match.start(1)]+','.join(keys)+tex[match.end(1):]
    for spec in plan['figures']:
        label='fig:rf-'+spec['id']
        if '\\label{'+label+'}' in active_text(tex):continue
        validate_plan(spec,known)
        marker=spec['after_heading'];start=active_text(tex).find(marker)
        if start<0:raise ValueError('Figure insertion heading missing: '+marker)
        next_heading=re.search(r'(?m)^\\(?:section|subsection)\*?\{',tex[start+len(marker):])
        stop=start+len(marker)+next_heading.start() if next_heading else tex.find(r'\begin{thebibliography}')
        if stop<start:raise ValueError('Cannot place conceptual figure inside article')
        reports.append(render_concept(spec,Path(output)/'figures'))
        single=spec.get('span','single')=='single';environment='figure' if single else 'figure*';width=r'\columnwidth' if single else r'\textwidth'
        block='\n'+spec['lead_in'].replace('{FIG}',r'\ref{'+label+'}')+'\n\n'+r'\begin{'+environment+'}[!t]'+'\n'+('% RF_SINGLE_COLUMN_FIGURE\n' if single else '')+r'\centering'+'\n'+r'\includegraphics[width='+width+']{figures/'+spec['id']+'.pdf}\n'+r'\caption{'+spec['caption']+r'\cite{'+','.join(spec['source_keys'])+'}.}\n'+r'\label{'+label+'}\n'+r'\end{'+environment+'}'+'\n\n'
        tex=tex[:stop]+block+tex[stop:]
    return tex,{'added':len(reports),'records':reports,'model_calls':0}
