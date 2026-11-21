param(
    [string]$Python = 'python',
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\build\windows')
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$output = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $output | Out-Null

Push-Location -LiteralPath $repo
try {
    $architecture = & $Python -c 'import sysconfig; print(sysconfig.get_platform())'
    if ($LASTEXITCODE -ne 0 -or $architecture -ne 'win-amd64') {
        throw 'Use a Windows x64 Python interpreter to build M4STCLAW.exe.'
    }

    $static = Join-Path $repo 'm4stclaw\ui\static'
    $arguments = @(
        '-m', 'PyInstaller', '--noconfirm', '--onefile', '--noupx',
        '--name', 'M4STCLAW',
        '--specpath', $output, '--distpath', $output,
        '--workpath', (Join-Path $output 'work'),
        '--add-data', "${static}:m4stclaw/ui/static",
        '--hidden-import', 'm4stclaw.ui.app_server',
        '--hidden-import', 'PIL', '--hidden-import', 'mcp', '--hidden-import', 'requests',
        '--collect-submodules', 'uvicorn',
        (Join-Path $repo 'start.py')
    )
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller exited with status $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
