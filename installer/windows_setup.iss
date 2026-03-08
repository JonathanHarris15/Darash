; Inno Setup Script for Jehu Reader
#define MyAppName "Jehu Reader"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Jonathan Harris"
#define MyAppExeName "JehuReader.exe"

[Setup]
AppId={{C6D2D68C-D90D-495A-8E28-E163EC90B73A}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=JehuReader_Setup
OutputDir=..\dist
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\resources\icons\app_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\JehuReader.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
