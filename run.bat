@echo off
cd /d "%~dp0"
if "%~1"=="1" (
    "%~dp0venv\Scripts\python.exe" "%~dp0part1_vector_db.py"
) else if "%~1"=="2" (
    "%~dp0venv\Scripts\python.exe" "%~dp0part2_models_and_decisions.py"
) else if "%~1"=="3" (
    "%~dp0venv\Scripts\python.exe" "%~dp0part3_graph_nodes.py"
) else if "%~1"=="4" (
    "%~dp0venv\Scripts\python.exe" "%~dp0part4_build_workflow.py"
) else if "%~1"=="5" (
    "%~dp0venv\Scripts\python.exe" "%~dp0part5_visualize_graph.py"
) else if "%~1"=="6" (
    "%~dp0venv\Scripts\python.exe" "%~dp0part6_helper_function.py" %2 %3 %4 %5 %6
) else if "%~1"=="7" (
    "%~dp0venv\Scripts\python.exe" "%~dp0part7_run_demos.py"
) else (
    "%~dp0venv\Scripts\python.exe" "%~dp0agentic_rag.py" %*
)
