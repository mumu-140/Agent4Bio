"""Validate the proposed JSON for one species against the user's reference table.
Rules (factor-level, documented): tissue normalised (lower/singular/strip replicate
suffix; long values collapse to the longest known organ phrase); treatment compared
by factor (NaCl~salt; zero time -> control; codes skipped); genotype compared by
gene+kind or WT (cultivar column is background, not genotype). Prints
agree/disagree per field for CURRENT and PROPOSED."""
import json, csv, re, sys, os

SLUG = sys.argv[1] if len(sys.argv) > 1 else '<species_slug>'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SING = {'leaves':'leaf','roots':'root','stems':'stem','buds':'bud','flowers':'flower',
        'seeds':'seed','needles':'needle','shoots':'shoot','branches':'branch',
        'fruits':'fruit','calli':'callus','xylem':'xylem','phloem':'phloem','cambium':'cambium'}
ORGANS = ['callus','leaf','root','stem','xylem','phloem','cambium','shoot','bud',
          'flower','seed','needle','branch','fruit','pollen','anther','ovary','stigma']
FACTORS = ['salt','nacl','peg','drought','nitrogen deficiency','cold','heat','aba',
           'ethylene','control','infection','wounding']

def norm_tissue(v):
    v = (v or '').lower().strip()
    v = re.sub(r'[-_\s]*\d+$', '', v)
    v = v.split(';')[0].split(',')[0].strip()
    if len(v) > 30:
        # collapse a long descriptive value to the longest known organ phrase
        best = ''
        for o in ORGANS:
            if o in v and len(o) > len(best): best = o
        if best: return best
    return SING.get(v, v)

def ref_treatment(row):
    env = (row.get('environment') or '').lower()
    chem = (row.get('\u5316\u5b66\u7269\u8d28\u5904\u7406') or '')
    # zero time / zero dose is the control arm
    if re.search(r'(?<!\d)0[_ ]?(h|hr|hours?|d|days?)(?![A-Za-z])', env) or re.search(r'(?<!\d)0[_ ]?(mM|uM)', env):
        return 'control'
    for pat, fac in [('salt', 'salt'), ('nitrogen', 'nitrogen deficiency'),
                     ('drought', 'drought'), ('cold', 'cold'), ('heat', 'heat'),
                     ('control', 'control'), ('untreated', 'control')]:
        if pat in env: return fac
    cl = chem.lower()
    if 'peg' in cl: return 'peg'
    if re.search(r'nacl|salt', cl): return 'salt'
    for w in ['aba', 'ga3', 'meja', 'mannitol', 'h2o2', 'ethylene', 'acc', 'sa', 'iaa']:
        if w in cl: return w
    return ''

def json_factor(t):
    t = (t or '').lower()
    if not t.strip(): return ''
    if t.strip() == 'control': return 'control'
    for f in FACTORS:
        if f in t: return 'salt' if f == 'nacl' else f
    return ''

def ref_genotype(row):
    ph = (row.get('Phenotype') or '').strip()
    mu = (row.get('Mutation') or '').strip()
    m = re.search(r'([A-Za-z][A-Za-z0-9_\-\.]*?)\s*[- ]?(OE|KO|KD)\b', ph, re.I)
    if m: return ('construct', m.group(1), m.group(2).upper())
    if re.search(r'\bwt\b', ph, re.I): return ('wt', '', '')
    if 'None-transgenic' in mu: return ('wt', '', '')
    return ('', '', '')

def compare(kind, ref, js):
    if kind == 'tissue':
        return norm_tissue(ref) == norm_tissue(js) if ref else None
    if kind == 'treatment':
        rf, jf = ref_treatment(ref), json_factor(js)
        if not rf: return None
        return rf == jf
    if kind == 'genotype':
        rkind, gene, k2 = ref_genotype(ref)
        if not rkind: return None
        jsn = 'WT' if re.search(r'wild[\s\-]?type', js or '', re.I) else (js or '')
        if rkind == 'wt': return jsn == 'WT'
        return gene.lower() in jsn.lower() and k2 in jsn
    return None

refs = list(csv.DictReader(open(f'{BASE}/pilot/{SLUG}/evidence/reference_key.tsv'), delimiter='\t'))
print('reference rows:', len(refs))
for label, path in [('CURRENT', f'{BASE}/output/{SLUG}/expression-metadata.json'),
                    ('PROPOSED', f'{BASE}/pilot/{SLUG}/expression-metadata.proposed.json')]:
    js = {r['experiment_accession']: r for r in json.load(open(path))['rows']}
    res = {'tissue': [0, 0], 'treatment': [0, 0], 'genotype': [0, 0]}
    missing = 0
    for ref in refs:
        row = js.get(ref['Experiment Accession'])
        if not row: missing += 1; continue
        for kind, refv in [('tissue', ref.get('Tissue') or ''),
                            ('treatment', ref),
                            ('genotype', ref)]:
            c = compare(kind, refv, row['tissue'] if kind == 'tissue' else
                        row['treatment'] if kind == 'treatment' else row['genotype'])
            if c is None: continue
            res[kind][0 if c else 1] += 1
    print(f'{label} agree/disagree: {res}  missing_experiments: {missing}')

