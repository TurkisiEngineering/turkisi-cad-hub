#!/usr/bin/env python3
"""Türkişi CAD Hub görsellerini üretir.

  python assets/build_assets.py           # SVG'ler (README'lerde kullanılanlar + PNG kaynakları)
  python assets/build_assets.py --png     # + PNG'ler (Playwright + Edge ya da Chromium gerekir)

Palet ve KUMPAS çizimi mikbalarikan/mikbalarikan → assets/build_assets.py ile aynıdır ("Lacivert Çelik"
tokenları). Yeni renk eklenmedi; açık tema aynı paletin açık uçlarını (kağıt, krom, gümüş) kullanır.

GitHub SVG'yi <img> olarak gösterir: script, harici font ve harici görsel yok. Metinler sistem fontlarıyla
çizilir. Başlık ve alt başlıklarda textLength genişliği sabitler; macOS, Linux ve Android'de font farklı
olsa da yerleşim kaymaz, taşma olmaz. Genişlik ölçümü Windows'taki Segoe UI ile yapılır; font yoksa
yaklaşık değer kullanılır.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent

# ---- palet (profil ile birebir) --------------------------------------------
GECE, DERIN, ZEMIN, PANEL = "#070C11", "#0D161F", "#141F2B", "#202E3C"
GUNMETAL, TITAN, GUMUS, KROM = "#394A5A", "#808E9B", "#B7C3CD", "#ECF1F5"
KIRMIZI, KOYU_KIRMIZI, SARI = "#FF3347", "#AF1537", "#E6FF1F"
MAVI, YESIL, CAMGOBEGI = "#64BFFF", "#46D193", "#22D3EE"
KAGIT, CELIK_MAVISI, CELIK = "#FCFCFA", "#39659B", "#3461A0"   # v5 'kagit', 'celik_mavisi'; profil çipi

SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'Cascadia Code', Consolas, 'Liberation Mono', monospace"


def mix(a: str, b: str, t: float) -> str:
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(pa, pb))


THEMES = {
    "dark": dict(
        bg=DERIN, g1=ZEMIN, g2=PANEL, frame=GUNMETAL, ink=KROM, sub=GUMUS, mute=TITAN,
        inset=GECE, chip_bg=PANEL, chip_line=GUNMETAL, chip_ink=GUMUS, acc=CAMGOBEGI,
        red=KIRMIZI, badge=KOYU_KIRMIZI, steel=CELIK, gears=(CAMGOBEGI, SARI, KIRMIZI), gear_op=.18,
        dim=SARI, bubble=KROM, bubble_ink=GECE, cta=KIRMIZI, cta_ink="#FFFFFF"),
    "light": dict(
        bg=KAGIT, g1=KROM, g2=mix(KROM, GUMUS, .45), frame=GUMUS, ink=GECE, sub=GUNMETAL, mute=mix(TITAN, GUNMETAL, .5),
        inset=KROM, chip_bg=KROM, chip_line=GUMUS, chip_ink=GUNMETAL, acc=CELIK_MAVISI,
        red=KOYU_KIRMIZI, badge=KOYU_KIRMIZI, steel=CELIK_MAVISI, gears=(CELIK_MAVISI, GUNMETAL, KOYU_KIRMIZI),
        gear_op=.16, dim=KOYU_KIRMIZI, bubble=GECE, bubble_ink=KROM, cta=KOYU_KIRMIZI, cta_ink="#FFFFFF"),
}

# ---- metin ölçümü -----------------------------------------------------------
# 800/900 → Segoe UI Black: Edge/Chrome Windows'ta 800'ü Black ile çizer, ölçüm de aynı dosyadan yapılmalı.
_FONT_FILES = {400: "segoeui.ttf", 600: "seguisb.ttf", 700: "segoeuib.ttf", 800: "seguibl.ttf", 900: "seguibl.ttf"}
_font_cache: dict = {}


def _pil_font(weight: int, size: float):
    key = (weight, round(size * 4))
    if key not in _font_cache:
        try:
            from PIL import ImageFont
            _font_cache[key] = ImageFont.truetype(str(Path("C:/Windows/Fonts") / _FONT_FILES[weight]), size)
        except Exception:
            _font_cache[key] = None
    return _font_cache[key]


def is_emoji(ch: str) -> bool:
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF


def text_w(s: str, size: float, weight: int = 700, mono: bool = False, ls: float = 0) -> float:
    """Yaklaşık metin genişliği (px). Emoji 1.25–1.3 em sayılır."""
    if mono:
        w = sum(0 if ord(c) == 0xFE0F else (1.3 if is_emoji(c) else 0.6) for c in s) * size
        return w + ls * len(s)
    f = _pil_font(weight, size)
    total, run = 0.0, ""

    def flush(r: str) -> float:
        if not r:
            return 0.0
        return f.getlength(r) if f else 0.56 * size * len(r)

    for c in s:
        if ord(c) == 0xFE0F:
            continue
        if is_emoji(c):
            total += flush(run) + 1.25 * size
            run = ""
        else:
            run += c
    return total + flush(run) + ls * len(s)


class Canvas:
    """SVG parçalarını ve taşma kontrolü için kutuları toplar."""

    def __init__(self, name: str, w: int, h: int, theme: str, margin: float = 16):
        self.name, self.W, self.H, self.T, self.margin = name, w, h, THEMES[theme], margin
        self.parts: list[str] = []
        self.defs: set[str] = set()
        self.boxes: list[tuple[str, float, float, float, float]] = []   # (etiket, x0, y0, x1, y1)

    def add(self, s: str) -> None:
        self.parts.append(s)

    def box(self, label: str, x0: float, y0: float, x1: float, y1: float) -> None:
        self.boxes.append((label, x0, y0, x1, y1))

    def check(self) -> list[str]:
        errs = []
        m = self.margin
        for lab, x0, y0, x1, y1 in self.boxes:
            if x0 < m - .5 or y0 < m - .5 or x1 > self.W - m + .5 or y1 > self.H - m + .5:
                errs.append(f"{self.name}: '{lab}' tuvalden taşıyor ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})")
        for i, a in enumerate(self.boxes):
            for b in self.boxes[i + 1:]:
                if a[0].startswith("~") or b[0].startswith("~"):
                    continue
                if a[0].startswith("kumpas") and b[0].startswith("kumpas"):
                    continue   # maskotun kendi iki kutusu
                if a[1] < b[3] - 1 and b[1] < a[3] - 1 and a[2] < b[4] - 1 and b[2] < a[4] - 1:
                    errs.append(f"{self.name}: '{a[0]}' ile '{b[0]}' üst üste")
        return errs


# ---- yapı taşları -----------------------------------------------------------
def text(c: Canvas, x: float, y: float, s: str, size: float, fill: str, weight: int = 400, mono: bool = False,
         anchor: str = "start", ls: float = 0, fit: bool = True, label: str | None = None) -> float:
    """Tek renkli metin; fit=True ise textLength ile genişlik sabitlenir. Genişliği döndürür."""
    w = text_w(s, size, weight, mono, ls)
    x0 = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
    tl = f' textLength="{w:.1f}" lengthAdjust="spacingAndGlyphs"' if fit and not any(map(is_emoji, s)) else ""
    lsa = f' letter-spacing="{ls}"' if ls else ""
    c.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO if mono else SANS}" font-size="{size}" '
          f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{lsa}{tl}>{escape(s)}</text>')
    c.box(label or s, x0, y - size * .78, x0 + w, y + size * .22)
    return w


def rich(c: Canvas, x: float, y: float, segs: list[tuple[str, str]], size: float, weight: int = 600,
         label: str = "rich", fit: bool = True) -> float:
    """Çok renkli tek satır: segs = [(metin, renk), ...]."""
    full = "".join(s for s, _ in segs)
    w = text_w(full, size, weight)
    tl = f' textLength="{w:.1f}" lengthAdjust="spacingAndGlyphs"' if fit and not any(map(is_emoji, full)) else ""
    spans = "".join(f'<tspan fill="{col}">{escape(s)}</tspan>' for s, col in segs)
    c.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{size}" font-weight="{weight}"'
          f'{tl} xml:space="preserve">{spans}</text>')
    c.box(label, x, y - size * .78, x + w, y + size * .22)
    return w


def chip(c: Canvas, x: float, y: float, label: str, kind: str = "outline", size: float = 18, h: float | None = None,
         weight: int = 700, ls: float = 0, dot: bool = False, mono: bool = True, anim: bool = True) -> float:
    """Çip/etiket. kind: outline | badge | steel | hl. Genişliği döndürür."""
    T = c.T
    h = h or round(size * 1.8)
    tw = text_w(label, size, weight, mono, ls)
    padx = size * .8
    dotw = size * .9 if dot else 0
    w = tw + 2 * padx + dotw
    fill, stroke, ink = {
        "outline": (T["chip_bg"], T["chip_line"], T["chip_ink"]),
        "badge": (T["badge"], None, KROM),
        "steel": (T["steel"], None, KROM),
        "hl": (SARI, None, GECE),
    }[kind]
    st = f' stroke="{stroke}" stroke-width="1.5"' if stroke else ""
    c.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h * .22:.1f}" fill="{fill}"{st}/>')
    if dot:
        c.add(f'<circle cx="{x + padx * .7 + size * .3:.1f}" cy="{y + h / 2:.1f}" r="{size * .28:.1f}" fill="{KROM}">'
              + ('<animate attributeName="opacity" values="1;.2;1" dur="1.4s" repeatCount="indefinite"/>' if anim else "")
              + '</circle>')
    lsa = f' letter-spacing="{ls}"' if ls else ""
    # Emoji'siz çip metninde genişliği sabitle: font ne olursa olsun çipin içinde kalır.
    tl = "" if any(map(is_emoji, label)) else f' textLength="{tw - ls:.1f}" lengthAdjust="spacingAndGlyphs"'
    c.add(f'<text x="{x + dotw + padx + (tw - ls) / 2:.1f}" y="{y + h / 2 + size * .36:.1f}" text-anchor="middle" '
          f'font-family="{MONO if mono else SANS}" font-size="{size}" font-weight="{weight}" fill="{ink}"{lsa}{tl}>'
          f'{escape(label)}</text>')
    c.box(f"chip:{label}", x, y, x + w, y + h)
    return w


def chip_row(c: Canvas, x: float, y: float, labels: list[str], gap: float = 12, **kw) -> float:
    for lab in labels:
        x += chip(c, x, y, lab, **kw) + gap
    return x - gap


def title_hl(c: Canvas, x: float, y: float, size: float, before: str, hl: str, after: str,
             weight: int = 800) -> float:
    """'Türkişi [CAD] Hub' — ortadaki kelime sarı kutuda (thumbnail kitindeki vurgu). Toplam genişliği döndürür."""
    T = c.T
    gap, padx = size * .22, size * .14
    x1 = x
    if before:
        x1 += text(c, x, y, before, size, T["ink"], weight, label=f"title:{before}") + gap
    w2 = text_w(hl, size, weight)
    c.add(f'<rect x="{x1:.1f}" y="{y - size * .86:.1f}" width="{w2 + 2 * padx:.1f}" height="{size * 1.02:.1f}" '
          f'rx="{size * .09:.1f}" fill="{SARI}"/>')
    c.box(f"title-hl:{hl}", x1, y - size * .86, x1 + w2 + 2 * padx, y + size * .16)
    text(c, x1 + padx, y, hl, size, GECE, weight, label=f"~title:{hl}")
    x2 = x1 + w2 + 2 * padx
    if after:
        x2 += gap
        x2 += text(c, x2, y, after, size, T["ink"], weight, label=f"title:{after}")
    return x2 - x


def kumpas(x: float, y: float, s: float, anim: bool = True) -> str:
    """KUMPAS kumpas-robot maskotu: 512'lik kutuda çizili, (x, y)'ye s ölçeğiyle konur. Profil ile aynı çizim."""
    blink = """<animateTransform attributeName="transform" type="scale" values="1 1;1 1;1 .08;1 1;1 1"
        keyTimes="0;.9;.94;.98;1" dur="4.5s" repeatCount="indefinite"/>""" if anim else ""
    jaw = """<animateTransform attributeName="transform" type="translate" values="0 0;-26 0;-26 0;0 0;0 0"
        keyTimes="0;.3;.55;.85;1" dur="6s" repeatCount="indefinite"/>""" if anim else ""
    bob = """<animateTransform attributeName="transform" type="translate" values="0 0;0 -6;0 0"
        dur="3s" repeatCount="indefinite"/>""" if anim else ""
    lamp = f"""<animate attributeName="fill" values="{KIRMIZI};#ff8a96;{KIRMIZI}" dur="1.6s" repeatCount="indefinite"/>""" if anim else ""
    ticks_big = "".join(f"M{40 + 40 * i},232V254" for i in range(11))
    ticks_small = "".join(f"M{60 + 40 * i},232V244" for i in range(11))
    return f"""
<g transform="translate({x:.1f} {y:.1f}) scale({s})">
  <rect x="20" y="222" width="472" height="58" rx="10" fill="{GUMUS}" stroke="{GECE}" stroke-width="14"/>
  <g stroke="{GECE}" stroke-width="5"><path d="{ticks_big}"/><path d="{ticks_small}"/></g>
  <path d="M60,270 L130,270 L130,470 L98,500 L60,500 Z" fill="{GUMUS}" stroke="{GECE}" stroke-width="14" stroke-linejoin="round"/>
  <g>{jaw}
    <path d="M382,270 L452,270 L452,500 L414,500 L382,470 Z" fill="{GUMUS}" stroke="{GECE}" stroke-width="14" stroke-linejoin="round"/>
  </g>
  <g>{bob}
    <rect x="96" y="96" width="320" height="300" rx="56" fill="{KIRMIZI}" stroke="{GECE}" stroke-width="14"/>
    <path d="M96,300 L416,300 L416,340 Q416,396 360,396 L152,396 Q96,396 96,340 Z" fill="{KOYU_KIRMIZI}" opacity=".6"/>
    <rect x="96" y="96" width="320" height="300" rx="56" fill="none" stroke="{GECE}" stroke-width="14"/>
    <rect x="136" y="140" width="240" height="150" rx="22" fill="{GECE}"/>
    <g transform="translate(256 205)"><g>{blink}<g transform="translate(-256 -205)">
      <path d="M182.4,212.9 Q205.4,183 228.4,212.9" fill="none" stroke="{SARI}" stroke-width="12.6" stroke-linecap="round"/>
      <path d="M283.6,212.9 Q306.6,183 329.6,212.9" fill="none" stroke="{SARI}" stroke-width="12.6" stroke-linecap="round"/>
    </g></g></g>
    <path d="M230.7,256.6 Q256,275 281.3,256.6" fill="none" stroke="{SARI}" stroke-width="9.2" stroke-linecap="round"/>
    <circle cx="196" cy="340" r="15" fill="{KROM}" stroke="{GECE}" stroke-width="7"/>
    <circle cx="256" cy="340" r="15" fill="{KROM}" stroke="{GECE}" stroke-width="7"/>
    <circle cx="316" cy="340" r="15" fill="{KROM}" stroke="{GECE}" stroke-width="7"/>
    <circle cx="256" cy="52" r="34" fill="{KIRMIZI}" stroke="{GECE}" stroke-width="14">{lamp}</circle>
    <path d="M236,52 L276,52 M256,32 L256,72" stroke="{GECE}" stroke-width="9" stroke-linecap="round"/>
    <rect x="244" y="80" width="24" height="22" fill="{TITAN}" stroke="{GECE}" stroke-width="8"/>
  </g>
</g>"""


def place_kumpas(c: Canvas, x: float, y: float, s: float, anim: bool = True) -> None:
    c.add(kumpas(x, y, s, anim))
    # 512'lik kutuda (kontur dahil): baş + lamba x 89..423, y 11..222 · cetvel + çeneler x 13..499, y 215..507
    c.box("kumpas-bas", x + 89 * s, y + 11 * s, x + 423 * s, y + 222 * s)
    c.box("kumpas-cetvel", x + 13 * s, y + 215 * s, x + 499 * s, y + 507 * s)


def ti_mark(x: float, y: float, size: float, col: str) -> str:
    """Türkişi 'Tİ' logo işareti (thumbnail kitindeki drawMark), 100'lük kutuda."""
    k = size / 100
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.4f})" fill="{col}">'
            f'<rect x="16" y="20" width="42" height="11"/><rect x="31" y="20" width="12" height="52"/>'
            f'<rect x="64" y="38" width="12" height="34"/><rect x="12" y="72" width="76" height="3.5"/>'
            f'<circle cx="70" cy="27" r="6.5" fill="{KIRMIZI}"/></g>')


def grid_bg(c: Canvas, uid: str, step: int = 24, rx: float = 18, frame: bool = True) -> None:
    T, W, H = c.T, c.W, c.H
    c.add(f"""<defs>
  <pattern id="g{uid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">
    <path d="M{step} 0H0V{step}" fill="none" stroke="{T['g1']}" stroke-width="1"/>
  </pattern>
  <pattern id="G{uid}" width="{step * 5}" height="{step * 5}" patternUnits="userSpaceOnUse">
    <path d="M{step * 5} 0H0V{step * 5}" fill="none" stroke="{T['g2']}" stroke-width="1.2"/>
  </pattern>
</defs>
<rect width="{W}" height="{H}" rx="{rx}" fill="{T['bg']}"/>
<rect width="{W}" height="{H}" rx="{rx}" fill="url(#g{uid})"/>
<rect width="{W}" height="{H}" rx="{rx}" fill="url(#G{uid})"/>""")
    if frame:
        c.add(f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="{max(rx - .75, 0)}" fill="none" '
              f'stroke="{T["frame"]}" stroke-width="1.5"/>')


def gear(cx: float, cy: float, r: float, teeth: int, color: str, dur: float, op: float = .18,
         rev: bool = False, anim: bool = True) -> str:
    pts = []
    for i in range(teeth * 4):
        a = 2 * math.pi * i / (teeth * 4)
        rr = r if (i % 4) in (0, 1) else r * .84
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    frm, to = (360, 0) if rev else (0, 360)
    rot = (f'<animateTransform attributeName="transform" type="rotate" from="{frm} {cx} {cy}" to="{to} {cx} {cy}" '
           f'dur="{dur}s" repeatCount="indefinite"/>') if anim else ""
    return (f'<g opacity="{op}"><polygon points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * .32:.1f}" fill="none" stroke="{color}" stroke-width="2"/>{rot}</g>')


def dim_line(c: Canvas, x1: float, x2: float, y: float, label: str, size: float = 16) -> None:
    """Ölçü çizgisi motifi:  |← Ø 42.00 →|"""
    col = c.T["dim"]
    lw = text_w(label, size, 700, True) + 18
    cx = (x1 + x2) / 2
    c.add(f'<g stroke="{col}" stroke-width="2" fill="{col}"><path d="M{x1:.1f} {y - 10:.1f}V{y + 10:.1f}M{x2:.1f} {y - 10:.1f}V{y + 10:.1f}"/>'
          f'<path d="M{x1 + 6:.1f} {y:.1f}H{x2 - 6:.1f}"/>'
          f'<path d="M{x1 + 6:.1f} {y:.1f}l10-5v10zM{x2 - 6:.1f} {y:.1f}l-10-5v10z" stroke="none"/></g>'
          f'<rect x="{cx - lw / 2:.1f}" y="{y - size * .85:.1f}" width="{lw:.1f}" height="{size * 1.7:.1f}" rx="5" fill="{c.T["bg"]}"/>')
    text(c, cx, y + size * .36, label, size, col, 700, mono=True, anchor="middle", fit=False, label="~dim")
    c.box("dim", x1, y - 11, x2, y + 11)


def bubble(c: Canvas, x: float, y: float, w: float, h: float, lines: list[str], size: float,
           tail: tuple[float, float, float, float, float, float], lh: float = 1.25) -> None:
    """Konuşma balonu. tail = üçgenin üç köşesi (x1,y1,x2,y2,x3,y3)."""
    T = c.T
    c.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{min(14, h / 4):.1f}" fill="{T["bubble"]}"/>'
          f'<polygon points="{",".join(f"{v:.1f}" for v in tail)}" fill="{T["bubble"]}"/>')
    n = len(lines)
    y0 = y + h / 2 - (n - 1) * size * lh / 2 + size * .36
    for i, ln in enumerate(lines):
        tw = text_w(ln, size, 800)
        assert tw <= w - size * .8, f"{c.name}: balon metni sığmıyor: {ln} ({tw:.0f} > {w - size * .8:.0f})"
        text(c, x + w / 2, y0 + i * size * lh, ln, size, T["bubble_ink"], 800, anchor="middle",
             label=f"~bubble:{ln}")
    c.box("bubble", x, y, x + w, y + h)


def svg_doc(c: Canvas, title: str, aria: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{c.W}" height="{c.H}" viewBox="0 0 {c.W} {c.H}" '
            f'role="img" aria-label="{escape(aria)}">\n<title>{escape(title)}</title>\n' + "\n".join(c.parts) + "\n</svg>\n")


# ---- parça render'ları ---------------------------------------------------------
# Lig reposundaki (TurkisiEngineering/turkisi-cad) ajan çizimi parçalar. Kit'teki design/ boru hattı
# (fetch_parts.py → Blender render_parts.py → export_webp.py) src/parts/*.webp + parts.json üretir.
PARTS_DIR = OUT / "src" / "parts"
_parts_meta: dict | None = None
_img_cache: dict = {}


def parts_meta() -> dict:
    global _parts_meta
    if _parts_meta is None:
        _parts_meta = json.loads((PARTS_DIR / "parts.json").read_text(encoding="utf-8"))
    return _parts_meta


def embed(name: str, w_disp: float, scale: float = 1.5, quality: int = 78) -> tuple[str, int, int]:
    """WebP render'ı görüntülenme genişliğinin ~1.5 katında yeniden kodlar → (data URI, w, h).
    GitHub SVG'yi <img> olarak gösterdiği için harici görsel yüklenmez; gömülü data URI çalışır."""
    key = (name, round(w_disp), scale, quality)
    if key not in _img_cache:
        from PIL import Image
        im = Image.open(PARTS_DIR / f"{name}.webp").convert("RGBA")
        tw = max(1, round(w_disp * scale))
        if tw < im.width:
            im = im.resize((tw, round(im.height * tw / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=quality, method=6)
        _img_cache[key] = ("data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode(), im.width, im.height)
    return _img_cache[key]


def part(c: Canvas, name: str, cx: float, cy: float, w: float, shadow: bool = True, op: float = 1.0) -> float:
    """Parça render'ını merkezi (cx, cy), genişliği w olacak şekilde koyar; yüksekliği döndürür."""
    uri, iw, ih = embed(name, w)
    h = w * ih / iw
    x, y = cx - w / 2, cy - h / 2
    if shadow:
        sid = f"sh{c.name}".replace("-", "")
        if sid not in c.defs:
            col, a = (GECE, .55) if c.T["bg"] == DERIN else (GUNMETAL, .22)
            c.add(f'<defs><radialGradient id="{sid}"><stop offset="0" stop-color="{col}" stop-opacity="{a}"/>'
                  f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient></defs>')
            c.defs.add(sid)
        c.add(f'<ellipse cx="{cx:.1f}" cy="{y + h * .93:.1f}" rx="{w * .46:.1f}" ry="{max(6, h * .12):.1f}" fill="url(#{sid})"/>')
    c.add(f'<image href="{uri}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"'
          + (f' opacity="{op}"' if op < 1 else "") + "/>")
    c.box(f"~part:{name}", x, y, x + w, y + h)
    return h


RING = ["#00E5FF", "#9DFF2E", "#E6FF1F", "#FF9A4D", "#FF4FB0", "#B07CFF", "#00E5FF"]   # v8 görev renkleri


def glow_ring(c: Canvas, cx: float, cy: float, r: float, width: float = 5) -> None:
    """Thumbnail V8'deki renkli hale: içi hafif aydınlık disk + parlayan çok renkli çember."""
    uid = c.name.replace("-", "")
    dark = c.T["bg"] == DERIN
    inner = PANEL if dark else KROM
    stops = "".join(f'<stop offset="{i / (len(RING) - 1):.3f}" stop-color="{col}"/>' for i, col in enumerate(RING))
    c.add(f'<defs><linearGradient id="rg{uid}" x1="0" y1="0" x2="1" y2="1">{stops}</linearGradient>'
          f'<radialGradient id="rd{uid}"><stop offset="0" stop-color="{inner}" stop-opacity="{.95 if dark else .9}"/>'
          f'<stop offset=".75" stop-color="{inner}" stop-opacity="{.55 if dark else .5}"/>'
          f'<stop offset="1" stop-color="{inner}" stop-opacity="0"/></radialGradient>'
          f'<filter id="bl{uid}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="{width * 1.8:.1f}"/></filter></defs>'
          f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#rd{uid})"/>'
          f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#rg{uid})" stroke-width="{width * 3.2:.1f}" '
          f'opacity="{.55 if dark else .35}" filter="url(#bl{uid})"/>'
          f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#rg{uid})" stroke-width="{width}" opacity="{1 if dark else .85}"/>')


def scan_line(c: Canvas, cx: float, cy: float, deg: float, length: float, width: float = 3) -> None:
    """Parlayan tarama çizgisi; render'daki STL/CAD kesimine hizalı (deg: görüntüde, y yukarı)."""
    uid = c.name.replace("-", "")
    dx, dy = math.cos(math.radians(deg)), -math.sin(math.radians(deg))
    x1, y1, x2, y2 = cx - dx * length / 2, cy - dy * length / 2, cx + dx * length / 2, cy + dy * length / 2
    dark = c.T["bg"] == DERIN
    # açık temada geniş camgöbeği hale turuncu CAD yarısını haki/zeytin rengine bulandırıyordu → dar ve soluk
    glow, mid, core = ("#00E5FF", "#00E5FF", "#FFFFFF") if dark else ("#00E5FF", "#00B8D9", CELIK_MAVISI)
    blur = width * (2 if dark else 1.1)
    c.add(f'<defs><filter id="sl{uid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{blur:.1f}"/></filter></defs>'
          f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{glow}" stroke-width="{width * (4 if dark else 2.6):.1f}" '
          f'stroke-linecap="round" opacity="{.8 if dark else .22}" filter="url(#sl{uid})"/>'
          f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{mid}" stroke-width="{width * (1.6 if dark else 1.2):.1f}" stroke-linecap="round"/>'
          f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{core}" stroke-width="{width * .55:.1f}" stroke-linecap="round"/>')


def hero(c: Canvas, cx: float, cy: float, r: float, line: float = 1.3, ring_w: float = 5) -> tuple[float, float, float]:
    """Halka + yarı STL / yarı CAD konik dişli (P16) + hizalı tarama çizgisi.
    Dişlinin görüntüdeki siluetini (x0, x1, üst y) döndürür: ölçü çizgisi halkayı değil dişliyi ölçsün."""
    variant = "dark" if c.T["bg"] == DERIN else "light"
    name = f"P16_split_{variant}"
    w = r * 1.72
    glow_ring(c, cx, cy, r, ring_w)
    part(c, name, cx, cy, w, shadow=False)
    scan_line(c, cx, cy, parts_meta()[name]["split_deg"], r * 2 * line, width=max(2, ring_w * .55))
    from PIL import Image
    im = Image.open(PARTS_DIR / f"{name}.webp")
    x0, y0, x1, _ = im.getchannel("A").point(lambda a: 255 if a > 96 else 0).getbbox()
    k = w / im.width
    return cx - w / 2 + x0 * k, cx - w / 2 + x1 * k, cy - w / 2 + y0 * k


GEAR_DIA = "Ø 32.56"   # P16 konik dişlinin dış çapı, STEP'ten ölçüldü (design/parts/parts.json)


# ---- 1. hub banner (README üstü) ------------------------------------------------
CATS_BANNER = ["🙋 Soru-Cevap", "🛠️ Projelerimiz", "🏁 Lig", "📺 Yayın Soruları"]


def banner(theme: str) -> tuple[str, list[str]]:
    c = Canvas(f"banner-{theme}", 1280, 320, theme)
    T = c.T
    grid_bg(c, "b" + theme[0])
    g1, g2, g3 = T["gears"]
    c.add(gear(838, 332, 62, 12, g3, 26, T["gear_op"] * .8))
    c.add(gear(1262, 300, 46, 10, g2, 18, T["gear_op"], rev=True))
    x = 64
    x = chip(c, x, 40, "TOPLULUK", "badge", size=15, h=34, ls=1.5, dot=True, mono=False) + x + 10
    x = chip(c, x, 40, "GitHub Discussions", "steel", size=15, h=34, ls=.5, mono=False) + x + 10
    chip(c, x, 40, "TR · EN", "outline", size=15, h=34, ls=1, mono=False)
    title_hl(c, 64, 168, 96, "Türkişi", "CAD", "Hub")
    rich(c, 66, 224, [("agentic CAD", T["acc"]), (" topluluğu", T["sub"])], 38, 600, label="subtitle")
    chip_row(c, 64, 246, CATS_BANNER[:3], size=26, h=46, weight=700)   # 3 büyük çip: telefonda da okunur
    # sağ: yarı STL / yarı CAD konik dişli (lig P16), KUMPAS ölçüyor
    gx0, gx1, _ = hero(c, 1126, 170, 110, line=1.2)
    dim_line(c, gx0, gx1, 34, GEAR_DIA)          # dişlinin kendi silueti: STEP'ten ölçülen dış çap
    place_kumpas(c, 855, 150, .30)
    return svg_doc(c, "Türkişi CAD Hub", "Türkişi CAD Hub — agentic CAD topluluğu: Soru-Cevap, Projelerimiz, Lig, "
                   "Yayın Soruları. Yarısı STL ağı yarısı CAD olan konik dişliyi KUMPAS ölçüyor."), c.check()


# ---- 2. org banner (github.com/TurkisiEngineering) ----------------------------
def org_banner(theme: str) -> tuple[str, list[str]]:
    c = Canvas(f"org-banner-{theme}", 1280, 280, theme)
    T = c.T
    grid_bg(c, "o" + theme[0])
    g1, g2, g3 = T["gears"]
    c.add(gear(1000, 286, 60, 12, g3, 34, T["gear_op"] * .8))
    place_kumpas(c, 36, 30, .45)
    # balon: KUMPAS başının sağ üstünde, kuyruk başa doğru
    bubble(c, 262, 22, 176, 84, ["Ölçmeden", "onay yok! 📏"], 19, (282, 106, 262, 126, 312, 106))
    x = 474
    x = chip(c, x, 40, "▶ YOUTUBE KANALI", "badge", size=15, h=34, ls=1.5, mono=False) + x + 10
    chip(c, x, 40, "GitHub", "steel", size=15, h=34, ls=.5, mono=False)
    text(c, 472, 138, "Türkişi Engineering", 58, T["ink"], 800, label="org-title")
    rich(c, 474, 190, [("Agentic CAD", T["acc"]), (", canlı ve Türkçe.", T["sub"])], 34, 600, label="org-sub")
    chip_row(c, 474, 214, ["💬 Türkişi CAD Hub", "🏁 Agentic CAD Ligi", "📺 YouTube"], size=18, h=38)
    # sağ üst: ajanların çizdiği lig parçaları
    part(c, "P19", 1196, 96, 92)
    part(c, "P10", 1090, 170, 92)
    part(c, "P05", 1196, 204, 100)
    return svg_doc(c, "Türkişi Engineering", "Türkişi Engineering — Agentic CAD, canlı ve Türkçe. "
                   "Türkişi CAD Hub, Agentic CAD Ligi ve YouTube. Maskot KUMPAS: Ölçmeden onay yok. "
                   "Yanında ajanların çizdiği lig parçaları."), c.check()


# ---- 3. profil kartı (kişisel profil README'leri) ------------------------------
def hub_card(theme: str) -> tuple[str, list[str]]:
    c = Canvas(f"hub-card-{theme}", 1200, 220, theme)
    T = c.T
    grid_bg(c, "c" + theme[0], step=20)
    c.add(f'<rect x="0" y="26" width="6" height="58" rx="2" fill="{KIRMIZI}"/>')
    c.add(gear(1150, 214, 44, 10, T["gears"][2], 22, T["gear_op"] * .8, rev=True))
    text(c, 40, 52, "// AGENTIC CAD TOPLULUĞU · GITHUB DISCUSSIONS", 15, T["acc"], 700, mono=True, ls=2,
         fit=False, label="kicker")
    title_hl(c, 40, 114, 54, "Türkişi", "CAD", "Hub")
    text(c, 41, 158, "Soru sor, projeni paylaş, lige katıl.", 29, T["sub"], 400, label="card-desc")
    chip_row(c, 40, 172, CATS_BANNER, size=16, h=30, gap=10)
    hero(c, 772, 110, 80, line=1.25, ring_w=4)
    # CTA
    bx, by, bw, bh = 882, 66, 278, 74
    c.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="14" fill="{T["cta"]}"/>')
    c.box("cta", bx, by, bx + bw, by + bh)
    text(c, bx + bw / 2, by + bh / 2 + 10, "Topluluğa katıl →", 30, T["cta_ink"], 800, anchor="middle",
         label="~cta-text")
    text(c, bx + bw / 2, by + bh + 30, "TurkisiEngineering/turkisi-cad-hub", 14, T["mute"], 400, mono=True,
         anchor="middle", fit=False, label="cta-url")
    return svg_doc(c, "Türkişi CAD Hub", "Türkişi CAD Hub — agentic CAD topluluğu: soru sor, projeni paylaş, "
                   "lige katıl. Topluluğa katıl."), c.check()


# ---- 4. social preview (1280×640 PNG kaynağı) ----------------------------------
def social_preview() -> tuple[str, list[str]]:
    c = Canvas("social-preview", 1280, 640, "dark", margin=40)
    T = c.T
    grid_bg(c, "s", step=32, rx=0, frame=False)
    g1, g2, g3 = T["gears"]
    c.add(gear(560, 680, 90, 14, g3, 26, .12, anim=False))
    x = 72
    x = chip(c, x, 64, "AGENTIC CAD TOPLULUĞU", "badge", size=20, h=44, ls=2, dot=True, mono=False, anim=False) + x + 12
    chip(c, x, 64, "GitHub Discussions", "steel", size=20, h=44, ls=.5, mono=False)
    text(c, 66, 258, "Türkişi", 132, T["ink"], 800, label="sp-title1")
    title_hl(c, 70, 406, 132, "", "CAD", "Hub")
    text(c, 74, 470, "Soru sor · projeni paylaş · lige katıl", 38, T["sub"], 600, label="sp-sub")
    text(c, 74, 520, "canlı yayın soruları · haftalık challenge", 30, T["mute"], 400, label="sp-sub2")
    c.add(ti_mark(68, 540, 64, KROM))
    c.box("ti-mark", 68 + 12 * .64, 540 + 20 * .64, 68 + 88 * .64, 540 + 76 * .64)
    text(c, 142, 588, "TÜRKİŞİ ENGINEERING", 22, KROM, 700, mono=True, ls=4, fit=False, label="sp-foot")
    # sağ: halka içinde yarı STL / yarı CAD konik dişli, çevresinde lig parçaları, önde KUMPAS
    gx0, gx1, _ = hero(c, 950, 318, 196, line=1.22, ring_w=7)
    dim_line(c, gx0, gx1, 86, GEAR_DIA, size=20)
    part(c, "P19", 1188, 140, 105)
    part(c, "P10", 728, 168, 112)
    part(c, "P05", 738, 548, 128)
    place_kumpas(c, 1032, 388, .41, anim=False)
    return svg_doc(c, "Türkişi CAD Hub", "Türkişi CAD Hub — agentic CAD topluluğu"), c.check()


# ---- 5. org avatarı (500×500, KUMPAS yüzü) ------------------------------------
def org_avatar() -> tuple[str, list[str]]:
    c = Canvas("org-avatar", 500, 500, "dark", margin=0)
    grid_bg(c, "a", step=25, rx=0, frame=False)
    s = 1.08
    c.add(kumpas(250 - 256 * s, 52 - 18 * s, s, anim=False))
    return svg_doc(c, "KUMPAS", "KUMPAS, Türkişi Engineering kumpas-robotu"), []


# ---- 6. karşılama görseli (600×300, 01-buradan-baslayin) ------------------------
def kumpas_welcome() -> tuple[str, list[str]]:
    c = Canvas("kumpas-welcome", 600, 300, "dark", margin=14)
    T = c.T
    grid_bg(c, "w", step=20)
    c.add(gear(560, 268, 54, 12, T["gears"][2], 26, .16, anim=False))
    place_kumpas(c, 22, 64, .43, anim=False)
    bubble(c, 210, 20, 186, 58, ["Hoş geldin! 👋"], 22, (228, 78, 208, 100, 258, 78))
    title_hl(c, 252, 168, 36, "Türkişi", "CAD", "Hub")
    rich(c, 254, 206, [("agentic CAD", T["acc"]), (" topluluğu", T["sub"])], 22, 600, label="w-sub")
    text(c, 254, 248, "Ölçmeden onay yok.", 18, SARI, 700, mono=True, fit=False, label="w-motto")
    return svg_doc(c, "KUMPAS: Hoş geldin!", "KUMPAS: Hoş geldin! Türkişi CAD Hub — agentic CAD topluluğu"), c.check()


# ---- çıktı ---------------------------------------------------------------------
SVG_JOBS = {
    "banner-dark.svg": lambda: banner("dark"),
    "banner-light.svg": lambda: banner("light"),
    "org-banner-dark.svg": lambda: org_banner("dark"),
    "org-banner-light.svg": lambda: org_banner("light"),
    "hub-card-dark.svg": lambda: hub_card("dark"),
    "hub-card-light.svg": lambda: hub_card("light"),
    "src/social-preview.svg": social_preview,
    "src/org-avatar.svg": org_avatar,
    "src/kumpas-welcome.svg": kumpas_welcome,
}
PNG_JOBS = {  # png: (kaynak svg, genişlik, yükseklik, şeffaf köşe)
    "social-preview.png": ("src/social-preview.svg", 1280, 640, False),
    "org-avatar.png": ("src/org-avatar.svg", 500, 500, False),
    "kumpas-welcome.png": ("src/kumpas-welcome.svg", 600, 300, True),
}


def render_pngs() -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge")
        except Exception:
            browser = p.chromium.launch()
        for png, (src, w, h, transparent) in PNG_JOBS.items():
            page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            svg = (OUT / src).read_text(encoding="utf-8")
            page.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            page.wait_for_timeout(150)
            page.screenshot(path=str(OUT / png), clip={"x": 0, "y": 0, "width": w, "height": h},
                            omit_background=transparent)
            page.close()
            print(f"  png  {png:28} {(OUT / png).stat().st_size / 1024:6.1f} KB")
        browser.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="store_true", help="PNG'leri de üret (Playwright gerekir)")
    a = ap.parse_args()
    (OUT / "src").mkdir(exist_ok=True)
    problems = []
    for name, job in SVG_JOBS.items():
        svg, errs = job()
        (OUT / name).write_text(svg, encoding="utf-8")
        problems += errs
        print(f"  svg  {name:28} {len(svg.encode('utf-8')) / 1024:6.1f} KB")
    if a.png:
        render_pngs()
    if problems:
        print("\nYerleşim uyarıları:")
        for e in problems:
            print("  ⚠", e)
        raise SystemExit(1)
    print("ok")


if __name__ == "__main__":
    main()
