import html
import io
import json

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def lineage_svg(lineage: dict) -> str:
    groups = {"upload": [], "mapping": [], "record_set": [], "metric": []}
    for node in lineage["nodes"]:
        groups.setdefault(node["type"], []).append(node)
    positions = {}
    columns = {"upload": 70, "mapping": 310, "record_set": 565, "metric": 820}
    for node_type, nodes in groups.items():
        for index, node in enumerate(nodes):
            positions[node["id"]] = (columns.get(node_type, 70), 55 + index * 70)
    lines = []
    for edge in lineage["edges"]:
        if edge["source"] in positions and edge["target"] in positions:
            sx, sy = positions[edge["source"]]
            tx, ty = positions[edge["target"]]
            lines.append(f'<path d="M {sx + 160} {sy + 20} C {sx + 195} {sy + 20}, {tx - 35} {ty + 20}, {tx} {ty + 20}" fill="none" stroke="#8fb9b7" stroke-width="2"/>')
    nodes = []
    colors_by_type = {"upload": "#e8f1f5", "mapping": "#eef8f6", "record_set": "#0b1938", "metric": "#078884"}
    for node in lineage["nodes"]:
        x, y = positions[node["id"]]
        fill = colors_by_type.get(node["type"], "#ffffff")
        text_color = "#ffffff" if node["type"] in {"record_set", "metric"} else "#0b1938"
        label = html.escape(str(node["label"]))
        nodes.append(f'<g><rect x="{x}" y="{y}" width="160" height="40" rx="8" fill="{fill}" stroke="#b7c7d1"/><text x="{x + 12}" y="{y + 25}" fill="{text_color}" font-size="12" font-family="Arial">{label[:24]}</text></g>')
    height = max([position[1] for position in positions.values()] + [80]) + 70
    return f'<svg viewBox="0 0 1060 {height}" role="img" aria-label="Data lineage graph">{"".join(lines)}{"".join(nodes)}</svg>'


def report_html(data: dict, shared: bool = False) -> str:
    metric_blocks = "".join(f'<article class="metric"><span>{html.escape(item["name"])}</span><strong>{html.escape(str(item["value"]))}</strong><p>{html.escape(item["description"])}</p><code>{html.escape(json.dumps(item["formula"]))}</code><p class="caveat">{html.escape(" · ".join(item["caveats"]))}</p></article>' for item in data["metrics"]) or '<p class="empty">No metrics have been computed yet.</p>'
    record_blocks = "".join(f'<details><summary><span>{html.escape(item["pseudonym"])}</span><span>{html.escape(item["source"])}</span></summary><dl><dt>Program</dt><dd>{html.escape(str(item["values"].get("program_name", "Not provided")))}</dd><dt>Date</dt><dd>{html.escape(str(item["values"].get("activity_date", "Missing")))}</dd><dt>Source record ID</dt><dd><code>{html.escape(item["source_record_id"])}</code></dd></dl></details>' for item in data["contributing_records"])
    gaps = "".join(f'<li><span>{html.escape(item["label"])}</span><strong>{item["count"]}</strong></li>' for item in data["data_gaps"])
    audit_rows = "".join(f'<tr><td>{html.escape(item["action"].replace("_", " ").title())}</td><td>{html.escape(item["actor"])}</td><td>{html.escape(item["created_at"])}</td><td><code>{html.escape(item["entity_id"])}</code></td></tr>' for item in data["audit_trail"])
    shared_label = '<span class="shared">Read-only shared report</span>' if shared else ""
    graph = lineage_svg(data.get("lineage", {"nodes": [], "edges": []}))
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Impact Ledger report</title><style>:root{{--ink:#0b1938;--teal:#078884;--muted:#66758e;--border:#dbe3ea;--paper:#f6f8fa}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Arial,sans-serif}}main,header,footer{{max-width:1180px;margin:auto}}header{{padding:48px 28px 26px;border-bottom:1px solid var(--border)}}h1{{font-size:38px;margin:0;letter-spacing:-.04em}}header p{{color:var(--muted)}}.shared{{display:inline-block;padding:5px 9px;border:1px solid var(--border);border-radius:6px;color:var(--teal);font-size:12px;font-weight:700}}main{{padding:28px}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}.metric,.panel{{background:white;border:1px solid var(--border);border-radius:10px;padding:20px}}.metric span{{color:var(--muted)}}.metric strong{{display:block;font-size:38px}}code{{font-size:11px}}.caveat{{color:#a45b00}}.panel{{margin-top:18px}}.gaps{{padding:0;list-style:none;max-width:620px}}.gaps li{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}}svg{{width:100%;height:auto;min-height:220px}}details{{border-top:1px solid var(--border)}}summary{{display:flex;justify-content:space-between;padding:13px 0;cursor:pointer}}dl{{display:grid;grid-template-columns:150px 1fr;margin:0 0 15px}}dt{{color:var(--muted)}}dd{{margin:0}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid var(--border)}}footer{{padding:20px 28px 42px;color:var(--muted);font-size:12px}}@media(max-width:650px){{h1{{font-size:30px}}summary{{gap:12px;flex-direction:column}}.panel{{overflow-x:auto}}}}@media print{{body{{background:white}}.panel,.metric{{break-inside:avoid}}}}</style></head><body><header>{shared_label}<h1>Source-linked report</h1><p>Every figure stays connected to its evidence.</p></header><main><section class="metrics">{metric_blocks}</section><section class="panel"><h2>Data gaps &amp; assumptions</h2><ul class="gaps">{gaps}</ul></section><section class="panel"><h2>Data lineage</h2><p>Raw files flow through confirmed mappings and the reviewed record set before contributing to metrics.</p>{graph}</section><section class="panel"><h2>Source-record drill-down</h2>{record_blocks}</section><section class="panel"><h2>Transformation audit trail</h2><table><thead><tr><th>Action</th><th>Actor</th><th>Time</th><th>Entity</th></tr></thead><tbody>{audit_rows}</tbody></table></section></main><footer>{html.escape(data["privacy_note"])} Generated {html.escape(data["generated_at"])}</footer></body></html>'''


def lineage_drawing(lineage: dict) -> Drawing:
    drawing = Drawing(470, 120)
    columns = [(10, "Raw files"), (130, "Mappings"), (250, "Reviewed set"), (370, "Metrics")]
    for index, (x, label) in enumerate(columns):
        fill = colors.HexColor("#0B1938") if index == 2 else colors.HexColor("#E8F5F3")
        text = colors.white if index == 2 else colors.HexColor("#0B1938")
        drawing.add(Rect(x, 45, 90, 34, 6, 6, fillColor=fill, strokeColor=colors.HexColor("#AFC3CE")))
        drawing.add(String(x + 10, 58, label, fontSize=8, fillColor=text))
        if index < len(columns) - 1:
            drawing.add(Line(x + 90, 62, columns[index + 1][0], 62, strokeColor=colors.HexColor("#078884"), strokeWidth=2))
    drawing.add(String(10, 17, f'{len(lineage.get("nodes", []))} nodes · {len(lineage.get("edges", []))} traceable relationships', fontSize=8, fillColor=colors.HexColor("#66758E")))
    return drawing


def report_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Source-linked report", styles["Title"]), Paragraph("Every figure stays connected to its evidence.", styles["BodyText"]), Spacer(1, 6 * mm)]
    for metric in data["metrics"]:
        elements.extend([Paragraph(f'{html.escape(metric["name"])}: <b>{html.escape(str(metric["value"]))}</b>', styles["Heading2"]), Paragraph(html.escape(metric["description"]), styles["BodyText"]), Paragraph(html.escape(json.dumps(metric["formula"])), styles["Code"]), Paragraph(html.escape("; ".join(metric["caveats"]) or "No recorded caveats"), styles["BodyText"]), Spacer(1, 3 * mm)])
    elements.extend([Paragraph("Data gaps & assumptions", styles["Heading2"]), Table([[item["label"], str(item["count"])] for item in data["data_gaps"]], colWidths=[130 * mm, 25 * mm], style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("PADDING", (0, 0), (-1, -1), 6)])), Spacer(1, 5 * mm), Paragraph("Data lineage", styles["Heading2"]), lineage_drawing(data.get("lineage", {})), Paragraph("Contributing records", styles["Heading2"])])
    rows = [["Pseudonym", "Program", "Date", "Source", "Record ID"]] + [[item["pseudonym"], str(item["values"].get("program_name", "")), str(item["values"].get("activity_date", "")), item["source"], item["source_record_id"][:10]] for item in data["contributing_records"]]
    elements.append(Table(rows, repeatRows=1, colWidths=[34 * mm, 30 * mm, 25 * mm, 52 * mm, 20 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1938")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("FONTSIZE", (0, 0), (-1, -1), 7), ("PADDING", (0, 0), (-1, -1), 4)])))
    elements.extend([Spacer(1, 5 * mm), Paragraph(html.escape(data["privacy_note"]), styles["BodyText"])])
    document.build(elements)
    return buffer.getvalue()
