import json
import os
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from typing import Iterator, List, Optional, Set, Tuple

# Config
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
INPUT_TEI = os.path.join(REPO_ROOT, "data", "eng-rus.tei")
OUTPUT_JSONL = os.path.join(REPO_ROOT, "en-ru", "dictionary.jsonl")
DEFAULT_FREQ_CSV = os.path.join(REPO_ROOT, "data", "unigram_freq.csv")
ALLOWED_POS = {"n", "v", "adj", "adv", "pn"}  # exclude suffix and others
POS_MAP = {
    "n": "noun",
    "v": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "pn": "proper_noun",
}
LANG_PAIR = "en-ru"

NS = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
}

RE_WIKI_LINK_PIPE = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")
RE_WIKI_LINK = re.compile(r"\[\[([^\]]+)\]\]")
RE_WS = re.compile(r"\s+")

# ---------------- Frequency utils ----------------

def normalize_key(s: str) -> str:
    s0 = strip_diacritics(s or "")
    s0 = s0.lower().strip()
    s0 = s0.replace("’", "'")
    # collapse spaces, drop surrounding quotes
    s0 = RE_WS.sub(" ", s0).strip("\"' “”«»[](){}")
    return s0


def load_freq_csv(path: str):
    import csv
    counts = {}
    min_log = None
    max_log = None
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        first = True
        for row in reader:
            if not row:
                continue
            if first and len(row) >= 2 and row[0].lower() == "word":
                first = False
                continue
            first = False
            if len(row) < 2:
                continue
            w = normalize_key(row[0])
            try:
                c = float(row[1])
            except Exception:
                continue
            if c < 0:
                continue
            counts[w] = c
    # precompute logs
    import math
    logs = [math.log(v + 1.0) for v in counts.values()]
    if logs:
        min_log = min(logs)
        max_log = max(logs)
    else:
        min_log = 0.0
        max_log = 1.0
    return counts, min_log, max_log


def count_to_frequency(count: float, min_log: float, max_log: float) -> int:
    import math
    x = math.log(count + 1.0)
    if max_log <= min_log:
        return 50
    score = (x - min_log) / (max_log - min_log)
    if score < 0:
        score = 0
    if score > 1:
        score = 1
    return int(round(1 + score * 99))


def now_ms() -> int:
    return int(time.time() * 1000)


def strip_diacritics(s: str) -> str:
    if not s:
        return s
    # Normalize then remove combining marks
    nfd = unicodedata.normalize("NFD", s)
    out = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", out)


def strip_wiki_markup(s: str) -> str:
    if not s:
        return s
    s = RE_WIKI_LINK_PIPE.sub(lambda m: m.group(2), s)
    s = RE_WIKI_LINK.sub(lambda m: m.group(1), s)
    return s


def clean_text(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = strip_wiki_markup(s)
    s = strip_diacritics(s)
    s = s.replace("\u200d", "")  # zero-width joiner
    s = s.replace("\uFEFF", "")  # BOM
    s = RE_WS.sub(" ", s)
    s = s.strip().strip("\u200b\u2060\ufeff")
    return s


def extract_entries(tei_path: str) -> Iterator[Tuple[str, str, Optional[str], List[str]]]:
    tree = ET.parse(tei_path)
    root = tree.getroot()

    for entry in root.findall(".//tei:entry", NS):
        # word (headword)
        word = entry.findtext(".//tei:form/tei:orth", namespaces=NS)
        pos = entry.findtext(".//tei:gramGrp/tei:pos", namespaces=NS)
        # collect ru translations in quotes under cit[@type='trans' and xml:lang='ru']
        quotes = [q.text or "" for q in entry.findall(".//tei:cit[@type='trans'][@xml:lang='ru']/tei:quote", NS)]
        # definition (optional) - take first
        definition = entry.findtext(".//tei:sense/tei:def", namespaces=NS)

        if not word:
            continue
        if not pos or pos not in ALLOWED_POS:
            continue

        # Clean up
        word_c = clean_text(word)
        pos_c = pos.strip()
        def_c = clean_text(definition) if definition else None
        trans_clean: List[str] = []
        for q in quotes:
            qc = clean_text(q)
            if not qc:
                continue
            # Reject entries that are only punctuation or symbols after cleaning
            # Simple alphabetic check (Latin + Cyrillic)
            if not re.search(r"[A-Za-zА-Яа-яЁё]", qc):
                continue
            trans_clean.append(qc)

        if not word_c or not trans_clean:
            continue

        yield (word_c, pos_c, def_c, trans_clean)


def write_jsonl(entries: Iterator[Tuple[str, str, Optional[str], List[str]]], out_path: str,
                 freq_map: Optional[dict] = None,
                 min_log: float = 0.0,
                 max_log: float = 1.0,
                 oov_default: int = 20) -> int:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp_path = out_path + ".tmp"
    seen: Set[Tuple[str, str, str]] = set()
    ts = now_ms()
    next_id = 1
    count = 0

    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        for word, pos_short, definition, translations in entries:
            pos_full = POS_MAP.get(pos_short, None)
            # frequency lookup by normalized source word
            freq_val = oov_default
            if freq_map is not None:
                key = normalize_key(word)
                c = freq_map.get(key)
                if c is not None:
                    freq_val = count_to_frequency(c, min_log, max_log)
            for t in translations:
                key_tuple = (word, t, pos_full or pos_short)
                if key_tuple in seen:
                    continue
                seen.add(key_tuple)
                obj = {
                    "id": next_id,
                    "source_word": word,
                    "target_word": t,
                    "language_pair": LANG_PAIR,
                    "part_of_speech": pos_full,
                    "definition": definition,
                    "frequency": int(freq_val),
                    "created_at": ts,
                    "updated_at": ts,
                }
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                next_id += 1
                count += 1

    # Atomic replace
    if os.path.exists(out_path):
        os.remove(out_path)
    os.replace(tmp_path, out_path)
    return count


def main(argv: List[str]) -> int:
    tei_path = INPUT_TEI
    out_path = OUTPUT_JSONL
    freq_path = None
    if len(argv) >= 2:
        tei_path = os.path.abspath(argv[1])
    if len(argv) >= 3:
        out_path = os.path.abspath(argv[2])
    if len(argv) >= 4:
        freq_path = os.path.abspath(argv[3])
    # Auto-detect default freq CSV
    if freq_path is None and os.path.exists(DEFAULT_FREQ_CSV):
        freq_path = DEFAULT_FREQ_CSV

    if not os.path.exists(tei_path):
        print(f"TEI file not found: {tei_path}", file=sys.stderr)
        return 2

    freq_map = None
    min_log = 0.0
    max_log = 1.0
    if freq_path and os.path.exists(freq_path):
        print(f"Loading frequencies: {freq_path}")
        freq_map, min_log, max_log = load_freq_csv(freq_path)
        print(f"Loaded {len(freq_map)} entries; log range=({min_log:.3f}, {max_log:.3f})")
    else:
        print("No frequency CSV found; using defaults.")

    print(f"Parsing TEI: {tei_path}")
    entries = extract_entries(tei_path)
    print(f"Writing JSONL: {out_path}")
    n = write_jsonl(entries, out_path, freq_map=freq_map, min_log=min_log, max_log=max_log)
    print(f"Done. Wrote {n} lines to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
