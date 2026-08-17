"""
PDF Export — generates downloadable tender detail PDF.
GET /api/tenders/{tender_id}/pdf
Install: pip install reportlab
"""
import json
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.tender import Tender

router = APIRouter(prefix="/tenders", tags=["pdf"])


@router.get("/{tender_id}/pdf")
async def export_tender_pdf(tender_id: str, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        DARK   = HexColor("#0f172a")
        TEAL   = HexColor("#14b8a6")
        GRAY   = HexColor("#64748b")
        RED    = HexColor("#ef4444")
        WHITE  = white

        title_style = ParagraphStyle("title", fontSize=16, textColor=TEAL,
                                     spaceAfter=6, fontName="Helvetica-Bold")
        h2_style    = ParagraphStyle("h2", fontSize=12, textColor=TEAL,
                                     spaceAfter=4, fontName="Helvetica-Bold")
        body_style  = ParagraphStyle("body", fontSize=10, textColor=black,
                                     spaceAfter=4, fontName="Helvetica", leading=14)
        small_style = ParagraphStyle("small", fontSize=8, textColor=GRAY,
                                     fontName="Helvetica")
        label_style = ParagraphStyle("label", fontSize=9, textColor=GRAY,
                                     fontName="Helvetica-Bold")

        def fmt_inr(val):
            if not val: return "N/A"
            cr = val / 10_000_000
            return f"₹{cr:.1f}Cr" if cr >= 1 else f"₹{val/100000:.1f}L"

        def fmt_date(d):
            if not d: return "N/A"
            if isinstance(d, str): return d[:10]
            return d.strftime("%d %b %Y")

        def parse_json_list(s):
            if not s: return []
            try:
                v = json.loads(s)
                return v if isinstance(v, list) else [str(v)]
            except Exception:
                return [s]

        story = []

        # Header
        story.append(Paragraph("TenderAI — Kelvin6K Tender Intelligence", small_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", small_style))
        story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=10))

        # Title
        story.append(Paragraph(tender.title or "Tender Details", title_style))
        story.append(Paragraph(tender.organization or "", body_style))
        story.append(Spacer(1, 10))

        # Key metrics table
        metrics = [
            ["Budget", fmt_inr(tender.budget_max), "Deadline", fmt_date(tender.deadline)],
            ["Source", (tender.source or "").upper(), "Country", tender.country or "India"],
        ]
        t = Table(metrics, colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), HexColor("#e2e8f0")),
            ("BACKGROUND", (2, 0), (2, -1), HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

        # Overview
        overview_val = getattr(tender, "overview", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("overview"))
        if overview_val:
            story.append(Paragraph("AI Summary", h2_style))
            story.append(Paragraph(overview_val, body_style))
            story.append(Spacer(1, 10))

        # Eligibility
        elig_val = getattr(tender, "eligibility", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("eligibility"))
        elig = parse_json_list(elig_val)
        if elig and elig[0] != "Refer to tender document for eligibility criteria.":
            story.append(Paragraph("Eligibility Requirements", h2_style))
            for item in elig:
                story.append(Paragraph(f"• {item}", body_style))
            story.append(Spacer(1, 10))

        # Risk Flags
        risk_val = getattr(tender, "risk_flags", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("risk_flags"))
        risks = parse_json_list(risk_val)
        if risks:
            story.append(Paragraph("Risk Flags", h2_style))
            for item in risks:
                story.append(Paragraph(f"⚠ {item}", body_style))
            story.append(Spacer(1, 10))

        # Source URL
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
        story.append(Spacer(1, 6))
        if tender.source_url:
            story.append(Paragraph(f"Source: <a href='{tender.source_url}' color='#14b8a6'>{tender.source_url}</a>", small_style))
        story.append(Paragraph("Generated by TenderAI • Kelvin6K Robotic & Sustainable Construction Technology", small_style))

        doc.build(story)
        buf.seek(0)

        filename = f"tender_{tender_id[:8]}_{(tender.title or 'export')[:30].replace(' ','_')}.pdf"
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed. Run: pip install reportlab")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
