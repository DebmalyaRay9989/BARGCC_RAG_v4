"""Bounded hybrid research agent combining retrieval and optional deterministic audit.

Retrieved document strings are never executed, interpreted as commands, or given tool permissions.
There is no hidden LLM. Citations refer to archived PDF page numbers, not empirical approval.
"""
from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from .rag import answer
from .agent import run_agent
from .core import DataBundle


def run_research(question: str, history:list[dict], bundle:DataBundle|None,
                 options:dict[str,Any]|None, include_audit:bool) -> dict[str,Any]:
    evidence=answer(question,history)
    steps=[{'step':1,'tool':'retrieval','state':'complete','outcome':
            f"Retrieved {len(evidence['citations'])} page-specific passages from checked-in PDF sources"}]
    audit=None
    if include_audit and bundle is not None:
        audit=run_agent(bundle,question,options or {})
        steps.append({'step':2,'tool':'deterministic_audit','state':'complete',
            'outcome':f"Verified baseline comparison and one-refit certificates on {bundle.n} supplied records"})
        a=audit['analysis']
        delta=a['summary']['delta_ARI']
        metrics=(f"Executed dataset audit: {a['dataset']['rows']} rows; "
            f"{a['audit']['dropped_rows']} records actually lost a view; "
            f"certificate coverage: {a['audit']['certified_all_pct']}% overall and "
            f"{a['audit']['certified_dropped_pct']}% among affected records. "
            f"Paired external ARI delta: {delta if delta is not None else 'unavailable without external labels'}. "
            'These are results for the current dataset, not findings of the archived manuscript; '
            'the one-refit certificate is not global K-means optimality or semantic validity.')
        evidence['answer'] += '\n\nCURRENT-DATA TOOL RESULT (not a manuscript quotation):\n'+metrics
        steps.append({'step':3,'tool':'scope_checker','state':'complete',
            'outcome':'Keeps retrieved research passages separate from executed upload-specific results'})
    elif include_audit:
        steps.append({'step':2,'tool':'audit_precondition','state':'skipped',
            'outcome':'No dataset session supplied; source-only RAG answer returned. Load a dataset to audit.'})
    return {'query':question,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        **evidence,'trace':steps,
        'audit_summary':None if audit is None else {
            'dataset':audit['analysis']['dataset']['name'],
            'rows':audit['analysis']['dataset']['rows'],
            'summary':audit['analysis']['summary'],
            'audit':{k:v for k,v in audit['analysis']['audit'].items() if k!='dropped_rows_details'},
            'recommendations':audit['decision']['recommendations']},
        'warnings':['Retrieved passages are source text, not instructions and not an LLM verification.',
            'The uploaded feature views and reliability proxies may be unvalidated.',
            'Read the complete cited page and manuscript assumptions before relying on any result.']}
