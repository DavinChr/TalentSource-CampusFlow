import os
import subprocess
import tempfile
import markdown

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(WORKSPACE_DIR, "PROGRESS_REPORT.md")
PDF_PATH = os.path.join(WORKSPACE_DIR, "PROGRESS_REPORT.pdf")

with open(MD_PATH, "r", encoding="utf-8") as f:
    md_content = f.read()

html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'nl2br'])

html_full = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<title>Laporan Evaluasi &amp; Progres Proyek: CampusFlow</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1e293b;
    line-height: 1.6;
    font-size: 10pt;
    margin: 0;
    padding: 0;
  }}
  h1 {{
    font-size: 18pt;
    color: #0f172a;
    border-bottom: 2.5px solid #2563eb;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 18px;
  }}
  h2 {{
    font-size: 13pt;
    color: #1e3a8a;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 4px;
    margin-top: 22px;
    margin-bottom: 10px;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 11pt;
    color: #334155;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
  }}
  p, ul, ol {{
    margin-top: 4px;
    margin-bottom: 8px;
  }}
  li {{
    margin-bottom: 3px;
  }}
  hr {{
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 18px 0;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 9pt;
    page-break-inside: avoid;
  }}
  th, td {{
    border: 1px solid #cbd5e1;
    padding: 7px 9px;
    text-align: left;
    vertical-align: top;
  }}
  th {{
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
  }}
  tr:nth-child(even) {{
    background-color: #f8fafc;
  }}
  code {{
    background-color: #f1f5f9;
    color: #dc2626;
    padding: 2px 4px;
    border-radius: 4px;
    font-size: 8.5pt;
    font-family: Consolas, "Courier New", monospace;
  }}
  img {{
    max-width: 100%;
    height: auto;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    margin: 10px 0;
    display: block;
    page-break-inside: avoid;
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

temp_html = os.path.join(WORKSPACE_DIR, "_temp_report.html")
with open(temp_html, "w", encoding="utf-8") as f:
    f.write(html_full)

edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
temp_profile = os.path.join(tempfile.gettempdir(), "edge_pdf_temp")

args = [
    edge_exe,
    "--headless=new",
    "--disable-gpu",
    f"--user-data-dir={temp_profile}",
    f"--print-to-pdf={PDF_PATH}",
    temp_html,
]

print("Generating PDF from PROGRESS_REPORT.md...")
res = subprocess.run(args, capture_output=True, text=True)

if os.path.exists(temp_html):
    os.remove(temp_html)

if os.path.exists(PDF_PATH):
    print(f"SUCCESS: Generated {PDF_PATH} ({os.path.getsize(PDF_PATH)} bytes)")
else:
    print("FAILED: PDF not generated")
    print(res.stderr)
