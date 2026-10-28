#!/usr/bin/env python3
"""Breeds moths and pins them to the two plates in the profile README.

    python3 scripts/moths.py render   redraw plates/, collection.md and the README text from data/
    python3 scripts/moths.py add      pin the issue author's moth; reads LOGIN, TITLE, BODY and OWNER
                                      from the environment and prints GitHub step outputs
    python3 scripts/moths.py avatar   write plates/avatar.svg

Every moth is drawn from a SHA-256 of a seed string, so the same visitor always gets the same moth.
Standard library only, so the Action needs no install step.
"""
import hashlib
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PLATES = ROOT / "plates"

INK = "#2b2520"
PAPER = "#eee6d3"
TAG = "#f8f3e6"
RED_INK = "#8a2f1f"
PENCIL = "#8d8473"
SERIF = "'Iowan Old Style','Palatino Linotype',Palatino,'Book Antiqua',Georgia,'Times New Roman',serif"

# (wing, pattern, accent) sets taken from real families, so a few moths come out vivid
SPECIES = [("#e3c9c4", "#9a4d5c", "#e2c35a"), ("#bcd0a3", "#5e7046", "#9a6a3a"), ("#ebe6da", "#2f2b27", "#c2802e"),
           ("#6f655b", "#d9cdb5", "#c9772e"), ("#d7b25a", "#6a4321", "#7a2a1a"), ("#a7a9a8", "#43464a", "#2f4a5a"),
           ("#c7b9d1", "#5b3f5e", "#e0b35b"), ("#b88a63", "#4d3424", "#d1a14d"), ("#c98f6b", "#5a2e22", "#e8d6a8")]
BASES = ["#c9b48a", "#b79a73", "#d8c8a4", "#a8a07e", "#c7a27c", "#b9b2a0", "#d1b48c",
         "#9fa58a", "#c8bfa7", "#b58f6a", "#bcc8a0", "#cdb79e", "#a99482"]
PATTERNS = ["#6b4f36", "#4d4436", "#7a5a3c", "#5a5e48", "#7b4b3a", "#3f3a33", "#5d4a52"]
ACCENTS = ["#8e3b2e", "#2f4a5a", "#b5782c", "#5b3f5e", "#3d5a3a", "#a0522d", "#6e2a2a"]
GENERA = ["Actias", "Catocala", "Noctua", "Hyalophora", "Saturnia", "Automeris", "Eacles",
          "Smerinthus", "Cerura", "Arctia", "Antheraea", "Zygaena", "Hemaris", "Lithosia"]
VISITOR_SLOTS = 12


def rng_for(seed):
    return random.Random(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big"))


def n(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def pt(x, y):
    return f"{n(x)},{n(y)}"


def mix(a, b, t):
    a, b = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


# ---------------------------------------------------------------- one moth

def forewing(L, r, shape):
    ax = L
    if shape == "sphinx":  # long, narrow and swept back, like a hawk moth
        ay, tx, ty = -L * r.uniform(.22, .32), L * r.uniform(.4, .48), L * r.uniform(.03, .08)
    elif shape == "round":
        ay, tx, ty = -L * r.uniform(.55, .66), L * r.uniform(.72, .8), L * r.uniform(.2, .28)
    else:
        ay, tx, ty = -L * r.uniform(.42, .58), L * r.uniform(.55, .7), L * r.uniform(.08, .2)
    d = f"M2.5,-5 C{pt(L * .25, -L * .42)} {pt(L * .7, ay - L * .08)} {pt(ax, ay)} "
    if r.random() < 0.18:  # falcate: a hooked tip and a hollow outer edge
        d += f"C{pt(ax - L * .14, ay + L * .16)} {pt(tx + L * .04, ty - L * .26)} {pt(tx, ty)} "
    else:
        d += f"C{pt(ax + L * .07 * r.random(), ay + L * .28)} {pt(tx + L * .22, ty - L * .08)} {pt(tx, ty)} "
    d += f"C{pt(tx - L * .22, ty + L * .06)} {pt(L * .12, 5)} 2.5,2 Z"
    return d, (ax, ay), (tx, ty)


def hindwing(H, tail):
    d = f"M2.5,1 C{pt(H * .45, -H * .12)} {pt(H * .98, -H * .02)} {pt(H * .95, H * .28)} "
    if tail:
        d += (f"C{pt(H * .95, H * .55)} {pt(H * .7, H * .85)} {pt(H * .6, H * .95)} "
              f"C{pt(H * .62, H * 1.35)} {pt(H * .8, H * 1.75)} {pt(H * .66, H * 1.95)} "
              f"C{pt(H * .52, H * 2.02)} {pt(H * .44, H * 1.5)} {pt(H * .38, H * 1.0)} ")
    else:
        d += f"C{pt(H * 1.0, H * .62)} {pt(H * .72, H * .98)} {pt(H * .42, H * .95)} "
    d += f"C{pt(H * .2, H * .92)} {pt(2, H * .6)} 1.5,11 Z"
    return d


def zigzag(r, x0, y0, x1, y1, jitter, steps=6):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        j = 0 if i in (0, steps) else r.uniform(-jitter, jitter)
        pts.append(pt(x0 + (x1 - x0) * t + j, y0 + (y1 - y0) * t))
    return "M" + " L".join(pts)


def antenna(r, L, feathered, agent):
    tip = (L * r.uniform(.26, .36), -L * r.uniform(.55, .68))
    if agent:
        mid = (tip[0] * .35, tip[1] * .6)
        s = (f'<path d="M1.2,-10 L{pt(*mid)} L{pt(*tip)}" fill="none" stroke="{INK}" stroke-width=".9"/>'
             f'<rect x="{n(tip[0] - 1.4)}" y="{n(tip[1] - 1.4)}" width="2.8" height="2.8" fill="{INK}"/>')
        return s
    c1 = (2.5, -L * .3)
    s = f'<path d="M1.2,-10 Q{pt(*c1)} {pt(*tip)}" fill="none" stroke="{INK}" stroke-width=".8"/>'
    if feathered:
        ticks = []
        for i in range(2, 16):
            t = i / 16
            x = (1 - t) ** 2 * 1.2 + 2 * (1 - t) * t * c1[0] + t * t * tip[0]
            y = (1 - t) ** 2 * -10 + 2 * (1 - t) * t * c1[1] + t * t * tip[1]
            k = 2.6 * (1 - t) + .6
            ticks.append(f"M{pt(x, y)} l{pt(k, k * .5)} M{pt(x, y)} l{pt(-k * .4, -k * .2)}")
        s += f'<path d="{" ".join(ticks)}" stroke="{INK}" stroke-width=".45" opacity=".8"/>'
    else:
        s += f'<circle cx="{n(tip[0])}" cy="{n(tip[1])}" r="1.1" fill="{INK}"/>'
    return s


def moth(seed, uid, kind="human", flap=False):
    """A moth as an SVG group, its pin (the thorax) at 0,0, about 2*60 px across."""
    r = rng_for(seed)
    agent = kind == "agent"
    shape = r.choice(["broad", "broad", "broad", "sphinx", "round"])
    L = {"sphinx": r.uniform(56, 66), "round": r.uniform(42, 50)}.get(shape, r.uniform(44, 60))
    H = L * {"sphinx": r.uniform(.38, .46), "round": r.uniform(.75, .85)}.get(shape, r.uniform(.55, .75))
    if r.random() < .5:
        base, pat, acc = r.choice(SPECIES)
    else:
        base, pat, acc = r.choice(BASES), r.choice(PATTERNS), r.choice(ACCENTS)
    tail = shape == "broad" and r.random() < 0.18
    fw, apex, tornus = forewing(L, r, shape)
    hw = hindwing(H, tail)
    under = r.random() < 0.3  # a coloured underwing, like Catocala
    hfill = mix(acc, base, .35) if under else mix(base, PAPER, .35)

    defs = (f'<linearGradient id="{uid}g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{n(L)}" y2="0">'
            f'<stop offset="0" stop-color="{mix(base, PAPER, .15)}"/><stop offset="1" stop-color="{mix(base, pat, .3)}"/>'
            f'</linearGradient>'
            f'<clipPath id="{uid}f"><path d="{fw}"/></clipPath><clipPath id="{uid}h"><path d="{hw}"/></clipPath>')

    # hindwing
    h = [f'<path d="{hw}" fill="{hfill}"/>', f'<g clip-path="url(#{uid}h)">']
    if agent:
        h.append(mosaic(r, H * 1.05, H * 2.1 if tail else H * 1.05, H / 7, pat, 0))
    else:
        for k in range(4):
            a = math.radians(-10 + k * 28)
            h.append(f'<path d="M2,3 L{pt(H * 1.1 * math.cos(a), H * 1.1 * math.sin(a))}" stroke="{INK}" stroke-width=".55" opacity=".22"/>')
        if under:
            for k in range(r.randint(1, 2)):
                s = .6 + k * .22
                h.append(f'<path d="{hindwing(H * s, False)}" fill="none" stroke="{INK}" stroke-width="{n(H * .07)}" opacity=".55" transform="translate({n(H * (1 - s) * .25)},0)"/>')
        h.append(f'<path d="{hw}" fill="none" stroke="{pat}" stroke-width="{n(r.uniform(3, 6))}" opacity=".35"/>')
        if r.random() < 0.4:
            cx, cy, rr = H * .55, H * .42, H * r.uniform(.13, .19)
            h.append(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(rr)}" fill="{pat}"/>'
                     f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(rr * .72)}" fill="{acc}"/>'
                     f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(rr * .38)}" fill="{INK}"/>'
                     f'<circle cx="{n(cx - rr * .2)}" cy="{n(cy - rr * .2)}" r="{n(rr * .14)}" fill="{TAG}"/>')
    h.append("</g>")
    h.append(f'<path d="{hw}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-dasharray="1 1.5" opacity=".3"/>')
    h.append(f'<path d="{hw}" fill="none" stroke="{INK}" stroke-width=".85" stroke-linejoin="round"/>')

    # forewing
    f = [f'<path d="{fw}" fill="url(#{uid}g)"/>', f'<g clip-path="url(#{uid}f)">']
    if agent:
        f.append(mosaic(r, L * 1.05, L * .9, L / 9, pat, -L * .7))
        f.append(f'<path d="M3,-2 H{n(L * .45)} V{n(-L * .3)} H{n(L * .8)} M3,1 H{n(L * .3)} V{n(L * .12)} H{n(L * .62)}" '
                 f'fill="none" stroke="{INK}" stroke-width=".7" opacity=".55"/>'
                 f'<circle cx="{n(L * .8)}" cy="{n(-L * .3)}" r="1.3" fill="{INK}" opacity=".6"/>'
                 f'<circle cx="{n(L * .62)}" cy="{n(L * .12)}" r="1.3" fill="{INK}" opacity=".6"/>')
    else:
        for k in range(6):
            t = k / 5
            x, y = apex[0] + (tornus[0] - apex[0]) * t, apex[1] + (tornus[1] - apex[1]) * t
            f.append(f'<path d="M3,-1.5 L{pt(x, y)}" stroke="{INK}" stroke-width=".55" opacity=".22"/>')
        for s in sorted(r.uniform(.28, .82) for _ in range(r.randint(1, 3))):
            d = zigzag(r, L * s, -L * .8, L * s * .82, L * .35, L * .035)
            f.append(f'<path d="{d}" fill="none" stroke="{pat}" stroke-width="{n(r.uniform(.8, 1.7))}" opacity=".75"/>'
                     f'<path d="{d}" fill="none" stroke="{TAG}" stroke-width=".7" opacity=".45" transform="translate(2,0)"/>')
        if r.random() < 0.6:
            f.append(f'<path d="{fw}" fill="none" stroke="{pat}" stroke-width="{n(r.uniform(3, 7))}" opacity=".32"/>')
        if r.random() < 0.3:
            f.append(f'<circle cx="{n(apex[0])}" cy="{n(apex[1])}" r="{n(L * .16)}" fill="{pat}" opacity=".45"/>')
        mark = r.choice(["dot", "ring", "crescent", "none"])
        mx, my = L * .5, -L * .22
        if mark == "dot":
            f.append(f'<circle cx="{n(mx)}" cy="{n(my)}" r="2.2" fill="{pat}"/>')
        elif mark == "ring":
            f.append(f'<circle cx="{n(mx)}" cy="{n(my)}" r="3.2" fill="{TAG}" stroke="{pat}" stroke-width="1.2" opacity=".9"/>')
        elif mark == "crescent":
            f.append(f'<path d="M{pt(mx - 3, my - 2)} Q{pt(mx + 1, my)} {pt(mx - 3, my + 3)}" fill="none" stroke="{pat}" stroke-width="1.6"/>')
        for _ in range(r.randint(0, 22)):
            f.append(f'<circle cx="{n(r.uniform(5, L))}" cy="{n(r.uniform(-L * .6, L * .2))}" r="{n(r.uniform(.4, 1))}" fill="{pat}" opacity=".35"/>')
    f.append("</g>")
    f.append(f'<path d="{fw}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-dasharray="1 1.5" opacity=".3"/>')
    f.append(f'<path d="{fw}" fill="none" stroke="{INK}" stroke-width=".85" stroke-linejoin="round"/>')

    wing = "".join(h) + "".join(f) + antenna(r, L, r.random() < .35, agent)
    if flap:
        wing += ('<animateTransform attributeName="transform" type="scale" values="1 1;.3 1;1 1" '
                 'dur=".22s" repeatCount="indefinite"/>')
    body_c = mix(pat, INK, .3)
    body = (f'<ellipse cx="0" cy="13" rx="3.3" ry="12" fill="{body_c}" stroke="{INK}" stroke-width=".7"/>'
            + "".join(f'<path d="M-3,{n(y)} Q0,{n(y + 1.8)} 3,{n(y)}" fill="none" stroke="{mix(body_c, PAPER, .4)}" stroke-width=".5"/>'
                      for y in (7, 11, 15, 19))
            + (f'<rect x="-4.4" y="-6.5" width="8.8" height="13" rx="2" fill="{body_c}" stroke="{INK}" stroke-width=".7"/>' if agent else
               f'<ellipse cx="0" cy="0" rx="4.4" ry="6.5" fill="{body_c}" stroke="{INK}" stroke-width=".7"/>')
            + f'<circle cx="0" cy="-8.5" r="3" fill="{body_c}" stroke="{INK}" stroke-width=".7"/>')
    pin = (f'<circle cx="0" cy="-1" r="1.7" fill="#1b1714"/>'
           f'<circle cx="-.5" cy="-1.5" r=".55" fill="#fff" opacity=".7"/>') if not flap else ""
    return (f'<defs>{defs}</defs><g id="{uid}w">{wing}</g>'
            f'<use href="#{uid}w" transform="scale(-1,1)"/>{body}{pin}')


def mosaic(r, w, h, s, color, y0):
    cells = []
    y = y0
    while y < y0 + h:
        x = 0.0
        while x < w:
            o = r.choice([0, 0, .22, .45, .7])
            if o:
                cells.append(f'<rect x="{n(x)}" y="{n(y)}" width="{n(s - .6)}" height="{n(s - .6)}" fill="{color}" opacity="{o}"/>')
            x += s
        y += s
    return "".join(cells)


# ---------------------------------------------------------------- plates

def paper(w, h, title, subtitle):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7"/>
    <feColorMatrix values="0 0 0 0 .25  0 0 0 0 .2  0 0 0 0 .12  0 0 0 .9 0"/>
    <feComposite in2="SourceGraphic" operator="in"/>
  </filter>
  <radialGradient id="age" cx=".5" cy=".45" r=".75">
    <stop offset=".6" stop-color="#7a5a30" stop-opacity="0"/><stop offset="1" stop-color="#7a5a30" stop-opacity=".22"/>
  </radialGradient>
  <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
    <feDropShadow dx="2.5" dy="3.5" stdDeviation="2.2" flood-color="#3a2a1a" flood-opacity=".3"/>
  </filter>
</defs>
<rect width="{w}" height="{h}" fill="{PAPER}"/>
<rect width="{w}" height="{h}" filter="url(#grain)" opacity=".16"/>
<rect width="{w}" height="{h}" fill="url(#age)"/>
<rect x="14" y="14" width="{w - 28}" height="{h - 28}" fill="none" stroke="{INK}" stroke-width="1.4"/>
<rect x="20" y="20" width="{w - 40}" height="{h - 40}" fill="none" stroke="{INK}" stroke-width=".5"/>
<g font-family="{SERIF}" fill="{INK}" text-anchor="middle">
  <text x="{w / 2}" y="62" font-size="15" letter-spacing="6">{escape(title)}</text>
  <text x="{w / 2}" y="90" font-size="20" font-style="italic">{escape(subtitle)}</text>
</g>
'''


def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


def tag(cx, y, w, rows, seed):
    """A paper label under a specimen. rows: (text, size, style, colour) from top to bottom."""
    r = rng_for("tag" + seed)
    h = 18 + sum(s * 1.32 for _, s, _, _ in rows)
    out = [f'<g transform="rotate({n(r.uniform(-1.6, 1.6))} {n(cx)} {n(y + h / 2)})">',
           f'<rect x="{n(cx - w / 2)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{TAG}" stroke="{INK}" stroke-width=".6"/>']
    ty = y + 7
    for text, size, style, colour in rows:
        ty += size * 1.32
        extra = ' font-style="italic"' if "i" in style else ""
        extra += ' letter-spacing="1.6"' if "caps" in style else ""
        out.append(f'<text x="{n(cx)}" y="{n(ty - size * .3)}" font-size="{size}" fill="{colour}"{extra}>{escape(text)}</text>')
    out.append("</g>")
    return "".join(out)


def render_works(works):
    cols, cw, top, ch = 4, 236, 104, 300
    w, h = 1000, top + ch * 2 + 64
    x0 = (w - cols * cw) / 2
    s = [paper(w, h, "PLATE  I", "Works of lanternmoth, most of them still kept in jars")]
    s.append(f'<g font-family="{SERIF}" text-anchor="middle">')
    for i, wk in enumerate(works):
        cx = x0 + cw * (i % cols) + cw / 2
        cy = top + ch * (i // cols) + 92
        s.append(f'<g transform="translate({n(cx)},{n(cy)}) scale(1.45)" filter="url(#shadow)">{moth(wk["seed"], f"w{i}")}</g>')
        released = wk.get("public")
        rows = [(f"fig. {i + 1}", 11, "i", PENCIL), (wk["latin"], 17, "i", INK)]
        rows += [(line, 12.5, "", INK) for line in wrap(wk["note"], 31)]
        rows.append((f"released · {wk['public']}" if released else "in a jar", 10, "caps", RED_INK if released else PENCIL))
        s.append(tag(cx, cy + 96, 214, [(t.upper() if "caps" in st else t, z, st, c) for t, z, st, c in rows], wk["seed"]))
    s.append("</g>")
    # fig. 9 got loose
    s.append(f'<g><animateMotion dur="19s" repeatCount="indefinite" rotate="0" '
             f'path="M 1060 {h - 60} C 820 {h - 140}, 600 {h + 10}, 420 {h - 70} S 80 {h - 150}, -80 {h - 40}"/>'
             f'<g transform="scale(.42)">{moth("escaped", "esc", flap=True)}</g></g>')
    s.append(f'<text x="{w - 40}" y="{h - 34}" font-family="{SERIF}" font-size="12.5" font-style="italic" fill="{PENCIL}" '
             f'text-anchor="end">fig. 9 got out before it could be described.</text>')
    s.append("</svg>\n")
    return "".join(s)


def latin(login):
    r = rng_for("genus:" + login.lower())
    ep = re.sub(r"[^a-z]", "", login.lower())[:14] or "anonyma"
    return f"{r.choice(GENERA)} {ep}{'na' if ep.endswith('a') else 'ana'}"


def short(text, width):
    return text if len(text) <= width else text[:width - 1] + "…"


def render_visitors(moths):
    cols, cw, top, ch = 6, 158, 110, 220
    pinned = sorted((m for m in moths if m["no"] > 0), key=lambda m: m["no"])
    keeper = [m for m in moths if m["no"] == 0]
    shown = (keeper + pinned)[-VISITOR_SLOTS:]
    rows_n = 1 if len(shown) < cols else VISITOR_SLOTS // cols
    w, h = 1000, top + ch * rows_n + 50
    x0 = (w - cols * cw) / 2
    s = [paper(w, h, "PLATE  II", "Visitors, pinned with their permission")]
    s.append(f'<g font-family="{SERIF}" text-anchor="middle">')
    next_no = (pinned[-1]["no"] if pinned else 0) + 1
    for slot in range(cols * rows_n):
        cx = x0 + cw * (slot % cols) + cw / 2
        cy = top + ch * (slot // cols) + 62
        if slot < len(shown):
            m = shown[slot]
            s.append(f'<g transform="translate({n(cx)},{n(cy)}) scale(.85)" filter="url(#shadow)">'
                     f'{moth("visitor:" + m["login"].lower(), f"v{slot}", m["kind"])}</g>')
            who = "the keeper" if m["no"] == 0 else "@" + short(m["login"], 22)
            name = latin(m["login"])
            rows = [(f"No. {m['no']}", 10.5, "i", PENCIL), (name, 12 if len(name) <= 21 else 10.5, "i", INK), (who, 11, "", INK)]
            if m["kind"] == "agent":
                rows.append((short("agent" + (f", {m['model']}" if m.get("model") else ""), 26), 10, "i", RED_INK))
            rows.append((m["date"], 10, "", PENCIL))
            s.append(tag(cx, cy + 66, 140, rows, m["login"]))
        else:
            s.append(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="34" fill="none" stroke="{PENCIL}" stroke-width=".7" stroke-dasharray="2 4" opacity=".7"/>'
                     f'<circle cx="{n(cx)}" cy="{n(cy - 1)}" r="1.7" fill="#1b1714"/>')
            label = f"No. {next_no}" if slot == len(shown) else ""
            s.append(tag(cx, cy + 66, 140, [(label or " ", 10.5, "i", PENCIL), ("vacant", 12, "i", PENCIL)], f"vacant{slot}"))
    s.append("</g>")
    total = len(pinned)
    note = "No visitors yet. No. 1 is still free." if total == 0 else f"{total} visitor{'s' if total != 1 else ''} so far. The full drawer is in collection.md."
    s.append(f'<text x="{w / 2}" y="{h - 34}" font-family="{SERIF}" font-size="12.5" font-style="italic" fill="{PENCIL}" text-anchor="middle">{escape(note)}</text>')
    s.append("</svg>\n")
    return "".join(s)


def render_avatar():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="460" height="460" viewBox="0 0 460 460">'
            f'<rect width="460" height="460" fill="{PAPER}"/>'
            f'<g transform="translate(230 228) scale(3.1)">{moth("keeper", "a")}</g></svg>\n')


# ---------------------------------------------------------------- text versions and the README

def replace_between(text, name, body):
    return re.sub(rf"(<!-- {name}:start -->).*?(<!-- {name}:end -->)", lambda m: f"{m[1]}\n{body}\n{m[2]}", text, flags=re.S)


def render():
    works = json.loads((DATA / "works.json").read_text())
    moths = json.loads((DATA / "moths.json").read_text())
    PLATES.mkdir(exist_ok=True)
    (PLATES / "works.svg").write_text(render_works(works))
    (PLATES / "visitors.svg").write_text(render_visitors(moths))

    rows = ["| No. | Species | Visitor | Pinned |", "| --- | --- | --- | --- |"]
    for m in sorted(moths, key=lambda m: m["no"]):
        who = "the keeper" if m["no"] == 0 else f"[@{m['login']}](https://github.com/{m['login']})"
        kind = " (agent" + (f", {m['model']}" if m.get("model") else "") + ")" if m["kind"] == "agent" else ""
        rows.append(f"| {m['no']} | *{latin(m['login'])}* | {who}{kind} | {m['date']} |")
    (ROOT / "collection.md").write_text("# The drawer\n\nEvery moth pinned so far, oldest first.\n\n" + "\n".join(rows) + "\n")

    readme = (ROOT / "README.md").read_text()
    work_text = "\n".join(f"{i + 1}. *{w['latin']}*: {w['note']}" + (f" Public: [{w['public']}](https://github.com/TUNA-NOPE/{w['public']})." if w.get("public") else " Private.")
                          for i, w in enumerate(works))
    readme = replace_between(readme, "works", work_text)
    visitors = [m for m in moths if m["no"] > 0]
    vis_text = ("Nobody yet." if not visitors else
                ", ".join(f"No. {m['no']} @{m['login']}" for m in sorted(visitors, key=lambda m: -m["no"])[:12]))
    readme = replace_between(readme, "visitors", vis_text)
    readme = re.sub(r"plates/visitors\.svg(\?n=\d+)?", f"plates/visitors.svg?n={len(moths)}", readme)
    (ROOT / "README.md").write_text(readme)


def add():
    login, title = os.environ["LOGIN"], os.environ.get("TITLE", "").strip().lower()
    body, owner = os.environ.get("BODY") or "", os.environ.get("OWNER", "")
    kind = "agent" if title == "moth|agent" else "human"
    model = None
    if kind == "agent":
        m = re.search(r"^\s*model\s*:\s*([A-Za-z0-9 ._\-]{1,32}?)\s*$", body, re.M | re.I)
        model = m[1] if m else None
    moths = json.loads((DATA / "moths.json").read_text())
    have = next((m for m in moths if m["login"].lower() == login.lower()), None)
    if have:
        msg = f"You already have one: No. {have['no']}, *{latin(login)}*. One moth per visitor."
        print(f"status=exists\nno={have['no']}\nmessage={msg}")
        return
    no = 0 if login.lower() == owner.lower() else max([m["no"] for m in moths] + [0]) + 1
    date = datetime.now(timezone.utc)
    roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][date.month - 1]
    moths.append({"no": no, "login": login, "kind": kind, "model": model, "date": f"{date.day}.{roman}.{date.year}"})
    (DATA / "moths.json").write_text(json.dumps(moths, indent=2) + "\n")
    render()
    msg = (f"Pinned. No. {no}, *{latin(login)}*, is on the plate at https://github.com/{owner}. "
           "GitHub caches images, so it can take a few minutes to show up.")
    print(f"status=pinned\nno={no}\nmessage={msg}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "add":
        add()
    elif cmd == "avatar":
        PLATES.mkdir(exist_ok=True)
        (PLATES / "avatar.svg").write_text(render_avatar())
    else:
        render()
