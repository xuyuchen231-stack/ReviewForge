"""Deterministic offline manuscript checks. Never invokes a model or modifies a manuscript."""
from __future__ import annotations
import hashlib
from collections import Counter
import json
import re
from pathlib import Path

CITES = re.compile(r'\\(?:cite|parencite|textcite|autocite|footcite|supercite)\w*\*?(?:\[[^\]]*\]){0,2}\{([^{}]+)\}')
BIB = re.compile(r'(?m)^\s*@(?!comment\b|preamble\b|string\b)[A-Za-z]+\s*[{(]\s*([^,\s]+)\s*,', re.I)
MANUAL = re.compile(r'\\bibitem(?:\[[^\]]*\])?\{([^{}]+)\}')
REF = re.compile(r'\\(?:ref|eqref|autoref|cref|Cref)\*?\{([^{}]+)\}')
LABEL = re.compile(r'\\label\{([^{}]+)\}')
ENV = re.compile(r'\\(begin|end)\{([^{}]+)\}')

def citekeys(text):
    keys = set()
    for group in CITES.findall(text):
        keys.update(k.strip() for k in group.split(",") if k.strip())
    return keys

def reference_targets(text):
    return {key.strip() for group in REF.findall(text) for key in group.split(',') if key.strip()}

def unique_label_targets(text):
    active=[]
    for line in text.splitlines():
        for index,char in enumerate(line):
            if char=='%' and (index-len(line[:index].rstrip('\\')))%2==0:
                line=line[:index];break
        active.append(line)
    return {key for key,count in Counter(LABEL.findall('\n'.join(active))).items() if count==1}

def bibkeys(text):
    return set(BIB.findall(text)) | set(MANUAL.findall(text))

def _load(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""

def source_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def tex_integrity(text):
    labels = LABEL.findall(text)
    references = {x.strip() for group in REF.findall(text) for x in group.split(",")}
    stack, errors = [], []
    for match in ENV.finditer(text):
        action, env = match.groups()
        if action == "begin":
            stack.append((env, match.start()))
        elif not stack or stack[-1][0] != env:
            errors.append({"kind": "environment_mismatch", "environment": env, "offset": match.start()})
        else:
            stack.pop()
    errors.extend({"kind": "unclosed_environment", "environment": env, "offset": pos}
                  for env, pos in stack)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    missing_refs = sorted(references - set(labels))
    if duplicates:
        errors.append({"kind": "duplicate_labels", "labels": duplicates})
    if missing_refs:
        errors.append({"kind": "unresolved_references", "labels": missing_refs})
    if "\ufffd" in text:
        errors.append({"kind": "replacement_characters"})
    return errors

def analyze(workspace):
    ws = Path(workspace)
    bib = _load(ws / "references.bib")
    papers = {}
    literature_path = ws / "literature.json"
    if literature_path.is_file():
        try:
            records = json.loads(_load(literature_path))
            papers = {p["key"]: p for p in records if isinstance(p, dict) and p.get("key")}
        except (ValueError, TypeError):
            pass
    languages = {}
    for lang in ("en", "zh"):
        source = ws / f"review_{lang}.tex"
        tex = _load(source)
        used = citekeys(tex)
        inline = bibkeys(tex)
        # The original review may use a manual thebibliography environment.
        known = inline if inline else bibkeys(bib)
        languages[lang] = {
            "exists": source.is_file(),
            "source_sha256": source_digest(source),
            "cited_keys": sorted(used),
            "cited_count": len(used),
            "missing_bibliography_keys": sorted(used - known),
            "unregistered_keys": sorted(used - set(papers)) if papers else [],
            "tex_issues": tex_integrity(tex) if tex else [{"kind": "missing_source"}],
            "bibliography_mode": "manual" if inline else "bibtex" if bibkeys(bib) else "missing",
        }
    languages["en"]["not_in_translation"] = sorted(set(languages["en"]["cited_keys"]) - set(languages["zh"]["cited_keys"]))
    languages["zh"]["not_in_translation"] = sorted(set(languages["zh"]["cited_keys"]) - set(languages["en"]["cited_keys"]))
    return {"languages": languages, "bibliography_entries": len(bibkeys(bib)),
            "catalogue_entries": len(papers), "offline": True}

def write_report(workspace):
    ws = Path(workspace)
    result = analyze(ws)
    target = ws / "reports"
    target.mkdir(parents=True, exist_ok=True)
    (target / "manuscript_integrity.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
