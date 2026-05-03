"""
Test planner implementation.

Analyzes codebase for testable subjects, detects existing test coverage,
generates scenario proposals by test level, and detects regression subjects.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

from utils import detect_project, format_markdown_artifact

class CoverageStatus(Enum):
    GREEN = "green"  # DONE
    YELLOW = "yellow"  # PARTIAL
    RED = "red"  # MISSING

@dataclass
class Subject:
    """Testable subject (function, class, module)."""
    name: str
    file: str
    line: int
    subject_type: str  # function | class | module
    coverage_status: CoverageStatus
    existing_tests: List[str]
    regression: bool = False

def discover_tests(project_path: str, language: str) -> Dict[str, List[str]]:
    """
    Discover existing tests by language.
    
    Returns:
        Dict[subject_name → List[test_files]]
    """
    # Language-specific test discovery
    if language == "python":
        cmd = ["python", "-m", "pytest", "--collect-only", "-q"]
    elif language == "go":
        cmd = ["go", "test", "-list", "."]
    elif language == "rust":
        cmd = ["cargo", "test", "--list"]
    else:
        return {}
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        # Parse output into test mapping
        # This is simplified; real implementation would parse tool output
        return {}
    except Exception as e:
        return {}

def detect_regression_subjects(
    project_path: str,
    regression_since: Optional[str] = None,
    regression_range: Optional[str] = None
) -> Set[str]:
    """
    Detect changed subjects via git diff.
    
    Returns:
        Set of changed file paths
    """
    if not regression_since and not regression_range:
        return set()
    
    git_range = regression_range or f"{regression_since}..HEAD"
    
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", git_range],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        return set(result.stdout.strip().split("\n"))
    except Exception:
        return set()

def generate_scenarios(
    subject: Subject,
    levels: List[str]
) -> Dict[str, List[str]]:
    """
    Generate test scenario proposals for a subject by level.
    
    Returns:
        Dict[level → List[scenario_descriptions]]
    """
    scenarios = {
        "smoke": ["Happy path (valid inputs)"],
        "unit": ["Edge cases", "Boundary values", "Error conditions", "State transitions"],
        "integration": ["External service interaction", "Database operations", "Cross-module calls"],
        "e2e": ["Full workflow from entry to exit", "User interaction patterns"],
        "regression": ["Previous passing scenarios", "Known edge cases"]
    }
    
    return {
        level: scenarios.get(level, [])
        for level in levels
    }

def generate_plan(
    project_path: str,
    levels: Optional[List[str]] = None,
    regression_since: Optional[str] = None,
    regression_range: Optional[str] = None,
    ignore_patterns: Optional[List[str]] = None,
) -> str:
    """
    Generate test plan.
    
    Args:
        project_path: Path to project root
        levels: Test levels to include (smoke|unit|integration|e2e|regression)
        regression_since: Git ref to compare against
        regression_range: Explicit git range (A..B)
        ignore_patterns: Patterns to skip
    
    Returns:
        Markdown artifact with test plan
    """
    if levels is None:
        levels = ["smoke", "unit", "integration"]
    
    language = detect_project(project_path)
    if not language:
        raise ValueError(f"Project not detected at {project_path}")
    
    # Discover tests
    existing_tests = discover_tests(project_path, language)
    
    # Detect regression subjects
    regression_subjects = detect_regression_subjects(
        project_path, regression_since, regression_range
    )
    
    # Mock analysis for demonstration
    # Real implementation would use AST parsing
    subjects = [
        Subject(
            name="authenticate(username, password) → bool",
            file="src/auth.py",
            line=42,
            subject_type="function",
            coverage_status=CoverageStatus.GREEN,
            existing_tests=["test_auth.py:12", "test_auth.py:34"],
            regression=False
        ),
        Subject(
            name="reset_password(email) → bool",
            file="src/auth.py",
            line=89,
            subject_type="function",
            coverage_status=CoverageStatus.YELLOW,
            existing_tests=["test_auth.py:56"],
            regression=False
        ),
        Subject(
            name="MFA.verify_otp(code) → bool",
            file="src/auth.py",
            line=120,
            subject_type="function",
            coverage_status=CoverageStatus.RED,
            existing_tests=[],
            regression=False
        ),
    ]
    
    # Count by coverage
    green_count = sum(1 for s in subjects if s.coverage_status == CoverageStatus.GREEN)
    yellow_count = sum(1 for s in subjects if s.coverage_status == CoverageStatus.YELLOW)
    red_count = sum(1 for s in subjects if s.coverage_status == CoverageStatus.RED)
    regression_count = len(regression_subjects)
    
    # Build sections
    sections = {}
    
    # Overview
    overview = f"""- **Coverage Status**:
  - 🟢 Green (DONE): {green_count}
  - 🟡 Yellow (PARTIAL): {yellow_count}
  - 🔴 Red (MISSING): {red_count}
- **Total Subjects**: {len(subjects)}
- **Regression Subjects**: {regression_count}
"""
    sections["Overview"] = overview
    
    # Coverage by module
    coverage_content = ""
    for subject in subjects:
        status_icon = "🟢" if subject.coverage_status == CoverageStatus.GREEN else \
                      "🟡" if subject.coverage_status == CoverageStatus.YELLOW else \
                      "🔴"
        
        coverage_content += f"#### {status_icon} {subject.name}\n"
        coverage_content += f"**Status**: "
        
        if subject.coverage_status == CoverageStatus.GREEN:
            coverage_content += f"DONE (existing: {', '.join(subject.existing_tests)})\n"
        elif subject.coverage_status == CoverageStatus.YELLOW:
            coverage_content += f"PARTIAL (existing: {', '.join(subject.existing_tests)})\n"
        else:
            coverage_content += "MISSING (no tests)\n"
        
        # Add scenarios
        scenarios = generate_scenarios(subject, levels)
        for level, scene_list in scenarios.items():
            coverage_content += f"- **{level.upper()}**: " + ", ".join(scene_list) + "\n"
        
        coverage_content += "\n"
    
    sections["Coverage by Subject"] = coverage_content
    
    # Metadata
    metadata = {
        "artifact_type": "test_plan",
        "language": language,
        "total_subjects": len(subjects),
        "coverage_green": green_count,
        "coverage_yellow": yellow_count,
        "coverage_red": red_count,
        "regression_subjects": regression_count
    }
    
    provenance = {
        "test_levels": levels,
        "regression_since": regression_since,
        "regression_range": regression_range,
        "regression_subjects": list(regression_subjects)
    }
    
    return format_markdown_artifact(
        "test_plan",
        "Test Plan Report",
        sections,
        metadata,
        provenance
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_planner.py <project_path>")
        sys.exit(1)
    
    artifact = generate_plan(sys.argv[1])
    print(artifact)
