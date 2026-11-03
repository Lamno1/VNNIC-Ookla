"""Figure 1 (analytical framework) for the next manuscript revision: left-to-right pipeline with pictograms.
Pictograms are schematic (no data). The map is the 63-province frame used in the analysis (read from the canonical boundary file; drawn only)."""
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Rectangle, Circle, Wedge
from pathlib import Path

H = Path(__file__).parent; O = H / "figures_rev15"; O.mkdir(exist_ok=True)
GJ = Path(r"D:\Q1_RESEARCH\GIS_DERIVED\CANONICAL_ADM1_63.geojson")
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "STIXGeneral"], "mathtext.fontset": "stix"})
BLUE, ORNG, INK, GREY = "#0072B2", "#D55E00", "#222222", "#6b6b6b"
LVL, SUP, BND, PAN = "#DCE9F7", "#ECECEC", "#FBEFD2", "#F5F7FA"

fig = plt.figure(figsize=(6.6, 4.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 69.7); ax.axis("off")


def box(x, y, w, h, fc="white", ec=INK, lw=0.9, ls="-", r=1.2, z=2, alpha=1):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, alpha=alpha); ax.add_patch(p); return p


def arrow(a, b, ls="-", lw=1.1, c="#444444", rad=0.0, z=5):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=8, lw=lw, color=c, ls=ls, connectionstyle=f"arc3,rad={rad}", zorder=z, shrinkA=0, shrinkB=0))


def tx(x, y, s, size=7.5, w="normal", c=INK, ha="center", va="center", st="normal", z=6):
    ax.text(x, y, s, fontsize=size, fontweight=w, color=c, ha=ha, va=va, fontstyle=st, zorder=z)


def stage(x, w, num, title):
    ax.add_patch(Circle((x + 1.6, 66.6), 1.5, fc=INK, ec="none", zorder=6)); tx(x + 1.6, 66.55, str(num), 7, "bold", "white")
    tx(x + 3.7, 66.6, title, 8, "bold", INK, ha="left")
    ax.plot([x, x + w], [64.6, 64.6], color="#bbbbbb", lw=0.7, zorder=1)


# ---------- stage headers
stage(0.5, 19, 1, "Two sources")
stage(25.5, 19.5, 2, "Common frame")
stage(50.5, 49, 3, "Four levels of agreement")

# ---------- 1 sources
def source(y, col, name, sub, icon):
    box(0.5, y, 19, 17, fc="white", ec=col, lw=1.4)
    icon(10, y + 12.2)
    tx(10, y + 6.3, name, 7.6, "bold"); tx(10, y + 3.7, sub[0], 6.4, c="#444444"); tx(10, y + 1.7, sub[1], 6.4, c="#444444")


def gauge(cx, cy):
    ax.add_patch(Wedge((cx, cy - 1.8), 4.6, 0, 180, width=1.3, fc="#cfe3f3", ec=BLUE, lw=0.8, zorder=4))
    ax.add_patch(Wedge((cx, cy - 1.8), 4.6, 100, 180, width=1.3, fc="#cfe3f3", ec=BLUE, lw=0.8, zorder=4))
    ax.add_patch(Wedge((cx, cy - 1.8), 4.6, 40, 100, width=1.3, fc=BLUE, ec=BLUE, lw=0.8, zorder=4, alpha=0.55))
    ax.plot([cx, cx + 3.0], [cy - 1.8, cy + 1.2], color=INK, lw=1.4, zorder=5, solid_capstyle="round"); ax.add_patch(Circle((cx, cy - 1.8), 0.6, fc=INK, zorder=5))
    ax.plot([cx - 5.4, cx + 5.4], [cy - 3.3, cy - 3.3], color=BLUE, lw=0.9, zorder=4)


def tiles(cx, cy):
    rng = np.random.default_rng(3); sh = ["#fbe0cc", "#f6b98d", "#ee9556", ORNG]
    for i in range(5):
        for j in range(4):
            ax.add_patch(Rectangle((cx - 5 + i * 2, cy - 4 + j * 2), 1.8, 1.8, fc=sh[int(rng.integers(0, 4))], ec="white", lw=0.4, zorder=4))
    ax.add_patch(Circle((cx + 2.8, cy + 1.2), 0.65, fc=INK, ec="white", lw=0.5, zorder=5))


source(44.5, BLUE, "VNNIC i-Speed", ("FTTH, province\u2013month,", "April to June"), gauge)
source(25.5, ORNG, "Ookla Open Data", ("tile\u2013quarter,", "second quarter"), tiles)
arrow((19.5, 53), (25.2, 40), c=BLUE, rad=0.0); arrow((19.5, 34), (25.2, 40), c=ORNG, rad=0.0)

# ---------- 2 common frame: real 63-province map
box(25.5, 25.5, 19.5, 37.3, fc=PAN, ec=INK, lw=0.9)
g = json.load(open(GJ, encoding="utf-8")); LAT0, LAT1, LON0, LON1 = 8.4, 23.6, 102.0, 110.0
k = np.cos(np.radians(16)); sc = 28.0 / (LAT1 - LAT0)
def prj(lon, lat): return 29.2 + (lon - LON0) * k * sc, 32.0 + (lat - LAT0) * sc
def rings(geom):
    if geom["type"] == "Polygon": yield geom["coordinates"][0]
    else:
        for p in geom["coordinates"]: yield p[0]
for f in g["features"]:
    for r in rings(f["geometry"]):
        r = np.array(r)
        if r[:, 0].min() > 110: continue
        ax.add_patch(Polygon(np.array([prj(a, b) for a, b in r]), closed=True, fc="#d6e2ee", ec="white", lw=0.35, zorder=3))
tx(35.25, 29.6, "63 historical provinces", 7.4, "bold"); tx(35.25, 27.4, "2021\u20132024", 6.6, c="#444444")
tx(35.25, 60.6, "one frame for both sources", 6.6, c="#444444", st="italic")
arrow((45, 40), (50.2, 40), c="#444444")

# ---------- 3 levels: 2x2 cards with pictograms
def card(x, y, tag, name, q, icon):
    box(x, y, 23.8, 19.6, fc=LVL, ec=INK, lw=0.9)
    icon(x + 6.4, y + 12.1)
    tx(x + 12.6, y + 15.0, tag, 8.4, "bold", ha="left"); [tx(x + 12.6, y + 12.2 - 2.4 * i, s, 6.7, "bold", ha="left") for i, s in enumerate(name.split("|"))]
    tx(x + 11.9, y + 3.6, q, 6.4, c="#333333")


def glyph_dir(cx, cy):
    arrow((cx - 2.6, cy - 3), (cx - 2.6, cy + 3.2), c=BLUE, lw=1.8); arrow((cx + 2.6, cy - 3), (cx + 2.6, cy + 3.2), c=ORNG, lw=1.8)


def glyph_disp(cx, cy):
    rng = np.random.default_rng(5)
    for yy, col, s in ((cy + 1.8, BLUE, 3.0), (cy - 1.8, ORNG, 1.1)):
        ax.plot([cx - 5, cx + 5], [yy, yy], color="#bbbbbb", lw=0.6, zorder=3)
        xs = rng.normal(0, s, 9); ax.scatter(cx + np.clip(xs, -4.6, 4.6), yy + rng.uniform(-0.5, 0.5, 9), s=7, color=col, zorder=4, lw=0)


def glyph_rank(cx, cy):
    ax.plot([cx - 4, cx - 4, cx + 4.4], [cy + 3.6, cy - 3.2, cy - 3.2], color=INK, lw=0.8, zorder=3)
    rng = np.random.default_rng(7); xs = np.linspace(-3, 3.4, 11); ys = xs * 0.9 + rng.normal(0, 1.1, 11)
    ax.scatter(cx + xs, cy + ys * 0.9, s=8, color=INK, zorder=4, lw=0); ax.plot([cx - 3, cx + 3.4], [cy - 2.7, cy + 3.0], color=GREY, lw=0.7, ls="--", zorder=3)


def glyph_chg(cx, cy):
    h = [5.4, 4.2, 3.2, 2.0, 1.0]
    for i, v in enumerate(h): ax.add_patch(Rectangle((cx - 4.6 + i * 2, cy - 3.2), 1.5, v, fc=[BLUE, BLUE, "#7fb2d8", "#7fb2d8", "#bcd5ea"][i], zorder=4))
    ax.plot([cx - 5, cx + 5], [cy - 3.2, cy - 3.2], color=INK, lw=0.8, zorder=4)


card(50.5, 43.5, "L1", "Direction", "same sign of change?", glyph_dir)
card(75.7, 43.5, "L2", "Dispersion", "same spread across provinces?", glyph_disp)
card(50.5, 22.6, "L3", "Provincial|ranking", "same ranking within a year?", glyph_rank)
card(75.7, 22.6, "L4", "Change|ranking", "same order of speed gains?", glyph_chg)

# ---------- supporting analyses (dashed) under the levels
box(50.5, 3.0, 49, 17.0, fc="white", ec=GREY, lw=0.9, ls=(0, (4, 2)))
tx(52.3, 17.7, "Supporting analyses: add no further level", 6.8, "bold", GREY, ha="left")
# stress tests (three small icons)
def mini(cx, cy, kind):
    if kind == "t":
        ax.add_patch(Circle((cx, cy), 1.9, fc="white", ec=INK, lw=0.8, zorder=4)); ax.plot([cx, cx], [cy, cy + 1.3], color=INK, lw=0.8, zorder=5); ax.plot([cx, cx + 1.0], [cy, cy - 0.5], color=INK, lw=0.8, zorder=5)
    elif kind == "a":
        for i, v in enumerate((1.2, 2.4, 1.8)): ax.add_patch(Rectangle((cx - 1.9 + i * 1.35, cy - 1.8), 1.0, v, fc=INK, zorder=4))
    else:
        for i in range(3): ax.add_patch(Rectangle((cx - 1.9 + i * 1.4, cy - 1.8 + (i % 2) * 0.6), 1.1, 1.1 + i * 0.7, fc="#9a9a9a", ec=INK, lw=0.5, zorder=4))
for i, (kd, nm) in enumerate((("t", "timing"), ("a", "aggregation"), ("c", "composition"))):
    cx = 55.2 + i * 8.6; mini(cx, 11.4, kd); tx(cx, 7.1, nm, 6.2, c="#333333")
ax.plot([79.6, 79.6], [5.2, 15.4], color="#cccccc", lw=0.7, zorder=3)
tx(67.3, 15.0, "sensitivity checks", 6.5, "bold", INK)
tx(89.6, 15.0, "context (exploratory)", 6.5, "bold", INK)
tx(89.6, 10.9, "noise reference", 6.5, c="#333333"); tx(89.6, 8.5, "outside indicators", 6.5, c="#333333")
tx(89.6, 5.6, "not accuracy criteria", 5.9, c=GREY, st="italic")
arrow((74.8, 20.2), (74.8, 22.2), ls=(0, (3, 2)), c=GREY, lw=0.9)

# ---------- boundary bar (bottom of frame/sources columns)
box(0.5, 3.0, 44.5, 19.0, fc=BND, ec=INK, lw=0.9)
ax.add_patch(Polygon([(2.8, 17.6), (6.4, 17.6), (4.6, 20.7)], closed=True, fc="#E69F00", ec=INK, lw=0.7, zorder=4)); tx(4.6, 18.5, "!", 6.3, "bold")
tx(8.4, 19.4, "Interpretation boundary", 8, "bold", ha="left")
for i, s in enumerate(("No independent criterion is available.", "The study describes how agreement varies", "with source, window and aggregation;", "it does not conclude which source is", "more accurate.")):
    tx(2.4, 14.6 - i * 2.35, s, 6.6, ha="left", c="#2a2a2a")
arrow((50.3, 11.5), (45.2, 11.5), c="#444444")

fig.savefig(O / "fig1_framework.png", dpi=300); fig.savefig(O / "fig1_framework.pdf"); print("ok")
