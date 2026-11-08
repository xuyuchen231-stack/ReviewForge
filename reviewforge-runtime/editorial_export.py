"""Build the final bilingual version; retain the cleaned full reference as source."""
import json
from pathlib import Path
import shutil
import time
from reviewforge import atomic_json


def finalize_versions(run,result,deadline,chat=None,export_reference=False,include_planned_figures=True):
    from autonomous_delivery import deliver_outputs,copy_project_assets
    run=Path(run).resolve();exports={}
    from editorial_refinement import sha
    for stage in ('clean','condense'):
        entry=result.get('versions',{}).get(stage)
        if not entry:continue
        path=Path(entry['path']).resolve()
        if not path.is_relative_to((run/'editorial').resolve()) or sha(path.read_text(encoding='utf-8'))!=entry.get('sha256'):raise ValueError('Editorial source digest changed or path outside run')
    for stage in (('clean','condense') if export_reference else ('condense',)):
        entry=result.get('versions',{}).get(stage)
        if not entry:continue
        source_path=Path(entry['path']).resolve()
        if not source_path.is_relative_to((run/'editorial').resolve()):raise ValueError('Editorial version outside run')
        from editorial_refinement import sha
        source=source_path.read_text(encoding='utf-8')
        if sha(source)!=entry.get('sha256'):raise ValueError('Editorial source digest changed')
        if time.time()+40>=deadline:
            exports[stage]={'status':'PAUSED','reason':'Compilation budget ended; source version retained'};continue
        version_run=source_path.parent/('full' if stage=='clean' else 'short')
        output=version_run/'output';output.mkdir(parents=True,exist_ok=True)
        assets=copy_project_assets(run/'output',output,source)
        if assets['missing']:
            exports[stage]={'status':'MISSING_ASSETS','missing':assets['missing']};continue
        (output/'review_en.tex').write_text(source,encoding='utf-8')
        if (run/'publication_figure_plan.json').exists():shutil.copyfile(run/'publication_figure_plan.json',version_run/'publication_figure_plan.json')
        if (run/'intro_citation_repairs.json').exists():shutil.copyfile(run/'intro_citation_repairs.json',version_run/'intro_citation_repairs.json')
        for name in ('literature_evidence_ledger.csv','literature_evidence_summary.csv'):
            item=run/'editorial'/name
            if item.exists():
                (output/'supplement').mkdir(exist_ok=True);shutil.copyfile(item,output/'supplement'/name)
        report={'accepted_units':0,'editorial_version':stage,'scientific_acceptance_unchanged':True,
                'editorial':{'citation_audit':result.get('citation_audit',{})},'retention_run':str(run),'source_versions':result.get('versions',{}),'run_started_epoch':result.get('run_started_epoch')}
        def no_model(*args):raise AssertionError('Publication build must not call a model')
        delivery_state={'deadline':deadline,'phase':'delivery','include_planned_figures':include_planned_figures}
        def bounded_chat(system,payload,role):
            bound=min(deadline,delivery_state.get('delivery_request_deadline',deadline))
            return (chat or no_model)(system,{**payload,'_delivery_deadline':bound},role)
        deliver_outputs(version_run,delivery_state,report,bounded_chat,stage=='condense' and chat is not None,allow_refinement=False,source_ready=True)
        acceptance=report.get('publication_acceptance',{})
        exports[stage]={'status':'READY_FOR_READING' if acceptance.get('delivery_ready') else ('COMPILED_PENDING_VISUAL_REVIEW' if acceptance.get('technical_ready') else 'NEEDS_ATTENTION'),
                        'output':str(output),'report':report}
        atomic_json(version_run/'delivery.json',exports[stage])
    result['exports']=exports
    atomic_json(run/'editorial/export_status.json',{'source_sha256':result.get('source_sha256'),'exports':exports,'expert_verified':False})
    return result
