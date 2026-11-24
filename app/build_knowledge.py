"""Offline PDF-to-SQLite FTS5 index builder.

This is a maintainer-side tool, not run on the memory-limited web service.
Install: pip install pymupdf; run: python -m app.build_knowledge
No OCR, embeddings, network access, or generative rewriting is performed.
"""
from __future__ import annotations
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    ('main', 'BARG-CC IJSS main manuscript (corrected, 2026)', ROOT/'knowledge_sources'/'main.pdf'),
    ('supp', 'BARG-CC IJSS supplementary material (corrected, 2026)', ROOT/'knowledge_sources'/'supplement.pdf'),
]
DB = ROOT/'app'/'knowledge'/'barg_sources.sqlite3'

def clean_page(text: str) -> str:
    """Remove running headers and line-number gutters without editing findings."""
    lines=[]
    for line in text.replace('\u00ad','').replace('\u200b','').splitlines():
        s=line.strip()
        if not s: lines.append('');continue
        if re.match(r'^BARG-CC / International Journal of Systems Science submission',s):continue
        if re.fullmatch(r'\d{1,4}',s):continue
        # Original main manuscript has sequential line-number labels.
        s=re.sub(r'^\d{1,4}\s+(?=[A-Za-z(])','',s)
        lines.append(s)
    out='\n'.join(lines)
    out=re.sub(r'(?<=\w)-\n(?=\w)','',out)
    return out

def paragraph_chunks(text: str, target: int=760, maximum: int=1200) -> list[str]:
    # Keep a page's text on its own page; do not cross page boundaries.
    text=re.sub(r'\n{3,}','\n\n',text)
    blocks=[re.sub(r'\s+',' ',p).strip() for p in re.split(r'\n\s*\n',text) if p.strip()]
    if len(blocks)<3:
        blocks=[re.sub(r'\s+',' ',p).strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-Z])',text) if p.strip()]
    chunks=[];curr=''
    for block in blocks:
        if len(block)>maximum:
            pieces=re.split(r'(?<=[.!?;])\s+',block)
            if len(pieces)==1:
                pieces=[block[i:i+maximum] for i in range(0,len(block),maximum)]
        else: pieces=[block]
        for piece in pieces:
            if curr and len(curr)+len(piece)+1>target:
                chunks.append(curr.strip()); curr=''
            if len(piece)>maximum:
                for k in range(0,len(piece),maximum):chunks.append(piece[k:k+maximum])
            else: curr=(curr+' '+piece).strip()
    if curr:chunks.append(curr)
    return [c for c in chunks if len(c)>=65]

def build():
    import fitz
    DB.parent.mkdir(parents=True,exist_ok=True)
    if DB.exists(): DB.unlink()
    con=sqlite3.connect(DB)
    con.executescript('''
    PRAGMA journal_mode=DELETE;
    CREATE TABLE documents(doc_id TEXT PRIMARY KEY, title TEXT NOT NULL, filename TEXT NOT NULL, pages INTEGER NOT NULL);
    CREATE TABLE chunks(id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT NOT NULL, page INTEGER NOT NULL, part INTEGER NOT NULL, body TEXT NOT NULL,
      FOREIGN KEY(doc_id) REFERENCES documents(doc_id));
    CREATE VIRTUAL TABLE chunks_fts USING fts5(body, content='chunks', content_rowid='id', tokenize='unicode61 remove_diacritics 2');
    CREATE INDEX chunk_document_page ON chunks(doc_id,page);
    ''')
    counts={}
    for doc_id,title,pdf_path in SOURCES:
        if not pdf_path.exists():raise FileNotFoundError(f'Cannot index missing source: {pdf_path}')
        pdf=fitz.open(pdf_path)
        con.execute('INSERT INTO documents VALUES (?,?,?,?)',(doc_id,title,pdf_path.name,len(pdf)))
        n=0
        for page_no,page in enumerate(pdf,1):
            body=clean_page(page.get_text(sort=True))
            for part,chunk in enumerate(paragraph_chunks(body),1):
                con.execute('INSERT INTO chunks(doc_id,page,part,body) VALUES (?,?,?,?)',(doc_id,page_no,part,chunk));n+=1
        counts[doc_id]=n
    con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    con.execute('PRAGMA optimize')
    con.commit(); con.close()
    print('Built',DB,counts,DB.stat().st_size,'bytes')

if __name__=='__main__': build()
