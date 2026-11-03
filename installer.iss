; ==============================================================================
; WattCost HaYTooL - Inno Setup Script
; Yayinci: HaYTooL | Gelistirici: HaYTo
; ==============================================================================

#ifndef AppVersion
  #define AppVersion "6.0"
#endif

#define MyAppName "WattCost HaYTooL"
#define MyAppPublisher "HaYTooL"
#define MyAppDeveloper "HaYTo"
#define MyAppURL "https://haytokoraz.github.io/WattCost/"
#define MyPortalURL "https://haytokoraz.github.io/"
#define MyRepoURL "https://github.com/HaYToKoRaZ/WattCost"
#define MyAppExeName "WattCost. HaYTooL.exe"

[Setup]
AppId={{E5813A70-2BD6-4F11-89B7-96DC2F4D597A}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} v{#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyPortalURL}
AppSupportURL={#MyRepoURL}/issues
AppUpdatesURL={#MyRepoURL}/releases
AppComments=Real-Time PC Wall Socket Power Draw & Electricity Cost Tracker with RTSS OSD
AppCopyright=Copyright (C) 2026 {#MyAppPublisher} / {#MyAppDeveloper}
DefaultDirName={autopf}\WattCost HaYTooL
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=release_assets
OutputBaseFilename=WattCost-HaYTooL-v{#AppVersion}-Setup
SetupIconFile=main\app_icon.ico
UninstallDisplayIcon={app}\main\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=auto
CloseApplications=yes
RestartApplications=no

; Versiyon ve Dosya Bilgileri (Windows Explorer Detaylari)
VersionInfoVersion={#AppVersion}.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Real-Time PC Wall Socket Power Draw & Electricity Cost Tracker
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher} / {#MyAppDeveloper}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Tum derlenmis dist dosyalarini hedef kurulum klasorune yukle
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Baslat Menusu Kisayollari
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\main\app_icon.ico"
Name: "{group}\Web Sitesi (HaYTooL)"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Masaustu Kisayolu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\main\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
