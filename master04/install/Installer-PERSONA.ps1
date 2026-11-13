<#
  PERSONA — installation PC Windows (gratuite, locale).
  Lancer depuis le dossier du paquet PERSONA_PC :
      powershell -ExecutionPolicy Bypass -File install\Installer-PERSONA.ps1           (installation)
      powershell -ExecutionPolicy Bypass -File install\Installer-PERSONA.ps1 -DryRun   (diagnostic seul, rien n'est installé)
  Chaque téléchargement demande confirmation. Aucune photo n'est envoyée nulle part.
#>
param(
  [switch]$DryRun,
  [switch]$Yes,                 # répondre oui à toutes les questions (installation sans surveillance)
  [switch]$SkipModels,
  [switch]$SkipBlender
)
$ErrorActionPreference = "Stop"
$Pkg = Split-Path -Parent $PSScriptRoot
$Data = Join-Path $env:APPDATA "PERSONA"
$Local = Join-Path $env:LOCALAPPDATA "PERSONA"
New-Item -ItemType Directory -Force -Path $Data, $Local | Out-Null
$Log = Join-Path $Data "installation.log"
function Say($m) { Write-Host $m; Add-Content -Path $Log -Value ("{0}  {1}" -f (Get-Date -Format s), $m) }
function Ask($q) { if ($Yes) { return $true }; return (Read-Host "$q [o/N]") -match '^(o|oui|y|yes)$' }

Say "=== PERSONA : installation $(if ($DryRun) {'(DIAGNOSTIC SEUL)'}) ==="

# ------------------------------------------------------------------ 1. Matériel
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs = Get-CimInstance Win32_ComputerSystem
$ramGb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
$freeGb = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)
$disk = Get-PSDrive -Name ($env:LOCALAPPDATA.Substring(0,1))
$diskGb = [math]::Round($disk.Free / 1GB, 1)
$gpus = @(Get-CimInstance Win32_VideoController | ForEach-Object { [pscustomobject]@{ name = $_.Name; driver = $_.DriverVersion } })
$vram = -1; $cuda = $false
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) {
  $q = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
  if ($q) { $f = ($q | Select-Object -First 1).Split(","); $vram = [math]::Round([double]$f[1].Trim() / 1024, 1); $cuda = $true }
}
$vulkan = Test-Path (Join-Path $env:SystemRoot "System32\vulkan-1.dll")
$persProfile = if ($ramGb -ge 28 -and $vram -ge 10) { "avance" } elseif ($ramGb -ge 14 -and $vram -ge 6) { "standard" } else { "leger" }
Say ("Processeur : {0} ({1} cœurs / {2} threads)" -f $cpu.Name.Trim(), $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)
Say ("RAM : {0} Go (libre {1} Go) · disque libre : {2} Go" -f $ramGb, $freeGb, $diskGb)
foreach ($g in $gpus) { Say ("GPU : {0} (pilote {1})" -f $g.name, $g.driver) }
Say ("VRAM NVIDIA : {0} Go · CUDA : {1} · Vulkan : {2}" -f $vram, $cuda, $vulkan)
Say "Profil retenu : $persProfile"
$report = [ordered]@{ generated_at = (Get-Date -Format s); source = "Installer-PERSONA.ps1"; profile = $persProfile
  cpu = @{ name = $cpu.Name.Trim(); cores = $cpu.NumberOfCores; logical_cores = $cpu.NumberOfLogicalProcessors }
  ram_gb = @{ total = $ramGb; available = $freeGb }; disk_free_gb = $diskGb
  gpu = @{ list = $gpus; vram_gb = $vram; cuda = $cuda; vulkan = $vulkan } }
$report | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $Data "hardware_report.json")
Say "Rapport matériel : $(Join-Path $Data 'hardware_report.json')"
if ($diskGb -lt 25) { Say "ATTENTION : moins de 25 Go libres ; les modèles et Blender demandent ~15 Go." }
if ($ramGb -lt 12) { Say "Profil léger : génération lente sur processeur, résolution réduite. Fermez PERSONA LIVE pendant les calculs IA." }
if ($DryRun) { Say "Diagnostic terminé (aucune installation)."; exit 0 }

# ------------------------------------------------------------------ 2. Python 3.11 (gratuit)
$py = $null
try { $v = & py -3.11 --version 2>$null; if ($LASTEXITCODE -eq 0) { $py = "py -3.11" } } catch {}
if (-not $py) {
  Say "Python 3.11 introuvable."
  if (Ask "Installer Python 3.11 avec winget (gratuit, Microsoft Store/winget) ?") {
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    $py = "py -3.11"
  } else { Say "Installation interrompue : Python 3.11 requis pour l'atelier."; exit 1 }
}
$Venv = Join-Path $Local "venv"
if (-not (Test-Path $Venv)) { Say "Création de l'environnement Python isolé…"; Invoke-Expression "$py -m venv `"$Venv`"" }
$Pip = Join-Path $Venv "Scripts\pip.exe"; $Python = Join-Path $Venv "Scripts\python.exe"
& $Pip install --upgrade pip | Out-Null
& $Pip install -r (Join-Path $Pkg "engine\requirements-pc.txt")
Say "Dépendances Python installées."

# ------------------------------------------------------------------ 3. Moteur de génération (sd-cli)
$SdCli = Join-Path $Pkg "engine\bin\sd-cli.exe"
if (-not (Test-Path $SdCli)) { Say "ERREUR : moteur sd-cli.exe absent du paquet."; exit 1 }
& $SdCli --help | Select-Object -First 1 | ForEach-Object { Say "Moteur : $_" }

# ------------------------------------------------------------------ 4. Modèles (téléchargement unique, vérifié)
$Models = Join-Path $Local "models"
$quant = if ($persProfile -eq "leger") { "q4_K" } else { "q8_0" }
$Gguf = Join-Path $Models "sdxl_$quant.gguf"
if (-not $SkipModels -and -not (Test-Path $Gguf)) {
  if (Ask "Télécharger les modèles (≈ 8,2 Go depuis huggingface.co, révisions figées et SHA-256 vérifiés) ?") {
    & $Python (Join-Path $Pkg "engine\fetch_models.py") $Models
    $lock = Get-Content (Join-Path $Models "models.lock.json") | ConvertFrom-Json
    Say "Quantification $quant (quelques minutes)…"
    & $SdCli -M convert -m $lock.sdxl.local_path -o $Gguf --type $quant
    if (Test-Path $Gguf) { Remove-Item $lock.sdxl.local_path; Say "Modèle prêt : $Gguf" } else { Say "ERREUR de quantification" ; exit 1 }
  }
}

# ------------------------------------------------------------------ 5. Blender portable (phase 3, facultatif)
$Blender = Join-Path $Local "blender\blender.exe"
if (-not $SkipBlender -and -not (Test-Path $Blender)) {
  if (Ask "Télécharger Blender 4.2 LTS portable (≈ 350 Mo, gratuit, GPL) pour la reconstruction 3D ?") {
    $zip = Join-Path $Local "blender.zip"
    Invoke-WebRequest "https://download.blender.org/release/Blender4.2/blender-4.2.3-windows-x64.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath $Local -Force; Remove-Item $zip
    Rename-Item (Join-Path $Local "blender-4.2.3-windows-x64") "blender"
    Say "Blender installé : $Blender"
  }
}

# ------------------------------------------------------------------ 6. Lanceurs
$env_lines = @(
  "@echo off",
  "set PERSONA_SDCPP_BIN=$SdCli",
  "set PERSONA_SDCPP_MODEL=$Gguf",
  "set PERSONA_SDCPP_VAE=$Models\vae\sdxl_vae.safetensors",
  "set PERSONA_SDCPP_PM=$Models\photomaker\photomaker-v1.safetensors",
  "set PYTHONPATH=$Pkg\engine"
)
($env_lines + "`"$Python`" -m persona_engine.worker --backend sdcpp --root `"$Data\atelier`" --token-file `"$Data\atelier_token.txt`" --open-ui") |
  Set-Content -Encoding ASCII (Join-Path $Pkg "PERSONA Atelier.cmd")
($env_lines + "set /p NAME=Nom du personnage : ", "set /p REFS=Dossier des photos autorisees : ",
  "`"$Python`" -m persona_engine.character build --name `"%NAME%`" --refs `"%REFS%`" --consent `"autorisation declaree par l'utilisateur`" --blender `"$Blender`"", "pause") |
  Set-Content -Encoding ASCII (Join-Path $Pkg "PERSONA Dossier personnage.cmd")
Say "Lanceurs créés : « PERSONA Atelier.cmd », « PERSONA Dossier personnage.cmd », live\PERSONA_LIVE.exe"
Say "=== Installation terminée ==="
