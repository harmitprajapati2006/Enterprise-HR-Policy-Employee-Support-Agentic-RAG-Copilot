param (
    [string]$Query
)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"
$AgentScript = Join-Path $ScriptDir "agentic_rag.py"

if ($Query) {
    & $PythonExe $AgentScript -q $Query
} else {
    & $PythonExe $AgentScript
}

