#define AppName "CTUN"
#ifndef AppVersion
#define AppVersion "0.2.0"
#endif
#ifndef SourceDir
#define SourceDir "build\\windows-dist\\ctun"
#endif
[Setup]
AppId={{0D47010C-D7CF-4A80-98BC-C0FA25770E71}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\CTUN
DefaultGroupName=CTUN
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=chatgpt-tun_{#AppVersion}_windows_amd64
Compression=lzma2
SolidCompression=yes
ChangesEnvironment=yes
UninstallDisplayName=CTUN {#AppVersion}
[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\CTUN Doctor"; Filename: "{app}\ctun.exe"; Parameters: "doctor"
[Run]
Filename: "{app}\\ctun.exe"; Parameters: "doctor"; Description: "Check CTUN dependencies"; Flags: postinstall nowait skipifsilent
