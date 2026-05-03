"""
Code extraction implementation.

Parses filesystem tree, groups files by type (source, test, config, doc),
and outputs markdown artifact with embedded JSON metadata.
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json

from utils import (
    detect_project, classify_file, format_markdown_artifact,
    normalize_path, truncate_file_content, count_lines
)

@dataclass
class FileInfo:
    path: str
    language: Optional[str]
    file_type: str
    size_bytes: int
    line_count: int
    content: str
    truncated: bool

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
    force: bool = False
) -> str:
    """
    Extract codebase into markdown artifact.
    
    Args:
        project_path: Path to project root
        ignore_patterns: Glob patterns to skip (default: common build dirs)
        max_file_bytes: Max file size before truncation
        include_tests: Include test files in output
        force: Skip project detection
    
    Returns:
        Markdown artifact string
    """
    if ignore_patterns is None:
        ignore_patterns = [
            "build", "dist", "__pycache__", "node_modules",
            ".git", ".venv", "*.egg-info", ".pytest_cache"
        ]
    
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
    # Example usage
    import sys
    if len(sys.argv) < 2:
        print("Usage: python code_extraction.py <project_path>")
        sys.exit(1)
    
    artifact = extract(sys.argv[1])
    print(artifact)
