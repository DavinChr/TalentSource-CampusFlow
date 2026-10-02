import os
import re
import subprocess
import time
import io
from markdown_it import MarkdownIt
import pypdf
import pypdfium2 as pdfium
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_header_footer_overlay(total_pages, doc_num="CF-SRS-2026-001", doc_title="CampusFlow — Software Requirements Specification (IEEE 830 / ISO 29148)"):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    width, height = A4 # 595.27 x 841.89 points

    for page_num in range(1, total_pages + 1):
        if page_num == 1:
            # Skip cover page
            c.showPage()
            continue

        # Header
        c.saveState()
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawString(45, height - 36, doc_title)
        c.drawRightString(width - 45, height - 36, f"{doc_num} | Draft")
        
        # Header rule
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.setLineWidth(0.6)
        c.line(45, height - 42, width - 45, height - 42)

        # Footer rule
        c.line(45, 45, width - 45, 45)

        # Footer
        c.drawString(45, 32, "26 September 2026 — Joseph Davin")
        page_str = f"Halaman {page_num} dari {total_pages}"
        c.drawRightString(width - 45, 32, page_str)
        c.restoreState()
        
        c.showPage()

    c.save()
    packet.seek(0)
    return pypdf.PdfReader(packet)

def build_pdf():
    md_path = r"d:\TalentSource\CampusFlow\docs\SRS_CampusFlow.md"
    output_pdf_docs = r"d:\TalentSource\CampusFlow\docs\SRS_CampusFlow.pdf"
    output_pdf_brain = r"C:\Users\davin\.gemini\antigravity-ide\brain\2e7d573b-6ca2-47ef-ad2c-ef9a0349ee8a\SRS_CampusFlow.pdf"
    scratch_dir = r"C:\Users\davin\.gemini\antigravity-ide\brain\2e7d573b-6ca2-47ef-ad2c-ef9a0349ee8a\scratch"
    raw_pdf = os.path.join(scratch_dir, "raw_chrome.pdf")
    output_html = os.path.join(scratch_dir, "SRS_CampusFlow.html")

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Pre-process mermaid blocks
    def mermaid_repl(match):
        code = match.group(1).strip()
        is_er = "erDiagram" in code
        extra_class = " er-diagram" if is_er else " seq-diagram"
        return f'\n\n<div class="mermaid{extra_class}">\n{code}\n</div>\n\n'

    md_processed = re.sub(r'```mermaid\s*\n(.*?)\n```', mermaid_repl, md_text, flags=re.DOTALL)

    # Convert markdown to HTML using CommonMark / GFM standard parser
    md = MarkdownIt('gfm-like')
    html_body = md.render(md_processed)

    # Structure page breaks for IEEE standard document
    html_body = re.sub(r'(<h2[^>]*>\d+\..*?</h2>)', r'<div class="page-break"></div>\1', html_body)
    html_body = re.sub(r'(<h2[^>]*>Lampiran.*?</h2>)', r'<div class="page-break"></div>\1', html_body)

    # Wrap Table of Contents in dedicated container so it fits on Page 2
    def wrap_toc(m):
        return f'<div class="page-break"></div><div class="toc-wrapper">{m.group(1)}{m.group(2)}</div>'

    html_body = re.sub(
        r'(<h2[^>]*>Daftar Isi.*?</h2>)(.*?)(?=<div class="page-break">)',
        wrap_toc,
        html_body,
        flags=re.DOTALL
    )

    # Page break before ER diagram so it fits cleanly on its own page
    html_body = html_body.replace('<div class="mermaid er-diagram">', '<div class="page-break"></div><div class="mermaid er-diagram">')

    full_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<title>Software Requirements Specification — CampusFlow (IEEE 830 / ISO 29148)</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
    mermaid.initialize({{
        startOnLoad: true,
        theme: 'neutral',
        securityLevel: 'loose',
        sequence: {{
            useMaxWidth: true,
            showSequenceNumbers: true,
            actorFontSize: 11,
            messageFontSize: 10,
            noteFontSize: 10
        }},
        er: {{
            useMaxWidth: true
        }}
    }});
</script>
<style>
    @page {{
        size: A4 portrait;
        margin: 18mm 16mm 18mm 16mm;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        background-color: #ffffff;
        line-height: 1.6;
        font-size: 9pt;
        margin: 0;
        padding: 0;
    }}

    .page-break {{
        page-break-before: always;
        break-before: page;
    }}

    /* Title Styling */
    h1 {{
        font-size: 22pt;
        font-weight: 800;
        color: #0f172a;
        margin-top: 15pt;
        margin-bottom: 6pt;
        letter-spacing: -0.02em;
        line-height: 1.25;
        border-bottom: none;
    }}

    h1 + h2 {{
        font-size: 13.5pt;
        font-weight: 600;
        color: #2563eb;
        margin-top: 0;
        margin-bottom: 16pt;
        border-bottom: 2pt solid #2563eb;
        padding-bottom: 8pt;
    }}

    /* Major Section Headings */
    h2 {{
        font-size: 14pt;
        font-weight: 700;
        color: #1e3a8a;
        border-bottom: 1.5pt solid #cbd5e1;
        padding-bottom: 4pt;
        margin-top: 16pt;
        margin-bottom: 10pt;
        page-break-after: avoid;
        break-after: avoid;
    }}

    h3 {{
        font-size: 10.5pt;
        font-weight: 600;
        color: #0284c7;
        margin-top: 13pt;
        margin-bottom: 5pt;
        page-break-after: avoid;
        break-after: avoid;
    }}

    h4 {{
        font-size: 9.5pt;
        font-weight: 600;
        color: #334155;
        margin-top: 9pt;
        margin-bottom: 4pt;
        page-break-after: avoid;
        break-after: avoid;
    }}

    p {{
        margin-top: 0;
        margin-bottom: 7pt;
        text-align: justify;
    }}

    /* Standard Lists (Numbered & Bulleted) with clear line breaks & indentation */
    ol {{
        margin-top: 4pt;
        margin-bottom: 8pt;
        padding-left: 20pt;
        list-style-type: decimal;
    }}

    ul {{
        margin-top: 4pt;
        margin-bottom: 8pt;
        padding-left: 18pt;
        list-style-type: disc;
    }}

    li {{
        margin-bottom: 3.5pt;
        line-height: 1.55;
        text-align: justify;
        display: list-item;
    }}

    /* Nested sub-lists */
    li > ol, li > ul {{
        margin-top: 3pt;
        margin-bottom: 3pt;
        padding-left: 18pt;
    }}

    li > ul {{
        list-style-type: circle;
    }}

    li > ul > li > ul {{
        list-style-type: square;
    }}

    /* Table of Contents Compact Fit on Page 2 */
    .toc-wrapper h2 {{
        margin-top: 0;
        margin-bottom: 10pt;
    }}

    .toc-wrapper ol {{
        margin-top: 2pt;
        margin-bottom: 4pt;
        padding-left: 18pt;
    }}

    .toc-wrapper ul {{
        margin-top: 1pt;
        margin-bottom: 3pt;
        padding-left: 16pt;
    }}

    .toc-wrapper li {{
        margin-bottom: 2pt;
        line-height: 1.35;
        font-size: 8.5pt;
    }}

    hr {{
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 14pt 0;
    }}

    /* Tables */
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 6pt;
        margin-bottom: 12pt;
        font-size: 8.5pt;
        page-break-inside: auto;
        break-inside: auto;
    }}

    tr {{
        page-break-inside: avoid;
        break-inside: avoid;
    }}

    th {{
        background-color: #f1f5f9;
        color: #0f172a;
        font-weight: 600;
        text-align: left;
        padding: 5.5pt 7pt;
        border: 1px solid #cbd5e1;
        border-bottom: 2px solid #94a3b8;
    }}

    td {{
        padding: 5pt 7pt;
        border: 1px solid #e2e8f0;
        vertical-align: top;
    }}

    tr:nth-child(even) td {{
        background-color: #f8fafc;
    }}

    /* Code & Pre */
    code {{
        font-family: 'Consolas', 'Cascadia Code', monospace;
        font-size: 8pt;
        background-color: #f1f5f9;
        color: #0f172a;
        padding: 1.5pt 3.5pt;
        border-radius: 3pt;
        border: 1px solid #e2e8f0;
    }}

    pre {{
        background-color: #0f172a;
        color: #f8fafc;
        padding: 8pt 10pt;
        border-radius: 4pt;
        font-family: 'Consolas', 'Cascadia Code', monospace;
        font-size: 7.8pt;
        line-height: 1.45;
        overflow-x: auto;
        margin-top: 5pt;
        margin-bottom: 10pt;
        page-break-inside: avoid;
        break-inside: avoid;
        white-space: pre-wrap;
        word-break: break-all;
    }}

    pre code {{
        background-color: transparent;
        color: inherit;
        padding: 0;
        border: none;
    }}

    /* Blockquotes / Alerts */
    blockquote {{
        margin: 7pt 0 10pt 0;
        padding: 7pt 10pt;
        background-color: #f0f9ff;
        border-left: 3.5pt solid #0284c7;
        border-radius: 0 4pt 4pt 0;
        color: #0369a1;
        font-size: 8.5pt;
        page-break-inside: avoid;
        break-inside: avoid;
    }}

    blockquote p:last-child {{
        margin-bottom: 0;
    }}

    /* Mermaid diagrams */
    .mermaid {{
        margin: 12pt auto;
        text-align: center;
        page-break-inside: avoid;
        break-inside: avoid;
        background: #f8fafc;
        padding: 10pt;
        border: 1px solid #e2e8f0;
        border-radius: 5pt;
        max-width: 100%;
        overflow: hidden;
    }}

    .mermaid svg {{
        max-width: 100% !important;
        height: auto !important;
        display: block;
        margin: 0 auto;
    }}

    .mermaid.er-diagram {{
        padding: 6pt;
        max-height: 220mm;
    }}

    .mermaid.er-diagram svg {{
        max-height: 210mm !important;
        width: auto !important;
    }}

    .mermaid.seq-diagram svg {{
        width: 100% !important;
    }}

    a {{
        color: #2563eb;
        text-decoration: none;
    }}

    a:hover {{
        text-decoration: underline;
    }}
</style>
</head>
<body>

<div class="content-wrapper">
{html_body}
</div>

</body>
</html>
"""

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(full_html)
    print("HTML written to:", output_html)

    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    browser_exe = edge_path if os.path.exists(edge_path) else chrome_path

    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=6000",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={raw_pdf}",
        output_html
    ]

    print("Generating raw PDF via browser headless...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    time.sleep(2)

    if not os.path.exists(raw_pdf):
        print("Failed to generate raw PDF.")
        return

    # Stamp running headers and footers with page numbers
    print("Stamping headers, footers, and page numbers...")
    raw_reader = pypdf.PdfReader(raw_pdf)
    total_pages = len(raw_reader.pages)
    print(f"Total pages before overlay: {total_pages}")

    overlay_reader = generate_header_footer_overlay(total_pages)

    writer = pypdf.PdfWriter()
    for idx, page in enumerate(raw_reader.pages):
        overlay_page = overlay_reader.pages[idx]
        page.merge_page(overlay_page)
        writer.add_page(page)

    with open(output_pdf_docs, "wb") as f_out:
        writer.write(f_out)
    
    # Copy to brain artifact directory as well
    with open(output_pdf_docs, "rb") as src, open(output_pdf_brain, "wb") as dst:
        dst.write(src.read())

    print(f"Final PDF saved to:\n1. {output_pdf_docs}\n2. {output_pdf_brain}")
    print(f"File size: {os.path.getsize(output_pdf_docs):,} bytes across {total_pages} pages.")

if __name__ == "__main__":
    build_pdf()
