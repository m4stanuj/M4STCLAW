#ifndef AppExe
  #error AppExe must point to the packaged M4STCLAW executable.
#endif
#ifndef AppVersion
  #error AppVersion must match the package version.
#endif

[Setup]
AppId={{9F29CF6B-6C65-43C2-99D4-C0F0D7065DEB}
AppName=M4STCLAW
AppVersion={#AppVersion}
AppPublisher=M4STCLAW
AppPublisherURL=https://github.com/m4stanuj/M4STCLAW
DefaultDirName={localappdata}\Programs\M4STCLAW
DefaultGroupName=M4STCLAW
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
SetupIconFile=..\assets\m4stclaw-windows.ico
UninstallDisplayIcon={app}\M4STCLAW.exe
OutputBaseFilename=M4STCLAW-{#AppVersion}-windows-x64-setup
CloseApplications=no
RestartApplications=no

[Files]
Source: "{#AppExe}"; DestDir: "{app}"; DestName: "M4STCLAW.exe"; Flags: ignoreversion nocompression
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\M4STCLAW"; Filename: "{app}\M4STCLAW.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\M4STCLAW.exe"; Description: "Launch M4STCLAW"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
