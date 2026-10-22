"""Evidence-aware iterative scholarly assessment; never overwrite originals."""
import json
from pathlib import Path

RUBRIC={"depth":20,"evidence":20,"synthesis":25,"critical_analysis":20,"clarity":15}

def assess(chat,heading,body):
    prompt=("Independent scholarly reviewer. Return ONLY a JSON object with keys "
      "scores, major_issues, unsupported_claims, revision_actions. Scores must "
      "include depth (0..20), evidence (0..20), synthesis (0..25), "
      "critical_analysis (0..20), clarity (0..15). Each issue must be actionable. "
      "Critique superficial literature listing, unsupported conclusions and weak comparisons. "
      "Never infer evidence from bibliography metadata.")
    raw=chat(prompt,{"heading":heading,"text":body}).strip()
    if raw.startswith(chr(96)*3):
        raw=raw.split("\n",1)[-1].rsplit(chr(96)*3,1)[0].strip()
    review=json.loads(raw)
    scores=review.get("scores",{})
    for name,maximum in RUBRIC.items():
        score=scores.get(name)
        if type(score) not in (int,float) or not 0<=score<=maximum:
            raise ValueError("Invalid rubric score: "+name)
    for key in ("major_issues","unsupported_claims","revision_actions"):
        if not isinstance(review.get(key),list):
            raise ValueError("Missing review list: "+key)
    review["total"]=sum(scores.values())
    return review

def improve(chat,gate,heading,original,max_rounds=3,target=85):
    """Bounded self-critique; preserve best accepted candidate and all source protections."""
    if not 1<=max_rounds<=10:raise ValueError("max_rounds outside 1..10")
    best=original
    review=assess(chat,heading,best)
    history=[{"round":0,"accepted":True,"review":review}]
    for number in range(1,max_rounds+1):
        if review["total"]>=target and not review["major_issues"] and not review["unsupported_claims"]:break
        prompt=("Revise the LaTeX academic review subsection based on the reviewer report. "
          "Prioritize primary-source evidence, cross-study synthesis, method comparisons, "
          "limitations and meaningful scientific depth. Do not pad length. "
          "Do not invent references, empirical results, numbers or verification. "
          "Keep original equations, citations, figures, tables, labels and cross-references. "
          "Return ONLY LaTeX.")
        try:
            candidate=chat(prompt,{"heading":heading,"text":best,"review":review}).strip()
            ok,reason=gate(original,candidate)
            if not ok:
                history.append({"round":number,"accepted":False,"reason":reason})
                continue
            new_review=assess(chat,heading,candidate)
            gain=new_review["total"]-review["total"]
            accepted=gain>=2 and len(new_review["unsupported_claims"])<=len(review["unsupported_claims"])
            history.append({"round":number,"accepted":accepted,"gain":gain,"review":new_review})
            if accepted:best,review=candidate,new_review
        except Exception as exc:
            history.append({"round":number,"accepted":False,
                            "error":type(exc).__name__+": "+str(exc)[:180]})
    return {"text":best,"review":review,"history":history,
            "status":"needs_human_review" if review["major_issues"] or review["unsupported_claims"] or review["total"]<target else "provisional_pass",
            "note":"Model scores are diagnostic, not scientific verification or acceptance prediction."}

def save(result,directory,name):
    path=Path(directory);path.mkdir(parents=True,exist_ok=True)
    (path/(name+".tex")).write_text(result["text"],encoding="utf-8")
    (path/(name+".json")).write_text(json.dumps({k:v for k,v in result.items() if k!="text"},ensure_ascii=False,indent=2),encoding="utf-8")
