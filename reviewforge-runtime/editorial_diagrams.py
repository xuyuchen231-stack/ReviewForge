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


def compact_figure_plan(tex,previous):
    """Merge owned framework illustrations; keep author analytic curves untouched."""
    import re
    from manuscript_integrity import bibkeys
    known=bibkeys(tex);old={f['id']:f for f in previous.get('figures',[])}
    groups=[('framework_abcd','overview','double',r'\subsection{Where learning enters the calculation}',
             ['learning_interfaces','learning_taxonomy','validation_claims','locked_validation','revision_ladder'],
             'An integrated model-revision framework. (a) Learned relations enter parameters, rates or the observation map. (b) Training, validation and independent testing are separated by a locked information boundary. (c) M0 is fixed; M1 refits selected parameters; M2 uses phase-specific parameters; M3 learns a process-term correction; M4 changes structure. Candidates share a comparison protocol, without assumed nesting. (d) Internal exchange is conservative. Conceptual synthesis.'),
            ('scale_single','scale','single',r'\subsection{Extrapolation, scale change and conservation constraints}',
             ['scale_transfer'],'Scale transfer requires matching the relevant transport, exposure and operating conditions. Schematic vessel sizes do not encode measured volume ratios.'),
            ('uncertainty_single','uncertainty','single',r'\subsection{Uncertainty: sources, propagation and calibration}',
             ['uncertainty_layers'],'Parameter, state, observation and input uncertainty remain distinct. Predictive intervals require held-out calibration; the interval shown is a conceptual symbol, not a numerical result.')]
    figures=[]
    for identity,diagram,span,heading,replaces,caption in groups:
        if heading not in tex:continue
        keys=set();leads=[]
        for old_id in replaces:
            spec=old.get(old_id,{})
            keys.update(k for k in spec.get('source_keys',[]) if k in known)
            if spec.get('lead_in'):leads.append(spec['lead_in'].replace('{FIG}',r'\ref{fig:rf-'+old_id+'}'))
            for match in re.finditer(r'\\begin\{figure\*?\}[\s\S]*?\\end\{figure\*?\}',tex):
                if '\\label{fig:rf-'+old_id+'}' in match.group(0):keys.update(citekeys(match.group(0)))
        if not keys:
            for preferred in ('vonstosch2014','psichogios1992','lemperle2026'):
                if preferred in known:keys.add(preferred)
        if not keys:raise ValueError('Existing scientific source identities required for diagram')
        figures.append({'id':identity,'layout':'research_diagram','diagram':diagram,'span':span,'after_heading':heading,
                        'source_keys':sorted(keys),'replaces':replaces,'superseded_lead_ins':leads,
                        'lead_in':{'overview':'Figure~{FIG} links learning location, validation and revision choice.','scale':'Figure~{FIG} identifies conditions to reconsider before scale transfer.','uncertainty':'Figure~{FIG} separates uncertainty sources from predictive-interval calibration.'}[diagram],'caption':caption+' '})
    return {'version':2,'kind':'integrated_abcd_with_single_column_companions','figures':figures}
