[Setup]
AppId={{5F30F03D-994B-4A77-B458-8F38A9E3D834}
AppName=DMCB Commissioner
AppVersion=0.1.0
DefaultDirName={autopf}\DMCB Commissioner
DefaultGroupName=DMCB Commissioner
OutputDir=..\dist
OutputBaseFilename=DMCB-Setup-Windows
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "..\dist\DMCB\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\DMCB Commissioner"; Filename: "{app}\DMCB.exe"
Name: "{autodesktop}\DMCB Commissioner"; Filename: "{app}\DMCB.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\DMCB.exe"; Description: "Launch DMCB Commissioner"; Flags: postinstall nowait skipifsilent
