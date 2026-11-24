#!/usr/bin/env python3
"""协调人统一重跑：用合并版提取器对全部已派发物种重生成拟用文件，并落 pilot_verify 供机械校验。

只读 output/ 与 pilot/<slug>/evidence/，只写 pilot/<slug>/{expression-metadata.proposed.json,trace.json}
与 pilot_verify/<slug>/。不晋升、不动 output/。

用法：python3 run_final_extract.py [--slugs a,b] [--report PATH]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTOR = f'{ROOT}/pilot/extract_classified.py'


def assigned_species():
    out = []
    for a in 'abcd':
        p = f'{ROOT}/pilot/_dispatch/species_agent-{a}.txt'
        if os.path.exists(p):
            out += [l.strip() for l in open(p) if l.strip()]
    pilots = [d for d in sorted(os.listdir(f'{ROOT}/pilot'))
              if os.path.isdir(f'{ROOT}/pilot/{d}') and not d.startswith('_')
              and d not in set(out)]
    return out + pilots


def run_one(slug):
    rec = {'slug': slug}
    src = f'{ROOT}/output/{slug}/expression-metadata.json'
    ev = f'{ROOT}/pilot/{slug}/evidence'
    if not os.path.exists(src):
        rec['status'] = 'FAIL:no-output'
        return rec
    if not json.load(open(src))['rows']:
        # D4: a 0-row species needs no evidence pull; proposed == current, empty trace.
        os.makedirs(f'{ROOT}/pilot/{slug}', exist_ok=True)
        shutil.copy(src, f'{ROOT}/pilot/{slug}/expression-metadata.proposed.json')
        json.dump([], open(f'{ROOT}/pilot/{slug}/trace.json', 'w'))
        rec['rows'] = rec['trace'] = 0
    elif not os.path.isdir(ev):
        rec['status'] = 'FAIL:no-evidence'
        return rec
    else:
        for f in ('biosample_samn.json', 'experiments.tsv', 'ena_samples.tsv'):
            if not os.path.exists(f'{ev}/{f}'):
                rec['status'] = f'FAIL:evidence-missing-{f}'
                return rec
        r = subprocess.run([sys.executable, EXTRACTOR, slug], cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode != 0:
            rec['status'] = 'FAIL:extract'
            rec['err'] = r.stderr.strip()[-500:]
            return rec
        rec['extract'] = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ''

    vd = f'{ROOT}/pilot_verify/{slug}'
    os.makedirs(f'{vd}/source', exist_ok=True)
    shutil.copy(f'{ROOT}/pilot/{slug}/expression-metadata.proposed.json',
                f'{vd}/expression-metadata.json')
    ssrc = f'{ROOT}/output/{slug}/source/{slug}.tsv'
    if os.path.exists(ssrc):
        shutil.copy(ssrc, f'{vd}/source/{slug}.tsv')
    v = subprocess.run([sys.executable, f'{ROOT}/scripts/verify_metadata.py', slug,
                        '--dir', 'pilot_verify'], cwd=ROOT, capture_output=True, text=True)
    rec['verify'] = 'PASS' if v.returncode == 0 else 'FAIL'
    if v.returncode != 0:
        rec['verify_out'] = (v.stdout + v.stderr).strip()[-400:]
    try:
        rec['trace'] = len(json.load(open(f'{ROOT}/pilot/{slug}/trace.json')))
        rec['rows'] = len(json.load(
            open(f'{ROOT}/pilot/{slug}/expression-metadata.proposed.json'))['rows'])
    except Exception as e:
        rec['status'] = 'FAIL:outputs'
        rec['err'] = str(e)
        return rec
    rec['status'] = 'OK' if rec['verify'] == 'PASS' else 'FAIL:verify'
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slugs', help='只跑这些 slug（逗号分隔）')
    ap.add_argument('--report', default=f'{ROOT}/pilot/_dispatch/final_run_report.json')
    a = ap.parse_args()
    slugs = a.slugs.split(',') if a.slugs else assigned_species()
    recs = []
    for i, s in enumerate(slugs, 1):
        rec = run_one(s.strip())
        recs.append(rec)
        print(f"{i}/{len(slugs)} {rec['slug']} {rec['status']} "
              f"rows={rec.get('rows','-')} trace={rec.get('trace','-')}", flush=True)
    json.dump(recs, open(a.report, 'w'), indent=1, ensure_ascii=False)
    bad = [r for r in recs if r['status'] != 'OK']
    print('OK', len(recs) - len(bad), 'FAIL', len(bad), '| report', a.report)


if __name__ == '__main__':
    main()