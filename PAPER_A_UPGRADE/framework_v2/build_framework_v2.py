"""Builds framework_v2.drawio and framework_v2_view.html (viewer page) in this folder.
Simple conceptual framework: teacher's four levels kept, a diagnosis layer added."""
import json, html, pathlib
from xml.sax.saxutils import escape
H = pathlib.Path(__file__).parent
cells, eid = [], [1]
def nid():
    eid[0] += 1; return f"n{eid[0]}"
def box(x, y, w, h, title, sub="", fill="#FFFFFF", stroke="#555555", bold=True):
    i = nid()
    t = f"<b>{escape(title)}</b>" if bold else escape(title)
    if sub: t += f"<br><font style=\"font-size:11px\">{escape(sub)}</font>"
    st = f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fontSize=13;fontColor=#222222;fillColor={fill};strokeColor={stroke};strokeWidth=1.2;"
    cells.append(f'<mxCell id="{i}" value="{escape(t, {chr(34): "&quot;"})}" style="{st}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return i
def arrow(a, b):
    i = nid()
    cells.append(f'<mxCell id="{i}" style="endArrow=block;endFill=1;html=1;strokeColor=#333333;strokeWidth=1.3;" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')
def text(x, y, w, h, t, size=11, color="#444444", align="center", italic=False):
    i = nid()
    st = f"text;html=1;whiteSpace=wrap;align={align};verticalAlign=middle;fontSize={size};fontColor={color};{'fontStyle=2;' if italic else ''}"
    cells.append(f'<mxCell id="{i}" value="{escape(t)}" style="{st}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')

BLUE, TEAL, AMBER = "#DCE9F7", "#D9F0EA", "#FBEFD2"
text(0, 5, 900, 30, "Agreement-and-Diagnosis Framework for Provincial Broadband Measurement", 15, "#111111")
text(0, 32, 900, 22, "VNNIC i-Speed and Ookla, 63 historical provinces, 2021–2024", 11)
v = box(150, 70, 220, 70, "VNNIC i-Speed", "province-month")
o = box(530, 70, 220, 70, "Ookla", "tile-quarter")
f = box(300, 190, 300, 70, "COMMON FRAME", "63 historical provinces")
arrow(v, f); arrow(o, f)
xs = [25, 245, 465, 685]
lv = [box(x, 320, 190, 75, t, s, BLUE) for x, (t, s) in zip(xs, [("L1 Direction", "same sign of change?"), ("L2 Dispersion", "same spread?"), ("L3 Rank", "same order within a year?"), ("L4 Change order", "same order of gains?")])]
for l in lv: arrow(f, l)
d = box(300, 460, 300, 65, "DIAGNOSE DISAGREEMENT", "four questions", TEAL)
for l in lv: arrow(l, d)
dg = [box(x, 595, 190, 85, t, s, TEAL) for x, (t, s) in zip(xs, [("Ceiling", "agreement possible given each source's own repeatability"), ("Where and when", "which windows and months drive it?"), ("Shared or specific", "one source or both? participation, composition"), ("Outside anchors", "NSO, DTI: not speed measures")])]
for g in dg: arrow(d, g)
c = box(275, 735, 350, 75, "CLAIM BOUNDARY", "describe agreement and its sources; no claim on accuracy", AMBER)
for g in dg: arrow(g, c)
text(0, 830, 900, 36, "Blue: four consistency levels. Teal: diagnosis layer added to the baseline framework. Levels become stricter from L1 to L4.", 11, "#555555", italic=True)
xml = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + '</root></mxGraphModel>'
(H / "framework_v2.drawio").write_text(f'<mxfile><diagram name="framework_v2">{xml}</diagram></mxfile>', encoding="utf-8")
cfg = html.escape(json.dumps({"highlight": "#0000ff", "nav": False, "resize": True, "toolbar": "", "xml": xml}))
(H / "framework_v2_view.html").write_text(f'<!doctype html><html><body style="margin:0;background:#fff"><div class="mxgraph" style="max-width:100%" data-mxgraph="{cfg}"></div><script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script></body></html>', encoding="utf-8")
print("ok", len(cells))
