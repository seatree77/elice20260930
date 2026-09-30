$ErrorActionPreference = 'Stop'
$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python "$PSScriptRoot/app.py" @args
} elseif (Test-Path -LiteralPath $bundledPython) {
    & $bundledPython "$PSScriptRoot/app.py" @args
} else {
    Write-Error 'Python 3이 필요합니다. Python 설치 후 다시 실행해 주세요.'
}
