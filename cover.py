# noface-clipper: cover for an avatar Short. Your still profile photo goes in the avatar square (a frame taken mid-word looks odd),
# and the game's name sits at the top in a pill badge, written in the skill's own font (never the game's official logo).
# Usage: python cover.py SHORT.mp4 [--photo PHOTO] [--label "GTA 6"] [--colors E61E32,1478FF] [--out SHORT_cover.jpg]
#   PHOTO default: ~/.clipper/avatar_photo.jpg (Claude saves the HeyGen look's preview image there once)
#   The avatar square comes from SHORT.render.json (avatar.box); a Short without an avatar only gets the badge.
#   python cover.py --selftest
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONT = HERE / "fonts" / "Anton-Regular.ttf"
PHOTO = Path.home() / ".clipper" / "avatar_photo.jpg"
K = 4  # supersampling for smooth edges
RING = 8


def frame_at(mp4, t=1.0):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "f.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", str(mp4), "-frames:v", "1", str(p)], check=True)
        return Image.open(p).convert("RGBA")


def face_crop(img, side_k=3.0):
    """Square crop around the biggest face (head and shoulders), or a centred square when none is found."""
    import cv2
    a = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR); H, W = a.shape[:2]
    yn = cv2.FaceDetectorYN.create("onnx", np.frombuffer((HERE / "models" / "yunet.onnx").read_bytes(), np.uint8), np.empty(0, np.uint8), (W, H), 0.6)
    _, fs = yn.detect(a)
    if fs is None or not len(fs): S = min(W, H); return img.crop(((W - S) // 2, (H - S) // 2, (W + S) // 2, (H + S) // 2))
    x, y, w, h = fs[np.argmax(fs[:, 2] * fs[:, 3])][:4]
    S = int(min(max(w * side_k, 64), W, H)); cx, cy = x + w / 2, y + h / 2 + w * 0.25
    x0 = int(min(max(cx - S / 2, 0), W - S)); y0 = int(min(max(cy - S / 2, 0), H - S))
    return img.crop((x0, y0, x0 + S, y0 + S))


def paste_photo(base, photo, box):
    X, Y, S = box; inner = S - 2 * RING
    ph = face_crop(Image.open(photo)).convert("RGB").resize((inner, inner), Image.LANCZOS)
    m = Image.new("L", (inner * K, inner * K), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, inner * K - 1, inner * K - 1), radius=int(0.16 * S * K) - RING * K, fill=255)
    base.paste(ph, (X + RING, Y + RING), m.resize((inner, inner), Image.LANCZOS))


def badge(base, label, colors=("E61E32", "1478FF"), size=92, top=22):
    """Pill badge with the game's name at the top: gradient fill, white outline, soft shadow."""
    W = base.size[0]; c0, c1 = (tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in colors)
    f = ImageFont.truetype(str(FONT), size); tb = f.getbbox(label); tw, th = tb[2] - tb[0], tb[3] - tb[1]
    bw, bh = tw + 110, int(size * 1.33); bx, by = (W - bw) // 2, top
    layer = Image.new("RGBA", (W * K, (by + bh + 40) * K), (0, 0, 0, 0))
    grad = Image.new("RGBA", (bw * K, bh * K)); g = ImageDraw.Draw(grad)
    for i in range(bw * K):
        t = i / (bw * K - 1); g.line([(i, 0), (i, bh * K)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c0, c1)) + (255,))
    pm = Image.new("L", (bw * K, bh * K), 0); ImageDraw.Draw(pm).rounded_rectangle((0, 0, bw * K - 1, bh * K - 1), radius=bh * K // 2, fill=255)
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((bx * K, (by + 8) * K, (bx + bw) * K, (by + bh + 8) * K), radius=bh * K // 2, fill=(0, 0, 0, 170))
    layer = Image.alpha_composite(layer, sh.filter(ImageFilter.GaussianBlur(10 * K))); layer.paste(grad, (bx * K, by * K), pm)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((bx * K, by * K, (bx + bw) * K - 1, (by + bh) * K - 1), radius=bh * K // 2, outline=(255, 255, 255, 255), width=5 * K)
    fK = ImageFont.truetype(str(FONT), size * K)
    d.text(((W * K - tw * K) // 2 - tb[0] * K, by * K + (bh * K - th * K) // 2 - tb[1] * K), label, font=fK, fill=(255, 255, 255, 255), stroke_width=4 * K, stroke_fill=(10, 10, 20, 255))
    base.alpha_composite(layer.resize((W, by + bh + 40), Image.LANCZOS), (0, 0))


def make(mp4, photo=None, label="GTA 6", colors=("E61E32", "1478FF"), out=None):
    mp4 = Path(mp4); out = Path(out) if out else mp4.with_name(mp4.stem + "_cover.jpg")
    base = frame_at(mp4)
    rj = mp4.with_suffix(".render.json"); box = (json.loads(rj.read_text(encoding="utf-8")).get("avatar") or {}).get("box") if rj.exists() else None
    photo = Path(photo) if photo else PHOTO
    if box and photo.exists(): paste_photo(base, photo, box)
    elif box: print(f"  no profile photo at {photo}: the cover keeps the video frame in the avatar square")
    if label: badge(base, label, colors)
    base.convert("RGB").save(out, quality=94); print("ok", out); return out


def selftest():
    img = Image.new("RGBA", (1080, 1920), (40, 60, 90, 255)); badge(img, "GTA 6")
    a = np.array(img); assert a[22 + 60, 540, :3].tolist() != [40, 60, 90], "badge drawn at the top"
    assert a[1000, 540, :3].tolist() == [40, 60, 90], "rest of the frame untouched"
    ph = Image.new("RGB", (1280, 720), (200, 100, 50)); p = Path(tempfile.mkdtemp()) / "p.jpg"; ph.save(p)
    paste_photo(img, p, (160, 1156, 760)); assert np.array(img)[1156 + 380, 540, :3].tolist() != [40, 60, 90], "photo in the square"
    assert np.array(img)[1160, 164, :3].tolist() == [40, 60, 90], "rounded corner left transparent"
    print("cover selftest ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--selftest"]: selftest(); sys.exit()
    if not a or a[0].startswith("-"): print(open(__file__, encoding="utf-8").read().split("\nimport")[0]); sys.exit(1)
    kw = dict(zip(a[1::2], a[2::2]))
    make(a[0], kw.get("--photo"), kw.get("--label", "GTA 6"), tuple(kw.get("--colors", "E61E32,1478FF").split(",")), kw.get("--out"))
