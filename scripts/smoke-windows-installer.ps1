[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Installer,
    [Parameter(Mandatory)]
    [string]$UpgradeInstaller,
    [string]$Python = 'python',
    [string]$Version = '3.6.0',
    [string]$UpgradeVersion = '3.6.1'
)

$ErrorActionPreference = 'Stop'
$Installer = (Resolve-Path -LiteralPath $Installer).ProviderPath
$UpgradeInstaller = (Resolve-Path -LiteralPath $UpgradeInstaller).ProviderPath
if ($Installer -eq $UpgradeInstaller) {
    throw 'Provide separate fresh and upgrade installer packages.'
}
if ($Version -eq $UpgradeVersion) {
    throw 'The fresh and upgrade packages must register different versions.'
}

$applicationId = '{9F29CF6B-6C65-43C2-99D4-C0F0D7065DEB}_is1'
$uninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall'
$registrationPath = "HKCU:\$uninstallKey\$applicationId"
$systemRegistrationPath = "HKLM:\$uninstallKey\$applicationId"
$programsDirectory = [Environment]::GetFolderPath('Programs', 'DoNotVerify')
$shortcutPath = Join-Path $programsDirectory 'M4STCLAW.lnk'

if ((Test-Path -LiteralPath $registrationPath) -or
    (Test-Path -LiteralPath $systemRegistrationPath) -or
    (Test-Path -LiteralPath $shortcutPath)) {
    throw 'This validation account already has an M4STCLAW registration or Start Menu shortcut. Use an isolated Windows account.'
}

$fixtureDirectory = Join-Path ([IO.Path]::GetTempPath()) "m4stclaw-installer-$([guid]::NewGuid().ToString('N'))"
$installDirectory = Join-Path $fixtureDirectory 'Installed Application'
$configDirectory = Join-Path $fixtureDirectory 'User Configuration'
$configFile = Join-Path $configDirectory '.env'
$installedExecutable = Join-Path $installDirectory 'M4STCLAW.exe'
$uninstaller = Join-Path $installDirectory 'unins000.exe'
$binarySmoke = Join-Path $PSScriptRoot 'smoke-windows.py'
$windowsShell = New-Object -ComObject WScript.Shell

New-Item -ItemType Directory -Path $fixtureDirectory, $configDirectory | Out-Null
[IO.File]::WriteAllText($configFile, "OPENROUTER_API_KEY=installer-smoke-fixture`n")
$configHash = (Get-FileHash -LiteralPath $configFile).Hash

function Invoke-InstallerStep {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments = @()
    )

    $logPath = Join-Path $fixtureDirectory "$Name.log"
    $options = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$logPath`"") + $Arguments
    $process = Start-Process -FilePath $Executable -ArgumentList $options -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        if (Test-Path -LiteralPath $logPath -PathType Leaf) {
            Get-Content -LiteralPath $logPath -Tail 40 | Write-Host
        }
        throw "$Name failed with exit code $($process.ExitCode)."
    }
}

function Assert-InstalledVersion {
    param([string]$ExpectedVersion)

    $registration = Get-ItemProperty -LiteralPath $registrationPath
    if ($registration.DisplayVersion -ne $ExpectedVersion) {
        throw "Expected per-user registration version $ExpectedVersion, found '$($registration.DisplayVersion)'."
    }
    if (-not $registration.InstallLocation -or $registration.InstallLocation.TrimEnd('\') -ne $installDirectory) {
        throw "Version $ExpectedVersion was registered outside the selected install directory."
    }
    if (Test-Path -LiteralPath $systemRegistrationPath) {
        throw 'The installer created a system-wide registration.'
    }
    if (-not (Test-Path -LiteralPath $shortcutPath -PathType Leaf)) {
        throw 'The user Start Menu shortcut is missing.'
    }

    $shortcut = $windowsShell.CreateShortcut($shortcutPath)
    if ($shortcut.TargetPath -ne $installedExecutable -or $shortcut.WorkingDirectory -ne $installDirectory) {
        throw 'The Start Menu shortcut must launch the installed EXE from its install directory.'
    }
}

function Assert-ConfigPreserved {
    if (-not (Test-Path -LiteralPath $configFile -PathType Leaf) -or
        (Get-FileHash -LiteralPath $configFile).Hash -ne $configHash) {
        throw 'The installer lifecycle changed or removed the user configuration.'
    }
}

$previousConfigDirectory = $env:M4STCLAW_CONFIG
$env:M4STCLAW_CONFIG = $configDirectory
try {
    Invoke-InstallerStep 'install' $Installer @("/DIR=`"$installDirectory`"")
    Assert-InstalledVersion $Version
    Assert-ConfigPreserved

    & $Python $binarySmoke $installedExecutable
    if ($LASTEXITCODE -ne 0) {
        throw "The installed EXE failed its dashboard smoke test with exit code $LASTEXITCODE."
    }

    Invoke-InstallerStep 'upgrade' $UpgradeInstaller
    Assert-InstalledVersion $UpgradeVersion
    Assert-ConfigPreserved

    & $Python $binarySmoke $installedExecutable
    if ($LASTEXITCODE -ne 0) {
        throw "The upgraded EXE failed its dashboard smoke test with exit code $LASTEXITCODE."
    }

    Invoke-InstallerStep 'uninstall' $uninstaller
    if ((Test-Path -LiteralPath $registrationPath) -or
        (Test-Path -LiteralPath $systemRegistrationPath) -or
        (Test-Path -LiteralPath $shortcutPath) -or
        (Test-Path -LiteralPath $installedExecutable)) {
        throw 'Uninstall left an executable, Start Menu shortcut, or Windows registration behind.'
    }
    Assert-ConfigPreserved
    Write-Host 'Per-user install, upgrade, Start Menu shortcut, configuration preservation, and uninstall passed.'
}
finally {
    $env:M4STCLAW_CONFIG = $previousConfigDirectory
    Write-Host "Installer logs and fixture config: $fixtureDirectory"
    if (Test-Path -LiteralPath $uninstaller -PathType Leaf) {
        try {
            Invoke-InstallerStep 'cleanup' $uninstaller
        }
        catch {
            Write-Warning "Could not uninstall the test fixture: $_"
        }
    }
}
