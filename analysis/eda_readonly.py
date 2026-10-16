"""Create a small, aggregate-only EDA report from the configured SQLite DB.

This script opens the database with SQLite's read-only URI mode. It only exports
aggregate counts, missing/duplicate checks, dates, and content lengths. It never
exports message text, identifiers, account data, or connection credentials.

Run from the repository root:
    python analysis/eda_readonly.py

Optional arguments:
    --db PATH       SQLite file (defaults to DATABASE_URL in environment or
                    backend/.env)
    --output PATH   Output folder (defaults to docs/eda_artifacts)
"""

from __future__ import annotations

import argparse
import csv
import html
import math
import os
import sqlite3
import statistics
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DEFAULT_OUTPUT = ROOT / "docs" / "eda_artifacts"


def _configured_database_url() -> str:
    """Read only the database setting; never print or log its value."""
    env_value = os.environ.get("DATABASE_URL", "").strip()
    if env_value:
        return env_value

    env_file = BACKEND / ".env"
    if not env_file.is_file():
        return ""
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "DATABASE_URL":
            return value.strip().strip("\"'")
    return ""


def _resolve_database_path(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        return path.resolve() if path.is_absolute() else (ROOT / path).resolve()

    database_url = _configured_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured; database URL withheld")
    if not database_url.startswith("sqlite:///"):
        raise RuntimeError(
            "The configured database is not SQLite. This script supports SQLite "
            "read-only mode only; database URL and credentials were withheld."
        )

    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        raise RuntimeError("An in-memory database cannot be audited by this script")
    path = Path(raw_path)
    return path.resolve() if path.is_absolute() else (BACKEND / path).resolve()


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise RuntimeError(f"Configured SQLite file does not exist: {path.name}")
    # quote() prevents reserved URI characters in a path from changing URI options.
    uri = f"file:{quote(path.as_posix(), safe='/:')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _message_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _svg_text(x: float, y: float, text: str, *, size: int = 18,
              fill: str = "#333333", anchor: str = "start", weight: str = "400",
              rotate: float | None = None) -> str:
    transform = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"'
        f'{transform}>{html.escape(text)}</text>'
    )


def _svg_start(title: str, subtitle: str, width: int = 1440, height: int = 900) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _svg_text(84, 78, title, size=32, fill="#222222", weight="700"),
        _svg_text(84, 116, subtitle, size=17, fill="#555555"),
    ]


def _write_pdf_from_svg(svg_path: Path, pdf_path: Path) -> None:
    """Render the script's simple SVG charts as vector-only, grayscale PDFs."""
    root = ET.parse(svg_path).getroot()
    view_x, view_y, view_width, view_height = [float(value) for value in root.attrib["viewBox"].split()]
    page_width, page_height = 842.0, 595.0  # A4 landscape, points
    margin = 22.0
    scale = min((page_width - 2 * margin) / view_width,
                (page_height - 2 * margin) / view_height)
    offset_x = (page_width - view_width * scale) / 2 - view_x * scale
    offset_y = (page_height - view_height * scale) / 2 - view_y * scale
    commands = ["q", "1 1 1 rg", f"0 0 {page_width:.2f} {page_height:.2f} re f"]

    def color(value: str) -> tuple[float, float, float]:
        value = value.lstrip("#")
        return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))

    def pdf_string(value: str) -> str:
        encoded = value.encode("ascii", errors="replace").decode("ascii")
        return "(" + encoded.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"

    for element in root:
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "rect":
            x, y = float(element.attrib.get("x", 0)), float(element.attrib.get("y", 0))
            raw_width, raw_height = element.attrib.get("width", "0"), element.attrib.get("height", "0")
            width = view_width if raw_width.endswith("%") else float(raw_width)
            height = view_height if raw_height.endswith("%") else float(raw_height)
            rgb = color(element.attrib.get("fill", "#000000"))
            px = offset_x + x * scale
            py = page_height - (offset_y + (y + height) * scale)
            commands.extend((f"{rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} rg",
                             f"{px:.2f} {py:.2f} {width * scale:.2f} {height * scale:.2f} re f"))
        elif tag == "line":
            x1, y1 = float(element.attrib["x1"]), float(element.attrib["y1"])
            x2, y2 = float(element.attrib["x2"]), float(element.attrib["y2"])
            rgb = color(element.attrib.get("stroke", "#000000"))
            commands.extend((f"{rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} RG", "0.55 w",
                             f"{offset_x + x1 * scale:.2f} {page_height - (offset_y + y1 * scale):.2f} m",
                             f"{offset_x + x2 * scale:.2f} {page_height - (offset_y + y2 * scale):.2f} l S"))
        elif tag == "text":
            label = "".join(element.itertext())
            x, y = float(element.attrib["x"]), float(element.attrib["y"])
            size = float(element.attrib.get("font-size", 18)) * scale
            rgb = color(element.attrib.get("fill", "#333333"))
            anchor = element.attrib.get("text-anchor", "start")
            text_width = len(label) * size * 0.52
            px = offset_x + x * scale
            if anchor == "middle":
                px -= text_width / 2
            elif anchor == "end":
                px -= text_width
            py = page_height - (offset_y + y * scale)
            font = "F2" if element.attrib.get("font-weight", "400") in ("600", "700", "bold") else "F1"
            rotation = element.attrib.get("transform")
            if rotation:
                angle = math.radians(float(rotation.split("(", 1)[1].split()[0]))
                cosine, sine = math.cos(angle), math.sin(angle)
                matrix = f"{cosine:.5f} {sine:.5f} {-sine:.5f} {cosine:.5f} {px:.2f} {py:.2f} Tm"
            else:
                matrix = f"1 0 0 1 {px:.2f} {py:.2f} Tm"
            commands.append(f"BT /{font} {size:.2f} Tf {rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} rg {matrix} {pdf_string(label)} Tj ET")

    commands.append("Q")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.2f} {page_height:.2f}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    pdf_path.write_bytes(pdf)


def _write_platform_chart(counts: Counter[str], output: Path, n: int) -> None:
    width, height = 1440, 900
    parts = _svg_start("Content Count by Platform", f"Assistant messages with a platform label | n = {n}", width, height)
    left, right, top, bottom = 360, 1280, 190, 770
    labels = sorted(counts, key=lambda label: (-counts[label], label.casefold()))
    max_value = max(counts.values(), default=1)
    row_height = min(76, (bottom - top) / max(1, len(labels)))
    grid_max = max(1, math.ceil(max_value / 5) * 5)
    for tick in range(0, grid_max + 1, max(1, math.ceil(grid_max / 5))):
        x = left + (right - left) * tick / grid_max
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="#dddddd"/>')
        parts.append(_svg_text(x, bottom + 34, str(tick), size=15, fill="#555555", anchor="middle"))
    for index, label in enumerate(labels):
        y = top + row_height * (index + 0.5)
        parts.append(_svg_text(left - 22, y + 6, label, size=19, anchor="end"))
        bar_width = (right - left) * counts[label] / grid_max
        parts.append(f'<rect x="{left}" y="{y - 17:.1f}" width="{bar_width:.1f}" height="34" rx="8" fill="#555555"/>')
        parts.append(_svg_text(left + bar_width + 12, y + 6, str(counts[label]), size=17, fill="#333333", weight="700"))
    parts.append(_svg_text((left + right) / 2, 842, "Number of assistant messages", size=18, fill="#555555", anchor="middle"))
    parts.append("</svg>")
    svg_path = output / "content_by_platform.svg"
    svg_path.write_text("\n".join(parts), encoding="utf-8")
    _write_pdf_from_svg(svg_path, output / "content_by_platform.pdf")


def _write_daily_chart(daily_counts: Counter[date], start: date, end: date,
                       output: Path, n: int) -> None:
    width, height = 1440, 900
    parts = _svg_start("Content Count by Day", f"Assistant messages | {start.isoformat()} to {end.isoformat()} | n = {n}", width, height)
    left, right, top, bottom = 110, 1340, 190, 740
    dates = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    values = [daily_counts[day] for day in dates]
    max_value = max(values, default=0)
    grid_max = max(1, math.ceil(max_value / 5) * 5)
    step = max(1, math.ceil(grid_max / 5))
    for tick in range(0, grid_max + 1, step):
        y = bottom - (bottom - top) * tick / grid_max
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#dddddd"/>')
        parts.append(_svg_text(left - 18, y + 5, str(tick), size=15, fill="#555555", anchor="end"))
    slot = (right - left) / max(1, len(dates))
    bar_width = min(48, slot * 0.66)
    for index, (day, value) in enumerate(zip(dates, values)):
        x = left + slot * (index + 0.5)
        bar_height = (bottom - top) * value / grid_max
        parts.append(f'<rect x="{x - bar_width / 2:.1f}" y="{bottom - bar_height:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="5" fill="#777777"/>')
        if len(dates) <= 18 or index % max(1, math.ceil(len(dates) / 18)) == 0:
            parts.append(_svg_text(x, bottom + 30, day.strftime("%b %d"), size=14, fill="#555555", anchor="middle"))
    parts.append(_svg_text((left + right) / 2, 830, "Date", size=18, fill="#555555", anchor="middle"))
    parts.append(_svg_text(32, (top + bottom) / 2, "Number of assistant messages", size=17, fill="#555555", anchor="middle", rotate=-90))
    parts.append("</svg>")
    svg_path = output / "content_by_day.svg"
    svg_path.write_text("\n".join(parts), encoding="utf-8")
    _write_pdf_from_svg(svg_path, output / "content_by_day.pdf")


def _write_length_chart(lengths: list[int], output: Path) -> int:
    n = len(lengths)
    bins = max(1, math.ceil(math.log2(n) + 1)) if n else 1
    minimum, maximum = (min(lengths), max(lengths)) if lengths else (0, 0)
    if minimum == maximum:
        bins = 1
    span = max(1, maximum - minimum + 1)
    width, height = 1440, 900
    parts = _svg_start("Distribution of Content Length", f"Non-empty assistant message text | n = {n} | {bins} equal-width bins", width, height)
    left, right, top, bottom = 130, 1330, 190, 740
    counts = [0] * bins
    for length in lengths:
        index = min(bins - 1, int((length - minimum) * bins / span))
        counts[index] += 1
    max_count = max(counts, default=0)
    grid_max = max(1, math.ceil(max_count / 5) * 5)
    step = max(1, math.ceil(grid_max / 5))
    for tick in range(0, grid_max + 1, step):
        y = bottom - (bottom - top) * tick / grid_max
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#dddddd"/>')
        parts.append(_svg_text(left - 18, y + 5, str(tick), size=15, fill="#555555", anchor="end"))
    slot = (right - left) / bins
    for index, count in enumerate(counts):
        x = left + slot * index
        bar_height = (bottom - top) * count / grid_max
        parts.append(f'<rect x="{x + 7:.1f}" y="{bottom - bar_height:.1f}" width="{slot - 14:.1f}" height="{bar_height:.1f}" rx="6" fill="#999999"/>')
        lo = minimum + (span * index // bins)
        hi = minimum + (span * (index + 1) // bins) - 1
        parts.append(_svg_text(x + slot / 2, bottom + 30, f"{lo:,}-{hi:,}", size=14, fill="#555555", anchor="middle"))
    parts.append(_svg_text((left + right) / 2, 830, "Content length (Unicode code points)", size=18, fill="#555555", anchor="middle"))
    parts.append(_svg_text(32, (top + bottom) / 2, "Number of messages", size=17, fill="#555555", anchor="middle", rotate=-90))
    parts.append("</svg>")
    svg_path = output / "content_length_distribution.svg"
    svg_path.write_text("\n".join(parts), encoding="utf-8")
    _write_pdf_from_svg(svg_path, output / "content_length_distribution.pdf")
    return bins


def run(database: Path, output: Path) -> dict[str, object]:
    connection = _open_readonly(database)
    try:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"messages", "conversations"}.issubset(tables):
            raise RuntimeError("Configured database lacks messages/conversations tables")
        message_columns = _message_columns(connection, "messages")
        conversation_columns = _message_columns(connection, "conversations")
        required = {"id", "conversation_id", "role", "content", "created_at"}
        if not required.issubset(message_columns) or not {"id"}.issubset(conversation_columns):
            raise RuntimeError("Required message fields are unavailable; no output generated")

        platform_column = (
            "COALESCE(NULLIF(TRIM(m.platform_name), ''), NULLIF(TRIM(m.prompt_type), ''))"
            if {"platform_name", "prompt_type"}.issubset(message_columns)
            else "NULLIF(TRIM(m.prompt_type), '')"
            if "prompt_type" in message_columns
            else "NULLIF(TRIM(m.platform_name), '')"
            if "platform_name" in message_columns
            else "NULL"
        )
        query = f"""
            SELECT {platform_column} AS platform, m.created_at AS created_at,
                   m.content AS content
            FROM messages AS m
            JOIN conversations AS c ON c.id = m.conversation_id
            WHERE m.role = 'assistant'
            ORDER BY m.created_at, m.id
        """
        rows = connection.execute(query).fetchall()
    finally:
        connection.close()

    if not rows:
        raise RuntimeError("No assistant messages found; insufficient data for the requested EDA")

    platform_values: list[str | None] = []
    parsed_dates: list[date | None] = []
    normalized_contents: list[str | None] = []
    lengths: list[int] = []
    for row in rows:
        platform = row["platform"]
        platform_values.append(platform.strip() if platform and platform.strip() else None)
        raw_timestamp = row["created_at"]
        try:
            parsed_dates.append(datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00")).date() if raw_timestamp else None)
        except (AttributeError, TypeError, ValueError):
            parsed_dates.append(None)
        raw_content = row["content"]
        if raw_content is None or not raw_content.strip():
            normalized_contents.append(None)
        else:
            normalized = unicodedata.normalize("NFC", raw_content)
            normalized_contents.append(normalized)
            lengths.append(len(normalized))

    total = len(rows)
    valid_dates = [value for value in parsed_dates if value is not None]
    if not valid_dates:
        raise RuntimeError("No valid timestamps found; daily chart cannot be produced")
    if not any(platform_values):
        raise RuntimeError("No platform labels found; platform chart cannot be produced")
    if not lengths:
        raise RuntimeError("No non-empty message content found; length chart cannot be produced")

    start, end = min(valid_dates), max(valid_dates)
    platform_counts = Counter(value if value is not None else "Unknown" for value in platform_values)
    daily_counts = Counter(value for value in parsed_dates if value is not None)
    nonempty_contents = [value for value in normalized_contents if value is not None]
    duplicate_excess = len(nonempty_contents) - len(set(nonempty_contents))
    output.mkdir(parents=True, exist_ok=True)

    _write_platform_chart(platform_counts, output, total)
    _write_daily_chart(daily_counts, start, end, output, total)
    bins = _write_length_chart(lengths, output)

    quality_rows = [
        ("Analysis population: assistant messages", total),
        ("Missing platform labels", sum(value is None for value in platform_values)),
        ("Missing or invalid timestamps", sum(value is None for value in parsed_dates)),
        ("Missing or blank content", sum(value is None for value in normalized_contents)),
        ("Exact duplicate non-empty content excess (NFC normalized)", duplicate_excess),
        ("Records with non-empty content used for length chart", len(lengths)),
        ("Length histogram bins (Sturges rule)", bins),
    ]
    with (output / "eda_missing_duplicate_summary.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["Metric", "Count"])
        writer.writerows(quality_rows)

    with (output / "eda_scope_summary.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Source file", database.name])
        writer.writerow(["Population", "Assistant messages joined to conversations"])
        writer.writerow(["Records", total])
        writer.writerow(["Date range (inclusive)", f"{start.isoformat()} to {end.isoformat()}"])
        writer.writerow(["Platforms", "; ".join(f"{name}: {count}" for name, count in sorted(platform_counts.items()))])
        writer.writerow(["Content length definition", "Python Unicode code points after NFC normalization"])
        writer.writerow(["Content length minimum", min(lengths)])
        writer.writerow(["Content length first quartile (inclusive)", statistics.quantiles(lengths, n=4, method="inclusive")[0] if len(lengths) > 1 else lengths[0]])
        writer.writerow(["Content length median", statistics.median(lengths)])
        writer.writerow(["Content length third quartile (inclusive)", statistics.quantiles(lengths, n=4, method="inclusive")[2] if len(lengths) > 1 else lengths[0]])
        writer.writerow(["Content length mean", f"{statistics.mean(lengths):.1f}"])
        writer.writerow(["Content length maximum", max(lengths)])
        writer.writerow(["Duplicate definition", "Excess rows with exactly equal non-empty content after NFC normalization"])
        writer.writerow(["Data exported", "Aggregates only; no message content or record identifiers"])

    with (output / "content_by_day_counts.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Assistant message count"])
        day = start
        while day <= end:
            writer.writerow([day.isoformat(), daily_counts[day]])
            day += timedelta(days=1)

    return {
        "database": database.name,
        "records": total,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "platforms": dict(platform_counts),
        "missing_platform": sum(value is None for value in platform_values),
        "missing_timestamp": sum(value is None for value in parsed_dates),
        "missing_content": sum(value is None for value in normalized_contents),
        "duplicate_excess": duplicate_excess,
        "length_records": len(lengths),
        "length_min": min(lengths),
        "length_max": max(lengths),
        "length_q1": statistics.quantiles(lengths, n=4, method="inclusive")[0] if len(lengths) > 1 else lengths[0],
        "length_median": statistics.median(lengths),
        "length_q3": statistics.quantiles(lengths, n=4, method="inclusive")[2] if len(lengths) > 1 else lengths[0],
        "length_mean": statistics.mean(lengths),
        "length_bins": bins,
        "output": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="SQLite database path; defaults to DATABASE_URL")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Output folder (default: {DEFAULT_OUTPUT.relative_to(ROOT)})")
    args = parser.parse_args()
    try:
        database = _resolve_database_path(args.db)
        output = args.output.resolve() if args.output.is_absolute() else (ROOT / args.output).resolve()
        result = run(database, output)
    except (OSError, sqlite3.Error, RuntimeError) as error:
        print(f"EDA stopped: {error}", file=sys.stderr)
        return 2

    print(f"Read-only source: {result['database']}")
    print(f"Assistant messages: {result['records']}; date range: {result['start']} to {result['end']}")
    print(f"Platform counts: {result['platforms']}")
    print(
        "Missing platform/timestamp/content: "
        f"{result['missing_platform']}/{result['missing_timestamp']}/{result['missing_content']}"
    )
    print(f"Exact duplicate content excess: {result['duplicate_excess']}")
    print(
        "Content length (Unicode code points): "
        f"n={result['length_records']}, min={result['length_min']}, "
        f"mean={result['length_mean']:.1f}, max={result['length_max']}"
    )
    print(f"Aggregate-only outputs: {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
