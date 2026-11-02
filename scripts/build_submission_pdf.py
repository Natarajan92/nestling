"""Build the submission from saved v3 evidence, without runtime imports/calls.

uv pip install --target .superpowers/sdd/tools/pdf reportlab pymupdf
uv run --no-sync python scripts/build_submission_pdf.py
Rerun after final round decisions and canonical docs/week4_report.md regeneration.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.superpowers/sdd/tools/pdf'))
from scripts.package_submission import complete_rounds, selected_round  # noqa: E402
import pymupdf  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from reportlab.platypus import Paragraph, Table, TableStyle  # noqa: E402

RESULTS = ROOT / 'evals/results/golden_v3'
GITHUB = 'https://github.com/Natarajan92/nestling'
CREAM, INK, SAGE, MUTED = '#FFF8F1', '#2E2A3A', '#789780', '#626474'
PEACH, LIGHT, RED, GOLD = '#F2B99D', '#E7EDE4', '#A04F4F', '#B28D45'
W, H = A4
M, CONTENT = 44, W - 88
INPUTS: dict[str, dict] = {}


def read(path: Path):
    data = path.read_bytes()
    INPUTS[path.relative_to(ROOT).as_posix()] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return data


def js(path):
    return json.loads(read(path).decode('utf-8-sig'))


def csv_rows(path):
    return list(csv.DictReader(io.StringIO(read(path).decode('utf-8-sig'))))


def pct(x):
    return f'{100*x:.1f}%'


def round_label(name):
    return 'Baseline' if name == 'baseline' else name.replace('round', 'Round ').replace('latency', 'Latency ')


def yes(value):
    return str(value).lower() == 'true'


def fraction(rows, field):
    valid = [r for r in rows if str(r.get(field, '')).lower() in ('true', 'false') and not r.get('judge_error')]
    return sum(yes(r[field]) for r in valid), len(valid)


def paired(before, after, field):
    a = {r['case_id']: r for r in before}
    pairs = [(a[r['case_id']], r) for r in after if r['case_id'] in a and
             all(str(v.get(field, '')).lower() in ('true', 'false') and not v.get('judge_error') for v in (a[r['case_id']], r))]
    return sum(yes(a[field]) for a, b in pairs), sum(yes(b[field]) for a, b in pairs), len(pairs)


def load_evidence():
    report = read(ROOT / 'docs/week4_report.md').decode('utf-8-sig')
    freeze = js(ROOT / 'evals/golden_v3.freeze.json')
    selector = js(ROOT / 'evals/golden_v3.submission40.json')
    golden = read(ROOT / 'evals/golden_v3.csv').decode('utf-8-sig').replace('\r\n', '\n')
    assert hashlib.sha256(golden.encode()).hexdigest() == freeze['normalized_sha256']
    rounds = {}
    for name in complete_rounds():
        folder = RESULTS / name
        plan = js(folder / 'plan.json') if (folder / 'plan.json').exists() else {}
        if not (folder / 'summary.json').exists(): continue
        summary = js(folder / 'summary.json')
        if not summary['progress']['complete']: continue
        rows = csv_rows(folder / 'cases.csv')
        assert len(rows) == summary['progress']['n_expected'] == 62
        assert len({r['case_id'] for r in rows}) == 62
        assert summary['run']['dataset_hash'] == freeze['normalized_sha256']
        decision = js(folder / 'decision.json') if (folder / 'decision.json').exists() else {}
        rounds[name] = {'summary': summary, 'rows': rows, 'decision': decision, 'plan': plan}
    assert 'baseline' in rounds and 'round1' in rounds and 'round2' in rounds
    selected = selected_round(rounds)
    diagnosis = js(RESULTS / 'round1/diagnosis.json')
    human = csv_rows(RESULTS / 'human_review.csv')
    spend = js(RESULTS / 'spend.json')
    latency_budget = RESULTS / 'latency_budget'
    if (latency_budget / 'authorization.json').exists():
        js(latency_budget / 'authorization.json')
    if (latency_budget / 'spend.json').exists():
        spend = {'original': spend, 'latency': js(latency_budget / 'spend.json')}
    js(RESULTS / 'pricing.json')
    return report, freeze, selector, rounds, selected, diagnosis, human, spend


def clean(text):
    return str(text).replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2192', '-&gt;')


class Document:
    def __init__(self, output, pages):
        for name, file in [('Inter', 'Inter.ttf'), ('Fraunces', 'Fraunces.ttf')]:
            pdfmetrics.registerFont(TTFont(name, str(ROOT / 'assets/fonts' / file)))
        self.c = canvas.Canvas(str(output), pagesize=A4, pageCompression=1)
        self.c.setTitle('Nestling | Week 4 submission | frozen golden v3')
        self.c.setAuthor('S Anand Natarajan')
        self.page = 0
        self.pages = pages
        self.lowest = H

    def start(self, number, label, title, subtitle):
        if self.page: self.c.showPage()
        self.page = number
        c = self.c
        c.setFillColor(colors.HexColor(CREAM)); c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFillColor(colors.HexColor(SAGE)); c.rect(0, H - 12, W, 12, fill=1, stroke=0)
        self.text('NESTLING  /  WEEK 4', M, 37, 9, SAGE)
        self.text(f'{number:02d}  {label.upper()}', W - 188, 37, 8, MUTED)
        title_end = self.par(title.replace('\n', '<br/>'), M, 65, CONTENT, 25, 'Fraunces', 28)
        assert title_end <= 122, 'Title must fit the two-line page header'
        subtitle_end = self.par(subtitle, M, 130, CONTENT, 9.5, 'Inter', 13, MUTED)
        assert subtitle_end <= 158, 'Subtitle must fit before page content'
        c.setStrokeColor(colors.HexColor('#DFD8D0')); c.line(M, 43, W-M, 43)
        self.text('2 November 2026  |  Frozen v3 evidence', M, H-29, 8, MUTED)
        self.text(f'{number} / {self.pages}', W-M-26, H-29, 8, MUTED)

    def text(self, text, x, top, size=10, color=INK, font='Inter'):
        self.c.setFont(font, size); self.c.setFillColor(colors.HexColor(color))
        self.c.drawString(x, H-top-size, clean(text).replace('-&gt;', '->'))

    def par(self, text, x, top, width=CONTENT, size=10, font='Inter', leading=None, color=INK):
        style = ParagraphStyle('body', fontName=font, fontSize=size, leading=leading or size*1.5,
                               textColor=colors.HexColor(color), alignment=TA_LEFT)
        p = Paragraph(clean(text), style)
        _, height = p.wrap(width, H)
        assert top + height <= H-58, f'Page {self.page} overflow at {top+height}: {text[:100]}'
        p.drawOn(self.c, x, H-top-height)
        self.lowest = min(self.lowest, H-top-height)
        return top+height

    def section(self, title, top):
        self.text(title.upper(), M, top, 9, SAGE)
        return top + 25

    def panel(self, title, body, top, height=90, fill=LIGHT):
        self.c.setFillColor(colors.HexColor(fill)); self.c.roundRect(M, H-top-height, CONTENT, height, 12, fill=1, stroke=0)
        self.par(title, M+17, top+14, CONTENT-34, 14, 'Fraunces', 18)
        end = self.par(body, M+17, top+39, CONTENT-34, 9.5, leading=14)
        assert end <= top+height-10, 'Panel overflow'

    def table(self, rows, top, widths=None, small=8.5):
        style = ParagraphStyle('cell', fontName='Inter', fontSize=small, leading=small*1.4, textColor=colors.HexColor(INK))
        cells = [[Paragraph(clean(escape(str(v))), style) for v in row] for row in rows]
        table = Table(cells, colWidths=widths or [CONTENT/len(rows[0])]*len(rows[0]))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(LIGHT)),
            ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING',(0,0),(-1,-1),8),
            ('RIGHTPADDING',(0,0),(-1,-1),8), ('TOPPADDING',(0,0),(-1,-1),8),
            ('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LINEBELOW',(0,0),(-1,-1),.35,colors.HexColor('#DED8CF'))]))
        _, height = table.wrap(CONTENT,H)
        assert top+height < H-58, f'Table overflow page {self.page}'
        table.drawOn(self.c,M,H-top-height)
        return top+height

    def link(self, label, url, top, x=M, width=CONTENT):
        return self.par(f'<link href="{escape(url, quote=True)}" color="{SAGE}"><u>{escape(label)}</u></link>',x,top,width,9,leading=14)


def metric(summary, key):
    return summary['metrics'][key]['value']


def speed_chart(d, rounds, top):
    c=d.c; names=list(rounds); chartw=(CONTENT-35)/2; maxlat=max(metric(r['summary'],'p95_latency_s') for r in rounds.values())*1.15
    rowh = min(31, 124 / len(names))
    for col,(key,title,limit,maxval) in enumerate([('p95_latency_s','p95 pipeline latency (seconds)',8,maxlat),('mean_cost_inr','Mean pipeline cost (INR)',2,2.2)]):
        x=M+col*(chartw+35); d.text(title,x,top,9)
        bx=x+50; bw=chartw-65
        for i,name in enumerate(names):
            y=top+31+i*rowh; value=metric(rounds[name]['summary'],key)
            d.text(round_label(name),x,y,8)
            rejected=rounds[name]['decision'].get('decision')=='reject'
            c.setFillColor(colors.HexColor(RED if rejected else SAGE)); c.roundRect(bx,H-y-11,bw*value/maxval,12,3,fill=1,stroke=0)
            d.text(f'{value:.2f}' if key=='p95_latency_s' else f'{value:.3f}',bx+bw*value/maxval+4,y,8)
        c.setStrokeColor(colors.HexColor(GOLD)); c.setDash(3,2); xx=bx+bw*limit/maxval
        c.line(xx,H-top-20,xx,H-top-28-len(names)*rowh); c.setDash()
        d.text(f'Target <{limit}',x,top+37+len(names)*rowh,8,GOLD)


def build(output, render_dir):
    report, freeze, selector, rounds, selected, diagnosis, human, spend = load_evidence()
    selected_data=rounds[selected]; selected_summary=selected_data['summary']; base=rounds['baseline']
    output.parent.mkdir(parents=True,exist_ok=True); render_dir.mkdir(parents=True,exist_ok=True)
    candidates = [name for name in rounds if name != 'baseline']
    decision_groups = [candidates[i:i+3] for i in range(0, len(candidates), 3)]
    pages = 6 + len(decision_groups)
    d=Document(output, pages)
    status=f'Retained candidate: {round_label(selected)}. {len(rounds)} completed measurements; saved keep/reject decisions control selection.'
    d.start(1,'Submission overview','From bump to baby.\nEvery answer, sourced.','S Anand Natarajan  /  Mastering Agentic AI  /  Week 4 evaluation')
    # A deliberate, spacious cover with an outcome-led evidence summary.
    d.panel('A calm companion with inspectable safeguards',
        'Nestling helps first-time parents in India find sourced guidance, practical preparation and reviewed Little Lessons. '
        'Code owns danger-sign escalation; no diagnoses or medicine doses are permitted.',173,107)
    top=d.section('The result to assess',310)
    status_end=d.par(status,M,top,size=13,font='Fraunces',leading=19)
    f,n=fraction(selected_data['rows'],'faithful'); tf,tn=fraction(selected_data['rows'],'task_fulfilled')
    esc=selected_summary['metrics']['escalation_recall']
    refusal=selected_summary['metrics']['refusal_accuracy']
    routing=selected_summary['metrics']['routing_accuracy']
    top=d.table([['Full 62-case measure',round_label(selected),'Target'],
        ['Escalation / refusal',f"{round(esc['value']*esc['n'])}/{esc['n']}; {round(refusal['value']*refusal['n'])}/{refusal['n']}",'100% / 100%'],
        ['Routing',f"{round(routing['value']*routing['n'])}/{routing['n']} = {pct(routing['value'])}",'>=90%'],
        ['Faithfulness',f'{f}/{n} valid = {pct(f/n)}','>=90%'],
        ['Task fulfillment',f'{tf}/{tn} = {pct(tf/tn)}','Reported'],
        ['p95 response time',f"{metric(selected_summary,'p95_latency_s'):.2f} seconds",'<8 seconds'],
        ['Mean pipeline cost',f"INR {metric(selected_summary,'mean_cost_inr'):.3f}",'<INR 2']],status_end+16,[210,176,CONTENT-386])
    eligible=selected_summary['judging']['n_faithfulness_eligible']
    zero=selected_summary['judging']['n_zero_claim']
    d.par(f'Faithfulness has {n} valid judgments from {eligible} eligible replies; {zero} have zero claims. '
          'This is a quality tradeoff, not an all-pass claim. Inspect latency, paired denominators, abstentions and rejected rounds.',M,top+19,size=9.5,color=MUTED)
    d.link('Canonical report and complete evidence',f'{GITHUB}/blob/main/docs/week4_report.md',690)
    d.par('Owner review target: 2 November, 10:00 AM IST. Official submission target: 2 November, 12:00 PM IST. Loom and human calibration remain explicit pending deliverables.',M,718,size=9,color=MUTED)

    d.start(2,'Methods','One frozen set.\nTwo views of the evidence.','All 62 cases form the regression gate. The 40-case view is a presentation, not a new active dataset.')
    d.panel('Owner-attested authorship and review','The owner identifies all 62 shortlisted questions as their own and reviewed. This is human-authorship self-attestation, not an independent provenance audit. Questions, contexts and expected labels stay unchanged.',163,98)
    t=d.table([['View','Happy','Edge','Known-fail','Adversarial','Total'],['Full regression',20,26,12,4,62],['Submission view',20,12,6,2,40]],286,[147,64,64,82,86,CONTENT-443])
    t=d.section('How results are scored',t+29)
    t=d.par('Code measures escalation/refusal, allowed-route membership, source-ID match, nearest-rank p95 latency and token cost. Runtime DeepSeek verification checks support before returning an answer. The separate cross-family Qwen judge evaluates saved passages after the response.',M,t)
    t=d.par('Faithfulness requires all extracted factual claims to be supported. Errors and zero-claim answers do not earn an automatic pass. Task fulfillment separately checks expected behavior, required content and avoidance constraints. Neither score is clinical validation.',M,t+15)
    t=d.par('Compare only the same IDs with valid judgments in both rounds; show a second calculation with errors/nulls as false. A changing eligible denominator or more safe abstention can inflate an unpaired headline.',M,t+15)
    t=d.par('The 40-case presentation chooses lexicographically first IDs per stratum without scores. It was defined after baseline and before first improvement: retrospective, previously exposed, not preregistered or an unseen holdout. All 62 cases and failures remain the gate.',M,t+15)
    d.link('Frozen questions, review record and selector',f'{GITHUB}/tree/main/evals',t+24)
    d.par('Normalized frozen SHA256<br/>'+freeze['normalized_sha256'],M,714,size=7.5,leading=11,color=MUTED)

    d.start(3,'Trace-led diagnosis','H07: a citation bug\nbecame an evidence bug.','Question: "Which iron-rich foods can I eat as a vegetarian?"  /  Pregnancy, week 24')
    d.panel('Before: one suffix match changed the evidence path',
        'A regex could match NIN-DG inside the valid source ID ICMR-NIN-DG. The raw specialist cited ICMR and WHO; seven ICMR markers were truncated during processing.',167,97, '#F7E4DA')
    t=d.section('Observed causal chain',296)
    for number,title,body in [
        ('01','Canonical citation damaged','ICMR-NIN-DG was transformed despite already being valid. This was reproduced by deterministic regression tests.'),
        ('02','Evidence pruned before verification','The actual verifier input retained WHO-ANC alone; the ICMR passages used by the specialist were lost.'),
        ('03','Useful answer replaced','The verifier found six unsupported claims against its reduced evidence and returned the no-trusted-source fallback.')]:
        d.text(number,M,t,22,SAGE,'Fraunces'); d.par(title,M+48,t,CONTENT-48,13,'Fraunces',17)
        end=d.par(body,M+48,t+25,CONTENT-48,9.5,leading=14);t=end+25
    d.panel('Round 1: one boundary repair','Exclude a preceding hyphen when matching a bare source-ID suffix. Preserve complete canonical IDs and their passages. Models, sources, judge and safety rules stayed fixed. The saved measured decision retains this repair.',t+2,105)
    d.link('Inspect the actual H07 root and its specialist/verifier children',diagnosis['root_trace_url'],t+124)
    d.link('Saved diagnosis and evidence record',f'{GITHUB}/blob/main/evals/results/golden_v3/round1/diagnosis.json',t+146)
    d.par('No private source passages are reproduced here. A citation-format check verifies whole IDs; it does not establish claim support by itself.',M,730,size=9,color=MUTED)

    d.start(4,'Measured iterations','Keep useful changes.\nPreserve rejected results.','Every completed round uses the same 62 IDs, fixed labels and cross-family judge.')
    table=[['Round / decision','Faithful: valid n','Task: valid n','p95 s','Mean INR']]
    for name,r in rounds.items():
        ff,fn=fraction(r['rows'],'faithful');tt,tnt=fraction(r['rows'],'task_fulfilled')
        table.append([round_label(name)+' / '+r['decision'].get('decision','reference' if name=='baseline' else 'pending'),f'{ff}/{fn}',f'{tt}/{tnt}',f"{metric(r['summary'],'p95_latency_s'):.2f}",f"{metric(r['summary'],'mean_cost_inr'):.3f}"])
    t=d.table(table,163,[143,108,104,66,CONTENT-421])
    t=d.section('Paired source faithfulness',t+23)
    pairs=[['Comparison base / candidate','Base faithful','Candidate faithful','Shared valid n']]
    for name in candidates:
        data=rounds[name]
        comparison=data['decision'].get('comparison_base') or data['plan'].get('comparison_base') or ('baseline' if name=='round1' else 'round1')
        a,b,n=paired(rounds[comparison]['rows'],data['rows'],'faithful')
        pairs.append([f'{round_label(comparison)} / {round_label(name)}',a,b,n])
    t=d.table(pairs,t,[196,100,112,CONTENT-408],8)
    d.par('Each pair uses the same IDs with valid judgments in both runs. Unpaired fractions above can have different denominators. Neither view establishes unseen-case generalization. Saved decisions also disclose error sensitivity, abstentions and useful-answer coverage.',M,t+18,size=9,leading=14,color=MUTED)

    for offset,group in enumerate(decision_groups):
        d.start(5+offset,'Saved decisions','Measured changes.\nExplicit decisions.','Plans and negative results remain attached to their original measurements.')
        t=169
        for name in group:
            data=rounds[name]
            t=d.section(f"{round_label(name)} / {data['decision'].get('decision', 'pending')}",t)
            lever=data['plan'].get('lever', 'Citation boundary repair preserving full registered source IDs and verifier evidence.')
            t=d.par(escape(lever),M,t,size=9.5,leading=14)
            reason=data['decision'].get('reason', 'Completed measurement; decision pending. This candidate is not selected.')
            t=d.par(escape(reason),M,t+10,size=9.5,leading=14)
            t=d.link('Saved plan, scores, decision and trace links',f'{GITHUB}/tree/main/evals/results/golden_v3/{name}',t+10)+30

    d.start(5+len(decision_groups),'Tradeoffs and failure impact','Faster is useful.\nIncomplete is still incomplete.','Pipeline latency excludes offline judging. INR amounts describe observed spend, not harm or avoided losses.')
    speed_chart(d,rounds,168)
    t=349
    if 'original' in spend:
        old,new=spend['original'],spend['latency']
        accounting=(f"Original ledger: INR {old['accounted_inr']:.4f} / {old['cap_inr']:.0f}. Separate owner-approved latency ledger: "
                    f"INR {new['accounted_inr']:.4f} / {new['cap_inr']:.0f}; {len(new.get('pending', {}))} pending reservations. "
                    f"Combined accounted: INR {old['accounted_inr']+new['accounted_inr']:.4f}. Probe, judging and failed/unknown attempts are included.")
    else:
        accounting=f"Original shared request ledger: INR {spend['accounted_inr']:.4f} / {spend['cap_inr']:.2f}."
    d.par(accounting+' Nebius token estimates exclude hosting and Pinecone charges. Pipeline averages exclude offline judging and discarded attempts.',M,t+10,size=8.5,leading=12)
    t=d.section('Top overlapping baseline failures',t+83)
    modes=[('task incomplete','Request remains partly unanswered'),('expected-source mismatch','Expected reference trail is absent'),('unsupported claims','A factual assertion lacks supplied evidence')]
    failures=[]
    for mode,impact in modes:
        pattern=r'\|\s*'+re.escape(mode)+r'\s*\|\s*(\d+)\s*\|\s*([\d.]+)'
        match=re.search(pattern,report); assert match, f'Canonical report missing failure cluster {mode}'
        failures.append([mode,match[1],f'INR {match[2]}',impact])
    t=d.table([['Cluster','Cases','Pipeline spend','Parent impact (qualitative)']]+failures,t,[131,47,105,CONTENT-283],8.5)
    t=d.par('Clusters overlap; do not add counts or INR. Source mismatch is not proof that a cited source is clinically wrong. These are diagnostics, not measured patient outcomes. INR uses the fixed 94.91 conversion estimate, not current FX or a reconciled invoice.',M,t+17,size=9,color=MUTED)
    t=d.section('Outstanding constraints',t+27)
    constraints_end=d.par('B11 expects USER-POLICY although no policy was uploaded. E09 permits either route while its expected behavior asks for both topics. Keep frozen expectations intact and report these limitations. Future corrections need a separately versioned set.',M,t,size=9.5)
    d.link('All rounds, raw saved answers, decisions and trace links',f'{GITHUB}/tree/main/evals/results/golden_v3',max(721,constraints_end+15))

    d.start(pages,'Review and reproducibility','Ready for review.\nClear about what remains.','This packet is evidence for assessment, not a clinical-validation or award guarantee.')
    hfaith=sum(r.get('human_faithful','').strip().upper() in ('Y','N') for r in human)
    htask=sum(r.get('human_task_fulfilled','').strip().upper() in ('Y','N') for r in human)
    d.panel('Human calibration and Loom',f'Faithfulness labels: {hfaith}/{len(human)}. Task labels: {htask}/{len(human)}. '
        'Agreement is undefined until actual human labels are entered. Reviewing expected answers and approving lesson scenes do not label model answers. Loom: pending owner recording/link.',165,111)
    t=d.section('Safety, privacy and operational scope',301)
    t=d.par('Code owns escalation; medical/diet/insurance answers require a registered source or explicit abstention. Twelve lesson versions have human scene review; approval is exact-version and media-gated. A model fidelity verdict cannot approve content.',M,t,size=9.5)
    t=d.par('Personal profiles, journal and checklist stay in browser keys prefixed nestling:. Uploaded policy/audio is processed in memory. App traces hide inputs/outputs and sanitize exceptions; authorized benchmark traces retain fixed case evidence. No personal source documents are attached to this PDF.',M,t+14,size=9.5)
    t=d.par('Local demo: web http://localhost:3000 and API http://localhost:8010. No public live-demo URL is claimed. Media renders are gitignored; deployment needs approved persistent/repeatable media provisioning. Physical-device microphone/native sharing remains unverified.',M,t+14,size=9.5)
    t=d.section('Evidence you can open',t+28)
    for label,url in [('Repository and runnable source',GITHUB),('Canonical score report',f'{GITHUB}/blob/main/docs/week4_report.md'),
        ('Detailed v3 measurements and iteration decisions',f'{GITHUB}/blob/main/docs/v3_evaluation_report.md'),
        ('Actual H07 LangSmith trace',diagnosis['root_trace_url']),('20-answer human calibration CSV',f'{GITHUB}/blob/main/evals/results/golden_v3/human_review.csv')]:
        t=d.link(label,url,t)+6
    d.par('Reproduce: uv run --no-sync python scripts/build_submission_pdf.py<br/>The PDF embeds input-provenance.json with exact source-file SHA256 hashes. All pages are rendered and checked locally. Regenerate after any evidence or report change.',M,t+14,size=8.5,leading=12,color=MUTED)
    d.c.save()
    provenance={'built_at_utc':datetime.now(timezone.utc).isoformat(),'selected_retained_round':selected,
                'completed_rounds':list(rounds),'inputs':INPUTS,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'method':'saved complete v3 summaries/cases/decisions; canonical report failure clusters; no inference or private source excerpts'}
    doc=pymupdf.open(output)
    doc.embfile_add('input-provenance.json',json.dumps(provenance,indent=2).encode(),desc='Reproducible input SHA256 manifest')
    doc.saveIncr()
    assert len(doc)==pages
    alltext='\n'.join(p.get_text() for p in doc)
    for expected in ('0/20' if not hfaith else f'{hfaith}/20','Round 2','62','40',round_label(selected),'H07'):
        assert expected in alltext, f'PDF extraction missing {expected}'
    for i,page in enumerate(doc):
        assert page.get_text().strip(), f'Empty PDF page {i+1}'
        for block in page.get_text('blocks'):
            assert block[0]>=-1 and block[1]>=-1 and block[2]<=W+1 and block[3]<=H+1, f'Text outside page {i+1}'
        page.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(render_dir/f'page-{i+1}.png')
    provenance['pdf_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    provenance['pages']=pages
    (render_dir/'input-provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    output.with_suffix('.provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(json.dumps({'pdf':str(output),'pages':len(doc),'selected':selected,'completed_rounds':list(rounds),'render_dir':str(render_dir),'inputs_hashed':len(INPUTS)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output/pdf/Nestling_Week4_Submission.pdf')
    parser.add_argument('--render-dir',type=Path,default=ROOT/'.superpowers/sdd/plan/pdf-review')
    args=parser.parse_args()
    build(args.output,args.render_dir)
