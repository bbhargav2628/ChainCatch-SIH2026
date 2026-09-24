"""
Generates a draft investigation report PDF from a stored analysis result.
Careful wording only: "likely VASP endpoint", "investigative lead",
"confidence" — never "confirmed criminal" / "proof of laundering".
"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def build_report_pdf(analysis: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=16, spaceAfter=2)
    sub_style = ParagraphStyle("SubX", parent=styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=10)
    h2 = ParagraphStyle("H2X", parent=styles["Heading2"], spaceBefore=12, spaceAfter=4)
    body = styles["Normal"]
    disclaimer_style = ParagraphStyle(
        "Disc", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#7a2e2e"),
        backColor=colors.HexColor("#fdecea"), borderPadding=6, spaceBefore=10, spaceAfter=10,
    )

    elems = []
    elems.append(Paragraph("ChainCatch — Draft Investigation Summary", title_style))
    elems.append(Paragraph(
        "Prototype output · Smart India Hackathon 2026 · Team CryptoKnights · "
        f"Case ID: {analysis['case_id']}", sub_style
    ))

    elems.append(Paragraph(
        "This is an automatically generated INVESTIGATIVE LEAD, not a legal finding. "
        "Wallet linkage and clustering reflect on-chain behavioural correlation and do "
        "not by themselves prove ownership or criminal intent. All figures below marked "
        "as demo/synthetic data are for prototype demonstration only.",
        disclaimer_style
    ))

    meta_rows = [
        ["Reported wallet", analysis["reported_wallet"]],
        ["Mode", analysis["mode"].upper()],
        ["Chain(s) analyzed", ", ".join(analysis["chains_analyzed"])],
        ["Transactions analyzed", str(analysis["summary"]["total_transactions_analyzed"])],
        ["Relevant transactions", str(analysis["summary"]["relevant_transactions"])],
        ["Hops traced", str(analysis["summary"]["hops_traced"])],
        ["Total funds traced", analysis["summary"]["total_funds_traced"]],
        ["Generated at", analysis["generated_at"]],
    ]
    t = Table(meta_rows, colWidths=[55 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1f6")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7ccd6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(t)

    elems.append(Paragraph("Fund-Flow Trace", h2))
    for e in analysis["graph"]["edges"]:
        line = (f"{e['source_label']} → {e['target_label']}: {e['amount']} {e['asset']} "
                f"on {e['chain']} at {e['timestamp']} (tx {e['tx_hash'][:18]}…)")
        elems.append(Paragraph(line, ParagraphStyle("mono", parent=body, fontSize=8.5, fontName="Courier")))

    if analysis.get("clusters"):
        elems.append(Paragraph("Wallet Clusters (Potentially Related Wallets)", h2))
        for c in analysis["clusters"]:
            elems.append(Paragraph(
                f"<b>{c['cluster_id']}</b> — {len(c['wallet_ids'])} wallets — risk: {c['risk'].upper()}", body
            ))
            items = [ListItem(Paragraph(ch, body)) for ch in c["characteristics"]]
            elems.append(ListFlowable(items, bulletType="bullet", start="circle"))

    if analysis.get("vasp_match"):
        v = analysis["vasp_match"]
        elems.append(Paragraph("Likely VASP Endpoint", h2))
        elems.append(Paragraph(
            f"<b>{v['vasp_id']} — {v['name']}</b> ({v['classification']}) · Chain: {v['chain']} · "
            f"Confidence: {v['confidence']}%", body
        ))
        elems.append(Paragraph(f"Dataset: {v['dataset_label']}", sub_style))
        items = [ListItem(Paragraph(ev, body)) for ev in v["evidence"]]
        elems.append(ListFlowable(items, bulletType="bullet", start="circle"))

    if analysis.get("cross_chain"):
        cc = analysis["cross_chain"]
        elems.append(Paragraph("Cross-Chain Observations", h2))
        elems.append(Paragraph(f"{cc['from_chain']} → {cc['to_chain']} via bridge contract.", body))
        items = [ListItem(Paragraph(ev, body)) for ev in cc["evidence"]]
        elems.append(ListFlowable(items, bulletType="bullet", start="circle"))

    risk = analysis["risk"]
    elems.append(Paragraph("Explainable Risk / Prioritization Score", h2))
    elems.append(Paragraph(
        f"<b>{risk['score']}/100 — {risk['level']}</b> &nbsp;|&nbsp; Confidence: {risk['confidence']}%", body
    ))
    elems.append(Paragraph(
        "This score prioritizes the wallet for investigator review. It is NOT proof of "
        "criminal activity or confirmed money laundering.", disclaimer_style
    ))
    rows = [["Signal", "Weight", "Observed value", "Contribution"]]
    for b in risk["breakdown"]:
        rows.append([b["signal"], f"{b['weight_pct']}%", str(b["value"]), f"{b['contribution']}"])
    t2 = Table(rows, colWidths=[55 * mm, 25 * mm, 35 * mm, 35 * mm])
    t2.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7ccd6")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elems.append(t2)

    elems.append(Paragraph("Supporting Evidence", h2))
    items = [ListItem(Paragraph(r, body)) for r in risk["reasons"]]
    elems.append(ListFlowable(items, bulletType="bullet", start="circle"))

    elems.append(Paragraph("Supporting Transaction Hashes", h2))
    hashes = ", ".join(e["tx_hash"] for e in analysis["graph"]["edges"])
    elems.append(Paragraph(hashes, ParagraphStyle("mono2", parent=body, fontSize=7.5, fontName="Courier")))

    elems.append(Spacer(1, 10))
    elems.append(Paragraph(
        "This report is an investigative lead generated by a hackathon prototype (ChainCatch, "
        "Team CryptoKnights, SIH 2026) using a demo/synthetic dataset in the current run. "
        "It requires human investigator review and, where required, lawful process before any "
        "action is taken against a named entity.", sub_style
    ))

    doc.build(elems)
    return buf.getvalue()
