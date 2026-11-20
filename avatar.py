# noface-clipper: your own talking avatar (HeyGen) as a webcam under the gameplay (or a round cam on a corner), with captions of what it says.
# The avatar is a second pass on Shorts already rendered: picks, download, transcript and cut stay the same.
# Usage:
#   python avatar.py plan   clips/picks.json clips/out   per Short: length, words to write, what happens when; writes clips/avatar/scripts.json
#   python avatar.py check  clips/picks.json clips/out   before spending credits: each script's predicted length and where its words land vs the Short
#   python avatar.py get    <video_url> clips/avatar/<name>.mp4   saves a finished HeyGen video and measures the voice's real speed
#   python avatar.py measure clips/avatar/<name>.mp4     measures the voice's speed from a video already saved (get does it by itself)
#   python avatar.py attach clips/picks.json             adds the avatar fields to each pick that has clips/avatar/<name>.mp4
#   python avatar.py --selftest
# Settings: ~/.clipper/avatar.json {"avatar_id": "<HeyGen look id>", "voice_id": "<optional>", "wps": {"<voice>": {"rate": 3.7, "samples": [...]}}}
#   avatar_id / voice_id are written once by Claude; "wps" is written by get / measure: the words per second this voice really speaks,
#   so plan and check size the scripts to the Short and one HeyGen video per Short is enough.
# clip.py reads the pick fields: avatar (mp4), avatar_script (exact text, fixes caption spelling), avatar_pos (bottom|tl|tr), avatar_shape (rounded|circle), avatar_size (px), avatar_ring (hex).
# Default (nocam layout): the game moves to the top and the avatar fills the free band under it, a 760 px square with rounded corners.
import difflib, json, re, shutil, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CONF = Path.home() / ".clipper" / "avatar.json"
WPS = 2.4            # fallback words per second until the voice is measured (HeyGen voices measured so far: 2.4 to 3.8, so measure early)
FILL = (0.85, 1.0)   # a script should fill 85-100 % of the Short at the voice's speed: shorter = the face holds still, longer = squeezed or cut
AT = 0.25            # the avatar starts talking this many seconds into the Short
FIT = (0.94, 1.08)   # speed range used to fit the speech to the Short (slower / faster than that sounds wrong)
RING = 8             # ring width in px around the round cam


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,duration:format=duration", "-of", "json", str(p)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out); v = next((s for s in j["streams"] if s["codec_type"] == "video"), {})
    return dict(w=int(v.get("width", 0)), h=int(v.get("height", 0)), dur=float(j["format"].get("duration") or v.get("duration") or 0),
                audio=any(s["codec_type"] == "audio" for s in j["streams"]))


def face_square(path, n=12, zoom=2.7):
    """Square crop (x, y, side) centred on the avatar's face, head and shoulders, from YuNet on n frames. Falls back to a centred square."""
    import cv2
    yun = np.frombuffer((HERE / "models" / "yunet.onnx").read_bytes(), np.uint8)
    cap = cv2.VideoCapture(str(path)); W, H, N = int(cap.get(3)), int(cap.get(4)), int(cap.get(7)) or 1
    yn = cv2.FaceDetectorYN.create("onnx", yun, np.empty(0, np.uint8), (640, int(640 * H / W)), 0.6); s = 640 / W
    boxes = []
    for i in np.linspace(0, N - 1, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i)); ok, f = cap.read()
        if not ok: continue
        _, fs = yn.detect(cv2.resize(f, (640, int(640 * H / W))))
        if fs is not None and len(fs): x, y, w, h = (fs[np.argmax(fs[:, 2] * fs[:, 3])][:4] / s); boxes.append((x + w / 2, y + h / 2, w))
    cap.release()
    if not boxes: S = min(W, H); return (W - S) // 2, (H - S) // 2, S
    cx, cy, fw = np.median(np.array(boxes), axis=0)
    S = int(min(max(fw * zoom, 120), W, H)); cy = cy + fw * 0.25  # a little below the face centre: chin and shoulders in, no empty headroom
    return int(min(max(cx - S / 2, 0), W - S)), int(min(max(cy - S / 2, 0), H - S)), S


def ring_pngs(work, D, color="FFFFFF", shape="circle"):
    """mask.png (alpha of the cam + ring) and ring.png (the ring drawn on transparent), both C x C, antialiased at 4x.
    shape: circle | rounded (square with well rounded corners, radius 16 % of the side)."""
    from PIL import Image, ImageDraw
    C, k = D + 2 * RING, 4; col = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    R = int(0.16 * C * k)
    def sh(dr, box, fill, inset=0):
        if shape == "rounded": dr.rounded_rectangle(box, radius=max(R - inset, 1), fill=fill)
        else: dr.ellipse(box, fill=fill)
    m = Image.new("L", (C * k, C * k), 0); sh(ImageDraw.Draw(m), (0, 0, C * k - 1, C * k - 1), 255)
    r = Image.new("RGBA", (C * k, C * k), (0, 0, 0, 0)); d = ImageDraw.Draw(r)
    sh(d, (0, 0, C * k - 1, C * k - 1), (20, 20, 20, 255))                                               # thin dark edge for contrast on bright game frames
    sh(d, (2 * k, 2 * k, (C - 2) * k - 1, (C - 2) * k - 1), col + (255,), 2 * k)                         # the ring
    sh(d, (RING * k, RING * k, (C - RING) * k - 1, (C - RING) * k - 1), (0, 0, 0, 0), RING * k)          # hole for the face
    m.resize((C, C), Image.LANCZOS).save(work / "av_mask.png"); r.resize((C, C), Image.LANCZOS).save(work / "av_ring.png")
    return C


def transcribe(wav):
    """Word timings of the avatar's speech (faster-whisper on this computer, English)."""
    from faster_whisper import WhisperModel
    segs, _ = WhisperModel("base", device="cpu", compute_type="int8").transcribe(str(wav), language="en", word_timestamps=True, vad_filter=False)
    return [dict(w=x.word.strip(), s=float(x.start), e=float(x.end)) for sg in segs for x in (sg.words or []) if x.word.strip()]


def norm(t): return re.sub(r"[^a-z0-9']", "", t.lower())


def align(words, script):
    """Give the heard words the script's exact spelling and punctuation (Whisper may write 'gonna' for 'going to' or drop a comma)."""
    toks = script.split()
    if not toks or not words: return words
    sm = difflib.SequenceMatcher(a=[norm(w["w"]) for w in words], b=[norm(t) for t in toks], autojunk=False)
    out = [dict(w) for w in words]
    for a, b, n in sm.get_matching_blocks():
        for i in range(n): out[a + i]["w"] = toks[b + i]
    for tag, a0, a1, b0, b1 in sm.get_opcodes():  # same-size replaced runs (homophones, numbers): take the script words too
        if tag == "replace" and a1 - a0 == b1 - b0:
            for i in range(a1 - a0): out[a0 + i]["w"] = toks[b0 + i]
    return out


def fit_speed(speech_end, avail):
    """Speed factor that makes the speech end inside the Short: >1 = faster. Clamped to FIT."""
    return min(max(speech_end / max(avail, 0.1), FIT[0]), FIT[1])


def build(avatar, work, dur, script="", size=380, ring="FFFFFF", at=AT, shape="circle"):
    """Round cam video (with alpha) and voice track, both exactly `dur` s long, plus caption words in Short time.
    -> dict(bubble, voice, words, speed, side, speech_end, still_s, cut_s)"""
    avatar, work = Path(avatar).resolve(), Path(work).resolve(); work.mkdir(parents=True, exist_ok=True)
    pr = probe(avatar)
    if not pr["audio"]: raise SystemExit(f"avatar video has no sound: {avatar}")
    wav = work / "av_src.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(avatar), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    words = transcribe(wav)
    if script: words = align(words, script)
    speech_end = max((w["e"] for w in words), default=pr["dur"])
    avail = dur - at - 0.15
    f = fit_speed(speech_end, avail)
    end_s = speech_end / f; cut = max(end_s - avail, 0.0); still = max(avail - min(pr["dur"] / f, avail), 0.0)
    words = [dict(w=w["w"], s=at + w["s"] / f, e=at + w["e"] / f, end=bool(re.search(r"[.?!]$", w["w"]))) for w in words]
    words = [w for w in words if w["s"] < dur - 0.2]
    x, y, S = face_square(avatar, zoom=3.0 if shape == "rounded" else 2.7); D = int(size); C = ring_pngs(work, D, ring, shape)  # the big square shows head and shoulders
    keep = min(pr["dur"], (dur - at) * f)  # source seconds that fit in the Short at speed f
    bub = work / "av_bubble.mov"
    vf = (f"[0:v]trim=0:{keep:.3f},setpts=(PTS-STARTPTS)/{f:.5f},fps=30,crop={S}:{S}:{x}:{y},scale={D}:{D},pad={C}:{C}:{RING}:{RING}:color=black,"
          f"tpad=start_duration={at:.3f}:start_mode=clone:stop_mode=clone:stop_duration={dur:.3f},trim=0:{dur:.3f},format=rgba[a];"
          f"[a][2:v]overlay=0:0:format=auto,format=rgba[ar];[1:v]format=gray[m];[ar][m]alphamerge,format=argb[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(avatar), "-i", "av_mask.png", "-i", "av_ring.png", "-filter_complex", vf, "-map", "[o]",
                    "-c:v", "qtrle", "-an", str(bub)], check=True, cwd=work, timeout=600)
    voice = work / "av_voice.wav"; ms = int(at * 1000)
    af = (f"atrim=0:{min(speech_end + 0.4, keep):.3f},asetpts=PTS-STARTPTS,atempo={f:.5f},highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
          f"aformat=channel_layouts=stereo,adelay={ms}|{ms},apad,atrim=0:{dur:.3f}")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(avatar), "-vn", "-af", af, str(voice)], check=True, timeout=300)
    return dict(bubble=bub, voice=voice, words=words, speed=round(f, 3), side=C, speech_end=round(at + end_s, 2), still_s=round(still, 2), cut_s=round(cut, 2))


def place(pos, C, y_game=384, h_game=1152, W=1080, m=36, H=1920):
    """Top-left corner of the cam. bottom: centred in the free band under the game (game at the top). tl/tr/bl/br: a corner of the game panel, like a streamer's webcam."""
    if pos == "bottom": return (W - C) // 2, y_game + h_game + max((H - y_game - h_game - C) // 2, 0)
    x = W - C - m if pos in ("tr", "br") else m
    y = y_game + h_game - C - m if pos in ("bl", "br") else y_game + m
    return x, y


# ---------- command line ----------
def short_words(tjson, rj):
    """Streamer's words heard in the Short, in Short time (same mapping as qc.py): what happens when, for the script writer."""
    sp, st, out = rj["kept_spans"], rj["seg_start"], []
    for x in (x for s in json.load(open(tjson, encoding="utf-8"))["segments"] for x in s.get("words", [])):
        mid, acc = (x["s"] + x["e"]) / 2 - st, 0.0
        for a, b in sp:
            if a <= mid <= b: out.append((round(acc + max(x["s"] - st, a) - a, 1), x["w"].strip())); break
            acc += b - a
    return out


def load_conf():
    return json.loads(CONF.read_text(encoding="utf-8")) if CONF.exists() else {}


def voice_key(conf): return conf.get("voice_id") or f"avatar:{conf.get('avatar_id', '?')}"  # no voice_id = the avatar's own voice


def voice_rate(conf=None):
    """(words per second, how many videos it was measured on) for the configured voice; (WPS, 0) until measured."""
    conf = load_conf() if conf is None else conf; r = (conf.get("wps") or {}).get(voice_key(conf)) or {}
    return (float(r["rate"]), len(r.get("samples", []))) if r.get("rate") else (WPS, 0)


def speech_rate(words):
    """Words per second over the speech span (first word start to last word end), pauses between sentences included."""
    if len(words) < 8: return None
    span = words[-1]["e"] - words[0]["s"]
    return len(words) / span if span > 1 else None


def record_rate(rate, source=""):
    """Add one measured rate to ~/.clipper/avatar.json for the configured voice; the rate used = median of the last 5."""
    conf = load_conf(); allw = conf.setdefault("wps", {}); r = allw.setdefault(voice_key(conf), {"samples": []})
    r["samples"] = (r.get("samples", []) + [dict(rate=round(rate, 3), video=str(source))])[-5:]
    r["rate"] = round(float(np.median([s["rate"] for s in r["samples"]])), 3)
    CONF.parent.mkdir(parents=True, exist_ok=True); CONF.write_text(json.dumps(conf, indent=1, ensure_ascii=False), encoding="utf-8")
    return r["rate"], len(r["samples"])


def measure(mp4):
    """Transcribe a saved avatar video and record how fast this voice speaks."""
    mp4 = Path(mp4); wav = mp4.with_suffix(".rate.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    try: words = transcribe(wav)
    finally: wav.unlink(missing_ok=True)
    rate = speech_rate(words)
    if not rate: print(f"  {mp4.name}: too little speech to measure the voice speed"); return None
    used, n = record_rate(rate, mp4.name)
    print(f"  voice speed: {rate:.2f} words/s in {mp4.name} ({len(words)} words) -> plan/check now use {used:.2f} words/s (median of {n})")
    return rate


def budget(L, rate):
    """Words a script should have for a Short of L s: (target, min, max). Speech runs from AT to the end, with the FIT speed margin."""
    avail = L - AT - 0.4
    return int(avail * rate * 0.97), int(avail * rate * FILL[0]), int((L - AT - 0.3) * rate * FIT[1] * FILL[1])


def at_word(t, rate): return max(int(round((t - AT) * rate)), 1)  # the word heard at second t of the Short


def find_render(out_dir, name):
    rjs = sorted(Path(out_dir).glob(f"*_{name}.render.json")) or sorted(Path(out_dir).glob(f"{name}.render.json"))
    return (rjs[-1], json.loads(rjs[-1].read_text(encoding="utf-8"))) if rjs else (None, None)


def plan(picks_file, out_dir):
    picks, out_dir = json.load(open(picks_file, encoding="utf-8")), Path(out_dir)
    conf = load_conf(); rate, n = voice_rate(conf)
    print(f"avatar: {conf.get('avatar_id') or 'NOT SET (write ~/.clipper/avatar.json first)'}  voice: {conf.get('voice_id') or 'avatar default'}")
    print(f"voice speed: {rate:.2f} words/s " + (f"(measured on {n} video{'s' if n > 1 else ''})" if n else
          "(NOT MEASURED: default guess. Generate ONE Short first, `get` measures the voice, then run plan again before writing the others)"))
    adir = Path(picks_file).parent / "avatar"; adir.mkdir(exist_ok=True)
    sf = adir / "scripts.json"; old = {s["name"]: s for s in json.loads(sf.read_text(encoding="utf-8"))} if sf.exists() else {}
    rows = []
    for i, p in enumerate(picks, 1):
        rpath, rj = find_render(out_dir, p["name"])
        if not rj: print(f"\n{p['name']}: no render in {out_dir}, render it first (batch.py)"); continue
        L = rj["length"]; target, lo, hi = budget(L, rate)
        print(f"\n== {i}. {p['name']}  ({rpath.stem.replace('.render', '')}.mp4)  {L:.1f} s  ->  {target} words (between {lo} and {hi})")
        print(f"   hook: {p['hook']}   credit: {p.get('credit', '')}")
        peaks = rj.get("punch_ins") or []
        if peaks: print("   peaks (zoom): " + ", ".join(f"{a:.1f}s = word {at_word(a, rate)}" for a, b in peaks) + "  <- put the reaction to the payoff on that word")
        line, t0 = [], None
        for t, w in short_words(p["transcript"], rj):
            t0 = t if t0 is None else t0; line.append(w)
            if len(line) >= 12 or re.search(r"[.?!]$", w): print(f"   {t0:5.1f}s (word {at_word(t0, rate):>3})  {' '.join(line)}"); line, t0 = [], None
        if line: print(f"   {t0:5.1f}s (word {at_word(t0, rate):>3})  {' '.join(line)}")
        row = old.get(p["name"]) or dict(name=p["name"], script="", keywords=[])
        row.update(seconds=L, target_words=target, min_words=lo, max_words=hi, wps=round(rate, 3)); rows.append(row)
    sf.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrite each script in {sf} (English, target_words words), then run `avatar.py check` before generating")


def check(picks_file, out_dir):
    """Each script vs its Short at the measured voice speed: OK, or what to change. Exit 1 if one does not fit."""
    picks = {p["name"]: p for p in json.load(open(picks_file, encoding="utf-8"))}
    sf = Path(picks_file).parent / "avatar" / "scripts.json"; scripts = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else []
    rate, n = voice_rate(); bad = 0
    print(f"voice speed {rate:.2f} words/s" + ("" if n else "  (NOT MEASURED YET: only the first Short can be checked against a guess)"))
    for s in scripts:
        if s["name"] not in picks: continue
        _, rj = find_render(out_dir, s["name"]); L = rj["length"] if rj else s.get("seconds", 0)
        words = len(s.get("script", "").split()); target, lo, hi = budget(L, rate); spoken = words / rate
        if not words: print(f"  {s['name']}: no script yet"); bad += 1; continue
        state = "OK" if lo <= words <= hi else ("TOO SHORT" if words < lo else "TOO LONG"); bad += state != "OK"
        msg = "" if state == "OK" else (f": add about {target - words} words" if words < lo else f": cut about {words - target} words")
        print(f"  {s['name']}: {words} words -> about {spoken:.1f} s of speech for a {L:.1f} s Short ({lo}-{hi} words fit)  {state}{msg}")
        peaks = (rj or {}).get("punch_ins") or []
        if peaks and words:
            toks = s["script"].split()
            for a, b in peaks:
                k = min(at_word(a, rate), len(toks)); print(f"     peak {a:.1f}s lands on word {k}: \"{' '.join(toks[max(k - 3, 0):k + 2])}\"")
    if bad: print(f"{bad} script(s) to fix before generating"); sys.exit(1)
    print("all scripts fit")


def get(url, dst):
    dst = Path(dst); dst.parent.mkdir(parents=True, exist_ok=True)
    if not url.startswith("https://"): raise SystemExit("expected an https video URL from HeyGen get_video")
    with urllib.request.urlopen(url, timeout=300) as r, open(dst, "wb") as f: shutil.copyfileobj(r, f)
    pr = probe(dst); print(f"ok {dst} {pr['w']}x{pr['h']} {pr['dur']:.1f}s audio={pr['audio']}")
    if pr["audio"]: measure(dst)


def attach(picks_file):
    pf = Path(picks_file); picks = json.load(open(pf, encoding="utf-8")); adir = pf.parent / "avatar"
    scripts = {s["name"]: s for s in json.loads((adir / "scripts.json").read_text(encoding="utf-8"))} if (adir / "scripts.json").exists() else {}
    n = 0
    for p in picks:
        mp4 = adir / f"{p['name']}.mp4"
        if not mp4.exists(): print(f"  {p['name']}: no {mp4}, left as is"); continue
        p["avatar"] = mp4.as_posix(); p["again"] = True; s = scripts.get(p["name"], {})  # again: batch.py would skip a moment it already clipped
        if s.get("script"): p["avatar_script"] = s["script"]
        if s.get("keywords"): p["keywords"] = s["keywords"]
        n += 1
    pf.write_text(json.dumps(picks, indent=1, ensure_ascii=False), encoding="utf-8"); print(f"{n} picks now use their avatar video ({pf})")


def selftest():
    W = [dict(w="gonna", s=0, e=.3), dict(w="look", s=.4, e=.6), dict(w="at", s=.7, e=.8), dict(w="this", s=.9, e=1.1)]
    assert [w["w"] for w in align(W, "Gonna look at THIS!")] == ["Gonna", "look", "at", "THIS!"]
    assert [w["w"] for w in align(W, "Going look at this.")][1:] == ["look", "at", "this."]
    assert fit_speed(20, 20) == 1 and fit_speed(30, 20) == FIT[1] and fit_speed(10, 20) == FIT[0] and abs(fit_speed(21, 20) - 1.05) < 1e-9
    assert place("tl", 396) == (36, 420) and place("tr", 396) == (1080 - 396 - 36, 420) and place("bottom", 760, 0) == (160, 1156)
    ws = [dict(w=str(i), s=i * 0.25, e=i * 0.25 + 0.2) for i in range(40)]
    assert abs(speech_rate(ws) - 40 / 9.95) < 1e-9 and speech_rate(ws[:5]) is None
    t, lo, hi = budget(23.19, 3.7); assert lo < t < hi and lo >= 70 and hi <= 92
    assert at_word(17.4, 3.7) == 63 and at_word(0.1, 3.7) == 1
    print("avatar selftest ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--selftest"]: selftest()
    elif a[:1] == ["plan"] and len(a) == 3: plan(a[1], a[2])
    elif a[:1] == ["check"] and len(a) == 3: check(a[1], a[2])
    elif a[:1] == ["get"] and len(a) == 3: get(a[1], a[2])
    elif a[:1] == ["measure"] and len(a) == 2: measure(a[1])
    elif a[:1] == ["attach"] and len(a) == 2: attach(a[1])
    else: print(__doc__ or open(__file__, encoding="utf-8").read().split("\nimport")[0]); sys.exit(1)
