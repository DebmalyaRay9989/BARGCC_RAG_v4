"""Bounded, deterministic, tool-using audit agent.

No claim of a generative LLM is made. Planning is explicit, transparent and
replayable. It can run multiple tool-equivalent analysis steps; it cannot
execute arbitrary code, browse private data, or mutate uploaded datasets.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any
from .core import DataBundle, analyze
from .llm import optional_explanation

SKILLS = {
    'profile': 'Inspect the schema, data coverage, score origin and limitations',
    'compare': 'Execute paired availability-only versus reliability-gated K-means',
    'certify': 'Stress-test single view removal and compute one-refit certificates',
    'assess': 'Evaluate evidence, recommend conservative deployment actions',
}

def select_tasks(query: str) -> list[str]:
    q=query.lower()
    tasks=['profile']
    if any(w in q for w in ['baseline','compare','performance','accuracy','cluster','gain','benchmark']):
        tasks.append('compare')
    if any(w in q for w in ['drop','view loss','view-loss','missing','certif','stabil','robust','audit','risk']):
        tasks.append('certify')
    if any(w in q for w in ['recommend','deploy','decision','safe','fallback','risk','audit','help','improve']):
        tasks.append('assess')
    if len(tasks)==1: tasks.extend(['compare','certify','assess'])
    else:
        # The analysis returns a paired run and audit together; expose both explicitly.
        if 'compare' not in tasks: tasks.insert(1,'compare')
        if 'certify' not in tasks: tasks.insert(2,'certify')
        if 'assess' not in tasks: tasks.append('assess')
    return tasks[:4]

def run_agent(bundle: DataBundle, query: str, config:dict[str,Any]) -> dict[str,Any]:
    query=re.sub(r'\s+', ' ', query or '').strip()[:500]
    if not query: query='Audit BARG-CC against an availability-only baseline, stress-test missing views, and recommend a safe next step'
    plan=select_tasks(query)
    result=analyze(bundle,**config)
    trace=[]
    now=datetime.now(timezone.utc).isoformat()
    for idx,step in enumerate(plan,1):
        if step=='profile':
            desc=f"Parsed {result['dataset']['rows']} rows × {len(result['dataset']['views'])} views; observed view entries: {result['dataset']['observed_pct']}%."
            evidence={'score_origin':result['dataset']['score_source'],'fingerprint':result['dataset']['fingerprint']}
        elif step=='compare':
            delta=result['summary']['delta_ARI']
            desc=('No labels available: ARI comparison withheld.' if delta is None else
                  f'Paired exploratory ARI difference (gated − baseline): {delta:+.5f}.')
            evidence={'baseline':result['summary']['baseline'],'gated':result['summary']['gated']}
        elif step=='certify':
            a=result['audit']
            desc=f"Audited {a['dropped_rows']} actual view losses; {a['certified_all_pct']}% overall certificate coverage; {a['certified_dropped_pct']}% among affected rows."
            evidence={'false_certificates':a['false_certificates'], 'scope':a['scope'],
                      'certificate_applicable':a['certificate_applicable']}
        else:
            desc=result['recommendation']
            evidence={'limitations':result['limitations'][:2], 'floor_enforced':result['config']['enforce_floor']}
        trace.append({'index':idx,'tool':step,'purpose':SKILLS[step],
                      'outcome':desc,'evidence':evidence,'state':'completed'})
    a=result['audit']
    recommendations=[result['recommendation']]
    if a['dropped_rows'] and (a['certified_dropped_pct'] or 0) < 50:
        recommendations.append('Escalate view-loss-affected rows for manual review: the sufficient certificate currently has low event-conditioned coverage.')
    if result['dataset']['has_external_labels'] is False:
        recommendations.append('Obtain a permitted, genuinely external validation label set before making any utility claim.')
    if not result['config']['enforce_floor']:
        recommendations.append('Review the strength setting against the participation-floor guarantee.')
    return {'query':query,'agent_kind':'Deterministic tool-orchestration agent (no LLM or external API)',
            'timestamp_utc':now,'plan':plan,'trace':trace,'decision':{'status':'REVIEW_REQUIRED',
              'recommendations':recommendations,'automatically_promoted':False},
            'analysis':result,'optional_llm':optional_explanation(query,result)}
