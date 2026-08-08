"""
Diagnostic scanner implementation.

Invokes language-appropriate tools (mypy, pylint, go vet, etc.),
captures errors/warnings, normalizes output, and generates fix prompts.
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from utils import detect_project, format_markdown_artifact

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class Violation:
    file: str
    line: int
    column: int
    severity: Severity
    code: str
    message: str
    fix_hint: Optional[str] = None

TOOL_COMMANDS = {
    "python": [
        ["python", "-m", "mypy", "--json"],
        ["python", "-m", "pylint", "--output-format=json"],
    ],
    "go": [
        ["go", "vet", "./..."],
        ["golangci-lint", "run", "--out-format", "json"],
    ],
    "rust": [
        ["cargo", "check", "--message-format", "json"],
        ["cargo", "clippy", "--message-format", "json"],
    ],
    "swift": [
        ["swiftc", "-typecheck"],
    ],
    "javascript": [
        ["eslint", "--format", "json", "."],
    ],
    "typescript": [
        ["tsc", "--noEmit", "--listFiles"],
        ["eslint", "--format", "json", "."],
    ],
}

def run_tool(command: List[str]) -> Tuple[int, str, str]:
    """Run a diagnostic tool, return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (1, "", "Tool timeout (30s)")
    except FileNotFoundError:
        return (1, "", f"Tool not found: {command[0]}")
    except Exception as e:
        return (1, "", str(e))

def parse_mypy_json(output: str) -> List[Violation]:
    """Parse mypy JSON output."""
    violations = []
    try:
        results = json.loads(output)
        for item in results:
            violations.append(Violation(
                file=item.get("filename", ""),
                line=item.get("line", 0),
                column=item.get("column", 0),
                severity=Severity.ERROR if item.get("severity") == "error" else Severity.WARNING,
                code=item.get("error_code", ""),
                message=item.get("message", "")
            ))
    except json.JSONDecodeError:
        pass
    return violations

def parse_pylint_json(output: str) -> List[Violation]:
    """Parse pylint JSON output."""
    violations = []
    try:
        results = json.loads(output)
        for item in results:
            violations.append(Violation(
                file=item.get("path", ""),
                line=item.get("line", 0),
                column=item.get("column", 0),
                severity=Severity(item.get("type", "warning").lower()),
                code=item.get("symbol", ""),
                message=item.get("message", "")
            ))
    except (json.JSONDecodeError, ValueError):
        pass
    return violations

def scan(
    project_path: str,
    include_tests: bool = False,
    ignore_patterns: Optional[List[str]] = None,
    max_analyze_bytes: int = 500000
) -> str:
    """
    Scan project for diagnostics.
    
    Args:
        project_path: Path to project root
        include_tests: Include test compilation
        ignore_patterns: Patterns to skip
        max_analyze_bytes: Max bytes to analyze
    
    Returns:
        Markdown artifact with diagnostic results
    """
    language = detect_project(project_path)
    if not language:
        raise ValueError(f"Project not detected at {project_path}")
    
    violations: List[Violation] = []
    tool_outputs: List[str] = []
    
    # Run language-appropriate tools
    for tool_command in TOOL_COMMANDS.get(language, []):
        exit_code, stdout, stderr = run_tool(tool_command)
        tool_outputs.append(f"Tool: {' '.join(tool_command)}")
        
        if exit_code == 0:
            tool_outputs.append("✅ Tool succeeded")
        else:
            tool_outputs.append(f"⚠️  Tool exited with code {exit_code}")
        
        # Parse output based on language/tool
        if "mypy" in tool_command[2]:
            violations.extend(parse_mypy_json(stdout))
        elif "pylint" in tool_command[2]:
            violations.extend(parse_pylint_json(stdout))
        # Add other parsers as needed
    
    # Group violations by severity
    errors = [v for v in violations if v.severity == Severity.ERROR]
    warnings = [v for v in violations if v.severity == Severity.WARNING]
    infos = [v for v in violations if v.severity == Severity.INFO]
    
    # Build sections
    sections = {}
    
    # Overview
    overview = f"""- **Language**: {language}
- **Errors**: {len(errors)}
- **Warnings**: {len(warnings)}
- **Infos**: {len(infos)}
- **Tools Run**: {len(TOOL_COMMANDS.get(language, []))}
"""
    sections["Overview"] = overview
    
    # Errors
    if errors:
        error_content = ""
        for v in errors:
            error_content += f"### {v.file}:{v.line} ({v.code})\n"
            error_content += f"```\n{v.message}\n```\n"
            if v.fix_hint:
                error_content += f"**Fix**: {v.fix_hint}\n\n"
        sections["Errors"] = error_content
    
    # Warnings
    if warnings:
        warning_content = ""
        for v in warnings:
            warning_content += f"### {v.file}:{v.line} ({v.code})\n"
            warning_content += f"`{v.message}`\n\n"
        sections["Warnings"] = warning_content
    
    # Tool output
    if tool_outputs:
        sections["Tool Output"] = "\n".join(tool_outputs)
    
    # Metadata
    metadata = {
        "artifact_type": "diagnostic",
        "language": language,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "info_count": len(infos),
        "severity": "error" if errors else "warning" if warnings else "info"
    }
    
    provenance = {
        "tools_run": TOOL_COMMANDS.get(language, []),
        "include_tests": include_tests,
        "ignore_patterns": ignore_patterns or []
    }
    
    return format_markdown_artifact(
        "diagnostic",
        "Diagnostic Scan Report",
        sections,
        metadata,
        provenance
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python diagnostic_scanner.py <project_path>")
        sys.exit(1)
    
    artifact = scan(sys.argv[1])
    print(artifact)
