"""Citation-aware, no-fee RAG over the exact archived BARG-CC PDF sources.

Retrieval is SQLite FTS5/BM25 on a checked-in, page-indexed corpus; the answer
is an extractive synthesis assembled from retrieved text, not a generated claim.
It never interprets document content as instructions or lets retrieval invoke tools.
"""
from __future__ import annotations
import os
import re
from contextlib import closing
import sqlite3
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent.parent
DB=Path(__file__).resolve().parent/'knowledge'/'barg_sources.sqlite3'
STOP={'a','an','the','is','are','was','were','do','does','did','i','we','you','me','my','our','your','in','on','of',
      'to','for','at','with','by','from','how','what','why','when','where','who','and','or','but','can','could','would','should',
      'explain','describe','tell','about','based','using','paper','manuscript','this','that','these','those','it','be',
      'please','research','barg','cc','agent','agentic','give','show','find','which','there','its','than','does','into'}
EXPAND={'drop':['view','loss','mask'], 'dropout':['view','loss','mask'], 'certificate':['certify','stability'],
        'certification':['certificate','stability'], 'stable':['stability','assignment'],
        'baseline':['availability','clustering'], 'quality':['reliability','proxy'],
        'robustness':['perturbation','stability'], 'kappa':['gate','strength'],
        'rho':['floor','share'], '14':['refit','centroid'], '22':['loss','exact'],
        'limitations':['limitations','weaknesses'], 'accuracy':['ARI','NMI'],
        'neural':['ablation','contrastive'], 'mask':['missing','availability']}
MAX_MATCHES=5


def tokenize(query: str) -> list[str]:
    q=query.lower().replace('κ',' kappa ').replace('ρ',' rho ').replace('α',' alpha ')
    toks=[v for v in re.findall(r'[a-z0-9]{2,24}',q) if v not in STOP]
    uniq=[]
    for t in toks:
        if t not in uniq:uniq.append(t)
    return uniq[:12]


def _match_expr(q: str) -> str:
    toks=tokenize(q)
    if not toks and ('barg' in q.lower() or 'manuscript' in q.lower()):toks=['reliability','fusion','clustering']
    if not toks:return ''
    expanded=toks.copy()
    for t in toks:
        for e in EXPAND.get(t,[]):
            if e.lower() not in expanded: expanded.append(e.lower())
    # All tokens are normalized alphanumeric, so no FTS5 operators or injected syntax.
    return ' OR '.join('"'+t+'"' for t in expanded[:18])


def _conn():
    if not DB.is_file(): raise RuntimeError('Bundled knowledge index missing; see README_INDEX.md')
    # Read-only: no database writes, no mutable server-side knowledge store.
    con=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=5)
    con.row_factory=sqlite3.Row
    return con


def list_sources() -> list[dict[str,Any]]:
    with closing(_conn()) as con:
        rows=con.execute('SELECT doc_id,title,filename,pages FROM documents ORDER BY doc_id').fetchall()
    return [dict(r) for r in rows]


def _selected_excerpt(body: str, keywords:list[str], width:int=520) -> str:
    body=' '.join(body.split())
    if len(body)<=width:return body
    sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z(])',body)
    if len(sentences)<=1:
        at=next((m.start() for t in keywords if (m:=re.search(r'\b'+re.escape(t)+r'\b',body.lower()))),0)
        start=max(0,at-70)
        return ('…' if start else '')+body[start:start+width]+('…' if start+width<len(body) else '')
    weighted=[]
    for idx,s in enumerate(sentences):
        sl=s.lower()
        score=sum(2 for t in keywords if re.search(r'\b'+re.escape(t)+r'\b',sl))
        if re.search('not|however|only|conditional|none|no observed|limitation',sl):score+=0.25
        weighted.append((score,idx,s))
    weighted.sort(key=lambda a:(-a[0],a[1]))
    best=weighted[0][1]
    out=sentences[best]
    if (best+1<len(sentences) and len(out)+len(sentences[best+1])<width
            and re.search(r'[.!?)]$',sentences[best+1].strip())):
        out+=' '+sentences[best+1]
    if len(out)>width:
        trunc=out[:width]
        last=max(trunc.rfind('. '),trunc.rfind('! '),trunc.rfind('? '))
        out=trunc[:last+1] if last>110 else trunc.rsplit(' ',1)[0]+'…'
    return out.strip()


def search(question:str, *, limit:int=4, history:list[dict]|None=None) -> list[dict[str,Any]]:
    if not question or len(question)>1200: return []
    context=question
    # Context only for short follow-ups; do not index assistant-generated answers.
    if len(tokenize(question))<=2 and history:
        prior=[h.get('content','') for h in history[-4:] if h.get('role')=='user' and isinstance(h.get('content'),str)]
        if prior:context=prior[-1][:180]+' '+question
    expr=_match_expr(context)
    if not expr:return []
    keywords=tokenize(context)
    with closing(_conn()) as con:
        rows=con.execute('''SELECT c.id,c.doc_id,c.page,c.part,c.body,d.title,d.pages,
             bm25(chunks_fts) AS relevance
             FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid
             JOIN documents d ON d.doc_id=c.doc_id
             WHERE chunks_fts MATCH ? ORDER BY relevance LIMIT 60''',(expr,)).fetchall()
    scored=[]
    for r in rows:
        body=r['body'].lower()
        overlap=sum(t in body for t in keywords)
        if not overlap:continue
        # prioritize supporting multiple requested concepts while retaining BM25 ranking.
        coverage=overlap/max(1,len(keywords))
        number_bonus=0
        for p in re.findall(r'(?:proposition|eq(?:uation)?)[. ]*([0-9]{1,2})',context.lower()):
            if re.search(r'(?:proposition|eq(?:uation)?)[. ]*'+p+r'\b',body):number_bonus+=1.1
        scored.append((coverage*4+number_bonus+min(2.,max(0.,-float(r['relevance']))/6.),r))
    scored.sort(key=lambda v:-v[0])
    selected=[];seen_pages=set()
    for score,r in scored:
        key=(r['doc_id'],r['page'])
        if key in seen_pages and len(selected)<2:continue
        if key in seen_pages and len(selected)>=2:continue
        seen_pages.add(key)
        selected.append({'id':f"{r['doc_id'].upper()}-P{r['page']:03d}-C{r['part']:02d}",
            'doc_id':r['doc_id'],'title':r['title'],'page':r['page'],
            'part':r['part'],'source_ref':f"{r['title']}, PDF page {r['page']}",
            'excerpt':_selected_excerpt(r['body'],keywords),'score':round(score,3),
            'view_url':f"/api/source/{r['doc_id']}#page={r['page']}" if os.environ.get('BARG_PUBLIC_SOURCE_PDFS')=='1' else None})
        if len(selected)>=max(1,min(MAX_MATCHES,limit)):break
    return selected


def answer(question:str, history:list[dict]|None=None, limit:int=4) -> dict[str,Any]:
    hits=search(question,limit=limit,history=history)
    if not hits:
        return {'status':'INSUFFICIENT_EVIDENCE', 'answer':
            'I could not locate a sufficiently relevant passage in the two indexed BARG-CC documents. Try a specific proposition, equation, audit result, or section. No claim was inferred.',
            'citations':[],'mode':'extractive_citation_rag','generated_by_llm':False}
    # All factual content below is literally excerpted from the PDFs, with page refs.
    # Explicit formatting preserves provenance and avoids generative hallucinations.
    paragraphs=[f"[{i}] {h['excerpt']}" for i,h in enumerate(hits,1)]
    return {'status':'RETRIEVED',
        'answer':'Relevant passages from the indexed manuscript and supplement (extractive, not a new scientific conclusion):\n\n'+'\n\n'.join(paragraphs),
        'citations':[{'number':i,**h} for i,h in enumerate(hits,1)],
        'mode':'extractive_citation_rag','generated_by_llm':False}


def inspect_index() -> dict:
    with closing(_conn()) as con:
        total=con.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
        count=con.execute('SELECT doc_id,COUNT(*) n FROM chunks GROUP BY doc_id').fetchall()
    return {'ready':True,'documents':len(count),'chunks':total,'by_source':{r[0]:r[1] for r in count},
            'method':'offline PDF page extraction + SQLite FTS5 BM25; no vector model and no paid API'}
