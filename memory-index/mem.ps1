#!/usr/bin/env pwsh
# mem.ps1 - run the memory-index CLI from anywhere.
# Locates mem.py next to this script ($PSScriptRoot) and uses the py310 interpreter
# that has chromadb/ollama. Override with $env:MEM_PYTHON; falls back to PATH python.
$py = if ($env:MEM_PYTHON) {
    $env:MEM_PYTHON
} elseif (Test-Path 'C:\Users\user\py310\Scripts\python.exe') {
    'C:\Users\user\py310\Scripts\python.exe'
} else {
    'python'
}
& $py (Join-Path $PSScriptRoot 'mem.py') @args
exit $LASTEXITCODE
