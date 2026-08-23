; Script do Inno Setup para o instalador do Sistema de Etiquetas.
; Compila installer\output\SistemaDeEtiquetas_Setup.exe a partir do
; executável já gerado pelo PyInstaller em dist\EtiquetaApp.exe.
;
; Requer o Inno Setup (https://jrsoftware.org/isdl.php) instalado no Windows.
; Normalmente você não roda este arquivo diretamente: use o
; build_installer.bat na raiz do projeto, que já chama o ISCC por você.

#define MyAppName "Sistema de Etiquetas"
#define MyAppVersion "1.0"
#define MyAppExeName "EtiquetaApp.exe"
#define MyAppPublisher "Sistema de Etiquetas"

[Setup]
AppId={{4C6E9F2A-8B3D-4E1F-9C2A-7D5B6A3E1F80}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=SistemaDeEtiquetas_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Não exige privilégios de administrador: instala em uma pasta do próprio
; usuário quando ele não tiver permissão de admin, evitando o prompt do UAC.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName} agora"; Flags: nowait postinstall skipifsilent
