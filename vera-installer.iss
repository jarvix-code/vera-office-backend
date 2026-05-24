[Setup]
AppName=VERA Office
AppVersion=1.0
DefaultDirName={autopf}\VERA Office
DefaultGroupName=VERA Office
OutputDir=D:\vera-office\installer
OutputBaseFilename=VERA-Office-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\vera.ico

[Files]
Source: "D:\vera-office\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\VERA Office"; Filename: "{app}\start-vera-http.bat"; WorkingDir: "{app}"
Name: "{autodesktop}\VERA Office"; Filename: "{app}\start-vera-http.bat"; WorkingDir: "{app}"

[Run]
Filename: "{app}\start-vera-http.bat"; Description: "VERA Office starten"; Flags: postinstall nowait skipifsilent
