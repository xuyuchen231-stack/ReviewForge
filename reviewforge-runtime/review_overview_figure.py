"""Editable conceptual diagrams: one integrated a-d overview and single-column companions."""
import hashlib
import json
from pathlib import Path


def portable_svg(path):
    """Express Matplotlib's point-based viewBox in CSS pixels without resizing content."""
    import re
    import xml.etree.ElementTree as ET
    text=path.read_text(encoding='utf-8');text=re.sub(r'<!DOCTYPE svg PUBLIC[^>]*>','',text)
    root=ET.fromstring(text);ns='http://www.w3.org/2000/svg'
    ET.register_namespace('',ns);ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
    if root.get('width','').endswith('pt') and root.get('height','').endswith('pt'):
        factor=96/72;view=[float(v) for v in root.attrib['viewBox'].split()]
        root.set('width',str(float(root.get('width')[:-2])*factor)+'px');root.set('height',str(float(root.get('height')[:-2])*factor)+'px')
        root.set('viewBox',' '.join(str(v*factor) for v in view))
        wrapper=ET.Element('{'+ns+'}g',{'transform':'scale('+str(factor)+')'})
        for child in list(root):
            if child.tag=='{'+ns+'}g':root.remove(child);wrapper.append(child)
        root.append(wrapper)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def render_overview(spec,directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch,Circle,Rectangle
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    kind=spec.get('diagram','overview');composite=kind=='overview'
    checks=[];texts=[];boxes=[]
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':8.2,'pdf.fonttype':42,'svg.fonttype':'none','text.usetex':False}):
        if composite:
            fig,axes=plt.subplots(2,2,figsize=(7.05,4.55));fig.subplots_adjust(left=.025,right=.99,bottom=.025,top=.985,wspace=.14,hspace=.20)
            axes=list(axes.flat)
        else:
            fig,ax=plt.subplots(figsize=(3.35,2.15));axes=[ax];fig.subplots_adjust(left=.025,right=.985,bottom=.025,top=.98)
        for ax in axes:ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
        dark='#27485D';teal='#087E83';muted='#526675';pale='#EBF3F4'
        def text(ax,x,y,value,**kwargs):
            artist=ax.text(x,y,value,color=kwargs.pop('color',dark),fontsize=kwargs.pop('fontsize',8.2),parse_math=False,**kwargs);texts.append((artist,ax));return artist
        def box(ax,x,y,w,h,value,accent=False):
            patch=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.006,rounding_size=0.015',facecolor=pale if accent else '#F4F6F7',edgecolor=teal if accent else '#81939E',linewidth=.8);ax.add_patch(patch)
            artist=text(ax,x+w/2,y+h/2,value,ha='center',va='center');boxes.append((artist,patch))
        def arrow(ax,a,b,style='-',color=dark):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'-|>','lw':1,'color':color,'linestyle':style,'shrinkA':2,'shrinkB':2})
        def heading(ax,label,title):text(ax,.01,.98,(label+'  ' if label else '')+title,ha='left',va='top',fontsize=9,fontweight='bold')
        def architecture(ax):
            heading(ax,'(a)' if composite else '', 'Where learning acts')
            box(ax,.30,.72,.40,.15,'Learned relation',True)
            box(ax,.19,.37,.43,.20,'Mechanistic\nbalances')
            box(ax,.73,.37,.24,.20,'Observation\nmap')
            text(ax,.025,.47,'u',ha='center',va='center',fontstyle='italic');arrow(ax,(.055,.47),(.18,.47))
            arrow(ax,(.63,.47),(.72,.47));text(ax,.67,.53,'x',ha='center',fontstyle='italic')
            arrow(ax,(.40,.71),(.29,.59),color=teal);arrow(ax,(.56,.71),(.53,.59),color=teal);arrow(ax,(.70,.78),(.86,.59),color=teal)
            text(ax,.20,.66,'Parameters',ha='center',fontsize=7.8);text(ax,.56,.65,'Rates',ha='left',fontsize=7.8)
            text(ax,.99,.78,'Output',ha='right',fontsize=7.8)
            text(ax,.03,.22,'Learning location determines what changes.',ha='left',fontsize=8)
            text(ax,.03,.10,'Retained balances remain explicit.',ha='left',fontsize=8)
        def protocol(ax):
            heading(ax,'(b)','Lock information before testing')
            groups=[(.03,.32,'Train','#DCE7EC'),(.36,.25,'Validate','#DFEEEB'),(.68,.29,'Test','#F1E8D8')]
            for x,w,label,fill in groups:
                ax.add_patch(Rectangle((x,.52),w,.18,facecolor=fill,edgecolor='#81939E',lw=.8));text(ax,x+w/2,.61,label,ha='center',va='center')
            ax.plot([.645,.645],[.36,.83],color=teal,lw=1.3);text(ax,.645,.86,'LOCK',ha='center',color=teal,fontweight='bold',fontsize=8)
            arrow(ax,(.04,.39),(.96,.39));text(ax,.50,.29,'Independent batches / conditions',ha='center',fontsize=8)
            text(ax,.03,.15,'Tune before lock; evaluate after lock.',ha='left',fontsize=8)
            text(ax,.03,.04,'Future measurements stay outside a forecast.',ha='left',fontsize=7.8)
        def candidates(ax):
            heading(ax,'(c)','Compare revision candidates')
            labels=['M0','M1','M2','M3','M4'];names=['Fixed','Refit','Phase','Term','Structure']
            for i,(label,name) in enumerate(zip(labels,names)):
                x=.035+i*.194;box(ax,x,.57,.16,.19,label)
                text(ax,x+.08,.49,name,ha='center',fontsize=7.6)
                ax.plot([x+.08,x+.08],[.43,.35],color='#81939E',lw=.8)
            ax.plot([.115,.891],[.35,.35],color='#81939E',lw=.8)
            text(ax,.50,.24,'Same held-out protocol and baseline',ha='center',fontsize=8)
            text(ax,.03,.09,'Choose evidence-supported complexity.',ha='left',fontsize=8)
        def conservation(ax,label='(d)'):
            heading(ax,label,'Keep exchange conservative')
            for x,name in ((.26,'Region 1'),(.75,'Region 2')):
                ax.add_patch(Circle((x,.57),.16,facecolor='#EDF3F5',edgecolor=dark,lw=1));text(ax,x,.57,name,ha='center',va='center')
            arrow(ax,(.42,.62),(.58,.62),color=teal);arrow(ax,(.58,.52),(.42,.52),color=teal)
            text(ax,.50,.81,'Internal exchange',ha='center',fontsize=8)
            text(ax,.50,.29,'Opposing fluxes cancel in the total balance.',ha='center',fontsize=7.8)
            text(ax,.50,.13,'External inputs and outputs remain accountable.',ha='center',fontsize=7.8)
        def scale(ax):
            heading(ax,'','Transfer requires matched conditions')
            for x,r,name in ((.23,.12,'Bench'),(.72,.18,'Pilot')):
                ax.add_patch(Circle((x,.56),r,facecolor='#EDF3F5',edgecolor=dark,lw=1));text(ax,x,.56,name,ha='center',va='center')
            arrow(ax,(.37,.56),(.51,.56));text(ax,.50,.84,'Same balance, different exposure',ha='center',fontsize=8)
            text(ax,.50,.22,'Recheck mixing, transfer and operating coverage.',ha='center',fontsize=7.8)
            text(ax,.50,.09,'Scale alone is not a validation result.',ha='center',fontsize=7.8)
        def uncertainty(ax):
            heading(ax,'','Keep uncertainty sources distinct')
            for x,label in ((.01,'Parameters'),(.26,'States'),(.51,'Observation'),(.76,'Inputs')):
                box(ax,x,.59,.23,.19,label)
            text(ax,.50,.42,'Propagation depends on the model and use case.',ha='center',fontsize=7.5)
            ax.plot([.13,.88],[.24,.24],color=teal,lw=1.4);ax.plot([.13,.13],[.19,.29],color=teal);ax.plot([.88,.88],[.19,.29],color=teal)
            text(ax,.50,.11,'Predictive interval: assess calibration on held-out data',ha='center',fontsize=7.2)
        if composite:
            architecture(axes[0]);protocol(axes[1]);candidates(axes[2]);conservation(axes[3])
        elif kind=='scale':scale(axes[0])
        elif kind=='uncertainty':uncertainty(axes[0])
        else:raise ValueError('Unknown authored diagram')
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        for artist,patch in boxes:
            a=artist.get_window_extent(renderer);b=patch.get_window_extent(renderer)
            if a.x0<b.x0 or a.x1>b.x1 or a.y0<b.y0 or a.y1>b.y1:raise ValueError('Diagram label exceeds node')
        for artist,ax in texts:
            a=artist.get_window_extent(renderer);b=ax.get_window_extent(renderer)
            if a.x0<b.x0-1 or a.x1>b.x1+1 or a.y0<b.y0-1 or a.y1>b.y1+1:raise ValueError('Diagram text exceeds panel')
        bounds=[list(ax.get_position().bounds) for ax in axes]
        for suffix in ('pdf','svg'):fig.savefig(directory/(spec['id']+'.'+suffix))
        portable_svg(directory/(spec['id']+'.svg'))
        plt.close(fig)
    manifest={'kind':'integrated_conceptual_overview' if composite else 'single_column_conceptual_diagram','experimental_data':False,'source_keys':spec['source_keys'],'semantic_verification':False,'visual_status':'PENDING','panel_bounds':bounds,'panel_labels':['a','b','c','d'] if composite else [],'spec_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()}
    from reviewforge import atomic_json
    atomic_json(directory/(spec['id']+'.manifest.json'),manifest);return manifest
