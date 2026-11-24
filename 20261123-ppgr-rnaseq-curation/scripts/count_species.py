#!/usr/bin/env python3
"""物种计数：逐个解析接受名/taxid 并计 NCBI RNA-seq experiment 数。

用法：python3 count_species.py [--list species_list.json] [--out species_counts.json]
输入 species_list.json：[{latin, chinese, taxonmyId, family}, ...]
  taxonmyId 为空时按名搜索 NCBI taxonomy 解析 taxid（taxid_source=name_search）。
输出 species_counts.json：每物种一条记录，可断点续跑（已计物种跳过，每计完一种即写盘）。
  {latin, chinese, table_taxid, resolved_taxid?, taxid_source, canonical_name,
   name_match, ncbi_sra_rnaseq_experiments}
  name_match=false 表示表上名与 NCBI 规范名不一致（陷阱，策展时按接受名重查）。
  计数是 experiment 数（NCBI esearch Count 计 experiment 不计 run），且未剔单细胞——
  只是体量上界，行数以策展结果为准。
NCBI 限速：每次请求后 sleep 0.4s（无 API key 限 3 次/秒）。
"""
import argparse
import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
logging.basicConfig(filename="species_counts.log", level=logging.INFO,
                    format="%(asctime)s %(message)s", datefmt="%H:%M:%S")


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "RNAseq-curation/2.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def taxonomy_name(taxid: str) -> str:
    d = get_json(f"{EUTILS}/esummary.fcgi?db=taxonomy&id={taxid}&retmode=json")
    return d["result"][str(taxid)]["scientificname"]


def taxonomy_search(name: str) -> str:
    q = urllib.parse.quote(name)
    d = get_json(f"{EUTILS}/esearch.fcgi?db=taxonomy&term={q}&retmode=json")
    ids = d["esearchresult"]["idlist"]
    if not ids:
        raise ValueError(f"taxonomy 无命中：{name}")
    return ids[0]


def sra_rnaseq_experiments(taxid: str) -> int:
    term = urllib.parse.quote(f"txid{taxid}[Organism] AND RNA-Seq[Strategy]")
    d = get_json(f"{EUTILS}/esearch.fcgi?db=sra&term={term}&retmode=json")
    return int(d["esearchresult"]["count"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default="species_list.json")
    ap.add_argument("--out", default="species_counts.json")
    args = ap.parse_args()

    species = json.loads(Path(args.list).read_text())
    out = Path(args.out)
    done = {}
    if out.exists():
        for rec in json.loads(out.read_text()):
            done[rec["latin"]] = rec

    for sp in species:
        latin = sp["latin"]
        if latin in done:
            continue
        table_taxid = (sp.get("taxonmyId") or "").strip()
        try:
            if table_taxid:
                taxid, source = table_taxid, "table"
            else:
                taxid = taxonomy_search(latin)
                source = "name_search"
                time.sleep(0.4)
            canonical = taxonomy_name(taxid)
            time.sleep(0.4)
            count = sra_rnaseq_experiments(taxid)
            time.sleep(0.4)
            rec = {"latin": latin, "chinese": sp.get("chinese", ""),
                   "table_taxid": table_taxid, "taxid_source": source,
                   "canonical_name": canonical,
                   "name_match": canonical.lower() == latin.lower(),
                   "ncbi_sra_rnaseq_experiments": count}
            if source == "name_search":
                rec["resolved_taxid"] = taxid
            logging.info("%s taxid=%s canonical=%s match=%s sra_exp=%s",
                         latin, taxid, canonical, rec["name_match"], count)
        except Exception as e:  # noqa: BLE001 - 记录后继续，不阻塞整批
            rec = {"latin": latin, "chinese": sp.get("chinese", ""),
                   "table_taxid": table_taxid, "taxid_source": "error",
                   "canonical_name": "", "name_match": False,
                   "ncbi_sra_rnaseq_experiments": -1, "error": str(e)}
            logging.info("%s ERROR %s", latin, e)
        done[latin] = rec
        out.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1))
    print(f"完成：{len(done)} / {len(species)}")


if __name__ == "__main__":
    main()
