"""Local delivery with independent build/translation budgets and no stale bilingual output."""
import hashlib
import re
from pathlib import Path
import time
import uuid
from reviewforge import atomic_json

def quarantine_stale_outputs(run):
    run=Path(run);out=run/'output'
    archived=[];archive=run/'stale_outputs'/uuid.uuid4().hex
    for path in [out/'review_zh.tex',out/'output/review_en.pdf',out/'output/review_zh.pdf',out/'translation_provenance.json',out/'reports/review_en_build.json',out/'reports/review_zh_build.json']:
        if path.exists():
            archive.mkdir(parents=True,exist_ok=True);target=archive/path.name
            path.replace(target);archived.append(str(target.relative_to(run)))
    return archived

def deliver_outputs(run,state,report,chat,translate=True,allow_refinement=True,source_ready=False):
    from reviewforge_v4 import compile_tex,generate_chinese_body
    run=Path(run);out=run/'output';out.mkdir(exist_ok=True)
    report.setdefault('stale_outputs_quarantined',[]).extend(quarantine_stale_outputs(run))
    report['review_en_build']={'status':'SKIPPED','reason':'No accepted units or insufficient build budget'}
    report['review_zh_build']={'status':'SKIPPED','reason':'No current successful translation'}
    if not report['accepted_units'] and not source_ready:
        report['translation']='not_run_no_accepted_units';return report
    remaining=state['deadline']-time.time()
    if remaining>30:
        from publication_export import canonicalize_references,prepare_two_column_export,reflow_wide_displays,mark_wide_material,reconcile_pdf_references
        original_blob=(out/'review_en.tex').read_bytes()
        source=(out/'review_en.tex').read_text(encoding='utf-8')
        original=source
        from publication_style import prose_lists,sorted_citation_groups
        import os
        if allow_refinement and os.environ.get('RF_MANUSCRIPT_REFINEMENT', '0') == '1':
            from editorial_refinement import audit,evidence_ledger,refine
            from autonomous_review import RunLock
            editorial=run/'editorial';editorial.mkdir(exist_ok=True)
            atomic_json(editorial/'audit.json',audit(source))
            evidence_ledger(run,editorial/'literature_evidence_ledger.csv')
            import shutil
            (out/'supplement').mkdir(exist_ok=True)
            for name in ('literature_evidence_ledger.csv','literature_evidence_summary.csv'):
                shutil.copyfile(editorial/name,out/'supplement'/name)
            # Reserve build time. Scientific acceptance remains unchanged by editorial review.
            previous_deadline=state.get('delivery_request_deadline')
            state['delivery_request_deadline']=min(state['deadline']-120,previous_deadline or float('inf'))
            try:
                with RunLock(editorial/'editorial.lock'):
                    report['editorial']=refine(source,editorial,chat,deadline=state['delivery_request_deadline'],quality_workspace=run)
            except RuntimeError:
                report['editorial']={'status':'PAUSED','reason':'Editorial workspace busy; existing process retained'}
            finally:
                if previous_deadline is None:state.pop('delivery_request_deadline',None)
                else:state['delivery_request_deadline']=previous_deadline
            version=report['editorial'].get('versions',{}).get('condense')
            if report['editorial']['status']=='COMPLETE' and version:
                source=Path(version['path']).read_text(encoding='utf-8')
        source,report['prose_presentation']=prose_lists(source)
        if (run/'publication_figure_plan.json').exists() and r'\label{fig:rf-compact}' not in source:
            import json
            from publication_figures import add_planned_figures
            try:source,report['figures']=add_planned_figures(source,json.loads((run/'publication_figure_plan.json').read_text(encoding='utf-8')),out)
            except (ValueError,TypeError,ImportError,OSError) as exc:report['figures']={'status':'FAILED','reason':type(exc).__name__+': '+str(exc)[:200],'model_calls':0}
        from compact_publication import compact_figures,column_math
        source,report['compact_figure_policy']=compact_figures(source,out)
        source,column_math_count=column_math(source)
        report['column_math_reflow']=column_math_count
        source,aliases=canonicalize_references(source);report['reference_aliases']=aliases
        source=sorted_citation_groups(source)
        from publication_export import prefer_multiline_displays
        source,multiline_count=prefer_multiline_displays(source)
        report['multiline_equations']={'changed':multiline_count,'policy':'single-column-first; algebra and labels preserved'}
        source=mark_wide_material(prepare_two_column_export(source))
        (out/'review_en.tex').write_bytes(source.encode('utf-8'))
        def build_current():
            return compile_tex(out,'review_en',timeout_seconds=int(max(1,min(600,state['deadline']-time.time()-15))))
        report['review_en_build']=build_current()
        build=report['review_en_build'];layout=build.get('layout',{});adjustments=[]
        eligible=build.get('status')=='PASS' and not layout.get('unresolved') and not layout.get('missing_glyphs') and re.search(r'\\documentclass\s*\[[^]]*\btwocolumn\b[^]]*\]',source)
        if eligible and layout.get('overflows') and state['deadline']-time.time()>30:
            source,count=column_math(source)
            if count:
                source=mark_wide_material(source)
                (out/'review_en.tex').write_bytes(source.encode('utf-8'));adjustments.append('full_width_math_strips:'+str(count))
                report['review_en_build']=build_current();layout=report['review_en_build'].get('layout',{})
            tiny=layout.get('overflows',[])
            if report['review_en_build'].get('status')=='PASS' and tiny and not layout.get('unresolved') and not layout.get('missing_glyphs') and all(re.search(r'Overfull \\vbox \((\d+(?:\.\d+)?)pt',w) and float(re.search(r'Overfull \\vbox \((\d+(?:\.\d+)?)pt',w).group(1))<=8 for w in tiny) and state['deadline']-time.time()>30:
                import math
                extra=max(3,math.ceil(max(float(re.search(r'Overfull \\vbox \((\d+(?:\.\d+)?)pt',w).group(1)) for w in tiny)))
                if extra>3:extra+=3  # Leave room for the output routine's baseline adjustment.
                source=source.replace(r'\begin{document}',r'\addtolength{\textheight}{'+str(extra)+'pt}'+'\n'+r'\begin{document}',1)
                (out/'review_en.tex').write_bytes(source.encode('utf-8'));adjustments.append('text_height_plus_'+str(extra)+'pt')
                report['review_en_build']=build_current()
        if source!=original:
            saved=run/'reports/layout_original_english.tex';saved.parent.mkdir(exist_ok=True);saved.write_bytes(original_blob)
            report['layout_adaptation']={'adjustments':adjustments,'original_sha256':hashlib.sha256(original_blob).hexdigest(),'export_sha256':hashlib.sha256(source.encode()).hexdigest(),'original_export':str(saved.relative_to(run)),'reason':'Requested columns preserved; wide material reflowed without changing math source.'}
            atomic_json(run/'reports/layout_adaptation.json',report['layout_adaptation'])
        if state['deadline']-time.time()>30:
            source,report['review_en_build'],report['citation_order']=reconcile_pdf_references(out,source,report['review_en_build'],build_current,deadline=state['deadline'])
            if report['citation_order']['status'] not in ('PASS','NOT_APPLICABLE'):report['review_en_build']['delivery_ready']=False
        if report.get('layout_adaptation'):
            report['layout_adaptation']['export_sha256']=hashlib.sha256((out/'review_en.tex').read_bytes()).hexdigest()
            atomic_json(run/'reports/layout_adaptation.json',report['layout_adaptation'])
        from editorial_quality import acceptance_report
        pages=None
        pdf=out/(report['review_en_build'].get('pdf') or 'output/review_en.pdf')
        if pdf.is_file() and report['review_en_build'].get('status')=='PASS':
            try:
                import fitz
                with fitz.open(pdf) as document:pages=len(document)
            except (ImportError,OSError,ValueError):pass
        report['publication_acceptance']=acceptance_report(source,report['review_en_build'],report.get('citation_order',{}),pages,report.get('editorial',{}).get('citation_audit'))
        report['publication_acceptance']['planned_figures_status']=report.get('figures',{}).get('status','CHECKED' if 'figures' in report else 'NOT_CONFIGURED')
        if report['publication_acceptance']['planned_figures_status']=='FAILED':
            report['publication_acceptance'].update(technical_ready=False,delivery_ready=False)
        if report.get('prose_presentation',{}).get('status')!='PASS':
            report['publication_acceptance'].update(technical_ready=False,delivery_ready=False)
        report['review_en_build']['delivery_ready']=report['publication_acceptance']['delivery_ready']
        atomic_json(out/'publication_acceptance.json',report['publication_acceptance'])
        if report['publication_acceptance']['technical_ready']:
            from publication_export import make_overleaf_project
            try:report['overleaf']=make_overleaf_project(out)
            except (ValueError,OSError) as exc:report['overleaf']={'status':'FAILED','reason':str(exc)[:200]}
    report['translation']='not_run_time_budget_or_disabled'
    if report.get('review_en_build',{}).get('status')=='FAILED':
        report['translation']='not_run_english_build_failed'
        return _compact_publication(run,out,report)
    if report.get('prose_presentation',{}).get('status') in ('FAILED','NEEDS_REVIEW'):
        report['translation']='not_run_presentation_needs_revision'
        return _compact_publication(run,out,report)
    if not translate or state['deadline']-time.time()<=120:return _compact_publication(run,out,report)
    remaining=state['deadline']-time.time();build_reserve=min(600,max(30,remaining*.25))
    translation_deadline=state['deadline']-build_reserve
    state['delivery_request_deadline']=translation_deadline
    class API:
        def chat(self,system,user,role='writer'):return chat(system,{'translation_request':user},role)
    english=(out/'review_en.tex').read_text(encoding='utf-8')
    try:
        chinese=generate_chinese_body(API(),english,[],out,deadline=translation_deadline,context_workspace=run)
        from publication_style import prose_lists,sorted_citation_groups
        chinese,report['chinese_prose_presentation']=prose_lists(chinese)
        chinese=sorted_citation_groups(chinese)
        from compact_publication import compact_figures
        chinese,report['chinese_compact_figure_policy']=compact_figures(chinese,out)
        (out/'review_zh.tex').write_bytes(chinese.encode('utf-8'))
        report['translation']='generated'
        atomic_json(out/'translation_provenance.json',{'english_sha256':hashlib.sha256(english.encode()).hexdigest(),'chinese_sha256':hashlib.sha256(chinese.encode()).hexdigest(),'expert_verified':False})
    except Exception as exc:
        report['translation']='incomplete';report['translation_error']=type(exc).__name__+': '+str(exc)[:250]
    finally:state.pop('delivery_request_deadline',None)
    if report['translation']=='generated' and state['deadline']-time.time()>30:
        report['review_zh_build']=compile_tex(out,'review_zh',timeout_seconds=int(max(1,min(600,state['deadline']-time.time()-15))))
        from publication_export import reconcile_pdf_references
        def build_chinese():return compile_tex(out,'review_zh',timeout_seconds=int(max(1,min(600,state['deadline']-time.time()-15))))
        chinese,report['review_zh_build'],report['chinese_citation_order']=reconcile_pdf_references(out,chinese,report['review_zh_build'],build_chinese,deadline=state['deadline'],basename='review_zh')
        if report['chinese_citation_order'].get('status') not in ('PASS','NOT_APPLICABLE') or report.get('chinese_prose_presentation',{}).get('status')!='PASS':report['review_zh_build']['delivery_ready']=False
        atomic_json(out/'translation_provenance.json',{'english_sha256':hashlib.sha256(english.encode()).hexdigest(),'chinese_sha256':hashlib.sha256(chinese.encode()).hexdigest(),'formatting_after_translation':['prose_lists','numeric_citation_order'],'expert_verified':False})
    return _compact_publication(run,out,report)


def _compact_publication(run,out,report):
    import os
    if any(report.get(key,{}).get('status')=='NEEDS_REVIEW' for key in ('compact_figure_policy','chinese_compact_figure_policy')):
        report['compact_results']={'status':'NOT_PUBLISHED','reason':'Ambiguous figure ownership requires review; author material preserved'}
        return report
    from result_retention import publish_latest,prune_build_artifacts
    try:
        report['compact_results']=publish_latest(run,report,output=out)
        if report['compact_results']['status']=='PUBLISHED':report['build_cleanup']=prune_build_artifacts(out,remove_page_images=os.environ.get('RF_SAVE_PAGE_PREVIEWS','0')!='1')
    except (OSError,ValueError) as exc:
        report['compact_results']={'status':'NOT_PUBLISHED','reason':type(exc).__name__}
    return report

def copy_project_assets(workspace,output,tex):
    """Package referenced local dependencies, never recursively copy other manuscripts."""
    import re,shutil
    root=Path(workspace).resolve();output=Path(output);queue=[(tex,root)];seen=set();copied=[];missing=[]
    pattern=re.compile(r'\\(input|include|includegraphics|bibliography|documentclass|usepackage)(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}')
    graphic_dirs=[root]
    for block in re.findall(r'\\graphicspath\s*\{((?:\{[^{}]*\})+)\}',tex):
        graphic_dirs.extend(root/p for p in re.findall(r'\{([^{}]*)\}',block))
    while queue:
        body,base=queue.pop()
        for command,names in pattern.findall(body):
            for name in names.split(','):
                name=name.strip()
                if not name or '\\' in name:continue
                suffixes={'includegraphics':['','.pdf','.png','.jpg','.jpeg','.eps','.svg'],'bibliography':['','.bib'],'documentclass':['','.cls'],'usepackage':['','.sty']}.get(command,['','.tex'])
                roots=[base,root]+(graphic_dirs if command=='includegraphics' else [])
                found=next((p.resolve() for folder in roots for ext in suffixes if (p:=folder/(name+ext)).is_file() and p.resolve().is_relative_to(root)),None)
                if found is None:
                    if command not in ('usepackage','documentclass'):missing.append(name)
                    continue
                rel=found.relative_to(root)
                # Only publication assets belong in a source package, even if an
                # untrusted manuscript names a local configuration file as input.
                allowed={'.tex','.sty','.cls','.bib','.bbl','.bst','.pdf','.png','.jpg','.jpeg','.eps','.svg',''}
                if any(part.startswith('.') for part in rel.parts) or found.suffix.lower() not in allowed:
                    missing.append(name);continue
                if rel.as_posix() in {'review_en.tex','review_zh.tex','original.tex'}:continue
                if found in seen:continue
                seen.add(found);target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(found,target)
                copied.append({'path':rel.as_posix(),'sha256':hashlib.sha256(found.read_bytes()).hexdigest()})
                if found.suffix.lower() in ('.tex','.sty','.cls'):queue.append((found.read_text(encoding='utf-8',errors='replace'),found.parent))
    return {'copied':copied,'missing':sorted(set(missing))}
