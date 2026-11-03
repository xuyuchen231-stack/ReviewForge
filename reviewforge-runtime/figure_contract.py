"""Original final-size checks for generated vector figures (no external assets)."""
import hashlib
from pathlib import Path


def audit_vector(pdf, printed_width_mm=89, page_mm=(210, 297), min_font_pt=6.5):
    """Measure text after inclusion scaling; technical PASS is not visual approval."""
    import fitz
    pdf = Path(pdf)
    with fitz.open(pdf) as document:
        if len(document) != 1:
            raise ValueError('A figure must contain one page')
        page = document[0]
        scale = printed_width_mm * 72 / 25.4 / page.rect.width
        height = page.rect.height * scale * 25.4 / 72
        lines = [line for block in page.get_text('dict')['blocks']
                 for line in block.get('lines', [])]
        spans = [span for line in lines for span in line['spans'] if span['text'].strip()]
        fonts = [span['size'] * scale for span in spans]
        # A smaller span is a possible math script only when it is physically
        # shifted from a nearby larger baseline; same-baseline small labels fail.
        baseline_fonts = [max(s['size'] for s in line['spans'] if s['text'].strip()) * scale
                          for line in lines if any(s['text'].strip() for s in line['spans'])]
        small_labels=[]
        for span in spans:
            if span['size'] * scale >= min_font_pt - .05:
                continue
            script=False
            for base in spans:
                ratio=span['size']/base['size']
                offset=abs(span['origin'][1]-base['origin'][1])/base['size']
                gap=max(0,span['bbox'][0]-base['bbox'][2],base['bbox'][0]-span['bbox'][2])
                if .65<=ratio<=.75 and .10<=offset<=.65 and gap<=base['size']*.6:
                    script=True
                    break
            if not script:small_labels.append(span['text'])
        clipped = [span['text'] for span in spans
                   if not (page.rect + (-.5, -.5, .5, .5)).contains(fitz.Rect(span['bbox']))]
        issues = []
        if not fonts:
            issues.append('No auditable vector text')
        elif small_labels or min(fonts) < min_font_pt * .65:
            issues.append('Text too small at printed width; simplify or reflow labels')
        if printed_width_mm * height / (page_mm[0] * page_mm[1]) > .125:
            issues.append('Graphic exceeds one eighth of page area')
        if clipped:
            issues.append('Text extends outside exported figure')
    return {'schema': 'reviewforge-figure-contract-v1',
            'technical_status': 'NEEDS_ATTENTION' if issues else 'PASS',
            'visual_status': 'PENDING', 'semantic_verification': False,
            'measurement_scope': 'standalone_vector_at_declared_inclusion_width',
            'final_manuscript_placement_verified': False,
            'printed_width_mm': printed_width_mm, 'printed_height_mm': round(height, 3),
            'page_area_fraction': round(printed_width_mm * height / (page_mm[0] * page_mm[1]), 5),
            'smallest_printed_font_pt': round(min(fonts), 3) if fonts else None,
            'smallest_line_baseline_pt': round(min(baseline_fonts), 3) if baseline_fonts else None,
            'clipped_text': clipped, 'issues': issues,
            'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()}


def require_vector_contract(pdf, report, printed_width_mm=89):
    from reviewforge import atomic_json
    pdf = Path(pdf)
    report = dict(report, final_size=audit_vector(pdf, printed_width_mm))
    atomic_json(pdf.with_suffix('.manifest.json'), report)
    if report['final_size']['issues']:
        raise ValueError('Figure final-size check: ' + '; '.join(report['final_size']['issues']))
    return report
