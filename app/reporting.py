"""Generate research-scoped audit reports as professionally formatted PDFs."""
from __future__ import annotations
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.units import mm

NAVY=colors.HexColor('#132138')
TEAL=colors.HexColor('#087f82')
LIGHT=colors.HexColor('#eef5f7')
SUB=colors.HexColor('#566980')

def esc(v):return escape(str(v if v is not None else 'N/A'))

def make_report(analysis:dict) -> bytes:
    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,
        topMargin=21*mm,bottomMargin=20*mm,title='BARG-CC Evidence-Constrained Audit',
        author='BARG-CC Agentic Research Lab')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle',parent=styles['Title'],fontName='Helvetica-Bold',
                fontSize=23,leading=27,textColor=NAVY,alignment=TA_LEFT,spaceAfter=9))
    styles.add(ParagraphStyle(name='ReportSubtitle',fontName='Helvetica',fontSize=10,
                leading=15,textColor=SUB,spaceAfter=16))
    styles.add(ParagraphStyle(name='ReportSection',fontName='Helvetica-Bold',fontSize=13,
                leading=18,textColor=NAVY,spaceBefore=17,spaceAfter=9))
    styles.add(ParagraphStyle(name='ReportBody',fontName='Helvetica',fontSize=9,
                leading=13.3,textColor=NAVY,spaceAfter=8))
    styles.add(ParagraphStyle(name='ReportSmall',fontName='Helvetica',fontSize=8,
                leading=12,textColor=SUB,spaceAfter=6))
    st=[]
    h=lambda t: st.append(Paragraph(esc(t),styles['ReportSection']))
    body=lambda t: st.append(Paragraph(esc(t),styles['ReportBody']))
    small=lambda t: st.append(Paragraph(esc(t),styles['ReportSmall']))
    st.append(Paragraph('BARG-CC / EVIDENCE AUDIT',styles['ReportTitle']))
    st.append(Paragraph('A scoped, reproducible report of reliability-gated multi-view clustering and one-refit stability certification. Analytical prototype; not an independent validation study.',styles['ReportSubtitle']))
    d=analysis['dataset'];c=analysis['config'];a=analysis['audit'];s=analysis['summary']
    h('1 / Dataset and parameters')
    rows=[['Field','Value'],['Dataset',d['name']],['Rows / view count',f"{d['rows']} / {len(d['views'])}"],
      ['View names',', '.join(d['views'])],['Data SHA-256 prefix',d['fingerprint']],
      ['External labels', 'Present (descriptive only)' if d['has_external_labels'] else 'Not supplied'],
      ['Gate setting',f"requested {c['requested_kappa']:.4f}; applied {c['applied_kappa']:.4f}"],
      ['Participation floor',f"{c['floor']*100:.1f}% ({'enforced' if c['enforce_floor'] else 'not enforced'})"],
      ['Dropout probability',f"{a['probability']*100:.1f}%"],['Random seed',str(c['seed'])]]
    make_table(st,rows,styles)
    h('2 / Paired exploratory clustering')
    rows=[['Metric','Availability-only (k=0)','Reliability gated'],
       ['ARI',val(s['baseline']['ARI']),val(s['gated']['ARI'])],
       ['NMI',val(s['baseline']['NMI']),val(s['gated']['NMI'])],
       ['Silhouette',val(s['baseline']['silhouette']),val(s['gated']['silhouette'])]]
    make_table(st,rows,styles,widths=[56*mm,56*mm,58*mm])
    body('External accuracy metrics use user-supplied labels only, if present. The same records and initialization seed are used for both conditions. This upload is transductive and supports no population-level inference.')
    h('3 / Conditional view-loss verification')
    rows=[['Event-conditioned metric','Value'],['Rows with an actual loss',str(a['dropped_rows'])],
      ['Sufficient certificate: all',pct(a['certified_all_pct'])],
      ['Sufficient certificate: affected',pct(a['certified_dropped_pct'])],
      ['Sufficient certificate: unaffected',pct(a['certified_retained_pct'])],
      ['Observed unchanged assignment: affected',pct(a['unchanged_dropped_pct'])],
      ['False certificates in this run',str(a['false_certificates'])],
      ['One-refit precondition checked','YES' if a['certificate_applicable'] else 'NO'],
      ['Exact dropout identity checked','PASS']]
    make_table(st,rows,styles)
    body('The certificate covers nearest-centroid assignment after ONE membership-preserving centroid refit. It does not establish a unique globally optimal partition, iterative training stability, calibrated reliability, or semantic correctness.')
    h('4 / Evidence-constrained recommendation')
    body(analysis['recommendation'])
    for warning in analysis['warnings']:small('Warning: '+warning)
    h('5 / Assumptions and limitations')
    for note in analysis['limitations']:small('- '+note)
    h('6 / Reproducibility and provenance')
    body('Equations implemented: gate Eq. (2), exact view-loss identity Eq. (22), one-centroid-refit certificate Eq. (24), as identified in the user-provided November 2026 BARG-CC IJSS manuscript.')
    body('Input transformations: '+d['preprocessing'])
    body('Reliability origin: '+d['score_source'])
    small('Report auto-generated by BARG-CC Agentic Research Lab. Human scientific interpretation and independent validation remain necessary. This is not a journal submission or empirical confirmation of published claims.')
    def page_number(c, doc):
        c.saveState();c.setFillColor(SUB);c.setFont('Helvetica',8)
        c.drawString(20*mm,12*mm,'BARG-CC / numerical assurance research')
        c.drawRightString(190*mm,12*mm,f'PAGE {doc.page}')
        c.restoreState()
    doc.build(st,onFirstPage=page_number,onLaterPages=page_number)
    return buf.getvalue()


def val(x):return 'Not available' if x is None else f'{x:.5f}'
def pct(x):return 'Not applicable' if x is None else f'{x:.2f}%'

def make_table(st, rows, styles, widths=None):
    cells=[[Paragraph(esc(v),styles['ReportSmall']) for v in row] for row in rows]
    t=Table(cells,colWidths=widths or [57*mm,113*mm],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
       ('BACKGROUND',(0,0),(-1,0),LIGHT),('TEXTCOLOR',(0,0),(-1,0),NAVY),
       ('LINEBELOW',(0,0),(-1,0),.7,TEAL),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#dce6ef')),
       ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),
       ('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)
    ]))
    st.append(t)
