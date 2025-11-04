import csv
import json
import os
import sys
import time
import unicodedata
from typing import Dict, Iterable, List, Optional, Set, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DEFAULT_INPUT_GLOB_DIR = os.path.join(REPO_ROOT, "data")
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "en-ru", "phrases.jsonl")
LANG_PAIR = "en-ru"


def now_ms() -> int:
    return int(time.time() * 1000)


def strip_diacritics(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    out = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", out)


def clean_text(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = s.replace("\u200d", "").replace("\uFEFF", "")
    s = strip_diacritics(s)
    s = " ".join(s.split())
    return s.strip("\u200b\u2060\ufeff ")


def discover_default_input() -> Optional[str]:
    # Pick the newest TSV whose name starts with 'phrases'
    cand: List[Tuple[float, str]] = []
    try:
        for name in os.listdir(DEFAULT_INPUT_GLOB_DIR):
            if not name.lower().endswith(".tsv"):
                continue
            if not name.lower().startswith("phrases"):
                continue
            path = os.path.join(DEFAULT_INPUT_GLOB_DIR, name)
            cand.append((os.path.getmtime(path), path))
    except FileNotFoundError:
        return None
    if not cand:
        return None
    cand.sort(key=lambda x: x[0], reverse=True)
    return cand[0][1]


def load_rows(tsv_path: str) -> List[Tuple[Optional[int], str, Optional[float], str]]:
    rows: List[Tuple[Optional[int], str, Optional[float], str]] = []
    with open(tsv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for r in reader:
            if not r:
                continue
            # Expect: id, source, count, target
            id_raw = None
            src = ""
            cnt_raw: Optional[float] = None
            tgt = ""
            try:
                id_raw = int(r[0]) if len(r) > 0 and r[0] != "" else None
            except Exception:
                id_raw = None
            if len(r) > 1:
                src = r[1]
            if len(r) > 2:
                try:
                    cnt_raw = float(r[2]) if r[2] != "" else None
                except Exception:
                    cnt_raw = None
            if len(r) > 3:
                tgt = r[3]
            rows.append((id_raw, src, cnt_raw, tgt))
    return rows


def compute_log_range(rows: Iterable[Tuple[Optional[int], str, Optional[float], str]]) -> Tuple[float, float]:
    import math
    vals: List[float] = []
    for _, __, c, ___ in rows:
        if c is None:
            continue
        if c < 0:
            continue
        vals.append(max(0.0, c))
    if not vals:
        return (0.0, 1.0)
    logs = [math.log(v + 1.0) for v in vals]
    return (min(logs), max(logs))


def count_to_frequency(count: Optional[float], min_log: float, max_log: float, default_oov: int = 20) -> int:
    import math
    if count is None:
        return default_oov
    x = math.log(max(0.0, count) + 1.0)
    if max_log <= min_log:
        return 50
    s = (x - min_log) / (max_log - min_log)
    s = 0.0 if s < 0 else (1.0 if s > 1 else s)
    return int(round(1 + s * 99))


def write_jsonl(rows: List[Tuple[Optional[int], str, Optional[float], str]], out_path: str) -> int:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp_path = out_path + ".tmp"
    min_log, max_log = compute_log_range(rows)
    ts = now_ms()

    seen_pair: Set[Tuple[str, str]] = set()

    # Sequential IDs starting from 1 for the written (deduped) lines
    next_id = 1

    count = 0
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as fw:
        for _id_raw, src, c_raw, tgt in rows:
            src_c = clean_text(src)
            tgt_c = clean_text(tgt)
            if not src_c or not tgt_c:
                continue
            key = (src_c, tgt_c)
            if key in seen_pair:
                continue
            seen_pair.add(key)

            freq = count_to_frequency(c_raw, min_log, max_log)

            out_id = next_id
            next_id += 1

            obj = {
                "id": out_id,
                "source_phrase": src_c,
                "target_phrase": tgt_c,
                "language_pair": LANG_PAIR,
                "frequency": int(freq),
                "confidence": 95,
                "created_at": ts,
                "updated_at": ts,
            }
            fw.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1

    # atomic replace
    if os.path.exists(out_path):
        os.remove(out_path)
    os.replace(tmp_path, out_path)
    return count


def main(argv: List[str]) -> int:
    in_path = None
    out_path = DEFAULT_OUTPUT
    if len(argv) >= 2:
        in_path = os.path.abspath(argv[1])
    if len(argv) >= 3:
        out_path = os.path.abspath(argv[2])

    if in_path is None:
        in_path = discover_default_input()
    if not in_path or not os.path.exists(in_path):
        print("TSV input not found. Provide path or place a 'phrases*.tsv' in data/", file=sys.stderr)
        return 2

    print(f"Reading TSV: {in_path}")
    rows = load_rows(in_path)
    print(f"Rows read: {len(rows)}")

    print(f"Writing JSONL: {out_path}")
    n = write_jsonl(rows, out_path)
    print(f"Done. Wrote {n} lines to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
