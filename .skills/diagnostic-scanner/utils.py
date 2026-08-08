"""
Shared utilities for megaprompter-derived skills.
- Project detection (language markers, file count fallback)
- Language classification (extension → language → tools)
- Artifact formatting (markdown + JSON metadata)
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class LanguageInfo:
    """Detected language info."""
    name: str
    package_manager: str
    file_extensions: List[str]
    marker_files: List[str]
    
LANGUAGE_CONFIG = {
    "python": LanguageInfo(
        name="python",
        package_manager="pip",
        file_extensions=[".py"],
        marker_files=["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"]
    ),
    "go": LanguageInfo(
        name="go",
        package_manager="go",
        file_extensions=[".go"],
        marker_files=["go.mod", "go.sum"]
    ),
    "rust": LanguageInfo(
        name="rust",
        package_manager="cargo",
        file_extensions=[".rs"],
        marker_files=["Cargo.toml", "Cargo.lock"]
    ),
    "swift": LanguageInfo(
        name="swift",
        package_manager="swift",
        file_extensions=[".swift"],
        marker_files=["Package.swift"]
    ),
    "javascript": LanguageInfo(
        name="javascript",
        package_manager="npm",
        file_extensions=[".js", ".jsx"],
        marker_files=["package.json", "package-lock.json"]
    ),
    "typescript": LanguageInfo(
        name="typescript",
        package_manager="npm",
        file_extensions=[".ts", ".tsx"],
        marker_files=["tsconfig.json", "package.json"]
    ),
    "java": LanguageInfo(
        name="java",
        package_manager="maven",
        file_extensions=[".java"],
        marker_files=["pom.xml", "build.gradle"]
    ),
}

def detect_project(path: str, force: bool = False) -> Optional[str]:
    """
    Detect project language.
    
    Returns language name if markers found or 8+ source files exist.
    Returns None if project not detected (unless force=True).
    """
    path = Path(path)
    if not path.exists():
        return None
    
    # Check for language markers
    for lang, config in LANGUAGE_CONFIG.items():
        for marker in config.marker_files:
            if (path / marker).exists():
                return lang
    
    # Fallback: count recognizable source files
    if force:
        return "unknown"
    
    source_file_count = sum(
        1 for cfg in LANGUAGE_CONFIG.values()
        for ext in cfg.file_extensions
        for _ in path.rglob(f"*{ext}")
    )
    
    if source_file_count >= 8:
        # Infer language from most frequent extension
        ext_counts = {}
        for cfg in LANGUAGE_CONFIG.values():
            for ext in cfg.file_extensions:
                ext_counts[ext] = len(list(path.rglob(f"*{ext}")))
        most_common_ext = max(ext_counts.items(), key=lambda x: x[1])[0]
        for lang, cfg in LANGUAGE_CONFIG.items():
            if most_common_ext in cfg.file_extensions:
                return lang
    
    return None

def classify_file(filepath: str) -> Tuple[Optional[str], str]:
    """
    Classify file by type (source, test, config, doc).
    Returns (language, file_type).
    """
    path = Path(filepath)
    name = path.name.lower()
    ext = path.suffix.lower()
    
    # Determine file type
    if name.startswith("test_") or name.endswith("_test.py") or "test" in path.parts:
        file_type = "test"
    elif name in ["readme.md", "license", "contributing.md"]:
        file_type = "doc"
    elif ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"]:
        file_type = "config"
    elif ext in [".md", ".rst", ".txt"]:
        file_type = "doc"
    else:
        file_type = "source"
    
    # Determine language
    language = None
    for lang, config in LANGUAGE_CONFIG.items():
        if ext in config.file_extensions:
            language = lang
            break
    
    return (language, file_type)

def format_markdown_artifact(
    artifact_type: str,
    title: str,
    sections: Dict[str, str],
    metadata: Dict,
    provenance: Optional[Dict] = None
) -> str:
    """
    Format a unified markdown artifact with metadata.
    
    Args:
        artifact_type: "code_extraction" | "diagnostic" | "test_plan" | "documentation"
        title: Report title
        sections: Dict[section_name → markdown_content]
        metadata: Dict with artifact_type, language, timestamp, etc.
        provenance: Optional dict with sources, commands, refs
    
    Returns:
        Formatted markdown string
    """
    md = f"# {title}\n\n"
    
    # Add sections
    for section_name, content in sections.items():
        md += f"## {section_name}\n"
        md += content + "\n\n"
    
    # Add metadata block
    md += "## Metadata\n"
    md += "```json\n"
    metadata["timestamp"] = datetime.utcnow().isoformat() + "Z"
    md += json.dumps(metadata, indent=2) + "\n"
    md += "```\n\n"
    
    # Add provenance block if provided
    if provenance:
        md += "## Provenance\n"
        md += "```json\n"
        md += json.dumps(provenance, indent=2) + "\n"
        md += "```\n"
    
    return md

def normalize_path(path: str, base: str) -> str:
    """Normalize path relative to base."""
    base = Path(base).resolve()
    path = Path(path).resolve()
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)

def truncate_file_content(content: str, max_bytes: int) -> Tuple[str, bool]:
    """
    Truncate content to max_bytes.
    
    Returns:
        (truncated_content, was_truncated)
    """
    if len(content) <= max_bytes:
        return (content, False)
    
    truncated = content[:max_bytes]
    truncated += "\n\n... (truncated, file exceeds max_bytes limit)\n"
    return (truncated, True)

def count_lines(content: str) -> int:
    """Count lines in content."""
    return len(content.splitlines())
