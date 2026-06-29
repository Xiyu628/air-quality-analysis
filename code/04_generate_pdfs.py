"""Generate the Chinese tutorial PDF from Markdown.

The English report is maintained as LaTeX in report/report.tex and should be
compiled with latexmk.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

from config import REPORT_DIR, ensure_output_dirs


IMAGE_RE = re.compile(r"!\[(?P<caption>.*?)\]\((?P<path>.*?)\)")
NUMBERED_RE = re.compile(r"^\d+\.\s+(.*)")


def make_styles(chinese: bool = False) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    body_font = "STSong-Light" if chinese else "Helvetica"
    bold_font = "STSong-Light" if chinese else "Helvetica-Bold"
    mono_font = "Courier"

    return {
        "title": ParagraphStyle(
            "TitleCustom",
            parent=styles["Title"],
            fontName=bold_font,
            fontSize=20,
            leading=25,
            spaceAfter=16,
            alignment=1,
            splitLongWords=True,
        ),
        "h1": ParagraphStyle(
            "Heading1Custom",
            parent=styles["Heading1"],
            fontName=bold_font,
            fontSize=16,
            leading=20,
            spaceBefore=14,
            spaceAfter=8,
            splitLongWords=True,
        ),
        "h2": ParagraphStyle(
            "Heading2Custom",
            parent=styles["Heading2"],
            fontName=bold_font,
            fontSize=13,
            leading=17,
            spaceBefore=10,
            spaceAfter=6,
            splitLongWords=True,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=styles["BodyText"],
            fontName=body_font,
            fontSize=10.3,
            leading=15,
            spaceAfter=6,
            splitLongWords=True,
            wordWrap="CJK" if chinese else None,
        ),
        "caption": ParagraphStyle(
            "CaptionCustom",
            parent=styles["BodyText"],
            fontName=body_font,
            fontSize=8.6,
            leading=12,
            textColor=colors.HexColor("#444444"),
            alignment=1,
            spaceBefore=4,
            spaceAfter=10,
            splitLongWords=True,
            wordWrap="CJK" if chinese else None,
        ),
        "code": ParagraphStyle(
            "CodeCustom",
            parent=styles["Code"],
            fontName=mono_font,
            fontSize=8.2,
            leading=10.5,
            leftIndent=8,
            rightIndent=8,
            backColor=colors.HexColor("#f4f4f4"),
            borderColor=colors.HexColor("#dddddd"),
            borderWidth=0.4,
            borderPadding=5,
            spaceBefore=6,
            spaceAfter=8,
            splitLongWords=True,
        ),
        "bullet": ParagraphStyle(
            "BulletCustom",
            parent=styles["BodyText"],
            fontName=body_font,
            fontSize=10.0,
            leading=14,
            leftIndent=0,
            splitLongWords=True,
            wordWrap="CJK" if chinese else None,
        ),
    }


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def add_paragraph(story: list, text_lines: list[str], styles: dict[str, ParagraphStyle]) -> None:
    if not text_lines:
        return
    text = " ".join(line.strip() for line in text_lines).strip()
    if text:
        story.append(Paragraph(inline_markup(text), styles["body"]))
    text_lines.clear()


def add_list(story: list, items: list[str], ordered: bool, styles: dict[str, ParagraphStyle]) -> None:
    if not items:
        return
    for idx, item in enumerate(items, start=1):
        prefix = f"{idx}. " if ordered else "- "
        story.append(Paragraph(inline_markup(prefix + item), styles["bullet"]))
    story.append(Spacer(1, 4))
    items.clear()


def add_image(story: list, md_path: Path, image_path: str, caption: str, styles: dict[str, ParagraphStyle]) -> None:
    path = (md_path.parent / image_path).resolve()
    if not path.exists():
        story.append(Paragraph(f"[Missing image: {html.escape(image_path)}]", styles["body"]))
        return
    max_width = A4[0] - 4 * cm
    max_height = 11 * cm
    image = Image(str(path))
    scale = min(max_width / image.drawWidth, max_height / image.drawHeight, 1.0)
    image.drawWidth *= scale
    image.drawHeight *= scale
    block = [image]
    if caption:
        block.append(Paragraph(inline_markup(caption), styles["caption"]))
    story.append(KeepTogether(block))


def markdown_to_story(md_path: Path, chinese: bool = False) -> list:
    styles = make_styles(chinese)
    story: list = []
    paragraph: list[str] = []
    bullets: list[str] = []
    numbers: list[str] = []
    in_code = False
    code_lines: list[str] = []
    title_seen = False

    for raw_line in md_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            add_paragraph(story, paragraph, styles)
            add_list(story, bullets, False, styles)
            add_list(story, numbers, True, styles)
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"]))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        image_match = IMAGE_RE.match(line.strip())
        if image_match:
            add_paragraph(story, paragraph, styles)
            add_list(story, bullets, False, styles)
            add_list(story, numbers, True, styles)
            add_image(story, md_path, image_match.group("path"), image_match.group("caption"), styles)
            continue

        if not line.strip():
            add_paragraph(story, paragraph, styles)
            add_list(story, bullets, False, styles)
            add_list(story, numbers, True, styles)
            continue

        if line.startswith("# "):
            add_paragraph(story, paragraph, styles)
            add_list(story, bullets, False, styles)
            add_list(story, numbers, True, styles)
            if title_seen:
                story.append(PageBreak())
            story.append(Paragraph(inline_markup(line[2:].strip()), styles["title"]))
            title_seen = True
            continue

        if line.startswith("## "):
            add_paragraph(story, paragraph, styles)
            add_list(story, bullets, False, styles)
            add_list(story, numbers, True, styles)
            story.append(Paragraph(inline_markup(line[3:].strip()), styles["h1"]))
            continue

        if line.startswith("### "):
            add_paragraph(story, paragraph, styles)
            add_list(story, bullets, False, styles)
            add_list(story, numbers, True, styles)
            story.append(Paragraph(inline_markup(line[4:].strip()), styles["h2"]))
            continue

        if line.startswith("- "):
            add_paragraph(story, paragraph, styles)
            add_list(story, numbers, True, styles)
            bullets.append(line[2:].strip())
            continue

        numbered = NUMBERED_RE.match(line)
        if numbered:
            add_paragraph(story, paragraph, styles)
            add_list(story, bullets, False, styles)
            numbers.append(numbered.group(1).strip())
            continue

        paragraph.append(line)

    add_paragraph(story, paragraph, styles)
    add_list(story, bullets, False, styles)
    add_list(story, numbers, True, styles)
    return story


def page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setAuthor("")
    canvas.setTitle("")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(md_name: str, pdf_name: str, chinese: bool = False) -> Path:
    md_path = REPORT_DIR / md_name
    out_path = REPORT_DIR / pdf_name
    story = markdown_to_story(md_path, chinese=chinese)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="",
        author="",
        subject="",
        creator="",
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return out_path


def main() -> None:
    ensure_output_dirs()
    registerFont(UnicodeCIDFont("STSong-Light"))
    tutorial_pdf = build_pdf("tutorial_zh.md", "tutorial_zh.pdf", chinese=True)
    print("Generated PDF:")
    print(f"- {tutorial_pdf}")


if __name__ == "__main__":
    main()
