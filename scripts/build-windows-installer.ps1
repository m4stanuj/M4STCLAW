param(
    [string]$Executable = (Join-Path $PSScriptRoot '..\build\windows\M4STCLAW.exe'),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\build\windows'),
    [string]$Python = 'python',
    [string]$Version,
    [string]$Compiler
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$binary = (Resolve-Path -LiteralPath $Executable).Path
$output = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
    throw 'Build the Windows executable before compiling the installer.'
}

if (-not $Version) {
    $metadata = Join-Path $repo 'pyproject.toml'
    $Version = & $Python -c 'import sys,tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["version"])' $metadata
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not read the package version from pyproject.toml.'
    }
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw 'Use a numeric major.minor.patch Windows package version.'
}

if (-not $Compiler) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { $Compiler = $command.Source }
    else { $Compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
}
if (-not (Test-Path -LiteralPath $Compiler -PathType Leaf)) {
    throw 'Install Inno Setup or pass the full path to ISCC.exe with -Compiler.'
}

New-Item -ItemType Directory -Path $output -Force | Out-Null
$definition = Join-Path $PSScriptRoot 'windows-installer.iss'
& $Compiler "/DAppExe=$binary" "/DAppVersion=$Version" "/O$output" $definition
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}
