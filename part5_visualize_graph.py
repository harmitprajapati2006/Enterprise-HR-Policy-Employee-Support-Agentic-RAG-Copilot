import os
import sys
import subprocess

# Auto-relaunch inside local virtual environment if invoked globally
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CURRENT_DIR, "venv", "Scripts", "python.exe")
if os.path.exists(VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(VENV_PYTHON):
    result = subprocess.run([VENV_PYTHON] + sys.argv, check=False)
    sys.exit(result.returncode)

# ---------------------------------------------------------------------------
# Section 22: Visualize the Graph
# ---------------------------------------------------------------------------
from part4_build_workflow import app

def visualize_graph(save_mermaid: bool = True, save_png: bool = True):
    print("\n" + "=" * 60)
    print("PART 5: GRAPH VISUALIZATION")
    print("=" * 60)
    
    graph = app.get_graph()

    # 1. Mermaid text representation
    try:
        mermaid_code = graph.draw_mermaid()
        print("\n--- Mermaid Graph Syntax ---")
        print(mermaid_code)
        
        if save_mermaid:
            mermaid_path = os.path.join(CURRENT_DIR, "graph.mermaid")
            with open(mermaid_path, "w", encoding="utf-8") as f:
                f.write(mermaid_code)
            print(f"\nSaved Mermaid graph syntax to: {mermaid_path}")
    except Exception as e:
        print("Mermaid text export notice:", e)

    # 2. Mermaid PNG rendering (via mermaid API)
    if save_png:
        try:
            png_bytes = graph.draw_mermaid_png()
            png_path = os.path.join(CURRENT_DIR, "graph.png")
            with open(png_path, "wb") as f:
                f.write(png_bytes)
            print(f"Graph image saved successfully to: {png_path}")
        except Exception as e:
            print("\nNote: Graph PNG visualization is optional. The graph can still run without it.")
            print("Reason:", e)
    
    print("=" * 60)

if __name__ == "__main__":
    visualize_graph()

