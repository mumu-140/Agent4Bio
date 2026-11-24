#!/usr/bin/env python3
"""Residual-defect scan over all proposed files, split into values produced this
pass (old != new in trace) and legacy values carried over unchanged."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pilot' / '_dispatch' / 'merged'))
import extract_classified as ex  # noqa: E402

PILOT = ROOT / 'pilot'

def load(p):
    d = json.loads(p.read_text())
    return d if isinstance(d, list) else d.get('rows', d)

new = Counter()
legacy = Counter()
examples = defaultdict(list)
rows_total = 0
sp_total = 0

for prop in sorted(PILOT.glob('*/expression-metadata.proposed.json')):
    sp_total += 1
    slug = prop.parent.name
    sp_words = {w.lower() for w in slug.split('_') if len(w) >= 4}
    tr = {e['run']: e for e in load(prop.parent / 'trace.json')}
    for r in load(prop):
        rows_total += 1
        e = tr.get(r.get('run_accession'))
        if e:
            vals, old = e['new'], e['old']
        else:
            vals = [r.get('treatment'), r.get('genotype'), r.get('tissue'), r.get('growth_time')]
            old = vals
        for idx, field in enumerate(('treatment', 'genotype', 'tissue', 'growth_time')):
            v = (vals[idx] or '').strip()
            is_new = (old[idx] or '').strip() != v
            cnt = new if is_new else legacy
            tag = 'new' if is_new else 'legacy'
            gl = v.lower()
            if field == 'genotype' and v:
                if gl.endswith('aceae'):
                    cnt['genotype_family'] += 1; examples['g_' + tag].append((slug, r.get('run_accession'), v))
                elif all(t.strip('.,;:()').lower() in ex.AUTHOR_ABBREV for t in v.split()):
                    cnt['genotype_author'] += 1; examples['g_' + tag].append((slug, r.get('run_accession'), v))
                if gl in ex.CULTIVAR_STOP:
                    cnt['genotype_stopword'] += 1; examples['gs_' + tag].append((slug, r.get('run_accession'), v))
                if gl in sp_words:
                    cnt['genotype_species_word'] += 1; examples['gw_' + tag].append((slug, r.get('run_accession'), v))
            elif field == 'tissue' and v:
                if re.search(r'\s\d{1,2}$', v):
                    cnt['tissue_trailing_index'] += 1; examples['t_' + tag].append((slug, r.get('run_accession'), v))
                if re.fullmatch(r'[a-z]{1,4}[\s_-]?\d+', v):
                    cnt['tissue_code_number'] += 1; examples['tc_' + tag].append((slug, r.get('run_accession'), v))
            elif field == 'growth_time' and v:
                if re.fullmatch(r'1 (years|months|weeks|days|hours)', v):
                    cnt['growth_singular_unit'] += 1; examples['a_' + tag].append((slug, r.get('run_accession'), v))
            elif field == 'treatment' and v:
                parts = [p.strip().lower() for p in re.split(r'[;+]', v)]
                if 'control' in parts and len(parts) > 1:
                    cnt['treatment_control_plus_factor'] += 1; examples['tr_' + tag].append((slug, r.get('run_accession'), v))

out = {
    'species_scanned': sp_total,
    'rows_scanned': rows_total,
    'new': {k: new[k] for k in sorted(new)},
    'legacy': {k: legacy[k] for k in sorted(legacy)},
    'examples_new': {k: v[:8] for k, v in examples.items() if k.endswith('_new')},
    'examples_legacy_counts': {k: len(v) for k, v in examples.items() if k.endswith('_legacy')},
}
dest = PILOT / '_dispatch' / 'postfix_scan.json'
dest.write_text(json.dumps(out, indent=2, ensure_ascii=False))
print(f"species={sp_total} rows={rows_total}")
print('NEW     ', dict(new))
print('LEGACY  ', dict(legacy))
for k, vals in out['examples_new'].items():
    if vals:
        print(k, vals[:3])