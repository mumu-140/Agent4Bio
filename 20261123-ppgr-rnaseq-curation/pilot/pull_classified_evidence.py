"""Pull classified-extraction evidence for one species slug:
  - NCBI BioSample XML (SAMN samples) -> evidence/biosample_samn.json
  - ENA sample records (alias + description, all samples) -> evidence/ena_samples.tsv
  - ENA experiment titles (read_experiment, by study) -> evidence/experiments.tsv
Usage: python3 pull_classified_evidence.py <slug>
Proxy via HTTPS_PROXY env when set (NCBI/ENA)."""
import json, os, subprocess, sys, time, urllib.parse, xml.etree.ElementTree as ET
from collections import Counter
P = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy') or ''

def curl(url, post=None, tries=3):
    for a in range(tries):
        cmd = ['curl', '-s', '--max-time', '90']
        if P: cmd += ['--proxy', P]
        cmd += [url]
        if post is not None:
            cmd += ['-X', 'POST', '-d', post]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
        time.sleep(5)
    return ''

def main(slug):
    import os
    os.makedirs(f'pilot/{slug}/evidence', exist_ok=True)
    rows = json.load(open(f'output/{slug}/expression-metadata.json'))['rows']
    sam = sorted(set(r['sample_accession'] for r in rows))
    samn = [s for s in sam if s.startswith('SAMN')]
    studies = sorted(set(r['study_accession'] for r in rows))
    print(f'{slug}: rows={len(rows)} samples={len(sam)} SAMN={len(samn)} studies={len(studies)}')
    # 1) BioSample XML
    out = {}
    for i in range(0, len(samn), 80):
        chunk = samn[i:i+80]
        url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=biosample&id=' + ','.join(chunk) + '&retmode=xml'
        txt = curl(url)
        try:
            root = ET.fromstring(txt)
        except Exception as e:
            print('  biosample chunk', i, 'parse fail', e); continue
        for bs in root.iter('BioSample'):
            acc = bs.get('accession')
            t = bs.find('.//Title'); d = bs.find('.//Description')
            attrs = {}
            for a in bs.iter('Attribute'):
                n = a.get('attribute_name')
                if n and a.text: attrs[n] = a.text.strip()
            out[acc] = {'title': t.text.strip() if t is not None and t.text else '',
                        'description': d.text.strip() if d is not None and d.text else '',
                        'attributes': attrs}
    json.dump(out, open(f'pilot/{slug}/evidence/biosample_samn.json', 'w'), indent=1, ensure_ascii=False)
    print('  biosample parsed:', len(out))
    # 2) ENA sample records (alias + description), chunked OR queries
    lines = ['sample_accession\tsample_alias\tsample_title\tdescription']
    for i in range(0, len(sam), 100):
        chunk = sam[i:i+100]
        q = ' OR '.join(f'sample_accession={s}' for s in chunk)
        body = urllib.parse.urlencode({'result': 'sample', 'query': q,
            'fields': 'sample_accession,sample_alias,sample_title,description',
            'format': 'tsv', 'limit': '500'})
        txt = curl('https://www.ebi.ac.uk/ena/portal/api/search', post=body)
        ls = [l for l in txt.splitlines() if l.strip() and not l.startswith('sample_accession')]
        lines += ls
        print(f'  ena sample chunk {i}: +{len(ls)}')
    open(f'pilot/{slug}/evidence/ena_samples.tsv', 'w').write('\n'.join(lines) + '\n')
    print('  ena sample rows:', len(lines) - 1)
    # 3) ENA experiment titles
    q = ' OR '.join(f'study_accession={s}' for s in studies)
    body = urllib.parse.urlencode({'result': 'read_experiment', 'query': q,
        'fields': 'experiment_accession,experiment_title,study_accession,sample_accession',
        'format': 'tsv', 'limit': '20000'})
    txt = curl('https://www.ebi.ac.uk/ena/portal/api/search', post=body)
    open(f'pilot/{slug}/evidence/experiments.tsv', 'w').write(txt)
    ls = [l for l in txt.splitlines() if l.strip()]
    print('  experiment rows:', len(ls) - 1 if ls else 0)

if __name__ == '__main__':
    main(sys.argv[1])

