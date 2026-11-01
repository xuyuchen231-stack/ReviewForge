"""Authored conceptual figures for this review; never experimental results."""
from manuscript_integrity import citekeys


def proposed_diagrams(tex):
    definitions = [
        ('learning_taxonomy', r'\subsection{Where learning enters the calculation}', False,
         ['Serial coupling: learned relation supplies an input or parameter to the mechanistic calculation.',
          'Parallel coupling: mechanistic output and a learned residual combine at the prediction interface.',
          'Observation correction: the measurement map changes; the physical state balance remains explicit.',
          'Derivative or rate learning: correction enters a balance term; dimensions and conservation must be checked.',
          'Compartment exchange: learned exchange must balance opposing fluxes across connected compartments.'],
         'Learning interfaces and conservation responsibilities. Serial/parallel describe coupling; observation, derivative and exchange describe location. These axes overlap and are not mutually exclusive categories.'),
        ('locked_validation', r'\subsection{Define the claim and decision before the final test}', True,
         ['Predeclare the claim, decision, reference baseline and measurable acceptance criteria.',
          'Define information available at each prediction/decision time; exclude future measurements.',
          'Partition independent batches or conditions and time windows before preprocessing.',
          'Fit transformations and parameters on training data; tune on validation data only.',
          'LOCK model, preprocessing, initialization and decision rule before examining test outcomes.',
          'Evaluate held-out predictions or executed decisions; report uncertainty and failures.',
          'Changes after test inspection require a new independent final test, not reuse of the old score.'],
         'Proposed validation protocol. The lock is an information boundary, not evidence that cited studies implemented this exact workflow.'),
        ('revision_ladder', r'\subsection{A nested model-revision ladder}', True,
         ['M0: retain the fixed-parameter mechanistic baseline calibrated earlier.',
          'M1: re-estimate a small predeclared kinetic subset while other parameters remain fixed.',
          'M2: use phase-specific parameterization when phase-dependent evidence justifies it.',
          'M3: learn a specified rate, yield, maintenance or transfer correction within explicit balances.',
          'M4: revise structure: state, compartment or physiological switch.',
          'At each step compare independent predictive evidence and complexity; stop at the adequate level.'],
         'Proposed diagnostic escalation from parameter adjustment to structural revision. This is an engineering ladder; mathematical nesting depends on the actual model definitions.')]
    figures=[]
    for identity, marker, connect, nodes, caption in definitions:
        start=tex.find(marker)
        if start<0:continue
        import re
        tail=tex[start+len(marker):]
        stop=re.search(r'\\(?:section|subsection)\*?\{',tail)
        keys=sorted(citekeys(tail[:stop.start()] if stop else tail))
        if not keys:raise ValueError('No local source identities for conceptual figure '+identity)
        figures.append({'id':identity,'layout':'workflow','connect':connect,'nodes':nodes,
                        'after_heading':marker,'source_keys':keys,
                        'lead_in':'Figure~{FIG} summarizes the proposed framework and its scientific boundaries.',
                        'caption':caption+' Conceptual synthesis, not experimental observations. '})
    return figures
