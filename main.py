#!/usr/bin/env python3
"""Best-looking food picture — a steaming bowl of tonkotsu ramen.

Drawn from scratch with the Python standard library only. No network, no
clock, no randomness: the same input always produces the same PNG bytes.

The picture: a dark ceramic bowl of ramen seen from a high angle on a warm
wooden table — golden broth, wavy noodles, a halved soft egg, chashu pork,
a standing sheet of nori, narutomaki, spring onion, chilli oil, sesame,
chopsticks lifting a noodle clump, and soft steam curling up. Two dried
chillies rest on the table beside the bowl.
"""

import math
import os
import struct
import zlib

SIZE = 1024
OUT_NAME = "entry.png"

# --- palette: warm wood, amber broth, pale noodles ---------------------------
WOOD_TOP = (66, 44, 26)
WOOD_BOT = (38, 23, 13)
WOOD_DARK = (30, 18, 10)
GLOW = (128, 84, 44)
BOWL_OUT = (46, 40, 42)
BOWL_RIM = (74, 64, 66)
BOWL_FOOT = (26, 22, 24)
BROTH_HI = (236, 162, 66)
BROTH_LO = (150, 88, 28)
BROTH_EDGE = (120, 66, 20)
NOODLE_A = (246, 216, 132)
NOODLE_B = (232, 192, 104)
EGG_WHITE = (250, 246, 234)
YOLK = (240, 142, 38)
YOLK_DEEP = (214, 110, 22)
CHASHU = (198, 112, 88)
CHASHU_DARK = (150, 76, 62)
CHASHU_RING = (222, 158, 128)
NORI = (22, 34, 20)
NORI_SHEEN = (58, 86, 52)
NARUTO = (250, 246, 240)
NARUTO_PINK = (240, 122, 142)
ONION = (96, 166, 74)
ONION_DARK = (58, 116, 44)
STICK = (178, 122, 68)
STICK_TIP = (140, 92, 50)
STEAM = (255, 250, 240)
CHILLI = (180, 34, 24)
CHILLI_DARK = (128, 22, 16)
SESAME = (248, 236, 200)


def _clamp01(t):
    return 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)


def _mix3(c1, c2, t):
    """Linear blend of two RGB triples, t=0 -> c1, t=1 -> c2."""
    t = _clamp01(t)
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


class Pic:
    """A plain RGB raster with a few filled-shape tools."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def dot(self, x, y, rgb):
        xi, yi = int(x), int(y)
        if 0 <= xi < self.w and 0 <= yi < self.h:
            o = self._off(xi, yi)
            self.buf[o:o + 3] = bytes(rgb)

    def blend_dot(self, x, y, rgb, a):
        xi, yi = int(x), int(y)
        if 0 <= xi < self.w and 0 <= yi < self.h and a > 0.0:
            if a >= 1.0:
                self.dot(xi, yi, rgb)
                return
            o = self._off(xi, yi)
            ia = 1.0 - a
            self.buf[o] = int(rgb[0] * a + self.buf[o] * ia)
            self.buf[o + 1] = int(rgb[1] * a + self.buf[o + 1] * ia)
            self.buf[o + 2] = int(rgb[2] * a + self.buf[o + 2] * ia)

    def hline(self, y, x0, x1, rgb):
        """Solid horizontal run [x0, x1) on row y (clipped)."""
        yi = int(y)
        if yi < 0 or yi >= self.h:
            return
        a = max(0, int(x0))
        b = min(self.w, int(x1))
        if b <= a:
            return
        o = self._off(a, yi)
        self.buf[o:o + (b - a) * 3] = bytes(rgb) * (b - a)

    def hline_blend(self, y, x0, x1, rgb, a):
        yi = int(y)
        if yi < 0 or yi >= self.h or a <= 0.0:
            return
        lo = max(0, int(x0))
        hi = min(self.w, int(x1))
        if hi <= lo:
            return
        if a >= 1.0:
            self.hline(yi, lo, hi, rgb)
            return
        ia = 1.0 - a
        o = self._off(lo, yi)
        for x in range(lo, hi):
            i = o + (x - lo) * 3
            self.buf[i] = int(rgb[0] * a + self.buf[i] * ia)
            self.buf[i + 1] = int(rgb[1] * a + self.buf[i + 1] * ia)
            self.buf[i + 2] = int(rgb[2] * a + self.buf[i + 2] * ia)

    def hline_grad(self, y, x0, x1, c_left, c_right):
        """Horizontal linear gradient run."""
        yi = int(y)
        if yi < 0 or yi >= self.h:
            return
        a = max(0, int(x0))
        b = min(self.w, int(x1))
        n = b - a
        if n <= 0:
            return
        o = self._off(a, yi)
        out = bytearray(n * 3)
        r, g, bl = float(c_left[0]), float(c_left[1]), float(c_left[2])
        dr = (c_right[0] - r) / n
        dg = (c_right[1] - g) / n
        db = (c_right[2] - bl) / n
        for i in range(n):
            out[i * 3] = int(r)
            out[i * 3 + 1] = int(g)
            out[i * 3 + 2] = int(bl)
            r += dr
            g += dg
            bl += db
        self.buf[o:o + n * 3] = out

    def vfill(self, c_top, c_bot):
        """Fill the whole raster with a vertical gradient."""
        for y in range(self.h):
            t = y / (self.h - 1)
            self.hline(y, 0, self.w, _mix3(c_top, c_bot, t))

    def png_bytes(self):
        """Encode the raster as a PNG (filter 0 rows, zlib level 6)."""
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            raw += self.buf[y * stride:(y + 1) * stride]
        comp = zlib.compress(bytes(raw), 6)

        def chunk(kind, data):
            return (struct.pack(">I", len(data)) + kind + data +
                    struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
                chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# --- shape helpers (module-level, they draw on a Pic) ------------------------


def fill_disc(p, cx, cy, r, rgb, a=1.0):
    """Solid disc, optionally translucent."""
    r = float(r)
    y0 = max(0, int(cy - r))
    y1 = min(p.h - 1, int(cy + r) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / r
        v = 1.0 - dy * dy
        if v <= 0:
            continue
        dx = r * math.sqrt(v)
        if a >= 1.0:
            p.hline(y, cx - dx, cx + dx, rgb)
        else:
            p.hline_blend(y, cx - dx, cx + dx, rgb, a)


def fill_ellipse(p, cx, cy, rx, ry, rgb, a=1.0):
    """Solid axis-aligned ellipse."""
    rx, ry = float(rx), float(ry)
    y0 = max(0, int(cy - ry))
    y1 = min(p.h - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        v = 1.0 - dy * dy
        if v <= 0:
            continue
        dx = rx * math.sqrt(v)
        if a >= 1.0:
            p.hline(y, cx - dx, cx + dx, rgb)
        else:
            p.hline_blend(y, cx - dx, cx + dx, rgb, a)


def ellipse_vgrad(p, cx, cy, rx, ry, c_top, c_bot):
    """Ellipse filled with a vertical gradient."""
    rx, ry = float(rx), float(ry)
    y0 = max(0, int(cy - ry))
    y1 = min(p.h - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        t = (y - (cy - ry)) / (2.0 * ry)
        dy = (y - cy) / ry
        v = 1.0 - dy * dy
        if v <= 0:
            continue
        dx = rx * math.sqrt(v)
        p.hline(y, cx - dx, cx + dx, _mix3(c_top, c_bot, t))


def glow_ellipse(p, cx, cy, rx, ry, bg_top, bg_bot, glow, strength=0.85):
    """Soft warm glow: an ellipse whose centre is `glow` fading to the
    table gradient underneath it, so no edge shows."""
    rx, ry = float(rx), float(ry)
    y0 = max(0, int(cy - ry))
    y1 = min(p.h - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        v = 1.0 - dy * dy
        if v <= 0:
            continue
        bg = _mix3(bg_top, bg_bot, y / (p.h - 1))
        dx = rx * math.sqrt(v)
        mid = _mix3(bg, glow, strength * v)
        p.hline_grad(y, cx - dx, cx, bg, mid)
        p.hline_grad(y, cx, cx + dx, mid, bg)


def fill_poly(p, pts, rgb):
    """Scanline fill of a simple polygon given as [(x, y), ...]."""
    if len(pts) < 3:
        return
    ys = [pt[1] for pt in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(p.h - 1, int(max(ys)) + 1)
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1v = pts[i]
            x2, y2v = pts[(i + 1) % n]
            if (y1v <= y < y2v) or (y2v <= y < y1v):
                t = (y - y1v) / (y2v - y1v)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            p.hline(y, xs[i], xs[i + 1], rgb)


def thick_seg(p, x0, y0, x1, y1, w, rgb):
    """A thick line segment drawn as a quad."""
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    if ln < 1e-6:
        fill_disc(p, x0, y0, w / 2.0, rgb)
        return
    nx, ny = -dy / ln * w / 2.0, dx / ln * w / 2.0
    fill_poly(p, [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                 (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], rgb)


def arc_dots(p, cx, cy, r, a0, a1, rgb, dot_r=3.0):
    """Dots along a circular arc (angles in radians)."""
    steps = max(2, int(abs(a1 - a0) * r / max(2.0, dot_r)))
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        fill_disc(p, cx + r * math.cos(a), cy + r * math.sin(a), dot_r, rgb)


def annulus(p, cx, cy, r_out, r_in, rgb):
    """Ring between two radii."""
    r_out, r_in = float(r_out), float(r_in)
    y0 = max(0, int(cy - r_out))
    y1 = min(p.h - 1, int(cy + r_out) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / r_out
        v = 1.0 - dy * dy
        if v <= 0:
            continue
        dxo = r_out * math.sqrt(v)
        di = (y - cy) / r_in
        vi = 1.0 - di * di
        if vi <= 0:
            p.hline(y, cx - dxo, cx + dxo, rgb)
        else:
            dxi = r_in * math.sqrt(vi)
            p.hline(y, cx - dxo, cx - dxi, rgb)
            p.hline(y, cx + dxi, cx + dxo, rgb)


def spiral(p, cx, cy, r_max, turns, rgb, dot_r=3.0):
    """Archimedean spiral drawn as dots (for narutomaki / chashu)."""
    total = int(r_max * turns * 2.2)
    for i in range(total + 1):
        t = i / total
        a = t * turns * 2.0 * math.pi
        r = r_max * t
        fill_disc(p, cx + r * math.cos(a), cy + r * math.sin(a) * 0.9,
                  dot_r, rgb)


def soft_blob(p, cx, cy, r, rgb, peak):
    """A soft round puff whose alpha falls off smoothly to the edge."""
    r = float(r)
    x0 = max(0, int(cx - r))
    x1 = min(p.w - 1, int(cx + r) + 1)
    y0 = max(0, int(cy - r))
    y1 = min(p.h - 1, int(cy + r) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / r
        for x in range(x0, x1 + 1):
            dx = (x - cx) / r
            d2 = dx * dx + dy * dy
            if d2 >= 1.0:
                continue
            a = peak * (1.0 - d2) * (1.0 - d2)
            if a > 0.01:
                p.blend_dot(x, y, rgb, a)


# --- scene -------------------------------------------------------------------


def _frac(x):
    """Deterministic pseudo-random fraction in [0, 1) from an index."""
    return (math.sin(x * 12.9898) * 43758.5453) % 1.0


def _pick(i, lo, hi):
    return lo + _frac(i) * (hi - lo)


def paint_table(p):
    """Warm wooden table: vertical gradient, plank seams, grain, glow."""
    p.vfill(WOOD_TOP, WOOD_BOT)
    for seam_y in (168, 424, 706, 948):
        p.hline(seam_y, 0, SIZE, WOOD_DARK)
        p.hline(seam_y + 2, 0, SIZE, (52, 34, 20))
    for i in range(26):
        y = int(_pick(i, 20, 1000))
        x0 = int(_pick(i + 100, 0, 500))
        ln = int(_pick(i + 200, 120, 420))
        p.hline_blend(y, x0, x0 + ln, WOOD_DARK, 0.25)
    glow_ellipse(p, 512, 430, 380, 320, WOOD_TOP, WOOD_BOT, GLOW, 0.45)


def paint_bowl(p):
    """Dark ceramic bowl: foot shadow, body, rim, broth."""
    # soft shadow the bowl casts on the table
    fill_ellipse(p, 522, 742, 330, 52, (16, 10, 6), 0.55)
    # bowl body: a slightly lower, darker ellipse peeking under the rim
    fill_ellipse(p, 512, 592, 330, 152, BOWL_FOOT)
    # rim
    fill_ellipse(p, 512, 560, 330, 150, BOWL_OUT)
    annulus(p, 512, 560, 330, 306, BOWL_RIM)
    # rim highlight along the top edge
    arc_dots(p, 512, 560, 318, math.pi * 1.08, math.pi * 1.92,
             (118, 102, 104), 4.0)
    # broth with a vertical golden gradient
    ellipse_vgrad(p, 512, 552, 296, 130, BROTH_HI, BROTH_LO)
    # darker edge ring where broth meets the bowl
    annulus(p, 512, 552, 296, 284, BROTH_EDGE)
    # oil sheen arcs on the broth
    arc_dots(p, 430, 540, 120, math.pi * 1.15, math.pi * 1.75,
             (252, 202, 112), 4.0)
    arc_dots(p, 620, 580, 90, math.pi * 0.05, math.pi * 0.55,
             (252, 202, 112), 4.0)
    # chilli-oil droplets
    for i in range(9):
        x = _pick(i + 31, 250, 770)
        y = _pick(i + 47, 450, 650)
        if ((x - 512) / 280.0) ** 2 + ((y - 552) / 118.0) ** 2 < 0.85:
            fill_disc(p, x, y, _pick(i + 63, 3.5, 6.0), (206, 74, 30))
    # sesame seeds
    for i in range(18):
        x = _pick(i + 71, 250, 770)
        y = _pick(i + 83, 450, 650)
        if ((x - 512) / 285.0) ** 2 + ((y - 552) / 122.0) ** 2 < 0.9:
            fill_disc(p, x, y, 2.5, SESAME)


def noodle_strand(p, y_base, amp, phase, x0=250, x1=774):
    """One wavy noodle strand across the broth, drawn as beads."""
    steps = 96
    for i in range(steps + 1):
        t = i / steps
        x = x0 + t * (x1 - x0)
        y = y_base + amp * math.sin(t * math.pi * 3.0 + phase)
        tone = NOODLE_A if (i // 5) % 2 == 0 else NOODLE_B
        fill_disc(p, x, y, 4.5, tone)


def paint_noodles(p):
    for k, (yb, amp, ph) in enumerate([
            (492, 7, 0.4), (516, 9, 1.9), (540, 6, 3.1),
            (566, 8, 0.9), (592, 7, 2.4), (616, 6, 4.4)]):
        noodle_strand(p, yb, amp, ph)


def onion_ring(p, x, y, r=6.0):
    fill_disc(p, x, y, r, ONION)
    fill_disc(p, x, y, r * 0.42, ONION_DARK)


def paint_toppings(p):
    # halved soft egg, left side
    fill_ellipse(p, 372, 512, 56, 42, EGG_WHITE)
    fill_disc(p, 372, 512, 24, YOLK)
    fill_disc(p, 364, 504, 12, YOLK_DEEP)
    fill_disc(p, 356, 500, 4, (255, 196, 110))
    # two chashu slices, right side, overlapping
    fill_disc(p, 636, 496, 50, CHASHU)
    spiral(p, 636, 496, 40, 2.2, CHASHU_DARK, 3.0)
    annulus(p, 636, 496, 50, 44, CHASHU_RING)
    fill_disc(p, 694, 556, 46, CHASHU)
    spiral(p, 694, 556, 36, 2.2, CHASHU_DARK, 3.0)
    annulus(p, 694, 556, 46, 40, CHASHU_RING)
    # narutomaki near the bottom of the bowl
    fill_disc(p, 470, 648, 28, NARUTO)
    spiral(p, 470, 648, 20, 2.0, NARUTO_PINK, 3.0)
    fill_disc(p, 470, 648, 5, NARUTO_PINK)
    # spring onion rings scattered over the broth
    for i, (x, y) in enumerate([
            (300, 480), (340, 580), (420, 470), (460, 600), (520, 470),
            (560, 620), (600, 470), (660, 630), (720, 500), (750, 570),
            (410, 540), (540, 540), (330, 540), (690, 470), (480, 660),
            (580, 580)]):
        onion_ring(p, x, y, 5.0 + (i % 3))
    # standing nori sheet at the back-right of the bowl
    fill_poly(p, [(640, 360), (686, 348), (710, 466), (664, 478)], NORI)
    fill_poly(p, [(650, 360), (662, 356), (680, 462), (670, 466)],
              NORI_SHEEN)


def paint_chopsticks(p):
    """Two wooden chopsticks from the top-right, lifting a noodle clump."""
    # stick bodies: two parallel quads, tips pointing down-left
    dx, dy = -260.0, 270.0
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln  # unit perpendicular
    for off, tip in [(0.0, (618, 332)), (19.0, (604, 318))]:
        x0, y0 = 880 + nx * off, 60 + ny * off
        x1, y1 = 620 + nx * off, 330 + ny * off
        w = 13.0
        fill_poly(p, [(x0 + nx * w / 2, y0 + ny * w / 2),
                      (x1 + nx * w / 2, y1 + ny * w / 2),
                      (x1 - nx * w / 2, y1 - ny * w / 2),
                      (x0 - nx * w / 2, y0 - ny * w / 2)], STICK)
        # darker band near the tip
        thick_seg(p, x1 - dx / ln * 46, y1 - dy / ln * 46,
                  x1, y1, w * 0.92, STICK_TIP)
    # lifted noodle clump hanging from the tips
    for s in range(7):
        spread = (s - 3) * 9.0
        ph = s * 1.1
        for i in range(26):
            t = i / 25.0
            x = 612 + spread + 7.0 * math.sin(t * math.pi * 2.2 + ph)
            y = 332 + t * 138.0
            tone = NOODLE_A if (i // 3) % 2 == 0 else NOODLE_B
            fill_disc(p, x, y, 4.5, tone)


def paint_steam(p):
    """Four soft steam columns curling up from the bowl."""
    for col, x_base in enumerate([400, 490, 580, 670]):
        for k in range(6):
            t = k / 5.0
            y = 396 - t * 250.0
            x = x_base + 16.0 * math.sin(t * math.pi * 1.6 + col * 1.7)
            r = 18.0 + t * 40.0
            soft_blob(p, x, y, r, STEAM, 0.16 + 0.08 * (1.0 - t))


def paint_table_garnish(p):
    """Two dried chillies, sesame and onion bits resting on the table."""
    for (x0, y0, x1, y1, bend) in [(140, 892, 268, 836, -26),
                                   (196, 936, 312, 902, -18)]:
        steps = 22
        for i in range(steps + 1):
            t = i / steps
            x = x0 + t * (x1 - x0)
            y = y0 + t * (y1 - y0) + bend * math.sin(t * math.pi)
            r = 9.0 * (1.0 - t * 0.55)
            fill_disc(p, x, y, r, CHILLI if i < steps - 4 else CHILLI_DARK)
        thick_seg(p, x0 - 14, y0 + 4, x0 + 2, y0 - 2, 7.0, (96, 84, 48))
    for i in range(12):
        x = _pick(i + 201, 700, 960)
        y = _pick(i + 217, 820, 960)
        fill_disc(p, x, y, 2.5, SESAME)
    for (x, y) in [(820, 780), (860, 800), (780, 830)]:
        onion_ring(p, x, y, 6.0)


def build():
    p = Pic(SIZE, SIZE)
    paint_table(p)
    paint_bowl(p)
    paint_noodles(p)
    paint_toppings(p)
    paint_chopsticks(p)
    paint_steam(p)
    paint_table_garnish(p)
    return p


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = build().png_bytes()
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "wb") as fh:
        fh.write(data)
    print(f"wrote {path}: {len(data)} bytes, {SIZE}x{SIZE}")


if __name__ == "__main__":
    main()
