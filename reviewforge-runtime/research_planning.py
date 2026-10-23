"""Question-level evidence coverage and figure briefs, independent of topic."""
import json
import re
from pathlib import Path
from manuscript_integrity import citekeys


def coverage_report(workspace, manuscript):
    path = Path(workspace)/'coverage_matrix.json'
    result = {'status': 'MISSING', 'complete': False, 'questions': [],
              'note': 'Coverage is author-curated; counts and anchors do not prove scientific support.'}
    if not path.exists(): return result
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        questions = data['questions']
        if not isinstance(questions, list) or not questions: raise ValueError('Questions required')
        used = citekeys(manuscript)
        for row in questions:
            if not isinstance(row, dict) or not row.get('id') or not row.get('question'):
                raise ValueError('Each question needs an id and question')
            support, counter = row.get('supporting_keys', []), row.get('counterevidence_keys', [])
            if any(not isinstance(x, list) or any(not isinstance(k,str) for k in x) for x in (support,counter)):
                raise ValueError('Citation keys must be lists of strings')
            gaps = []
            if not support: gaps.append('supporting_studies_missing')
            if set(support+counter)-used: gaps.append('listed_studies_not_cited')
            if not row.get('counterevidence_search'): gaps.append('counterevidence_search_not_documented')
            if not counter and not row.get('no_counterevidence_reason'): gaps.append('counterevidence_absence_unexplained')
            if row.get('unresolved'): gaps.append('unresolved_evidence_question')
            result['questions'].append({**row, 'gaps': gaps})
        result.update(status='ASSESSED', complete=not any(x['gaps'] for x in result['questions']))
    except (OSError, ValueError, KeyError, TypeError):
        result.update(status='INVALID', complete=False)
    return result


def figure_inventory(tex):
    result = []
    for i, match in enumerate(re.finditer(r'\\begin\{figure\*?\}.*?\\end\{figure\*?\}',tex,re.S),1):
        body = match.group()
        label = re.search(r'\\label\{([^{}]+)\}',body)
        result.append({'id':i, 'label':label.group(1) if label else '',
                       'status':'NEEDS_DESIGN_REVIEW',
                       'question_answered':'', 'evidence_sources':[], 'decision':'review',
                       'checks':['Scientific meaning and arrows supported by evidence',
                                 'Readable at final column width; no overlapping labels',
                                 'Caption explains abbreviations and evidence boundaries',
                                 'Consistent bilingual terminology; source available for editing']})
    return result
