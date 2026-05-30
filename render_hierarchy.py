import sys
from pathlib import Path
import subprocess

def render_mermaid_to_svg(mmd_path, svg_path):
    mmd_content = Path(mmd_path).read_text()
    
    if "flowchart" not in mmd_content and "graph" not in mmd_content:
        print("Error: Not a valid Mermaid file.")
        sys.exit(1)

    print(f"Attempting to render {mmd_path} to {svg_path} using npx mermaid-cli...")
    
    try:
        result = subprocess.run(
            ["npx", "-y", "mermaid-cli", mmd_path, "-o", svg_path],
            capture_output=True,
            text=True,
            check=True
        )
        print("Render successful.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error during rendering with npx mermaid-cli:")
        print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'npx' not found. Please ensure Node.js is installed.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python render_hierarchy.py <input.mmd> <output.svg>")
        sys.exit(1)
    
    render_mermaid_to_svg(sys.argv[1], sys.argv[2])
