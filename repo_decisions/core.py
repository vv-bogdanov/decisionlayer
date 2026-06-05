from __future__ import annotations

import os
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable


LOCAL_CONFIG = Path(".codex/repo-decisions.toml")
GLOBAL_CONFIG_ENV = "REPO_DECISIONS_GLOBAL_CONFIG"
DEFAULT_GLOBAL_CONFIG = Path("~/.codex/repo-decisions/config.toml")
DEFAULT_ADR_DIR = Path("docs/adr")
COMMON_ADR_DIRS = [
    Path("docs/adr"),
    Path("docs/adrs"),
    Path("docs/decisions"),
    Path("doc/adr"),
    Path("adr"),
    Path("adrs"),
    Path("decisions"),
    Path(".adr"),
    Path("architecture/decisions"),
    Path("docs/architecture/decisions"),
]
DEFAULT_BRIEF_MAX_CHARS = 6000
ACTIVE_STATUS = "accepted"
INACTIVE_STATUSES = {"proposed", "rejected", "deprecated", "superseded"}


@dataclass(frozen=True)
class AdrRecord:
    id: str
    number: int | None
    title: str
    status: str
    path: Path
    date: str | None = None
    context: str = ""
    decision: str = ""
    consequences: str = ""
    options: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    frontmatter: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FormatProfile:
    number_width: int = 4
    filename_style: str = "{number:04d}-{slug}.md"
    status_style: str = "section"
    date_style: str = "inline"
    section_headings: tuple[str, ...] = (
        "Status",
        "Context and Problem Statement",
        "Considered Options",
        "Decision",
        "Consequences",
    )
    template_path: Path | None = None


@dataclass(frozen=True)
class LocationResult:
    root: Path
    adr_dir: Path
    source: str
    config: dict[str, object]
    profile: FormatProfile
    records: tuple[AdrRecord, ...]


def find_repo_root(start: Path | str = ".") -> Path:
    start_path = Path(start).resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(start_path), "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return start_path
    return Path(result.stdout.strip()).resolve()


def load_config(root: Path) -> dict[str, object]:
    global_config = _global_config_path()
    merged: dict[str, object] = {}
    for path in (global_config, root / LOCAL_CONFIG):
        if path.exists():
            merged.update(_read_toml(path))
    return merged


def locate_adrs(start: Path | str = ".") -> LocationResult:
    root = find_repo_root(start)
    config = load_config(root)
    candidates = _candidate_dirs(root, config)

    for rel_dir, source in candidates:
        adr_dir = root / rel_dir
        records = tuple(_scan_records(adr_dir))
        template_path = _find_template(adr_dir)
        if records or template_path:
            profile = profile_format(records, template_path)
            return LocationResult(root, adr_dir, source, config, profile, records)

    default_dir = Path(str(config.get("default_dir") or DEFAULT_ADR_DIR))
    adr_dir = root / default_dir
    profile = FormatProfile()
    return LocationResult(root, adr_dir, "default", config, profile, tuple())


def list_decisions(start: Path | str = ".", include_inactive: bool = True) -> list[AdrRecord]:
    records = list(locate_adrs(start).records)
    if include_inactive:
        return records
    return [record for record in records if record.status == ACTIVE_STATUS]


def build_brief(start: Path | str = ".", max_chars: int | None = None) -> str:
    location = locate_adrs(start)
    configured_max = _as_int(location.config.get("brief_max_chars"), DEFAULT_BRIEF_MAX_CHARS)
    limit = max_chars or configured_max
    active = [record for record in location.records if record.status == ACTIVE_STATUS]

    if not active:
        return ""

    lines = [
        "# Repository ADR Decisions (Hard Requirements)",
        "",
        "These accepted ADR decisions are binding unless the user explicitly supersedes them.",
        "",
    ]
    for record in active:
        summary = _one_line(record.decision or record.sections.get("decision outcome", ""))
        if not summary:
            summary = _one_line(record.title)
        record_id = record.id or _display_id(record)
        lines.append(f"- {record_id}: {record.title}. Decision: {summary}")
        if record.consequences:
            lines.append(f"  Consequences: {_one_line(record.consequences)}")

    brief = "\n".join(lines).strip() + "\n"
    if len(brief) <= limit:
        return brief
    clipped = brief[: max(0, limit - 90)].rstrip()
    return clipped + "\n- Additional accepted ADRs were omitted because the brief size limit was reached.\n"


def add_decision(
    start: Path | str = ".",
    *,
    title: str,
    context: str,
    decision: str,
    consequences: Iterable[str] | str,
    options: Iterable[str] = (),
    status: str = ACTIVE_STATUS,
    supersedes: AdrRecord | None = None,
) -> Path:
    location = locate_adrs(start)
    location.adr_dir.mkdir(parents=True, exist_ok=True)
    next_number = _next_number(location.records)
    filename = _filename_for(location.profile, next_number, title)
    path = location.adr_dir / filename
    if path.exists():
        raise FileExistsError(path)

    text = render_adr(
        location.profile,
        number=next_number,
        title=title,
        status=status,
        context=context,
        decision=decision,
        consequences=consequences,
        options=options,
        supersedes=supersedes,
    )
    path.write_text(text, encoding="utf-8")
    return path


def supersede_decision(
    start: Path | str,
    target: str,
    *,
    title: str,
    context: str,
    decision: str,
    consequences: Iterable[str] | str,
    options: Iterable[str] = (),
) -> tuple[Path, Path]:
    location = locate_adrs(start)
    old = _find_record(location.records, target)
    if old.status != ACTIVE_STATUS:
        raise ValueError(f"Only accepted ADRs can be superseded through this tool: {old.path}")

    new_path = add_decision(
        start,
        title=title,
        context=context,
        decision=decision,
        consequences=consequences,
        options=options,
        status=ACTIVE_STATUS,
        supersedes=old,
    )
    new_record = parse_adr_file(new_path)
    _mark_superseded(old.path, old, new_record)
    _append_backlink(new_path, old)
    return old.path, new_path


def profile_format(records: Iterable[AdrRecord], template_path: Path | None = None) -> FormatProfile:
    records = tuple(records)
    if not records:
        return FormatProfile(template_path=template_path)

    latest = sorted(records, key=lambda record: (record.number or 0, str(record.path)))[-1]
    number_width = _number_width(records)
    filename_style = _filename_style(latest.path.name, number_width)
    status_style = _status_style(latest)
    date_style = _date_style(latest)
    section_headings = _section_headings(latest)
    return FormatProfile(
        number_width=number_width,
        filename_style=filename_style,
        status_style=status_style,
        date_style=date_style,
        section_headings=section_headings,
        template_path=template_path,
    )


def parse_adr_file(path: Path) -> AdrRecord:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    title = _extract_title(body) or path.stem
    sections = _extract_sections(body)
    status = _normalize_status(
        frontmatter.get("status")
        or _inline_value(body, "status")
        or _first_section_line(sections, "status")
        or "unknown"
    )
    date_value = frontmatter.get("date") or _inline_value(body, "date")
    number = _extract_number(path.name)
    context = _section_value(sections, "context and problem statement", "context")
    decision = _section_value(sections, "decision", "decision outcome")
    consequences = _section_value(sections, "consequences")
    options = _list_items(_section_value(sections, "considered options", "options"))
    return AdrRecord(
        id=_display_id_from_number(number),
        number=number,
        title=title,
        status=status,
        path=path,
        date=date_value,
        context=context,
        decision=decision,
        consequences=consequences,
        options=options,
        sections=sections,
        frontmatter=frontmatter,
    )


def render_adr(
    profile: FormatProfile,
    *,
    number: int,
    title: str,
    status: str,
    context: str,
    decision: str,
    consequences: Iterable[str] | str,
    options: Iterable[str],
    supersedes: AdrRecord | None = None,
) -> str:
    today = date.today().isoformat()
    title_line = _title_line(profile, number, title)
    context_heading = _pick_heading(profile, "Context and Problem Statement", "Context")
    options_heading = _pick_heading(profile, "Considered Options", "Options")
    decision_heading = _pick_heading(profile, "Decision", "Decision Outcome")
    consequences_heading = _pick_heading(profile, "Consequences")
    parts: list[str] = []

    if profile.status_style == "frontmatter":
        parts.extend(["---", f"status: {status}", f"date: {today}"])
        if supersedes:
            parts.append(f"supersedes: {supersedes.id}")
        parts.extend(["---", ""])
        parts.append(title_line)
    else:
        parts.append(title_line)
        parts.append("")
        if profile.date_style == "inline":
            parts.append(f"Date: {today}")
            parts.append("")
        if supersedes:
            parts.append(f"Supersedes: [{supersedes.id} {supersedes.title}]({supersedes.path.name})")
            parts.append("")
        if profile.status_style == "inline":
            parts.append(f"Status: {status.title()}")
        else:
            status_heading = _pick_heading(profile, "Status")
            parts.append(f"## {status_heading}")
            parts.append("")
            parts.append(status.title())
        parts.append("")

    parts.extend([f"## {context_heading}", "", context.strip(), ""])
    option_list = list(options)
    if option_list or _has_heading(profile, options_heading):
        parts.extend([f"## {options_heading}", ""])
        parts.extend([f"- {option.strip()}" for option in option_list if option.strip()])
        if not option_list:
            parts.append("- Chosen option")
        parts.append("")
    parts.extend([f"## {decision_heading}", "", decision.strip(), ""])
    parts.extend([f"## {consequences_heading}", ""])
    if isinstance(consequences, str):
        consequence_lines = [line.strip() for line in consequences.splitlines() if line.strip()]
    else:
        consequence_lines = [line.strip() for line in consequences if line.strip()]
    if len(consequence_lines) <= 1:
        parts.append(consequence_lines[0] if consequence_lines else "No known consequences yet.")
    else:
        parts.extend([f"- {line.removeprefix('-').strip()}" for line in consequence_lines])
    parts.append("")
    return "\n".join(parts)


def _candidate_dirs(root: Path, config: dict[str, object]) -> list[tuple[Path, str]]:
    dirs: list[tuple[Path, str]] = []
    local_dir = config.get("adr_dir") or config.get("default_dir")
    if isinstance(local_dir, str):
        dirs.append((Path(local_dir), "config"))
    for key in ("adr_dirs", "candidate_dirs"):
        value = config.get(key)
        if isinstance(value, list):
            dirs.extend((Path(str(item)), "config") for item in value)
    dirs.extend((path, "common") for path in COMMON_ADR_DIRS)

    seen: set[Path] = set()
    result: list[tuple[Path, str]] = []
    for rel_dir, source in dirs:
        normalized = Path(rel_dir)
        if normalized.is_absolute():
            try:
                normalized = normalized.relative_to(root)
            except ValueError:
                pass
        if normalized not in seen:
            seen.add(normalized)
            result.append((normalized, source))
    return result


def _scan_records(adr_dir: Path) -> list[AdrRecord]:
    if not adr_dir.is_dir():
        return []
    records = []
    for path in sorted(adr_dir.glob("*.md")):
        if _is_template(path):
            continue
        try:
            record = parse_adr_file(path)
        except UnicodeDecodeError:
            continue
        if _looks_like_adr(record):
            records.append(record)
    return records


def _find_template(adr_dir: Path) -> Path | None:
    if not adr_dir.is_dir():
        return None
    names = ("adr-template.md", "template.md", "adr_template.md")
    for name in names:
        path = adr_dir / name
        if path.exists():
            return path
    for path in sorted(adr_dir.glob("*template*.md")):
        return path
    return None


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 4 :].lstrip()
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower()] = value.strip().strip('"').strip("'")
    return data, body


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def _extract_sections(text: str) -> dict[str, str]:
    headings: list[tuple[str, int, int]] = []
    for match in re.finditer(r"(?m)^\s*(#{2,6})\s+(.+?)\s*$", text):
        headings.append((_normalize_heading(match.group(2)), match.start(), match.end()))
    sections: dict[str, str] = {}
    for idx, (name, _start, end) in enumerate(headings):
        next_start = headings[idx + 1][1] if idx + 1 < len(headings) else len(text)
        sections[name] = text[end:next_start].strip()
    return sections


def _inline_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?im)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else None


def _first_section_line(sections: dict[str, str], key: str) -> str | None:
    value = sections.get(key)
    if not value:
        return None
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _section_value(sections: dict[str, str], *names: str) -> str:
    for name in names:
        value = sections.get(_normalize_heading(name))
        if value:
            return value.strip()
    return ""


def _list_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def _normalize_heading(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    normalized = normalized.strip("# ")
    return normalized


def _normalize_status(value: str) -> str:
    lowered = value.strip().lower().rstrip(".")
    if "superseded" in lowered or "superceded" in lowered:
        return "superseded"
    for status in ("accepted", "proposed", "rejected", "deprecated"):
        if status in lowered:
            return status
    return lowered.split()[0] if lowered else "unknown"


def _looks_like_adr(record: AdrRecord) -> bool:
    if record.number is not None:
        return True
    if record.status in {ACTIVE_STATUS, *INACTIVE_STATUSES} and (record.decision or record.context):
        return True
    return bool(record.decision and record.consequences)


def _is_template(path: Path) -> bool:
    lowered = path.name.lower()
    return "template" in lowered or lowered.startswith("0000-")


def _extract_number(filename: str) -> int | None:
    match = re.match(r"^(?:adr[-_ ]*)?0*(\d+)", filename, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _display_id(record: AdrRecord) -> str:
    return record.id or _display_id_from_number(record.number)


def _display_id_from_number(number: int | None) -> str:
    return f"ADR-{number:04d}" if number is not None else "ADR"


def _number_width(records: Iterable[AdrRecord]) -> int:
    widths = []
    for record in records:
        match = re.match(r"^(?:adr[-_ ]*)?(\d+)", record.path.name, re.IGNORECASE)
        if match:
            widths.append(len(match.group(1)))
    return max(widths) if widths else 4


def _filename_style(filename: str, width: int) -> str:
    match = re.match(r"^(?P<prefix>.*?)(?P<num>\d+)(?P<sep>[-_. ]?)(?P<title>.*)\.md$", filename)
    if not match:
        return f"{{number:0{width}d}}-{{slug}}.md"
    prefix = match.group("prefix")
    sep = match.group("sep") or "-"
    return f"{prefix}{{number:0{width}d}}{sep}{{slug}}.md"


def _status_style(record: AdrRecord) -> str:
    text = record.path.read_text(encoding="utf-8")
    if "status" in record.frontmatter:
        return "frontmatter"
    if re.search(r"(?im)^\s*status\s*:", text):
        return "inline"
    return "section"


def _date_style(record: AdrRecord) -> str:
    text = record.path.read_text(encoding="utf-8")
    if "date" in record.frontmatter:
        return "frontmatter"
    if re.search(r"(?im)^\s*date\s*:", text):
        return "inline"
    return "none"


def _section_headings(record: AdrRecord) -> tuple[str, ...]:
    text = record.path.read_text(encoding="utf-8")
    headings = []
    for line in text.splitlines():
        match = re.match(r"^\s*##+\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(1).strip())
    return tuple(headings) or FormatProfile().section_headings


def _pick_heading(profile: FormatProfile, default: str, *alternatives: str) -> str:
    wanted = {_normalize_heading(default), *(_normalize_heading(item) for item in alternatives)}
    for heading in profile.section_headings:
        if _normalize_heading(heading) in wanted:
            return heading
    return default


def _has_heading(profile: FormatProfile, heading: str) -> bool:
    wanted = _normalize_heading(heading)
    return any(_normalize_heading(item) == wanted for item in profile.section_headings)


def _title_line(profile: FormatProfile, number: int, title: str) -> str:
    if profile.filename_style.lower().startswith("adr-"):
        return f"# ADR-{number:0{profile.number_width}d}: {title}"
    if any(re.match(r"^\d+\.", heading) for heading in [title]):
        return f"# {title}"
    return f"# {number}. {title}"


def _next_number(records: Iterable[AdrRecord]) -> int:
    numbers = [record.number for record in records if record.number is not None]
    return (max(numbers) + 1) if numbers else 1


def _filename_for(profile: FormatProfile, number: int, title: str) -> str:
    slug = _slugify(title)
    return profile.filename_style.format(number=number, slug=slug)


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return slug or "decision"


def _one_line(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"^[-*]\s+", "", value)
    return value[:280].rstrip()


def _find_record(records: Iterable[AdrRecord], target: str) -> AdrRecord:
    normalized = target.lower().strip()
    for record in records:
        candidates = {
            str(record.number or ""),
            record.id.lower(),
            record.path.name.lower(),
            record.path.stem.lower(),
        }
        if normalized in candidates:
            return record
    raise ValueError(f"ADR not found: {target}")


def _mark_superseded(path: Path, old: AdrRecord, new: AdrRecord) -> None:
    text = path.read_text(encoding="utf-8")
    replacement = f"Superseded by {new.id}"
    if "status" in old.frontmatter:
        text = re.sub(r"(?im)^status\s*:.*$", f"status: {replacement}", text, count=1)
    elif re.search(r"(?im)^\s*status\s*:", text):
        text = re.sub(r"(?im)^(\s*status\s*:\s*).*$", rf"\1{replacement}", text, count=1)
    else:
        text = _replace_status_section(text, replacement)
    path.write_text(text, encoding="utf-8")


def _replace_status_section(text: str, replacement: str) -> str:
    match = re.search(r"(?im)^\s*##\s+Status\s*$", text)
    if not match:
        return text + f"\n\n## Status\n\n{replacement}\n"
    next_heading = re.search(r"(?m)^\s*##\s+", text[match.end() :])
    section_end = match.end() + next_heading.start() if next_heading else len(text)
    return text[: match.end()] + f"\n\n{replacement}\n\n" + text[section_end:].lstrip()


def _append_backlink(path: Path, old: AdrRecord) -> None:
    text = path.read_text(encoding="utf-8")
    backlink = f"\nSupersedes: [{old.id} {old.title}]({old.path.name})\n"
    if "Supersedes:" not in text:
        text = text.rstrip() + "\n" + backlink
        path.write_text(text, encoding="utf-8")


def _read_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _global_config_path() -> Path:
    override = os.environ.get(GLOBAL_CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    return DEFAULT_GLOBAL_CONFIG.expanduser()


def _as_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
