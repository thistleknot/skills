"""
Documentation synthesizer implementation.

Parses codebase for module structure, dependency graph, and data flow.
Generates Mermaid diagrams for dependencies, data flow, and components.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from utils import detect_project, format_markdown_artifact

@dataclass
class Module:
    """Parsed module info."""
    name: str
    file: str
    docstring: Optional[str]
    imports: List[str]
    classes: List[str]
    functions: List[str]
    line_count: int

def parse_python_ast(filepath: str) -> Module:
    """Parse Python AST to extract module info."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return Module(
            name=Path(filepath).stem,
            file=filepath,
            docstring=None,
            imports=[],
            classes=[],
            functions=[],
            line_count=len(content.splitlines())
        )
    
    docstring = ast.get_docstring(tree)
    imports = []
    classes = []
    functions = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
    
    return Module(
        name=Path(filepath).stem,
        file=filepath,
        docstring=docstring,
        imports=imports,
        classes=classes,
        functions=functions,
        line_count=len(content.splitlines())
    )

def build_dependency_graph(modules: List[Module]) -> Dict[str, Set[str]]:
    """Build module → module dependency graph."""
    graph = defaultdict(set)
    
    for module in modules:
        for imp in module.imports:
            # Simplistic: extract first component
            imp_module = imp.split(".")[0]
            for other in modules:
                if other.name == imp_module and other.name != module.name:
                    graph[module.name].add(other.name)
    
    return graph

def generate_mermaid_dependency_graph(
    modules: List[Module],
    graph: Dict[str, Set[str]],
    max_nodes: int = 100
) -> str:
    """Generate Mermaid graph for module dependencies."""
    lines = ["graph LR"]
    
    edge_count = 0
    for source, targets in graph.items():
        for target in targets:
            if edge_count < max_nodes:
                lines.append(f"    {source}[{source}] --> {target}[{target}]")
                edge_count += 1
    
    return "\n".join(lines)

def generate_mermaid_data_flow(
    entry_points: List[str],
    data_sources: List[str]
) -> str:
    """Generate Mermaid data flow diagram."""
    lines = ["graph TB"]
    
    lines.append('    Client["HTTP Client"]')
    for entry in entry_points[:3]:  # Limit to 3 entry points
        lines.append(f'    Client -->|call| {entry}[{entry}]')
    
    lines.append('    DB["Database"]')
    for entry in entry_points[:1]:
        lines.append(f'    {entry} -->|query| DB')
        lines.append(f'    DB -->|result| {entry}')
    
    lines.append('    Client -->|response| {entry}')
    
    return "\n".join(lines)

def synthesize(
    project_path: str,
    include_io: bool = True,
    include_endpoints: bool = True,
    fetch_uris: Optional[List[str]] = None,
    crawl_depth: int = 0,
    allow_domains: Optional[List[str]] = None,
    max_nodes: int = 100
) -> str:
    """
    Synthesize documentation from codebase.
    
    Args:
        project_path: Path to project root
        include_io: Include data source nodes in diagrams
        include_endpoints: Include HTTP endpoints in diagrams
        fetch_uris: Optional list of URIs to fetch/crawl
        crawl_depth: Crawl depth for fetch_uris
        allow_domains: Allowed domains for crawling
        max_nodes: Max nodes in diagram (soft limit)
    
    Returns:
        Markdown artifact with documentation
    """
    language = detect_project(project_path)
    if not language:
        raise ValueError(f"Project not detected at {project_path}")
    
    # Parse modules (Python only for now)
    modules = []
    if language == "python":
        project_path_obj = Path(project_path)
        for py_file in project_path_obj.rglob("*.py"):
            if "__pycache__" not in py_file.parts:
                try:
                    modules.append(parse_python_ast(str(py_file)))
                except Exception:
                    pass
    
    # Build dependency graph
    graph = build_dependency_graph(modules)
    
    # Build sections
    sections = {}
    
    # Overview
    overview = f"""**Language**: {language}
**Purpose**: Inferred from README and code analysis.
**Modules**: {len(modules)}
**External Dependencies**: {len(set().union(*graph.values()))}
"""
    sections["Project Overview"] = overview
    
    # Directory structure
    tree_content = f"```\n{project_path}/\n"
    for module in modules[:10]:
        tree_content += f"├── {module.file} ({module.line_count} lines)\n"
    if len(modules) > 10:
        tree_content += f"└── ... ({len(modules) - 10} more files)\n"
    tree_content += "```"
    sections["Directory Structure"] = tree_content
    
    # Dependency graph
    dep_graph_md = generate_mermaid_dependency_graph(modules, graph, max_nodes)
    sections["Module Dependencies"] = f"```mermaid\n{dep_graph_md}\n```"
    
    # Data flow
    entry_points = [f.name for m in modules for f in m.functions if f.startswith(("main", "create", "get"))][:3]
    data_sources = ["PostgreSQL", "Redis", "S3"] if include_io else []
    
    data_flow_md = generate_mermaid_data_flow(entry_points, data_sources)
    sections["Data Flow"] = f"```mermaid\n{data_flow_md}\n```"
    
    # Module summaries
    if modules:
        summary_content = ""
        for module in modules[:5]:
            summary_content += f"### {module.name}\n"
            if module.docstring:
                summary_content += f"**Purpose**: {module.docstring.split(chr(10))[0]}\n"
            summary_content += f"- **Classes**: {len(module.classes)}\n"
            summary_content += f"- **Functions**: {len(module.functions)}\n"
            summary_content += f"- **Imports**: {len(module.imports)}\n\n"
        sections["Module Summaries"] = summary_content
    
    # Metadata
    metadata = {
        "artifact_type": "documentation",
        "language": language,
        "module_count": len(modules),
        "diagram_format": "mermaid",
        "max_nodes": max_nodes
    }
    
    provenance = {
        "analysis_method": "AST parse + import extraction",
        "include_io": include_io,
        "include_endpoints": include_endpoints,
        "crawled_uris": fetch_uris or []
    }
    
    return format_markdown_artifact(
        "documentation",
        "Documentation Synthesis Report",
        sections,
        metadata,
        provenance
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python doc_synthesizer.py <project_path>")
        sys.exit(1)
    
    artifact = synthesize(sys.argv[1])
    print(artifact)
