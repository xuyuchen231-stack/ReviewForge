"""Compact, single-column scientific synthesis; no invented empirical results."""
from pathlib import Path
import re

FIGURE_MM=(89,68)
OWNED={'fig:process','fig:model','fig:alternatives','fig:validation',
       'fig:rf-framework_abcd','fig:rf-scale_single','fig:rf-uncertainty_single'}


def column_math(tex,directory=None,deadline=None):
    pattern=re.compile(r'\\begin\{strip\}([\s\S]*?)\\end\{strip\}')
    def unwrap(match):
        body=match.group(1)
        if not re.search(r'\\\[|\\begin\{(?:equation|align)',body):return match.group()
        body=re.sub(r'\\hypertarget\{rf-wide-\d+-(?:start|end)\}\{\}','',body)
        body=re.sub(r'(?m)^\s*\\small\s*$','',body)
        return body.strip()
    tex=pattern.sub(unwrap,tex)
    # Genuine author aligned systems remain opaque. The measured formatter
    # reflows only explicitly tagged continuations.
    if directory is None:return tex,0
    from math_layout import balanced_math
    return balanced_math(tex,directory,deadline)


def render_compact(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Rectangle, Circle
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':7,'pdf.fonttype':42,'svg.fonttype':'none'}):
        fig=plt.figure(figsize=(FIGURE_MM[0]/25.4,FIGURE_MM[1]/25.4))
        axes=[fig.add_axes(rect) for rect in ((.04,.56,.43,.34),(.56,.56,.40,.34),(.13,.12,.34,.29),(.56,.12,.40,.29))]
        titles=('a  Learning interface','b  Conservative coupling','c  Non-identifiability','d  Locked validation')
        for ax,title in zip(axes,titles):
            ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
            ax.text(0,1.12,title,transform=ax.transAxes,fontsize=7,fontweight='bold',va='bottom')
        a,b,c,d=axes
        def box(ax,x,y,w,h,label,accent=False):
            ax.add_patch(Rectangle((x,y),w,h,linewidth=.7,edgecolor='#146B78' if accent else '#435967',facecolor='#E7F3F3' if accent else '#F3F5F6'))
            ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=7)
        def arrow(ax,start,end):ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','lw':.75,'color':'#146B78','shrinkA':1,'shrinkB':1})
        box(a,.06,.60,.86,.26,r'$r_\phi(x,u)$',True)
        box(a,.06,.14,.86,.27,r'$\dot x=f_{\rm mech}(x,u,r_\phi)$')
        arrow(a,(.49,.60),(.49,.41))
        a.text(.50,-.04,r'$\hat y=h_\psi(x,u)$',ha='center',fontsize=7)
        for x,label in ((.19,r'$M_1$'),(.81,r'$M_2$')):
            b.add_patch(Circle((x,.67),.16,facecolor='#F3F5F6',edgecolor='#435967',lw=.7));b.text(x,.67,label,ha='center',va='center')
        arrow(b,(.35,.72),(.65,.72));arrow(b,(.65,.60),(.35,.60))
        b.text(.50,.94,r'$q_{12},q_{21}$',ha='center',fontsize=7)
        b.text(.5,.25,r'$\dot M_1+\dot M_2=r_1+r_2$',ha='center',fontsize=7)
        b.text(.5,.02,'Internal fluxes cancel',ha='center',fontsize=7)
        c.axis('on');c.spines[['top','right']].set_visible(False)
        t=np.linspace(0,4,160);c.plot(t,1-np.exp(-t),color='#146B78',lw=1.3)
        c.set(xlim=(0,4),ylim=(0,1.08),xticks=[0,4],yticks=[0,1]);c.tick_params(labelsize=6.5,pad=1,length=2)
        c.set_xlabel(r'$t$',fontsize=7,labelpad=0);c.set_ylabel(r'$M(t)$',fontsize=7,labelpad=0)
        c.text(.43,.48,r'$R_f=e^{-t}+a$'+'\n'+r'$D=a$'+'\n'+r'$a=0.3,0.6$',transform=c.transAxes,fontsize=6.6,va='top')
        for x,label,accent in ((.02,'Train',False),(.36,'Val.',False),(.70,'Test',True)):
            box(d,x,.54,.28,.32,label,accent)
        d.plot([.66,.66],[.40,.96],lw=.9,color='#146B78');d.text(.66,1.01,'LOCK',ha='center',fontsize=6.5,color='#146B78')
        d.text(.5,.20,'Held-out batches / inputs',ha='center',fontsize=6.8)
        d.text(.5,-.02,'No future observations',ha='center',fontsize=6.8)
        for suffix in ('pdf','svg'):
            fig.savefig(directory/('compact_synthesis.'+suffix))
        plt.close(fig)
        from review_overview_figure import portable_svg
        portable_svg(directory/'compact_synthesis.svg')
        from figure_contract import require_vector_contract
        require_vector_contract(directory/'compact_synthesis.pdf', {
            'kind':'analytical_synthesis','experimental_data':False,
            'panel_roles':['learning interface','conservation','analytical non-identifiability example','validation protocol'],
            'editable_source':'compact_publication.py:render_compact',
            'vector_source':'compact_synthesis.svg',
            'analytical_example':'M=1-exp(-t); R_f=exp(-t)+a; D=a; not observed data'})


def compact_figures(tex,output):
    """Remove explicitly identified redundant schematics, keeping unknown author figures."""
    from manuscript_integrity import citekeys
    from bibliography_delivery import active_text
    matches=list(re.finditer(r'\\begin\{figure\*?\}(?:\[[^]]*\])?[\s\S]*?\\end\{figure\*?\}',active_text(tex)))
    selected=[];ambiguous=[]
    assets={'fig:rf-framework_abcd':'framework_abcd.pdf','fig:rf-scale_single':'scale_single.pdf','fig:rf-uncertainty_single':'uncertainty_single.pdf'}
    signatures={'fig:process':(r'F(t),I(t)','Feed and induction'),
                'fig:model':(r'r_\theta(x,u)',r'\hat x(t_0)'),
                'fig:alternatives':(r'(R_f,D)\rightarrow',r'1-exp(-\x)'),
                'fig:validation':('Competing explanations','Historical measurements')}
    for match in matches:
        labels=set(re.findall(r'\\label\{([^}]+)\}',match.group()))
        if not labels or not labels<=OWNED:continue
        graphics=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',match.group())
        verified=all((label in assets and graphics==['figures/'+assets[label]]) or
                     (label in signatures and not graphics and r'\begin{tikzpicture}' in match.group() and all(token in match.group() for token in signatures[label])) for label in labels)
        if verified:selected.append(match)
        else:ambiguous.extend(sorted(labels))
    existing=r'\label{fig:rf-compact}' in active_text(tex)
    if not selected:
        if existing:render_compact(Path(output)/'figures')
        return tex,{'removed_redundant':0,'retained_synthesis':int(existing),'ambiguous_figures':ambiguous,'status':'NEEDS_REVIEW' if ambiguous else ('PASS' if existing else 'NOT_APPLICABLE')}
    render_compact(Path(output)/'figures')
    old_keys=citekeys(tex)
    chinese=bool(re.search(r'\\usepackage\[[^]]*\]\{ctex\}',tex))
    caption=('学习位置、守恒约束、可辨识性与独立验证。曲线为解析示例。' if chinese else 'Learning, conservation, identifiability and validation. Analytical illustration.')
    block='\n'+r'\begin{figure}[!t]'+'\n% RF_SINGLE_COLUMN_FIGURE\n'+r'\centering'+'\n'+r'\includegraphics[width=\columnwidth,height=.24\paperheight,keepaspectratio]{figures/compact_synthesis.pdf}'+'\n'+r'\caption{'+caption+'}\n'+r'\label{fig:rf-compact}'+'\n'+r'\end{figure}'+'\n'
    insertion=selected[0].start()
    removed_labels={label for match in selected for label in re.findall(r'\\label\{([^}]+)\}',match.group())}
    for match in reversed(selected):tex=tex[:match.start()]+tex[match.end():]
    if not existing:tex=tex[:insertion]+block+tex[insertion:]
    if 'fig:process' in removed_labels:
        tex=re.sub(r'\s*[（(](?:Figure|图)\s*~?\\ref\{fig:process\}[）)]','',tex)
    for label in removed_labels & {'fig:rf-scale_single','fig:rf-uncertainty_single'}:
        tex=re.sub(r'(?:Figure|图)\s*~?\\ref\{'+re.escape(label)+r'\}[^.!?。]*[.!?。]','',tex)
    for label in removed_labels:tex=tex.replace('\\ref{'+label+'}',r'\ref{fig:rf-compact}')
    missing=old_keys-citekeys(tex)
    if missing:
        tex=tex.replace(r'\caption{'+caption+'}',r'\caption{'+caption+r'\cite{'+','.join(sorted(missing))+'}.}',1)
    return tex,{'status':'NEEDS_REVIEW' if ambiguous else 'PASS','ambiguous_figures':ambiguous,'removed_redundant':len(selected),'retained_synthesis':1,'graphic_mm':list(FIGURE_MM),'page_area_limit':.125,'experimental_data':False}
