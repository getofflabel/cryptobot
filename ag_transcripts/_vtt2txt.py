#!/usr/bin/env python3
"""Convert YouTube auto-caption VTT to deduped plain text with [HH:MM:SS] markers.
Owned by the Alex Gonzalez corpus job. Writes <id>.txt next to the vtt."""
import re, sys, os, glob

def parse(path):
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    out = []
    last = None
    cur_ts = "00:00:00"
    for ln in lines:
        m = re.match(r'^(\d\d:\d\d:\d\d)\.\d+ --> ', ln)
        if m:
            cur_ts = m.group(1)
            continue
        if not ln.strip() or ln.startswith(('WEBVTT', 'Kind:', 'Language:', 'NOTE')):
            continue
        txt = re.sub(r'<[^>]+>', '', ln).strip()
        if not txt or txt == last:
            continue
        last = txt
        out.append((cur_ts, txt))
    # dedupe rolling-window repeats
    final = []
    seen_tail = []
    for ts, t in out:
        if t in seen_tail:
            continue
        seen_tail.append(t)
        if len(seen_tail) > 6:
            seen_tail.pop(0)
        final.append((ts, t))
    return final

def write(vtt, dest):
    rows = parse(vtt)
    with open(dest, 'w', encoding='utf-8') as f:
        block = []
        block_ts = rows[0][0] if rows else "00:00:00"
        for ts, t in rows:
            block.append(t)
            if len(block) >= 12:
                f.write(f"[{block_ts}] " + " ".join(block) + "\n")
                block = []
                block_ts = ts
        if block:
            f.write(f"[{block_ts}] " + " ".join(block) + "\n")
    return dest

if __name__ == '__main__':
    targets = sys.argv[1:] or glob.glob('*.en.vtt')
    for v in targets:
        base = os.path.basename(v).split('.')[0]
        d = write(v, base + '.txt')
        print(d, os.path.getsize(d))
