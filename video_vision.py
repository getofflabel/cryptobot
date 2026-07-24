"""
video_vision.py — WATCH the chart, don't just read the words.

Wallace, 2026-07-24: "these guys are profitable for a reason... you got to
see WHY it works for them and how it will work for us. I believe you not
being able to see the chart while seeing the transcript may be an issue."

He is right, and it was the biggest hole in the R72/R73/R75 guru pipeline.
A trader teaching on video says "we sweep this level and then we get our
break of structure" — the WORDS are narration; the INFORMATION is on the
screen: which level, how deep the sweep ran, what the surrounding structure
looked like, how far the entry sat from the stop, and (most valuable) all
the setups they scrolled past WITHOUT taking. Coding the transcript alone
captures the vocabulary and misses the judgment.

This module closes that: it pulls the transcript, finds the moments where
the trader is actually demonstrating (keyword-timed), grabs the VIDEO FRAME
at each of those moments, and writes them to a folder for the lead agent to
LOOK AT with vision. The formalization then gets written from what was
SEEN, not only from what was said — and any place the chart contradicts the
narration is exactly where the real, unspoken rule lives.

USAGE
  python3 video_vision.py <youtube-url> [outdir]

RATE LIMITS, stated plainly: YouTube throttles (HTTP 429) after a handful of
pulls from one machine — three guru videos in one afternoon was enough to
trip it on 2026-07-24. This script therefore RETRIES with exponential
backoff rather than failing the round, and it uses the browser's own cookies
plus a JS runtime (node) because YouTube's bot check rejects bare requests.
Nothing here is a workaround of any protection the user does not already
have: it is the same account, the same browser session, the same video the
owner is watching in the next tab.

FRAME SELECTION — the moments that carry the teaching:
  KEYWORDS below are the vocabulary that reliably precedes a demonstration
  ("here we have", "as you can see", "entry", "stop loss", "we sweep",
  "break of structure", ...). Each hit yields a timestamp; frames are taken
  a couple of seconds AFTER the phrase so the annotation the trader is
  drawing is already on screen. Hits are deduped to one frame per ~20s so a
  talkative minute cannot flood the folder.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time

KEYWORDS = (
    "here we have", "as you can see", "look at", "this is where", "right here",
    "entry", "stop loss", "take profit", "target", "risk reward",
    "break of structure", "bos", "market structure", "swept", "sweep",
    "liquidity", "fair value gap", "fvg", "order block", "supply", "demand",
    "retest", "confirmation", "engulfing", "candle close", "we enter",
    "i take this", "this trade", "setup", "invalidation", "higher timeframe",
)

DEDUPE_SECONDS = 20      # at most one frame per this many seconds
MAX_FRAMES = 40          # a hard cap so a long course cannot fill the disk
FRAME_OFFSET = 2.0       # seconds AFTER the phrase (annotation lands first)
RETRIES = 6
BACKOFF_START = 60       # seconds; doubles each retry (60,120,240,...)


def _run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _ytdlp_base() -> list[str]:
    """Every yt-dlp call needs the same two fixes: a JS runtime (node — the
    default deno is not installed here) and the browser's own cookies (the
    bot check rejects anonymous requests)."""
    return ["yt-dlp", "--js-runtimes", "node",
            "--cookies-from-browser", "chrome"]


def fetch_with_retry(cmd: list[str], what: str) -> tuple[bool, str]:
    """Run a yt-dlp command, retrying on 429/bot-check with exponential
    backoff. Returns (ok, output). Rate limiting is EXPECTED, not an error
    worth aborting a research round over."""
    wait = BACKOFF_START
    for attempt in range(1, RETRIES + 1):
        code, out = _run(cmd)
        if code == 0:
            return True, out
        throttled = ("429" in out or "Too Many Requests" in out
                     or "not a bot" in out)
        print(f"  [{what}] attempt {attempt}/{RETRIES} failed"
              f"{' (throttled)' if throttled else ''}: {out.strip()[-160:]}")
        if not throttled or attempt == RETRIES:
            return False, out
        print(f"  [{what}] backing off {wait}s")
        time.sleep(wait)
        wait *= 2
    return False, "exhausted"


def parse_vtt(path: str) -> list[tuple[float, str]]:
    """(seconds, text) from a .vtt subtitle file, whitespace-normalised."""
    out: list[tuple[float, str]] = []
    if not os.path.exists(path):
        return out
    ts_re = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d+)\s+-->")
    cur = None
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = ts_re.search(line)
        if m:
            h, mi, s, ms = m.groups()
            cur = int(h) * 3600 + int(mi) * 60 + int(s) + int(ms[:3]) / 1000
            continue
        if cur is not None:
            txt = re.sub(r"<[^>]+>", "", line).strip()
            if txt and not txt.startswith(("WEBVTT", "Kind:", "Language:")):
                out.append((cur, txt))
                cur = None
    return out


def demo_moments(cues: list[tuple[float, str]]) -> list[tuple[float, str]]:
    """Timestamps where the trader is demonstrating rather than talking."""
    picked: list[tuple[float, str]] = []
    for t, txt in cues:
        low = txt.lower()
        if not any(k in low for k in KEYWORDS):
            continue
        if picked and t - picked[-1][0] < DEDUPE_SECONDS:
            continue
        picked.append((t, txt))
        if len(picked) >= MAX_FRAMES:
            break
    return picked


def capture(url: str, outdir: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    base = _ytdlp_base()

    print("[1/3] transcript")
    ok, _ = fetch_with_retry(
        base + ["--skip-download", "--write-auto-subs", "--sub-langs", "en",
                "--sub-format", "vtt", "-o", os.path.join(outdir, "sub"), url],
        "subs")
    vtt = next((os.path.join(outdir, f) for f in os.listdir(outdir)
                if f.endswith(".vtt")), None)
    cues = parse_vtt(vtt) if vtt else []
    moments = demo_moments(cues)
    print(f"  {len(cues)} cues -> {len(moments)} demonstration moments")

    print("[2/3] video (480p is plenty to read a chart's structure)")
    vid = os.path.join(outdir, "video.mp4")
    ok, out = fetch_with_retry(
        base + ["-f", "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "--merge-output-format", "mp4", "-o", vid, url], "video")
    if not ok:
        return {"ok": False, "stage": "video", "moments": len(moments),
                "error": out.strip()[-300:]}

    print("[3/3] frames")
    ffmpeg = "ffmpeg"
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    written = []
    for i, (t, txt) in enumerate(moments):
        png = os.path.join(outdir, f"frame_{i:02d}_{int(t):05d}s.png")
        code, _ = _run([ffmpeg, "-y", "-ss", str(max(0.0, t + FRAME_OFFSET)),
                        "-i", vid, "-frames:v", "1", "-q:v", "2", png], 120)
        if code == 0 and os.path.exists(png):
            written.append({"file": png, "at_s": round(t, 1), "said": txt})
    with open(os.path.join(outdir, "moments.txt"), "w") as f:
        for w in written:
            f.write(f"{w['at_s']:>8.1f}s  {os.path.basename(w['file'])}  "
                    f"{w['said']}\n")
    print(f"  wrote {len(written)} frames -> {outdir}")
    return {"ok": True, "frames": written, "outdir": outdir}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python3 video_vision.py <url> [outdir]")
    target = sys.argv[2] if len(sys.argv) > 2 else "video_frames"
    res = capture(sys.argv[1], target)
    print(res if not res.get("ok") else
          f"OK: {len(res['frames'])} frames in {res['outdir']}")
