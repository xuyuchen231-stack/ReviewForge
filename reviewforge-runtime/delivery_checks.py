"""Separate compiler, layout diagnostics, rendered pages and visual sign-off."""
import hashlib
import json
import re
from pathlib import Path
from reviewforge import atomic_json


def input_digests(ws, basename):
    ws = Path(ws).resolve()
    paths = {ws/(basename+'.tex')} | set(ws.rglob('*.bib'))
    fls = ws/'output'/(basename+'.fls')
    if fls.exists():
        for line in fls.read_text(encoding='utf-8', errors='replace').splitlines():
            if line.startswith('INPUT '):
                path = (ws/line[6:]).resolve()
                if path.is_relative_to(ws) and not path.is_relative_to(ws/'output'):
                    paths.add(path)
    return {str(path.relative_to(ws)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths) if path.is_file()}


def build_is_current(ws, basename, report):
    ws = Path(ws)
    source, pdf = ws/(basename+'.tex'), ws/'output'/(basename+'.pdf')
    return bool(source.is_file() and pdf.is_file() and report.get('status') == 'PASS' and
                report.get('source_sha256') == hashlib.sha256(source.read_bytes()).hexdigest() and
                report.get('pdf_sha256') == hashlib.sha256(pdf.read_bytes()).hexdigest() and
                report.get('inputs') == input_digests(ws,basename))


def layout_diagnostics(log):
    overflows = re.findall(r'Overfull \\[hv]box[^\n]*', log)
    unresolved = re.findall(r'(?:Citation|Reference)[^\n]*undefined[^\n]*|(?:Author|Year) undefined for citation[^\n]*|There were undefined (?:references|citations)', log, re.I)
    missing_glyphs = re.findall(r'Missing character:[^\n]*', log)
    return {'status': 'FAILED' if overflows or unresolved or missing_glyphs else 'PASS',
            'overflows': sorted(set(overflows)), 'unresolved': sorted(set(unresolved)),
            'missing_glyphs': sorted(set(missing_glyphs))}


def render_preview(pdf, directory):
    pdf, directory = Path(pdf), Path(directory)
    report = {'status': 'UNAVAILABLE', 'pages': [], 'visual_status': 'PENDING',
              'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()}
    try:
        import fitz
        directory.mkdir(parents=True, exist_ok=True)
        with fitz.open(pdf) as doc:
            for index, page in enumerate(doc):
                filename = f'page-{index+1:03d}.png'
                page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(directory/filename)
                report['pages'].append({'page': index+1, 'image': filename,
                                        'width_pt': page.rect.width, 'height_pt': page.rect.height})
        report['status'] = 'PASS' if report['pages'] else 'FAILED'
    except ImportError:
        report['reason'] = 'Install optional PyMuPDF to render page previews'
    except Exception as exc:
        report.update(status='FAILED', reason=type(exc).__name__ + ': PDF rendering failed')
    directory.mkdir(parents=True, exist_ok=True)
    atomic_json(directory/'manifest.json', report)
    return report


def visual_status(ws, basename, rendered):
    path = Path(ws)/'reports'/(basename+'_visual_review.json')
    if not path.exists() or rendered.get('status') != 'PASS': return 'PENDING'
    try:
        review = json.loads(path.read_text(encoding='utf-8'))
        expected = list(range(1, len(rendered['pages'])+1))
        if (review.get('pdf_sha256') == rendered['pdf_sha256'] and
            review.get('reviewed_pages') == expected and review.get('approved') is True and
            isinstance(review.get('reviewer'), str) and review['reviewer'].strip()):
            return 'PASS'
    except (ValueError, TypeError):
        pass
    return 'PENDING'


def delivery_audit(ws):
    ws = Path(ws)
    languages = {}
    for lang in ('en', 'zh'):
        name = 'review_'+lang
        path = ws/'reports'/(name+'_build.json')
        try:
            report = json.loads(path.read_text(encoding='utf-8'))
            current = build_is_current(ws,name,report)
            visual = visual_status(ws, name, report.get('rendered', {})) if current else 'PENDING'
            ready = bool(current and report.get('status') == 'PASS' and report.get('layout_status') == 'PASS' and visual == 'PASS')
            languages[lang] = {'current': bool(current), 'compile': report.get('status'),
                               'layout': report.get('layout_status'), 'visual': visual, 'ready': ready}
        except (OSError, ValueError, TypeError):
            languages[lang] = {'ready': False, 'reason': 'Missing or invalid build report'}
    try:
        trans = json.loads((ws/'reports'/'translation_gate.json').read_text(encoding='utf-8'))
        translation_pass = (isinstance(trans, dict) and trans.get('status') == 'PASS' and
            trans.get('source_sha256') == hashlib.sha256((ws/'review_en.tex').read_text(encoding='utf-8').encode()).hexdigest() and
            trans.get('output_sha256') == hashlib.sha256((ws/'review_zh.tex').read_text(encoding='utf-8').encode()).hexdigest())
    except (OSError, ValueError, TypeError):
        translation_pass = False
    return {'languages': languages, 'translation_pass': translation_pass,
            'ready': translation_pass and all(x['ready'] for x in languages.values())}
