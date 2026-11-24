# v11 (2026-11-24): merged extractor.
# Baseline v10 + coordinator merge (known defects Q1-Q10, per-agent patches,
# merge additions 1-7). This version produced the proposed files that
# were promoted to output/ on 2026-11-24 (verified by byte-identical
# re-extraction on five test species). Run record kept at
# pilot/_dispatch/merged/extract_classified.py (sha256 f4763990e2e27f49...).
"""Classified extraction pilot: harvest per-sample evidence in layers (L1 attributes,
L2 sample/experiment titles, L3 study titles as vocabulary only) and normalize
treatment / genotype / tissue / growth_time. Never assigns a study-level value to
a sample; never copies a value across samples in a multi-arm study."""
import json, re, csv, sys
from collections import Counter

IGNORE = {'', 'not collected', 'not applicable', 'missing', 'none', 'na', 'n/a',
          'not determined', 'unknown', 'not recorded', 'not available', 'not collect',
          'not provided', 'not aplicable', 'unapplicable', 'unavailable', 'mising', 'misssing',
          'missing sample', 'no data', 'not applicate', 'not application', 'not specified',
          'unidentified', 'null', 'not completed', 'not complete', 'not done'}
WORDNUM = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,
           'nine':9,'ten':10,'eleven':11,'twelve':12}
SINGULAR = {'leave':'leaf','leaves':'leaf','roots':'root','stems':'stem','buds':'bud','flowers':'flower',
  'fruits':'fruit','seeds':'seed','shoots':'shoot','needles':'needle','petals':'petal',
  'branches':'branch','cotyledons':'cotyledon','anthers':'anther','ovules':'ovule',
  'spikes':'spike','tillers':'tiller','panicles':'panicle','siliques':'silique'}
ORGAN_PHRASES = ['developing xylem','flower bud','fruit flesh','fruit peel','berry skin',
  'storage root','young leaf','first uncurled leaf','second leaf','stem differentiating xylem',
  'floral bud','apical bud','lateral bud','leaf primordia','root tip','shoot tip',
  'mature leaf','senescing leaf','flag leaf','seed coat','seed kernel','fruit peel']

def clean(v):
    return (v or '').strip().strip('"').strip("'").strip()

def is_ignore(v):
    x = clean(v).lower()
    return x in IGNORE or re.sub(r'[\s_-]+', ' ', x).strip() in IGNORE

def norm_tissue(raw):
    v = clean(raw).lower()
    if is_ignore(v): return ''
    v = re.sub(r'\([^)]*\)', ' ', v)     # drop complete parentheticals before splitting: 'branch (adaxial/abaxial)'
    parts = re.split(r'[/,\uFF0C\+;]|\s+and\s+|\s+with\s+', v)
    outs = []
    for p in parts:
        p = p.strip()
        if not p or is_ignore(p): continue
        p = re.sub(r'\([^)]*\)?', ' ', p).replace(')', ' ')      # parenthetical annotation, incl. unbalanced
        p = re.sub(r'\b(?:biological\s+)?replicate\s*=.*$', '', p).strip()
        p = re.sub(r'^combination\s+of\s+', '', p)
        p = re.sub(r'^mix(?:ture)?\s*(?:of|:)\s*', '', p)
        if ' side of ' in p: p = p.split(' side of ')[-1]
        p = re.sub(r'^(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|the|a|an)\s+', '', p)
        p = p.strip()
        if not p or p in WORDNUM or p in ('a', 'an') or p in TISSUE_STOP: continue
        if p in LONE_QUALIFIERS: continue
        if set(re.findall(r'[a-z]+', p)) <= TISSUE_STOP: continue
        if ' ' in p:
            p = ' '.join(w for w in p.split() if w not in TISSUE_STOP).strip()
            if not p: continue
        p = re.sub(r'[-_,]\s*[a-z]*\d+[a-z0-9_-]*$', '', p).strip()
        # 'egg-fruit_replicate 3' keeps the word, not the replicate id
        p = re.sub(r'[_\-\s]+(?:replicate|rep)\s*#?\d+$', '', p).strip()
        p = re.sub(r'(?<=[a-z])\d+$', '', p).strip()   # Q4: 'female bud1' -> 'female bud'
        # 'ovule 3' / 'callus 3': a space-separated replicate index is not organ identity
        m = re.match(r'^(.*?)\s+\d{1,2}$', p)
        if m and (m.group(1) in ORGAN_VOCAB or m.group(1) in SINGULAR):
            p = m.group(1)
        # a short code plus a number ('gj 2' from 'Heterograft GS/GJ 2') is not a tissue
        if re.fullmatch(r'[a-z]{1,4}[\s_-]?\d+', p):
            continue
        p = re.sub(r'\s+lpi\d.*$', '', p).strip()
        organ_hit = re.search(r'(leaf|stem|root|flower|fruit|seed|bud|shoot|xylem|phloem|bark|petal|pericarp|flesh|peel|embryo|callus|cambium|needle|pulp|mesocarp|branch|anther|ovule|spike|tiller|panicle|silique|cotyledon)', p)
        # only a relative-depth percentage is positional information that must stay whole
        # ('20-50% relative root'); stage/time/size qualifiers collapse to the organ
        numeric_organ = bool(organ_hit
                             and re.search(r'\b\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*%', p)
                             and not re.search(r'stage|month|week|day|hour|\b\d+\s*(?:mm|cm)\b', p))
        if len(p) > 30 or '(' in p or 'growth on' in p or 'medium' in p or 'institute' in p \
                or (len(p.split()) >= 3 and p not in ORGAN_VOCAB and not numeric_organ):
            hit = ''
            for ph in ORGAN_PHRASES:
                if ph in p and len(ph) > len(hit): hit = ph
            if hit: p = hit
            else:
                m = re.search(r'(leaf|stem|root|flower|fruit|seed|bud|shoot|xylem|phloem|bark|petal|pericarp|flesh|peel|embryo|callus|cambium|needle|pulp|mesocarp|branch|anther|ovule|spike|tiller|panicle|silique|cotyledon)', p)
                p = m.group(1) if m else ''
        if not p: continue
        # 'skin tissues' / 'cambium tissues' -> the organ itself
        if p.endswith((' tissue',' tissues')):
            q = p.rsplit(' ', 1)[0]
            if q in ORGAN_VOCAB: p = q
        p = SINGULAR.get(p, p)
        if ' ' not in p and p.endswith('s') and p[:-1] in ORGAN_VOCAB:
            p = p[:-1]
        if p not in outs: outs.append(p)
    return ';'.join(outs)

TISSUE_STOP = {'pooled','mixed','combined','bulk','fresh','frozen','dried','ground',
              'homogenized','extract','biological','technical','replicate','rep','reps',
              'sample','samples','control','treated','untreated','total','average','pool',
              'i.e.','e.g.','ie','eg'}
# a split segment that is only a qualifier ('young' from 'young and adult leaves')
# carries no organ identity; multi-word values keep their qualifier
LONE_QUALIFIERS = {'young','mature','old','adult','tender','immature','ripe',
                   'over-ripe','overripe','developing','senescing'}

ORGAN_VOCAB = set(SINGULAR.values()) | set(ORGAN_PHRASES) | {
    'leaf','root','stem','shoot','bud','flower','fruit','seed','needle','petal','branch',
    'cotyledon','anther','ovule','spike','tiller','panicle','silique','xylem','phloem',
    'cambium','callus','embryo','bark','mesocarp','pericarp','flesh','peel','pollen',
    'ovary','stigma','style','endosperm','hypocotyl','coleoptile','tuber','rhizome',
    'stolon','petiole','peduncle','berry','pod','husk','grain','meristem','seedling',
    'wood','pulp','rind','skin','epicarp','sarcocarp','exocarp'}

def norm_tissue_title(raw):
    """Q13: an experiment/sample title is prose, and norm_tissue turns prose into an organ
    phrase by substring collapse ('Ontogenic Resistance in Apple' -> itself, 'Genetic and
    physiological mechanisms...' -> 'genetic;flower'). Accept a title as tissue evidence only
    when the whole title is a short organ phrase, never a sentence."""
    v = clean(raw)
    if not v or len(v.split()) > 6 or '(' in v or len(v) > 40:
        return ''
    out = norm_tissue(v)
    if not out:
        return ''
    for p in out.split(';'):
        if p.strip() not in ORGAN_VOCAB:
            return ''
    return out


AGE_UNITS = {'year': 'year', 'years': 'years', 'yr': 'year', 'yrs': 'years',
             'month': 'month', 'months': 'months', 'week': 'week', 'weeks': 'weeks',
             'wk': 'week', 'wks': 'weeks', 'day': 'day', 'days': 'days',
             'hour': 'hour', 'hours': 'hours', 'hr': 'hour', 'hrs': 'hours',
             'waf': 'WAF', 'dac': 'DAC', 'dpi': 'DPI', 'dap': 'DAP', 'dpa': 'DPA',
             'hpi': 'HPI', 'dai': 'DAI'}

def norm_age(raw):
    v = clean(raw).lower()
    if is_ignore(v): return ''
    # Q3: '-old' removal must respect word boundaries ('2-year-old' -> '2 year', not '2-year')
    v = re.sub(r'[\s\-_]*\bold\b', ' ', v).strip(' -_')
    for w, n in WORDNUM.items():
        v = re.sub(rf'\b{w}\b', str(n), v)
    # Q2: WAF/DAC/DPI/... are plant time quantities (STANDARD §4: WAF counts);
    # they are usually written unit-first ('WAF 5'), occasionally number-first.
    units = '|'.join(sorted(AGE_UNITS, key=len, reverse=True))
    pre = re.search(r'\b(waf|dac|dpi|dap|dpa|hpi|dai)\s*(\d+(?:\.\d+)?)\b', v)
    if pre:
        return f"{pre.group(2)} {AGE_UNITS[pre.group(1)]}"
    # '12hpi,24hpi,48hpi,72hpi' is a time-course list, not one age: picking the
    # first entry is a guess, so let the existing value stand.
    parts = [p.strip(' .') for p in re.split(r'[,/;]', v) if p.strip(' .')]
    qs = [re.fullmatch(r'(\d+(?:\.\d+)?)\s*(' + units + r')', p) for p in parts]
    if len(parts) > 1 and all(qs):
        return ''
    # 'after tissue culture of 30 days ... rooting medium for 45 days': two
    # sequential durations; the first is a transfer age, not the sampling age
    if re.search(r'\b(?:after|following)\b.{0,60}\bof\s+\d+(?:\.\d+)?\s*(?:' + units + r')'
                 r'.{0,80}\bfor\s+\d+(?:\.\d+)?\s*(?:' + units + r')', v):
        return ''
    m = re.search(r'(\d+(?:\.\d+)?)[\s\-_]*(' + units + r')\b', v)
    if not m: return ''
    unit = AGE_UNITS[m.group(2)]
    # '1 years' must not survive next to the singular form used elsewhere
    if float(m.group(1)) == 1 and unit in ('years', 'months', 'weeks', 'days', 'hours'):
        unit = unit[:-1]
    return f"{m.group(1)} {unit}"

CHEM = [('methyl jasmonate', 'MeJA'), ('\\bmj\\b', 'MeJA'), ('\\bmeja\\b', 'MeJA'),
        ('\\bnahs\\b', 'NaHS'), ('salicylic acid', 'SA'), ('\\bsa\\b', 'SA'),
        ('gibberellic acid', 'GA3'), ('\\bga3\\b', 'GA3'), ('indole-3-acetic acid', 'IAA'),
        ('8-hydroxyquinoline', '8-HQ'), ('\\b8\\s*-?\\s*hq\\b', '8-HQ'),
        ('\\bmelatonin\\b', 'melatonin')]
LEVEL_FACTORS = {'drought', 'salt', 'NaCl', 'PEG', 'cold', 'heat', 'nitrogen deficiency',
                 'infection', 'wounding', 'osmotic', 'elevated CO2'}
LEVEL = {'low': 'low', 'middle': 'middle', 'moderate': 'moderate', 'high': 'high', 'severe': 'severe', 'mild': 'mild'}
NEG_FACTOR_RE = re.compile(r'\b(?:unwound(?:ed)?|non[- ]?wound(?:ed)?|non[- ]?inoculat\w*|'
                           r'not[- ]?inoculat\w*|uninoculat\w*|non[- ]?infect\w*|not[- ]?infect\w*|'
                           r'uninfect\w*|mock[- ]?inoculat\w*)\b')
# '_' is a word character: 'mock_inoculated' and 'Mits_1_..._Control' need
# non-letter lookarounds, not \b, to be read as the control arm.
CONTROL_RE = re.compile(r'(?<![a-z])(control|mock|ck|ctl)([-_ ]?\d+)?(?:bis)?(?![a-z])')

def _parse_treatment_one(v, src):
    v = clean(v)
    if is_ignore(v): return None
    low = v.lower()
    # 'without ABA' / 'no SA' names the absence of a chemical, not that treatment
    if re.search(r'\b(?:without|no|lacking)\b|absence of', low): return None
    for pat, name in CHEM:
        if pat == r'\bsa\b' and src == 'L1:alias' and len(v.strip()) <= 4:
            continue          # 'SA' as an alias is usually the tissue abbreviation (shoot apex)
        if re.search(pat, low): return (name, src)
    return None

def norm_treatment(cands):
    # candidates are ALTERNATIVE sources for the same treatment: first one that
    # parses wins. '+'-split applies WITHIN one value only (mj+salt -> MeJA;salt).
    for v, src in cands:
        v = clean(v)
        if is_ignore(v): continue
        lowv = v.lower()
        # 'control for ET and ABA experiments' describes the control arm of both
        if re.search(r'\bcontrol\s+for\b', lowv):
            return ('control', src)
        # a narrative naming both arms ('control and drought-treated',
        # 'between the control and melatonin-treated') is study-level, not this sample
        if re.search(r'\bbetween\b.{0,60}\bcontrol\b', lowv) or \
           re.search(r'\b(?:control|untreated)\b.{0,60}\b(?:treated|treatment)\b', lowv):
            continue
        # a design title naming both severity arms ('mild (B2 T30) and severe
        # (B6 VT)') describes the study, not this sample's arm
        if re.search(r'\bmild\b', lowv) and re.search(r'\bsevere\b', lowv):
            continue
        parts = [p.strip() for p in re.split(r'\s*\+\s*|\s+and\s+|;', v) if p.strip()]
        results = []
        for part in parts:
            # Q12: a level word describes its own part, not every part of a ';'-joined value
            level = ''
            for w, lv in LEVEL.items():
                if re.search(r'\b' + w + r'\b', part.lower()):
                    level = lv
                    break
            r = _norm_treatment_single(part, src, level)
            if r: results.append(r)
        if not results: continue
        # 'Deionized water 8h + 8-HQ 24h': a vehicle/control fragment must not
        # swallow the factor named in the same value
        non_control = [r for r in results if r[0].strip().lower() != 'control']
        if non_control:
            results = non_control
        by_factor = {}
        for (val, ssrc) in results:
            # a space-joined dual factor comes back as one ';'-composite
            for one in val.split(';'):
                f = one.split()[0].lower().replace('nacl', 'salt')
                if f not in by_factor or len(one) > len(by_factor[f][0]):
                    by_factor[f] = (one, ssrc)
        vals = [by_factor[f][0] for f in by_factor]
        return (';'.join(vals), results[0][1])
    return ('', '')

def _norm_treatment_single(v, src, level=''):
    for v0, src0 in [(v, src)]:
        v = clean(v0)
        if is_ignore(v): return None
        v = re.sub(r'[_-]\d+$', '', v)  # replicate suffix (NaCl_1, PEG8000_2)
        low = v.lower()
        # the control marker must be read before negation stripping:
        # 'mock_inoculated' IS the control arm, not an inoculation to strip.
        if ('no treatment' in low or 'normal watering' in low or 'untreated' in low
            or CONTROL_RE.search(low)):
            return ('control', src)
        # 'ambient CO2' is the control arm of an eCO2 experiment, not eCO2 itself
        if re.search(r'\bambient\b', low) and re.search(r'carbon dioxide|\bco2\b', low):
            return ('control', src)
        # 'unwounded, non-inoculated' / 'uninfected' names the ABSENCE of the factor;
        # 'post-inoculation' and 'treatment/inoculation' are time/assay phrases.
        neg_hit = bool(NEG_FACTOR_RE.search(low))
        if neg_hit:
            low = NEG_FACTOR_RE.sub(' ', low)
        low = re.sub(r'\b(?:days?|hours?|weeks?|dpi|hpi)\s*(?:post|after)[- ]?'
                     r'(?:inoculat\w*|infect\w*)\b', ' ', low)
        low = re.sub(r'\bpost[- ]?(?:inoculat\w*|infect\w*)\b', ' ', low)
        low = re.sub(r'\btreatment\s*/\s*inoculation\b', ' ', low)
        dose = ''
        # '5-10%' is a range: taking the upper endpoint as an exact dose invents precision
        dm = re.search(r'(?<![\d.-])(\d+(?:\.\d+)?)\s*(mM|uM|mg/L|%|ppb)', v)
        if dm: dose = dm.group(1) + dm.group(2)
        dur = ''
        tm = re.search(r'(?<![\d.-])(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|days?|d|weeks?|w|min)', low)
        if tm:
            n, u = tm.group(1), tm.group(2)
            dur = f"{n}h" if u.startswith('h') else (f"{n}d" if u.startswith('d') else (f"{n}w" if u.startswith('w') else f"{n}m"))
        chem = _parse_treatment_one(v, src)
        if chem:
            parts = [chem[0]]
            if dose: parts.append(dose)
            if dur: parts.append(dur)
            return (' '.join(parts), chem[1])
        factor = ''
        # eCO2 x warming is often written space-joined ('carbon dioxide high
        # temperature'), which §3.15 has no separator to split on.
        co2_hit = bool(re.search(r'carbon dioxide|elevated co2|\bco2\b', low)) \
            and 'storage' not in low
        tm2 = re.search(r'(-?\d+(?:\.\d+)?)\s*(?:℃|°[Cc]|\bc\b)', v, re.I)
        # in 'uninfected ... at the condition of 33C' the temperature is the assay
        # condition, not a heat arm; only an explicit heat/cold word makes it a factor
        explicit_heat = re.search(r'\bheat\b|high[- ]?temp|chilling|\bcold\b|low temp', low)
        # 'drought: 30 C, soil humidity 5-10%' is a drought arm at a shared growth
        # temperature; the number alone does not make it a heat arm
        temp_shared = re.search(r'\bdrought\b|watering|soil hum', low) and not explicit_heat
        if tm2 and not ((neg_hit or temp_shared) and
                        not re.search(r'\bheat\b|high[- ]?temp|chilling|\bcold\b|low temp|stress', low)):
            tv = float(tm2.group(1))
            if tv <= 10:
                factor = 'cold'; dose = f'{tm2.group(1)}C'
            elif tv >= 30:
                factor = 'elevated CO2;heat' if co2_hit else 'heat'
                dose = f'{tm2.group(1)}C'
        if factor:
            pass
        elif 'peg' in low:
            # osmotic stress: keep the water potential as the dose (-0.6 MPa)
            pm = re.search(r'(-?\d+(?:\.\d+)?)\s*MPa', v)
            dose = f"{pm.group(1)}MPa" if pm else dose
            factor = 'PEG'
        elif re.search(r'nacl', low): factor = 'NaCl'
        elif re.search(r'\bsalt\b', low): factor = 'salt'
        elif 'drought' in low or 'water deficit' in low or 'water stress' in low or 'withheld' in low: factor = 'drought'
        elif 'nitrogen defici' in low or 'low nitrogen' in low or 'nitrate' in low: factor = 'nitrogen deficiency'
        elif 'cold' in low or 'chilling' in low or 'low temp' in low: factor = 'cold'
        elif 'heat' in low or re.search(r'high[- ]?temp', low):
            factor = 'elevated CO2;heat' if co2_hit else 'heat'
        elif re.search(r'\baba\b', low) and not re.search(r'\b(?:without|no|lacking)\b', low):
            factor = 'ABA'
        elif 'ethylene' in low: factor = 'ethylene'
        elif 'short day' in low or 'short-day' in low: factor = 'short day'
        elif 'long day' in low or 'long-day' in low: factor = 'long day'
        elif 'photoperiod' in low: factor = 'photoperiod'
        elif re.search(r'\bozone\b', low): factor = 'ozone'
        elif re.search(r'mycorrhiz|arbuscular|\bamf\b|\bglomus\b|funneliformis|rhizophagus', low):
            factor = 'mycorrhizal inoculation'
        elif 'wound' in low: factor = 'wounding'
        elif 'infect' in low or 'inocul' in low or 'challeng' in low: factor = 'infection'
        elif 'graft' in low: factor = 'grafting'
        elif co2_hit:
            factor = 'elevated CO2'
        if factor:
            # Q12: 'low temperature' / 'high nitrogen' define the factor; the level word is not a qualifier
            if level and (re.search(r'\b(?:low|high|middle|moderate|severe|mild)[\s-]+(?:temperature|temp\w*)', low)
                          or re.search(r'\b(?:low|high)[\s-]+nitrogen\b', low)):
                level = ''
            if re.search(r'(?<![\d.])0\s*(h|hrs?|hours?|d|days?)\b', low) or \
               re.search(r'(?<![\d.])0\s*(mM|uM|mg/L|%)\b', low, re.I):
                return ('control', src)
            parts = [factor]
            if dose: parts.append(dose)
            if dur: parts.append(dur)
            if level and not dose and not dur and factor in LEVEL_FACTORS: parts.append(level)
            return (' '.join(parts), src)
        # Q5: a bare zero time/dose is the control arm even when no factor word appears
        # ('0 h' -> control). The lookbehind keeps '10 d' and '0.5 mM' out.
        if re.search(r'(?<![\d.])0\s*(h|hrs?|hours?|d|days?)\b', low) or \
           re.search(r'(?<![\d.])0\s*(mM|uM|mg/L|%|ppm|MPa)\b', low):
            return ('control', src)
        # 'uninfected'/'non-inoculated' with no other factor names the control arm
        if neg_hit: return ('control', src)
        # no factor pattern matched: do NOT keep raw text as a treatment value
    return None

def dedup_gene(g):
    # submitters sometimes double the family prefix in sample names
    # (e.g. MYBMYB180 -> MYB180); strip the first copy. Also drop a trailing
    # separator left over from the isolate/sample-name join (MYB180_ -> MYB180).
    g = g.strip('-_ ')
    m = re.match(r'^(MYB)(MYB\d.*)$', g)
    return m.group(2).strip('-_ ') if m else g

def _strip_species_prefix(tok, ctx):
    "'trichocarpaPtrMYB161' carries the species epithet glued to the gene symbol."
    for w in sorted(ctx.get('species_words', ()), key=len, reverse=True):
        if len(w) >= 4 and tok[:len(w)].lower() == w and len(tok) > len(w) \
                and (tok[len(w)].isupper() or tok[len(w)].isdigit()):
            return tok[len(w):]
    return tok


def _bad_gene(gene, ctx):
    "A token that is a stop word, or the species/genus name, is not a gene."
    g = gene.lower()
    return g in GENE_STOP or g in ctx.get('species_words', ())


def _parse_genotype_one(v, src, ctx=None):
    ctx = ctx or {}
    """Parse one candidate value; returns (value, gene, kind, line) or None."""
    v = clean(v)
    if is_ignore(v): return None
    # 'trichocarpaPtrMYB161-OE' / 'amurensis Japan' / 'mirabilis_UNL': leading species epithet
    for w in ctx.get('species_words', ()):
        if len(w) >= 4:
            v = re.sub(r'^' + re.escape(w) + r'(?:[\s_\-]+(?=[A-Z0-9])|(?=[A-Z0-9]))', '', v)
    if is_ignore(v): return None
    if src in ('L1:cultivar', 'L1:isolate'):
        # replicate suffix only (1-12); SWASP_097 is a genotype code, not replicate 97
        v = re.sub(r'_(?:[1-9]|1[0-2])$', '', v)
    else:
        v = re.sub(r'[_-]\d+$', '', v)
    low = v.lower()
    if low in ('soil','rna extraction','populus hybridization clones'): return None
    if re.search(r'\bwt\b', low) or low in ('wild', 'wildtype', 'wild type') \
            or 'wild type' in low or 'wildtype' in low or 'wild-type' in low:
        if re.search(r'overexpress|oe\b|-oe|transgenic', low):
            pass
        else:
            return ('WT', '', 'WT', '')
    m = re.search(r'([A-Za-z][A-Za-z0-9_\-\.]*?)\s*[- ]?oe\b', v, re.I)
    if m and m.group(1).lower() not in ('line',):
        gene = _strip_species_prefix(dedup_gene(m.group(1).strip('- ')), ctx)
        if _bad_gene(gene, ctx): return None
        lm = re.search(r'line\s*(\d+)', v, re.I) or re.search(r'[-_](\d+)\s*$', v)
        return (f"{gene}-OE" + (f" line {lm.group(1)}" if lm else ''), gene, 'OE', lm.group(1) if lm else '')
    m = re.search(r'([A-Za-z][A-Za-z0-9_\-\.]*?)[\s\-]+(overexpress\w*|over-expressed)', v, re.I)
    if m:
        gene = _strip_species_prefix(dedup_gene(m.group(1)), ctx)
        if _bad_gene(gene, ctx): return None
        return (f"{gene}-OE", gene, 'OE', '')
    m = re.search(r'overexpress\w*\s+(?:of\s+)?([A-Za-z][A-Za-z0-9_\-\.]*)', v, re.I)
    if m:
        gene = _strip_species_prefix(dedup_gene(m.group(1)), ctx)
        if _bad_gene(gene, ctx): return None
        return (f"{gene}-OE", gene, 'OE', '')
    m = re.search(r'([A-Za-z][A-Za-z0-9_\-\.]*?)\s*[- ]?ko\b', v, re.I)
    if m:
        gene = _strip_species_prefix(dedup_gene(m.group(1)), ctx)
        if _bad_gene(gene, ctx): return None
        return (f"{gene}-KO", gene, 'KO', '')
    m = re.search(r'([A-Za-z][A-Za-z0-9_\-\.]*?)\s*[- ]?kd\b', v, re.I)
    if m:
        gene = _strip_species_prefix(dedup_gene(m.group(1)), ctx)
        if _bad_gene(gene, ctx): return None
        return (f"{gene}-KD", gene, 'KD', '')
    m = re.search(r'deletion of (?:the )?([A-Za-z][A-Za-z0-9_\-\.]*)', v, re.I)
    if m:
        gene = _strip_species_prefix(dedup_gene(m.group(1)), ctx)
        if _bad_gene(gene, ctx): return None
        return (f"{gene}-KO", gene, 'KO', '')
    m = re.search(r'([A-Za-z][A-Za-z0-9_\-\.]*?)\s+(knockout|mutant)', v, re.I)
    if m and m.group(1).lower() not in ('gene','editing'):
        gene = _strip_species_prefix(dedup_gene(m.group(1)), ctx)
        if _bad_gene(gene, ctx): return None
        return (f"{gene}-KO", gene, 'KO', '')
    m = re.search(r'([A-Za-z][A-Za-z0-9_\-\.]*?)\s*srx?dx', v, re.I)
    if m:
        gene = _strip_species_prefix(dedup_gene(m.group(1)), ctx)
        if _bad_gene(gene, ctx): return None
        return (f"{gene}-SRDX", gene, 'SRDX', '')
    # cultivar fallback: ONLY from the cultivar/isolate attributes, never from titles;
    # and only for name-like values (rejects arm codes, stages, species+tissue strings)
    if src in ('L1:cultivar', 'L1:isolate'):
        v = re.sub(r'^(?:ecotype|cultivar|cv\.?)\s+', '', v, flags=re.I)
        # a Latin binomial is a species, not a cultivar: strip a leading genus (+ epithet)
        # and keep the cultivar part ('<物种名> Liaohong' -> 'Liaohong');
        # a bare species name then leaves nothing and is rejected.
        genus = clean(ctx.get('genus', ''))
        words = set(ctx.get('species_words', ()))
        sw = '|'.join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        stripped = False
        # a botanical author abbreviation is only suspect at the tail of 'Genus species Author'
        raw_toks = v.split()
        taxo_prefix = bool(genus) and len(raw_toks) >= 3 and raw_toks[0].lower() == genus.lower()
        if sw:
            # '10<物种名> Linn': a sample number glued to the species name
            v2 = re.sub(r'^\d+(?=(?:' + sw + r'))', '', v, flags=re.I)
            stripped = stripped or v2 != v
            v = v2
        toks0 = v.split()
        if len(toks0) == 2 and toks0[0][:1].isupper() and toks0[-1].lower().strip('.,') in words:
            # a two-word binomial whose epithet is this species' own name ('Millettia pinnata')
            # is a species label, not a cultivar; 'Shuchazao of <物种名>' is handled below
            return None
        if genus:
            v2 = re.sub(r'^' + re.escape(genus) + r'(?:[\s_\-]+|$)', '', v, flags=re.I)
            if v2 != v:
                v = v2.strip(' .,').strip('"').strip("'").strip()
                stripped = True
                if not v: return None
        if stripped:
            toks = v.split()
            i = 0
            while i < len(toks) and (toks[i].lower() in words or toks[i].lower() in ('x', 'sp', 'sp.', 'spp', 'spp.')):
                i += 1
            v = ' '.join(toks[i:]).strip(' .,').strip('"').strip("'").strip()
            if not v: return None
            # after the genus was removed the epithet can still lead the rest:
            # '<物种名>_EN142' -> 'EN142', '<物种名>_UNL' -> 'UNL'
            changed = True
            while changed:
                changed = False
                for w in sorted(words, key=len, reverse=True):
                    m = re.match(r'^' + re.escape(w) + r'(?:[\s_\-]+|(?=[A-Z0-9]))', v, re.I)
                    if m:
                        v = v[m.end():].strip(' .,').strip('"').strip("'").strip()
                        changed = True
                        break
            if not v: return None
        # a trailing lowercase genus/epithet or author abbreviation is not a cultivar name:
        # 'Diploid forsythia' -> 'Diploid'
        toks = v.split()
        if len(toks) >= 2 and toks[-1].lower().strip('.,') in words:
            v = ' '.join(toks[:-1])
        elif toks[-1].lower().strip('.,') in ('linn', 'l.'):
            v = ' '.join(toks[:-1]) if len(toks) > 1 else ''
        low = v.lower()
        if not v: return None
        if low.endswith('aceae'): return None      # a plant family is not a genotype
        if taxo_prefix and len(v.split()) == 1 and low.strip('.,') in AUTHOR_ABBREV:
            return None                            # '<物种名> Bge.' -> Bge
        if re.fullmatch(r'[ACGT]{4,}', v): return None   # a DNA barcode is not a cultivar
        if '/ ' in low or '/' in v: return None
        if sw and (re.search(r'[A-Za-z](?:' + sw + r')', v, re.I)
                   or re.search(r'(?:' + sw + r')[A-Za-z0-9]', v, re.I)):
            return None   # 'nuciferaL', 'Asaccharum1730': an epithet glued into a code
        if ' of ' in low:
            v = v[:low.index(' of ')].strip(); low = v.lower()
        if not v or (len(v.split()) == 1 and v.islower()):
            return None
        toks = set(re.findall(r'[a-z]+', low))
        if toks <= ORIGIN_WORDS:
            return None   # a bare country is provenance, not a genotype
        if (len(v) >= 2 and re.search(r'[A-Za-z]', v) and len(v) <= 35 and len(v.split()) <= 4
            and not re.search(r'[.,;:!?()]', v)
            and v.count('_') < 2
            and not re.match(r'^[A-Z]{2,5}$', v)
            and not re.match(r'^[A-Za-z]{1,2}\d+[A-Za-z]{1,3}\d*$', v)
            and not re.match(r'^[A-Za-z]+\d+-[A-Za-z]+\d+$', v)
            and not re.match(r'^\d+(?:\.\d+)?\s*(?:m|cm|mm|km|g|kg|mg|ml|l|h|d|min|s|x|%|°c)$', low)
            and not re.match(r'^\d+[a-z]{0,3}-\d+$', low)
            and not re.search(r'(?:tree|plant|individual|line|sample|no|number)\s*[#.]?\s*\d+', low)
            and not (toks & CULTIVAR_STOP)
            # species/tissue words reject a name only when they make up the whole value:
            # '<物种名>' is a species, 'Riparia Gloire de Montpellier' is a cultivar
            and not toks <= (set(ctx.get('species_words', ()))
                             | set(ctx.get('tissue_words', ())) | CULTIVAR_STOP)):
            return (v, v, 'cultivar', '')
    return None

def norm_genotype(cands, ctx=None):
    # most-specific-wins: collect every candidate's parse; same gene+kind -> keep the one with a line number
    parsed, raws = [], []
    for v, src in cands:
        p = _parse_genotype_one(v, src, ctx)
        if p:
            parsed.append((p, src))
            raws.append((p, src, clean(v).strip().lower()))
    if not parsed: return ('', '', '')
    # A lone botanical author in a name slot ('cultivar: Kuntze') is mislabelled
    # metadata; but 'Kom' is also a real litchi cultivar, so keep the value when a
    # second sample-level field (title/alias/isolate/cultivar) independently says it.
    corpus = {}
    for _, _, raw in raws:
        corpus[raw] = corpus.get(raw, 0) + 1
    def _author_only(val):
        return len(val.split()) == 1 and val.strip('.,').lower() in AUTHOR_ABBREV
    kept = [(p, src) for (p, src, raw) in raws
            if not (_author_only(p[0]) and corpus[raw] < 2)]
    if not kept: return ('', '', '')
    best, bsrc = kept[0]
    for (p, src) in kept[1:]:
        if p[1] == best[1] and p[2] == best[2] and p[3] and not best[3]:
            best, bsrc = p, src
    return (best[0], bsrc, best[2])   # kind: WT / OE / KO / KD / SRDX / cultivar
GENE_STOP = {'of','the','and','a','an','gene','genes','transgenic','overexpression','poplar','populus',
             # Q1: ordinary words that are not gene names but sit before mutant/ko/oe
             'insertion','deletion','transfer','mutant','mutants','stress','drought','salt','cold',
             'heat','treatment','control','plant','plants','line','lines','t-dna','tdna','ems',
             'ethyl','methanesulfonate','salinity','osmotic','wounding','infection','endogenous',
             'targeted','induced','random','stable','homozygous','heterozygous','double','triple',
             'single','null','loss','gain','function','knock','out','down','ox','up',
             # Q11: sequencing-design words that are not gene names either
             'replicate','replicates','rep','reps','biological','technical','sample','samples'}

GENERIC_GENOTYPE = {'replicate','replicates','rep','reps','sample','samples','cdna','rna','dna',
                    'control','treatment','unknown','missing','tissue','plant','plant sample',
                    'not collected','not applicable'}

CULTIVAR_STOP = {'day','days','week','weeks','month','months','hour','hours','year','years',
                 'adult','mature','seedling','juvenile','individual','individuals','all','none',
                 'yes','no','true','false','tea','variety','mock','nacl','h2o','water','agar','soil',
                 'flower','bud','seed','callus','protoplast','suspension','shoot','root','leaf',
                 'stem','fruit','tissue','stage','time','replicate','rep','sample','line','plant',
                 'tree','unknown','missing','other','others','raw','sequence','transcriptome','genome',
                 'poplar','populus','control','treatment','rna','dna','sequencing','clone',
                 'hybridization','cultivar','ecotype','cdna','hybrid',
                 # generic plant/common names and compass words: never a cultivar name
                 'wild','wildtype','domesticated','cultivated','landrace','breeding','germplasm',
                 'china','chinese','eastern','western','northern','southern','interior',
                 'spruce','pine','larch','fir','cedar','peach','apple','pear','grape','grapevine',
                 'kiwifruit','cotton','rice','maize','wheat','barley','sorghum','soybean','tomato',
                 'potato','cassava','willow','oak','birch','eucalyptus','citrus','orange','lemon',
                 'banana','mango','cacao','coffee','rubber','jute','hemp','flax','rapeseed',
                 'mustard','cucumber','melon','watermelon','strawberry','cherry','plum','apricot',
                 'almond','walnut','chestnut','hazelnut','pistachio','olive','avocado','papaya',
                 'pineapple','coconut','palm','persimmon','pomegranate','fig','mulberry','ginkgo',
                 'bamboo','moss','fern','sinensis','sativa','japonica','indica',
                 'longan','lychee','litchi','jujube','oleaster','rambutan','durian','mangosteen',
                 'jackfruit','breadfruit','sapodilla','guava','passionfruit','kiwi','date','olive',
                 # growth/site/observation words seen in cultivar/isolate slots
                 'block','row','position','building','greenhouse','garden','orchard','nursery',
                 'field','plot','site','population','stand','forest','institute',
                 'inoculated','inoculation','infected','infection','susceptible','resistant',
                 'sapling','saplings','old','trees','annual','woody','species','monoisolate',
                 'repeat','fruits','pods','leaves','seeds','flowers','buds',
                 'january','february','march','april','june','july','august','september',
                 'october','november','december','jan','feb','mar','apr','jun','jul','aug',
                 'sep','sept','oct','nov','dec'}

# botanical author abbreviations: reject only when they are the tail of 'Genus species Author'
AUTHOR_ABBREV = {'baill','bge','sarg','planch','carr','fisch','linn','dc','miq','thunb','willd',
                 'benth','kunth','hook','lindl','maxim','franch','hance','oliv','rehd','rehder',
                 'wils','sieb','zucc','nakai','kom','koidz','hayata','hu','cheng','chun','wang',
                 'chen','fang','spach','raf','nutt','torr','pursh','engelm','marsh','muhl',
                 'roxb','wight','walp','steud','meisn','diels','dode','pax','pierre','urb',
                 'voss','zabel','moore','munro','ohwi','jeps','hutch','standl','kuntze','lev',
                 'merr','schneid','schott','spreng','roem','schult','endl','bureau','decne',
                 'hemsl','graebn','schlecht','schmidt'}

# A value that is only a country is accession provenance, not a genotype; but the same word
# inside a longer name stays ('Brown Turkey' is a fig cultivar, 'Israel-F4' is a line).
ORIGIN_WORDS = {'japan','russia','korea','taiwan','india','vietnam','thailand','indonesia',
                'malaysia','brazil','usa','europe','africa','asia','australia','canada',
                'mexico','peru','chile','argentina','colombia','ecuador','turkey','iran',
                'israel','egypt','kenya','nigeria','ethiopia','pakistan','bangladesh','nepal',
                'myanmar','philippines','singapore','netherlands','france','germany','italy',
                'spain','portugal','greece','poland','ukraine','hungary','romania','bulgaria',
                'serbia','croatia','slovakia','czech','austria','switzerland','belgium',
                'denmark','sweden','norway','finland','iceland','ireland','zealand','lanka',
                'cambodia','jiangsu','yunnan','sichuan','guangdong','zhejiang'}

def is_junk_genotype(v, ctx):
    v = clean(v or '')
    if not v: return False
    if re.fullmatch(r'\d+', v): return True
    if v.lower() == 'cultivar': return True
    if any(w in v.lower() for w in ctx.get('species_words', ())): return True
    p = _parse_genotype_one(v, 'L1:genotype', ctx)
    if p and p[1].lower() in GENE_STOP: return True
    return False

ACCESSION_RE = re.compile(
    r'(?i)^(?:[SED]R[RXP]\d{5,}|[SED]AM[NDE][A-Z]?\d{5,}|PRJ[EDN][AB]\d{5,}|CRA\d{6,}|GSE\d{4,})$')
PLATFORM_PREFIX = re.compile(
    r'^(?:Illumina|NextSeq|HiSeq|MiSeq|NovaSeq|Genome Analyzer|PacBio|Oxford Nanopore|Nanopore|'
    r'454|GS FLX|BGISEQ|DNBSEQ|Ion Torrent|ABI)[^:]{0,80}?sequencing:\s*', re.I)


def is_accession_like(v):
    return bool(ACCESSION_RE.match((v or '').strip()))


def clean_title(t):
    """Q10: DDBJ records return the run accession as the experiment title, and only the
    Illumina platform prefix was stripped. Both leak accession fragments into tissue/genotype."""
    t = (t or '').strip()
    if not t or is_accession_like(t):
        return ''
    t = PLATFORM_PREFIX.sub('', t).strip()
    if not t or is_accession_like(t):
        return ''
    if re.fullmatch(r'(?i)[a-z0-9 .+-]*sequencing', t):
        return ''
    return t


def main(slug):
    base = f'output/{slug}'
    d = json.load(open(f'{base}/expression-metadata.json'))
    rows = d['rows']
    bs = json.load(open(f'pilot/{slug}/evidence/biosample_samn.json'))
    exp_t = {}
    study_titles = {}
    # the evidence study column is empty for many SRA rows and carries a platform string for
    # shifted DDBJ rows; the row's own study accession is the reliable grouping key
    row_study = {r['experiment_accession']: (r.get('study_accession') or '').strip()
                 for r in rows if (r.get('experiment_accession') or '').strip()}
    with open(f'pilot/{slug}/evidence/experiments.tsv') as f:
        r = csv.DictReader(f, delimiter='\t')
        for row in r:
            acc = row['experiment_accession']
            t = clean_title(row.get('experiment_title',''))
            exp_t[acc] = t
            study = row_study.get(acc) or (row.get('study_accession','') or '').strip()
            # ENA returns project accessions (PRJEB/PRJNA/PRJDB) here far more often than SRP/ERP/DRP.
            if re.fullmatch(r'(?:[SED]RP\d{5,}|PRJ[EDN][AB]\d{3,})', study):
                study_titles.setdefault(study, set()).add(t)
    # Q7: a title shared by every experiment of a study is a study-level label (ENA falls back to
    # the study title); STANDARD 3.14 forbids assigning a study-level value to a single sample.
    study_single = {k for k, v in study_titles.items() if len(v) == 1}
    ena_sam = {}
    try:
        with open(f'pilot/{slug}/evidence/ena_samples.tsv') as f:
            r = csv.DictReader(f, delimiter='\t')
            for row in r:
                ena_sam[row['sample_accession']] = row
    except FileNotFoundError:
        pass
    changed = Counter(); trace = []
    for row in rows:
        sam = row['sample_accession']; exp = row['experiment_accession']; stu = row['study_accession']
        species_words = set(x for x in slug.split('_') if len(x) > 2)
        tissue_words = set(re.split(r'[;\s]+', (row['tissue'] or '').lower())) | set(
            w for ph in ORGAN_PHRASES for w in ph.split())
        attrs = bs.get(sam, {}).get('attributes', {}) if sam in bs else {}
        stitle = bs.get(sam, {}).get('title','') if sam in bs else ''
        etitle = exp_t.get(exp, '')
        if stu in study_single:
            etitle = ''
        stitle_clean = '' if stitle.lower().startswith('plant sample from') else stitle
        alias = ena_sam.get(sam, {}).get('sample_alias','') or ''
        edesc = ena_sam.get(sam, {}).get('description','') or ''
        # a long ENA description is a study/dataset narrative, not sample-level evidence
        # (it can mention 'some were droughted' for a whole cohort)
        edesc_ev = edesc if len(edesc) <= 160 else ''
        adesc = attrs.get('description','') or ''
        adesc_ev = adesc if len(adesc) <= 160 else ''
        esam_title = ena_sam.get(sam, {}).get('sample_title','') or ''
        if esam_title == stitle_clean:
            esam_title = ''
        # Q10: an accession in a title/alias slot is not a name; norm_* would keep only its letters
        if is_accession_like(stitle_clean):
            stitle_clean = ''
        if is_accession_like(esam_title):
            esam_title = ''
        if is_accession_like(alias):
            alias = ''
        tcands = [(attrs.get('treatment',''), 'L1:treatment'),
                  (etitle, 'L2:exp_title'), (stitle_clean, 'L2:sample_title'),
                  (esam_title, 'L2:ena_sample_title'),
                  (attrs.get('isolate',''), 'L1:isolate'),
                  (alias, 'L1:alias'), (edesc_ev, 'L1:ena_description'),
                  (attrs.get('dev_stage',''), 'L1:dev_stage'),
                  (adesc_ev, 'L1:description')]
        nt, tsrc = norm_treatment(tcands)
        gcands = [(attrs.get('genotype',''), 'L1:genotype'),
                  (etitle, 'L2:exp_title'), (stitle_clean, 'L2:sample_title'),
                  (esam_title, 'L2:ena_sample_title'),
                  (attrs.get('isolate',''), 'L1:isolate'),
                  (alias, 'L1:alias'), (edesc_ev, 'L1:ena_description'),
                  (attrs.get('cultivar',''), 'L1:cultivar')]
        ng, gsrc, gkind = norm_genotype(gcands, {'species_words': species_words,
                                                'tissue_words': tissue_words,
                                                'genus': slug.split('_')[0]})
        if ng and ng.strip().lower() in GENERIC_GENOTYPE:
            ng, gsrc, gkind = '', '', ''
        ntis_ev, ntis_src = '', ''
        for cand, csrc in ((attrs.get('tissue',''), 'L1:tissue'),
                           (etitle, 'L2:exp_title'),
                           (stitle_clean, 'L2:sample_title'),
                           (esam_title, 'L2:ena_sample_title')):
            v = norm_tissue(cand) if csrc == 'L1:tissue' else norm_tissue_title(cand)
            if v:
                ntis_ev, ntis_src = v, csrc
                break
        ntis = ntis_ev or row['tissue']
        ngt = norm_age(attrs.get('age',''))
        ngt_src = 'L1:age' if ngt else ''
        ngt = ngt or row['growth_time']
        old = (row['treatment'], row['genotype'], row['tissue'], row['growth_time'])
        # junk filter: a current value that matches no factor/gene pattern is cleared, not kept
        # bare numbers carry no factor/gene meaning: clear them (code-like values such
        # as cultivar names are kept, only flagged in the trace)
        if not nt and re.fullmatch(r'\d+', row['treatment'].strip() or 'x'):
            row['treatment'] = ''; changed['treatment_junk_cleared'] += 1
        elif not nt and re.fullmatch(r'(wt|wild[\s-]?type)', row['treatment'].strip(), re.I):
            row['treatment'] = ''; changed['treatment_junk_cleared'] += 1
        if not ng and re.search(r'wild[\s\-]?type', row['genotype'] or '', re.I):
            row['genotype'] = 'WT'; changed['genotype_verbose_wt'] += 1
        elif not ng and is_junk_genotype(row['genotype'], {'species_words': species_words, 'tissue_words': tissue_words}):
            row['genotype'] = ''; changed['genotype_junk_cleared'] += 1
        elif not ng and row['genotype'].strip().lower() in GENERIC_GENOTYPE:
            row['genotype'] = ''; changed['genotype_junk_cleared'] += 1
        du = set(x for x in row['default_used'].split(';') if x) if row['default_used'] else set()
        if nt and nt != row['treatment']:
            row['treatment'] = nt; changed['treatment'] += 1
            du.discard('treatment=control')
        # D4: a cultivar/isolate/alias fallback fills an empty genotype, it does not
        # overwrite one that is already set (e.g. L1 genotype VAD-2 replaced by 'Gen').
        weak_g = gsrc in ('L1:cultivar', 'L1:isolate', 'L1:alias', 'L1:ena_description')
        if ng and ng != row['genotype'] and (
                not row['genotype'] or not weak_g
                or is_junk_genotype(row['genotype'], {'species_words': species_words,
                                                      'tissue_words': tissue_words})):
            row['genotype'] = ng; changed['genotype'] += 1
            du.discard('genotype=WT')
        if ntis and ntis != row['tissue']:
            row['tissue'] = ntis; changed['tissue'] += 1
            du.discard('tissue=whole_plant')
        if ngt and ngt != row['growth_time']:
            row['growth_time'] = ngt; changed['growth_time'] += 1
        row['default_used'] = ';'.join([k for k in ['treatment=control','genotype=WT','tissue=whole_plant'] if k in du])
        # Q6: STANDARD §3.13 asks for a recompute on rows this pass touched, not just a downgrade.
        # H needs every one of tissue/treatment/genotype to be an evidence value; we additionally
        # require all four to be non-empty, which is stricter than the written rule and so cannot
        # manufacture a false H.
        # STANDARD §4: a cultivar fallback or an arm-code treatment is at most M, so a cultivar-derived
        # genotype can never reach H even when every field is populated.
        evidence_ok = (not row['default_used']) and bool(nt) and bool(ng) and bool(ntis_ev) \
            and all(row[f] for f in ('treatment', 'genotype', 'tissue')) and gkind != 'cultivar'
        if row['confidence'] == 'H' and not evidence_ok:
            row['confidence'] = 'M'; changed['conf_H_to_M'] += 1
        elif old != (row['treatment'], row['genotype'], row['tissue'], row['growth_time']) \
                and row['confidence'] == 'M' and evidence_ok:
            row['confidence'] = 'H'; changed['conf_M_to_H'] += 1
        new = (row['treatment'], row['genotype'], row['tissue'], row['growth_time'])
        if old != new:
            trace.append({'run': row['run_accession'], 'study': stu,
                          'old': old, 'new': new, 'tsrc': tsrc, 'gsrc': gsrc,
                          'tisrc': ntis_src, 'gtsrc': ngt_src})
    out = f'pilot/{slug}/expression-metadata.proposed.json'
    json.dump(d, open(out,'w'), indent=2, ensure_ascii=False)
    json.dump(trace, open(f'pilot/{slug}/trace.json','w'), indent=1, ensure_ascii=False)
    print('rows:', len(rows), '| changed:', dict(changed), '| traced rows:', len(trace))
    print('rows with defaults now:', sum(1 for r in rows if r['default_used']))
    print('treatment control now:', sum(1 for r in rows if r['treatment']=='control'),
          '| empty treatment:', sum(1 for r in rows if not r['treatment']))
    print('genotype empty now:', sum(1 for r in rows if not r['genotype']),
          '| WT now:', sum(1 for r in rows if r['genotype']=='WT'))
    print('confidence now:', Counter(r['confidence'] for r in rows))

if __name__ == '__main__':
    main(sys.argv[1])


