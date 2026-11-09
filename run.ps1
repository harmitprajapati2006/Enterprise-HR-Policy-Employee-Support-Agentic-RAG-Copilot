param (
    [string]$Mode = "server",
    [string]$Query
)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"

switch ($Mode) {
    "ingest" {
        & $PythonExe (Join-Path $ScriptDir "ingest_sample_kb.py")
    }
    "cli" {
        if ($Query) {
            & $PythonExe (Join-Path $ScriptDir "agentic_rag.py") -q $Query
        } else {
            & $PythonExe (Join-Path $ScriptDir "agentic_rag.py")
        }
    }
    Default {
        & $PythonExe (Join-Path $ScriptDir "run.py")
    }
}
