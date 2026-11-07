"""Build paper/preview.pdf from paper/draft.md: an approximation of the Apart template, used to check the page limit.

    python3 paper/build_preview.py            # writes paper/preview.pdf and prints page counts

The layout comes from the official Google Docs template, exported as HTML on 2026-11-07:
- US Letter, 1 in margins (72 pt padding, 468 pt text width), one column;
- body 11 pt "Old Standard TT" (serif), headings bold 14 pt, title 20 pt;
- falls back to DejaVu Serif for glyphs the font lacks.

Steps:
1. Strip drafting-only text: the drafting-rules box, the abstract recount note, and the
   verification note in the References heading.
2. Convert with pandoc (markdown reader with implicit figures, dollar math and sub/superscript
   off, so "$0.85" and "~36" stay text).
3. Inline the figures from plan/figs/ at text width and add print CSS.
4. Print with headless Chrome.

It renders the full preview: main body, then References on a new page, then the appendices.
The main-body page count is the number of pages before References, the count checked against
the Apart limit of 8 pages excluding references and appendices. PyMuPDF (`fitz`) is used to read it.

Needs `pandoc`, `google-chrome`, and network access for the Google Font (otherwise the fallback
serif is used and the page count is approximate). No LLM calls.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
DRAFT = PAPER / "draft.md"
OUT = PAPER / "preview.pdf"
CHROME = "google-chrome"

CSS = """
@page { size: letter; margin: 1in; }
html { font-size: 11pt; }
body { font-family: 'Old Standard TT', 'DejaVu Serif', serif; line-height: 1.15; color: #000;
       margin: 0; background: #fff; }
h1 { font-size: 20pt; font-weight: 700; text-align: center; margin: 0 0 10pt; line-height: 1.1; }
h2 { font-size: 14pt; font-weight: 700; margin: 14pt 0 4pt; page-break-after: avoid; }
h3 { font-size: 12pt; font-weight: 700; margin: 10pt 0 3pt; page-break-after: avoid; }
p { margin: 0 0 6pt; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 6pt; padding-left: 18pt; }
li { margin: 0 0 2pt; }
table { border-collapse: collapse; font-size: 8.5pt; margin: 4pt 0 8pt; width: 100%;
        page-break-inside: avoid; }
th, td { border-top: 0.5pt solid #999; border-bottom: 0.5pt solid #999; padding: 1.5pt 3pt;
         text-align: left; vertical-align: top; }
th { font-weight: 700; }
figure { margin: 6pt 0 8pt; page-break-inside: avoid; text-align: center; }
img { max-width: 100%; }
figure img { width: 100%; max-width: 6.5in; }
figure.wrap { float: right; width: 4.0in; margin: 2pt 0 6pt 12pt; }
figure.wrap img { width: 100% !important; }
figcaption { font-size: 9pt; text-align: left; margin-top: 2pt; line-height: 1.1; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; }
hr { display: none; }
.pagebreak { page-break-before: always; }
"""
FONT_LINK = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Old+Standard+TT:'
             'ital,wght@0,400;0,700;1,400&display=block">')
# Figures printed at their natural 4.0 in width with text wrapping beside them (Google Docs
# "wrap text"); designed for a narrow column.
WRAP = ("paperfig5_board_mechanism",)
# Per-figure print widths (share of the 6.5 in text width); unlisted figures use 100%.
WIDTHS = {"paperfig1_schematic": 80, "paperfig4a_grid_effects": 85, "paperfig4b_sweep_effects": 65,
          "paperfig5_board_mechanism": 61.5, "paperfig3_divergence": 95, "paperfig2_network": 75}


def clean_markdown(md: str) -> str:
    """Drop drafting-only text that is not part of the submitted paper."""
    md = re.sub(r"^> .*\n(?:>.*\n)*\n?", "", md, flags=re.M)              # drafting-rules box
    md = re.sub(r"^## Abstract \(.*\)$", "## Abstract", md, flags=re.M)
    md = re.sub(r"^\*\(Recount.*\)\*\s*$\n?", "", md, flags=re.M)
    md = re.sub(r"^## References \(.*\)$", "## References", md, flags=re.M)
    md = re.sub(r"^Verification note:.*?(?=\n\n)", "", md, flags=re.M | re.S)
    return md


def split_main(md: str) -> tuple[str, str]:
    """(main body = title .. Code and Data, rest = References + appendices + LLM statement)."""
    i = md.index("\n## References")
    return md[:i], md[i:]


def to_html(md: str) -> str:
    """Markdown -> HTML fragment via pandoc; figure paths resolved to absolute file URIs."""
    html = subprocess.run(
        ["pandoc", "-f", "markdown+lists_without_preceding_blankline-tex_math_dollars-subscript-superscript",
         "-t", "html", "--wrap=none"],
        input=md, capture_output=True, text=True, check=True).stdout
    def fix(m: re.Match) -> str:
        src = (PAPER / m.group(1)).resolve()
        return f'src="file://{src}"'
    html = re.sub(r'src="(\.\./plan/figs/[^"]+)"', fix, html)
    for name in WRAP:
        html = re.sub(r'<figure>(\s*<img[^>]*?' + name + ')', r'<figure class="wrap">\1', html)
    for name, pct in WIDTHS.items():
        html = re.sub(r'<img (src="[^"]*' + name + r'\.png")', rf'<img style="width:{pct}%" \1', html)
    return html


def page_html(body: str) -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'>{FONT_LINK}"
            f"<style>{CSS}</style><title>Keys &amp; God preview</title></head><body>{body}</body></html>")


def print_pdf(html: str, pdf: Path, workdir: Path) -> int:
    """Print an HTML string to a PDF with headless Chrome and return its page count."""
    src = workdir / (pdf.stem + ".html")
    src.write_text(html, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--no-pdf-header-footer", "--virtual-time-budget=20000",
                    "--run-all-compositor-stages-before-draw",
                    f"--print-to-pdf={pdf}", f"file://{src}"],
                   check=True, capture_output=True)
    try:
        import fitz  # PyMuPDF, if available: exact page count
        with fitz.open(pdf) as doc:
            return doc.page_count
    except ImportError:
        return len(re.findall(rb"/Type\s*/Page(?!s)", pdf.read_bytes()))


def main_body_pages(pdf: Path) -> tuple[int, set[str]]:
    """Pages before the one where "References" starts (it always starts a new page), plus the
    font names used, so a fallback-font render can be spotted."""
    import fitz  # PyMuPDF
    with fitz.open(pdf) as doc:
        fonts = {f[3].split("+")[-1] for page in doc for f in page.get_fonts()}
        for i, page in enumerate(doc):
            if any(line.strip() == "References" for line in page.get_text().splitlines()):
                return i, fonts
    raise RuntimeError("no References heading found")


def main() -> int:
    md = clean_markdown(DRAFT.read_text(encoding="utf-8"))
    main_md, rest_md = split_main(md)
    full = to_html(main_md) + '<div class="pagebreak"></div>' + to_html(rest_md)
    with tempfile.TemporaryDirectory() as tmp:
        total = print_pdf(page_html(full), OUT, Path(tmp))
    main_pages, fonts = main_body_pages(OUT)
    words = len(re.sub(r"!\[.*?\]\(.*?\)", "", main_md[main_md.index("## 1 Introduction"):]).split())
    print(f"main body (title .. Code and Data): {main_pages} pages; full preview: {total} pages")
    print(f"body words (Intro .. Code and Data, excluding figure captions): {words}")
    if not any("OldStandard" in f for f in fonts):
        print("WARNING: Old Standard TT was not loaded; the count uses a fallback font.")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
