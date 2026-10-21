"""Offline, conservative research-quality gates for ReviewForge.
No LLM calls, DOI lookups, or inferred primary-source verification.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

CITE = re.compile(r'\\cite[a-zA-Z*]*(?:\[[^\]]*\])*\{([^{}]+)\}')
REQUIRED_FIELDS = ("doi", "title", "authors", "year", "full_text_access",
                   "evidence_location", "supported_claim", "verification_status")
VERIFIED = "PRIMARY_TEXT_VERIFIED"
AXES = ("model_structure", "learned_component", "mechanistic_constraints",
        "measured_signals", "validation_design", "unseen_operating_conditions",
        "cross_batch_validation", "baseline_comparison", "failure_modes",
        "evidence_location")

def _read_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default

def _keys(tex):
    result = set()
    for match in CITE.finditer(tex):
        result.update(key.strip() for key in match.group(1).split(",") if key.strip())
    return result

def _tex_checks(text):
    errors = []
    for env in ("equation", "align", "figure", "table", "figure*", "table*"):
        begins = len(re.findall(r'\\begin\{' + re.escape(env) + r'\}', text))
        ends = len(re.findall(r'\\end\{' + re.escape(env) + r'\}', text))
        if begins != ends:
            errors.append(f"Unbalanced {env}: {begins} begins, {ends} ends")
    labels = re.findall(r'\\label\{([^{}]+)\}', text)
    duplicate = sorted({x for x in labels if labels.count(x) > 1})
    if duplicate:
        errors.append("Duplicate labels: " + ", ".join(duplicate[:20]))
    if "\ufffd" in text:
        errors.append("Unicode replacement character detected")
    if re.search(r'\\(?:mathbb|forall)\s+[A-Za-z]', text):
        errors.append("Potential malformed math command")
    return errors

def _claims(workspace):
    """Optional author-curated JSON; absence must not imply verification."""
    data = _read_json(workspace / "evidence_ledger.json", [])
    return data if isinstance(data, list) else []

def _studies(workspace):
    data = _read_json(workspace / "study_matrix.json", [])
    return data if isinstance(data, list) else []

def evaluate(workspace, minimum=60):
    ws = Path(workspace)
    reports = ws / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    literature = _read_json(ws / "literature.json", [])
    if not isinstance(literature, list):
        literature = []
    by_key = {p.get("key"): p for p in literature if isinstance(p, dict) and p.get("key")}
    tex = {}
    for language in ("en", "zh"):
        path = ws / f"review_{language}.tex"
        tex[language] = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    citations = {language: _keys(body) for language, body in tex.items()}
    ledger = _claims(ws)
    studies = _studies(ws)
    evidence = []
    for i, row in enumerate(ledger):
        if not isinstance(row, dict):
            evidence.append({"index": i, "status": "INVALID_ROW"})
            continue
        missing = [field for field in REQUIRED_FIELDS if not row.get(field)]
        key = row.get("citekey")
        if not key:
            missing.append("citekey")
        if key not in by_key:
            missing.append("citekey_in_literature")
        verified = (not missing and row.get("verification_status") == VERIFIED
                    and row.get("full_text_access") not in ("none", "metadata_only", "abstract_only"))
        evidence.append({"index": i, "citekey": key,
                         "status": "VERIFIED_RECORDED" if verified else "UNVERIFIED",
                         "missing": missing})
    verified_keys = {row.get("citekey") for i, row in enumerate(ledger)
                     if isinstance(row, dict) and evidence[i]["status"] == "VERIFIED_RECORDED"}
    all_cited = citations["en"] | citations["zh"]
    uncovered = sorted(all_cited - verified_keys)
    matrix = []
    for i, study in enumerate(studies):
        if not isinstance(study, dict):
            matrix.append({"index": i, "missing": list(AXES)})
            continue
        matrix.append({"index": i, "citekey": study.get("citekey"),
                       "missing": [field for field in AXES if not study.get(field)]})
    missing_study_keys = sorted(all_cited - {s.get("citekey") for s in studies if isinstance(s, dict)})
    issues = []
    for language, body in tex.items():
        if not body:
            issues.append({"severity": "critical", "gate": "manuscript",
                           "message": f"Missing review_{language}.tex"})
        for err in _tex_checks(body):
            issues.append({"severity": "major", "gate": "latex", "message": f"{language}: {err}"})
    if citations["en"] != citations["zh"]:
        issues.append({"severity": "major", "gate": "bilingual",
                       "message": "English/Chinese citation sets differ",
                       "english_only": sorted(citations["en"] - citations["zh"]),
                       "chinese_only": sorted(citations["zh"] - citations["en"])})
    if uncovered:
        issues.append({"severity": "critical", "gate": "evidence",
                       "message": "Cited works lack independently inspected primary-text evidence",
                       "keys": uncovered})
    if missing_study_keys:
        issues.append({"severity": "major", "gate": "synthesis",
                       "message": "Cited works lack a structured comparison-matrix entry",
                       "keys": missing_study_keys})
    incomplete = [r for r in matrix if r["missing"]]
    if incomplete:
        issues.append({"severity": "major", "gate": "synthesis",
                       "message": "Study matrix has incomplete comparison axes",
                       "rows": incomplete})
    if len(citations["en"]) < minimum or len(citations["zh"]) < minimum:
        issues.append({"severity": "major", "gate": "citation_count",
                       "message": "Minimum distinct citations not met"})
    build = {language: _read_json(reports / f"review_{language}_build.json", {})
             for language in ("en", "zh")}
    for language, result in build.items():
        if result.get("status") != "PASS":
            issues.append({"severity": "critical", "gate": "build",
                           "message": f"{language} PDF build not confirmed"})
    # Explicit external review: never self-certify scientific quality.
    independent_review = _read_json(ws / "independent_review.json", {})
    if independent_review.get("decision") != "approved" or not independent_review.get("reviewer"):
        issues.append({"severity": "critical", "gate": "peer_review",
                       "message": "Independent expert approval not recorded"})
    result = {
        "schema_version": 1,
        "submission_ready": not issues,
        "scientific_quality_human_verified": False,
        "cited": {lang: len(keys) for lang, keys in citations.items()},
        "evidence_rows": evidence,
        "primary_text_verified_citekeys_recorded": sorted(verified_keys),
        "unverified_cited_keys": uncovered,
        "study_matrix_rows": len(studies),
        "study_matrix_missing_keys": missing_study_keys,
        "build": {lang: report.get("status", "UNKNOWN") for lang, report in build.items()},
        "issues": issues,
        "note": "A recorded evidence excerpt and independent approval require human authentication; this offline gate cannot prove that an excerpt truly supports a claim."
    }
    (reports / "quality_gate.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports / "major_issues.md").write_text(
        "# ReviewForge quality findings\n\n" +
        "\n".join(f"- **{item['severity'].upper()} / {item['gate']}**: {item['message']}"
                  for item in issues) + "\n", encoding="utf-8")
    return result

def scaffold(workspace):
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    templates = {
        "evidence_ledger.example.json": [{
            "citekey": "EXAMPLE2026", "doi": "10.xxxx/example", "title": "Example title",
            "authors": ["Author A"], "year": 2026, "full_text_access": "local_pdf",
            "evidence_location": "p. 5, Fig. 2",
            "supporting_excerpt": "Exact quotation checked against the source",
            "supported_claim": "Claim supported by this evidence",
            "verification_status": "PENDING_HUMAN_CHECK",
            "limitations": "Validation excludes unseen feed policies"
        }],
        "study_matrix.example.json": [{
            "citekey": "EXAMPLE2026", "model_structure": "parallel hybrid",
            "learned_component": "growth rate", "mechanistic_constraints": "mass balance",
            "measured_signals": "biomass, substrate, product",
            "validation_design": "held-out batches", "unseen_operating_conditions": "not tested",
            "cross_batch_validation": "not reported", "baseline_comparison": "mechanistic model",
            "failure_modes": "unknown outside training range",
            "evidence_location": "p. 5, Fig. 2"
        }],
        "independent_review.example.json": {
            "reviewer": "", "decision": "pending", "major_issues": [],
            "scientific_novelty": "", "synthesis_depth": "",
            "claim_support": "", "methods_and_limitations": "",
            "figure_and_equation_integrity": "", "bilingual_consistency": ""
        }
    }
    created = []
    for name, value in templates.items():
        path = ws / name
        if not path.exists():
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            created.append(str(path))
    return created
