"""
Code extraction implementation.

Parses filesystem tree, groups files by type (source, test, config, doc),
and outputs markdown artifact with embedded JSON metadata.
"""

import argparse
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from utils import (
    detect_project, classify_file, format_markdown_artifact,
    normalize_path, truncate_file_content, count_lines
)

FUNCTION_RE = re.compile(r"^(?:local\s+)?function\s+([A-Za-z_][\w\.:]*)\s*\(")
LOCAL_ASSIGN_RE = re.compile(r"^local\s+([A-Za-z_][\w]*)\s*=")
GLOBAL_ASSIGN_RE = re.compile(r"^([A-Za-z_][\w]*)\s*=")
IGNORED_TOKENS = {
    "if",
    "for",
    "while",
    "repeat",
    "until",
    "return",
    "end",
    "do",
    "then",
    "else",
    "elseif",
    "function",
    "local",
    "require",
    "print",
}

@dataclass
class FileInfo:
    path: str
    language: Optional[str]
    file_type: str
    size_bytes: int
    line_count: int
    content: str
    truncated: bool


@dataclass
class SurfaceFileInfo:
    path: str
    functions: List[str]
    constants: List[str]
    line_count: int


def should_ignore(filepath: Path, ignore_patterns: List[str]) -> bool:
    """Check if file matches any ignore pattern."""
    path_str = str(filepath).replace("\\", "/")
    
    for pattern in ignore_patterns:
        # Simple glob matching (could use fnmatch or glob)
        if "*" in pattern:
            if fnmatch_simple(path_str, pattern):
                return True
        elif pattern in path_str:
            return True
    
    return False

def fnmatch_simple(path: str, pattern: str) -> bool:
    """Simple glob pattern matching."""
    import fnmatch
    return fnmatch.fnmatch(path, pattern)


def extract_lua_symbols(content: str) -> Tuple[List[str], List[str]]:
    """Extract top-level function and constant names from Lua content."""
    functions: List[str] = []
    constants: List[str] = []
    seen_functions = set()
    seen_constants = set()

    for raw_line in content.splitlines():
        if not raw_line or raw_line[0].isspace():
            continue

        code = raw_line.split("--", 1)[0].rstrip()
        if not code:
            continue

        function_match = FUNCTION_RE.match(code)
        if function_match:
            name = function_match.group(1)
            if name not in seen_functions:
                functions.append(name)
                seen_functions.add(name)
            continue

        local_match = LOCAL_ASSIGN_RE.match(code)
        if local_match:
            name = local_match.group(1)
            if name not in seen_constants:
                constants.append(name)
                seen_constants.add(name)
            continue

        global_match = GLOBAL_ASSIGN_RE.match(code)
        if global_match:
            name = global_match.group(1)
            if name not in IGNORED_TOKENS and name not in seen_constants:
                constants.append(name)
                seen_constants.add(name)

    return (sorted(functions), sorted(constants))


def extract_surface_inventory(
    project_path: str,
    ignore_patterns: List[str],
) -> List[SurfaceFileInfo]:
    """Extract Lua surface vectors from a project tree."""
    project_path = Path(project_path)
    surface_files: List[SurfaceFileInfo] = []

    for filepath in sorted(project_path.rglob("*.lua")):
        if not filepath.is_file():
            continue

        if should_ignore(filepath, ignore_patterns):
            continue

        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        functions, constants = extract_lua_symbols(content)
        surface_files.append(
            SurfaceFileInfo(
                path=normalize_path(filepath, project_path),
                functions=functions,
                constants=constants,
                line_count=count_lines(content),
            )
        )

    return surface_files


def infer_inventory_label(project_path: str, fallback: str) -> str:
    """Infer a stable label for a comparison root."""
    if not project_path:
        return fallback

    path = Path(project_path)
    parts = [part.lower() for part in path.parts]
    if "base" in parts:
        return "base"
    if "masterwork" in parts:
        return "masterwork"
    path_text = str(project_path).replace("/", "\\").lower()
    if "df_44_12_win" in path_text or "vanilla" in path_text:
        return "base"
    if "masterwork" in path_text:
        return "masterwork"
    return fallback


def summarize_surface_inventory(surface_files: List[SurfaceFileInfo], root_path: str) -> Dict[str, object]:
    """Build summary stats for a Lua surface inventory."""
    function_count = sum(len(file_info.functions) for file_info in surface_files)
    constant_count = sum(len(file_info.constants) for file_info in surface_files)
    terminal_leaf_paths = set()
    for file_info in surface_files:
        terminal_leaf_paths.add(file_info.path)

    return {
        "root_path": str(Path(root_path).resolve()),
        "file_count": len(surface_files),
        "function_count": function_count,
        "constant_count": constant_count,
        "terminal_leaf_paths": sorted(terminal_leaf_paths),
    }


def format_surface_inventory_section(title: str, surface_files: List[SurfaceFileInfo]) -> str:
    """Format a Lua surface inventory section for markdown output."""
    lines: List[str] = []
    for file_info in sorted(surface_files, key=lambda item: item.path.lower()):
        lines.append(f"### {file_info.path}")
        lines.append(f"- functions: {', '.join(file_info.functions) if file_info.functions else 'NONE'}")
        lines.append(f"- constants: {', '.join(file_info.constants) if file_info.constants else 'NONE'}")
        lines.append(f"- lines: {file_info.line_count}")
        lines.append("")

    if not lines:
        lines.append("No Lua files found.")

    return "\n".join(lines)


def build_dimension_inventory_report(
    primary_path: str,
    comparison_path: Optional[str],
    ignore_patterns: List[str],
    force: bool,
) -> str:
    """Build a comparison report for Lua surface vectors."""
    primary_label = infer_inventory_label(primary_path, "primary")
    comparison_label = infer_inventory_label(comparison_path, "comparison") if comparison_path else None

    primary_files = extract_surface_inventory(primary_path, ignore_patterns)
    comparison_files = extract_surface_inventory(comparison_path, ignore_patterns) if comparison_path else []

    primary_summary = summarize_surface_inventory(primary_files, primary_path)
    comparison_summary = summarize_surface_inventory(comparison_files, comparison_path) if comparison_path else None

    sections: Dict[str, str] = {}
    mode_lines = [
        "- **Mode**: dimension_inventory",
        "- **Sort order**: mod -> file -> top-level key type",
        f"- **Primary Root**: {primary_summary['root_path']}",
    ]
    if comparison_summary:
        mode_lines.append(f"- **Comparison Root**: {comparison_summary['root_path']}")
    sections["Mode"] = "\n".join(mode_lines) + "\n"

    def summary_block(label: str, summary: Dict[str, object]) -> str:
        terminal_leaf_paths = ", ".join(summary["terminal_leaf_paths"]) if summary["terminal_leaf_paths"] else "NONE"
        return (
            f"- **Root**: {summary['root_path']}\n"
            f"- **Files**: {summary['file_count']}\n"
            f"- **Functions**: {summary['function_count']}\n"
            f"- **Constants**: {summary['constant_count']}\n"
            f"- **Terminal Leaf Paths**: {terminal_leaf_paths}\n"
        )

    sections[f"{primary_label.title()} Summary"] = summary_block(primary_label, primary_summary)
    sections[f"{primary_label.title()} Inventory"] = format_surface_inventory_section(primary_label, primary_files)

    if comparison_summary and comparison_label:
        sections[f"{comparison_label.title()} Summary"] = summary_block(comparison_label, comparison_summary)
        sections[f"{comparison_label.title()} Inventory"] = format_surface_inventory_section(comparison_label, comparison_files)

    metadata = {
        "artifact_type": "code_extraction",
        "mode": "dimension_inventory",
        "language": "lua",
        "primary_root": primary_summary["root_path"],
        "comparison_root": comparison_summary["root_path"] if comparison_summary else None,
        "file_count": primary_summary["file_count"] + (comparison_summary["file_count"] if comparison_summary else 0),
        "function_count": primary_summary["function_count"] + (comparison_summary["function_count"] if comparison_summary else 0),
        "constant_count": primary_summary["constant_count"] + (comparison_summary["constant_count"] if comparison_summary else 0),
    }

    provenance = {
        "primary_path": str(Path(primary_path).resolve()),
        "comparison_path": str(Path(comparison_path).resolve()) if comparison_path else None,
        "ignore_patterns": ignore_patterns,
        "report_mode": "dimension_inventory",
    }

    return format_markdown_artifact(
        "code_extraction",
        "Dimension Inventory",
        sections,
        metadata,
        provenance,
    )

def extract_files(
    project_path: str,
    ignore_patterns: List[str],
    max_file_bytes: int,
    include_tests: bool = True
) -> Dict[str, List[FileInfo]]:
    """
    Extract files from project, grouped by type.
    
    Returns:
        Dict[file_type → List[FileInfo]]
    """
    project_path = Path(project_path)
    grouped_files: Dict[str, List[FileInfo]] = {
        "source": [],
        "test": [],
        "config": [],
        "doc": []
    }
    
    for filepath in project_path.rglob("*"):
        if not filepath.is_file():
            continue
        
        # Check ignore patterns
        if should_ignore(filepath, ignore_patterns):
            continue
        
        # Skip tests if not included
        lang, file_type = classify_file(str(filepath))
        if file_type == "test" and not include_tests:
            continue
        
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            continue  # Skip unreadable files
        
        truncated_content, was_truncated = truncate_file_content(
            content, max_file_bytes
        )
        
        file_info = FileInfo(
            path=normalize_path(filepath, project_path),
            language=lang,
            file_type=file_type,
            size_bytes=len(content),
            line_count=count_lines(content),
            content=truncated_content,
            truncated=was_truncated
        )
        
        grouped_files[file_type].append(file_info)
    
    return grouped_files

def build_tree(project_path: str, max_depth: int = 5) -> str:
    """Build directory tree with file counts."""
    lines = []
    
    def walk_tree(path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
        
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            current = "└── " if is_last else "├── "
            next_prefix = "    " if is_last else "│   "
            
            if entry.is_file():
                line_count = count_lines(entry.read_text(errors="ignore"))
                lines.append(f"{prefix}{current}{entry.name} ({line_count} lines)")
            else:
                lines.append(f"{prefix}{current}{entry.name}/")
                walk_tree(entry, prefix + next_prefix, depth + 1)
    
    lines.append(f"{project_path}/")
    walk_tree(Path(project_path))
    return "\n".join(lines)

def extract(
    project_path: str,
    ignore_patterns: Optional[List[str]] = None,
    max_file_bytes: int = 50000,
    include_tests: bool = True,
    force: bool = False,
    report_mode: str = "standard",
    comparison_path: Optional[str] = None
) -> str:
    """
    Extract codebase into markdown artifact.
    
    Args:
        project_path: Path to project root
        ignore_patterns: Glob patterns to skip (default: common build dirs)
        max_file_bytes: Max file size before truncation
        include_tests: Include test files in output
        force: Skip project detection
        report_mode: "standard" or "dimension_inventory"
        comparison_path: Optional comparison root for dimension inventory mode
    
    Returns:
        Markdown artifact string
    """
    if ignore_patterns is None:
        ignore_patterns = [
            "build", "dist", "__pycache__", "node_modules",
            ".git", ".venv", "*.egg-info", ".pytest_cache"
        ]
    
    if report_mode == "dimension_inventory" or comparison_path:
        return build_dimension_inventory_report(
            project_path,
            comparison_path,
            ignore_patterns,
            force,
        )

    # Detect project
    language = detect_project(project_path, force=force)
    if not language:
        raise ValueError(
            f"Project not detected at {project_path}. "
            "Pass force=True to override, or add marker file."
        )
    
    # Extract files
    grouped_files = extract_files(
        project_path, ignore_patterns, max_file_bytes, include_tests
    )
    
    # Count totals
    total_files = sum(len(f) for f in grouped_files.values())
    total_lines = sum(f.line_count for files in grouped_files.values() for f in files)
    
    # Build sections
    sections = {}
    
    # Overview
    overview = f"""- **Language**: {language}
- **Source Files**: {len(grouped_files['source'])}
- **Test Files**: {len(grouped_files['test'])}
- **Config Files**: {len(grouped_files['config'])}
- **Total Files**: {total_files}
- **Total Lines**: {total_lines}
"""
    sections["Project Overview"] = overview
    
    # Directory tree
    sections["Directory Tree"] = f"```\n{build_tree(project_path)}\n```"
    
    # Source files
    source_content = ""
    for file_info in grouped_files["source"]:
        marker = " ⚠️ TRUNCATED" if file_info.truncated else ""
        source_content += f"### {file_info.path}{marker}\n"
        source_content += f"```{file_info.language or 'text'}\n"
        source_content += file_info.content + "\n```\n\n"
    if source_content:
        sections["Source Files"] = source_content
    
    # Test files
    if grouped_files["test"]:
        test_content = ""
        for file_info in grouped_files["test"]:
            test_content += f"### {file_info.path}\n"
            test_content += f"```{file_info.language or 'text'}\n"
            test_content += file_info.content + "\n```\n\n"
        sections["Test Files"] = test_content
    
    # Config files
    if grouped_files["config"]:
        config_content = ""
        for file_info in grouped_files["config"]:
            config_content += f"### {file_info.path}\n"
            config_content += f"```{file_info.language or 'text'}\n"
            config_content += file_info.content + "\n```\n\n"
        sections["Configuration Files"] = config_content
    
    # Build metadata
    metadata = {
        "artifact_type": "code_extraction",
        "mode": report_mode,
        "language": language,
        "file_count": total_files,
        "source_count": len(grouped_files["source"]),
        "test_count": len(grouped_files["test"]),
        "config_count": len(grouped_files["config"]),
        "total_lines": total_lines
    }
    
    provenance = {
        "project_path": str(Path(project_path).resolve()),
        "ignore_patterns": ignore_patterns,
        "max_file_bytes": max_file_bytes
    }
    
    return format_markdown_artifact(
        "code_extraction",
        "Code Extraction Report",
        sections,
        metadata,
        provenance
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract a codebase into markdown.")
    parser.add_argument("project_path", help="Path to the project root")
    parser.add_argument("--compare-with", dest="comparison_path", help="Optional comparison root for dimension inventory mode")
    parser.add_argument(
        "--mode",
        dest="report_mode",
        choices=["standard", "dimension_inventory"],
        default="standard",
        help="Report mode to generate",
    )
    parser.add_argument("--force", action="store_true", help="Skip project detection")
    args = parser.parse_args()

    artifact = extract(
        args.project_path,
        force=args.force,
        report_mode=args.report_mode,
        comparison_path=args.comparison_path,
    )
    print(artifact)
