param(
  [string]$PythonExecutable = "python",
  [string]$OutputDirectory = "dist",
  [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputPath = if ([IO.Path]::IsPathRooted($OutputDirectory)) {
  [IO.Path]::GetFullPath($OutputDirectory)
} else {
  [IO.Path]::GetFullPath((Join-Path $projectRoot $OutputDirectory))
}

function Assert-BuildChildPath {
  param([string]$Path, [string]$Parent)

  $fullPath = [IO.Path]::GetFullPath($Path)
  $parentPath = [IO.Path]::GetFullPath($Parent).TrimEnd('\', '/')

  if (-not $fullPath.StartsWith($parentPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "A build ideiglenes útvonala a kijelölt kimeneti mappán kívülre mutat."
  }

  # A törlés nem követhet a build mappáján kívülre vezető könyvtárhivatkozást.
  $currentPath = $fullPath

  while ($currentPath.Length -ge $parentPath.Length) {
    if (Test-Path -LiteralPath $currentPath) {
      $item = Get-Item -LiteralPath $currentPath -Force

      if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "A build útvonala nem tartalmazhat könyvtárhivatkozást: $currentPath"
      }
    }

    $currentPath = Split-Path -Parent $currentPath
  }
}

$stagingPath = Join-Path $outputPath (".build-" + [guid]::NewGuid().ToString("N"))
Assert-BuildChildPath -Path $stagingPath -Parent $outputPath
$stagingDist = Join-Path $stagingPath "dist"
$workPath = Join-Path $stagingPath "work"
$specPath = Join-Path $stagingPath "spec"
$stagingExe = Join-Path $stagingDist "GPTTranslator.exe"
$outputExe = Join-Path $outputPath "GPTTranslator.exe"
$mainScript = Join-Path $projectRoot "main.py"
$iconFile = Join-Path $projectRoot "gpttranslator\assets\icon.ico"
$icon128File = Join-Path $projectRoot "gpttranslator\assets\icon-128.png"
$checkMarkFile = Join-Path $projectRoot "gpttranslator\assets\check.svg"
$automationScript = Join-Path $projectRoot "gpttranslator\automation.js"
$defaultsFile = Join-Path $projectRoot "gpttranslator\defaults.py"
$requirementsFile = Join-Path $projectRoot "requirements-lock.txt"

if (-not (Test-Path -LiteralPath $requirementsFile -PathType Leaf)) {
  $requirementsFile = Join-Path $projectRoot "requirements.txt"
}

Push-Location -LiteralPath $projectRoot
$originalSearchPath = $env:PATH

try {
  # A külső programok PATH-on lévő DLL-jei nem kerülhetnek az alkalmazásba.
  $resolvedPythonExecutable = (Get-Command $PythonExecutable -CommandType Application,ExternalScript -ErrorAction Stop).Source
  $env:PATH = @([Environment]::GetFolderPath("System"), $env:SystemRoot, (Split-Path -Parent $resolvedPythonExecutable)) -join ';'
  New-Item -ItemType Directory -Path $stagingPath -Force | Out-Null

  # A Windows fájltulajdonságai és a Feladatkezelő is az aktuális nevet mutatják.
  $versionMatch = [regex]::Match([IO.File]::ReadAllText($defaultsFile), '(?m)^APP_VERSION\s*=\s*"(\d+(?:\.\d+){0,3})"')
  if (-not $versionMatch.Success) {
    throw "Az alkalmazás numerikus verziója nem olvasható ki."
  }
  $productVersion = $versionMatch.Groups[1].Value
  $versionParts = @($productVersion.Split('.') | ForEach-Object { [int]$_ })
  while ($versionParts.Count -lt 4) { $versionParts += 0 }
  if (@($versionParts | Where-Object { $_ -gt 65535 }).Count -gt 0) {
    throw "Az alkalmazás verziószáma nem használható Windows verzióadatként."
  }
  $numericVersion = $versionParts -join ', '
  $versionInfoPath = Join-Path $stagingPath 'version-info.txt'
  $versionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($numericVersion), prodvers=($numericVersion), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'ColorsASD'),
    StringStruct('FileDescription', 'GPTTranslator'),
    StringStruct('FileVersion', '$productVersion'),
    StringStruct('InternalName', 'GPTTranslator'),
    StringStruct('LegalCopyright', 'Copyright (c) 2026 ColorsASD'),
    StringStruct('OriginalFilename', 'GPTTranslator.exe'),
    StringStruct('ProductName', 'GPTTranslator'),
    StringStruct('ProductVersion', '$productVersion')
  ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"@
  [IO.File]::WriteAllText($versionInfoPath, $versionInfo, [Text.UTF8Encoding]::new($false))

  if (-not $SkipDependencyInstall) {
    & $resolvedPythonExecutable -m pip install -r $requirementsFile

    if ($LASTEXITCODE -ne 0) {
      throw "A Python függőségek telepítése sikertelen (kilépési kód: $LASTEXITCODE)."
    }
  }

  & $resolvedPythonExecutable -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --distpath "$stagingDist" `
    --workpath "$workPath" `
    --specpath "$specPath" `
    --collect-all "rapidocr" `
    --collect-all "winrt" `
    --collect-all "wordfreq" `
    --hidden-import "onnxruntime" `
    --name "GPTTranslator" `
    --version-file "$versionInfoPath" `
    --icon "$iconFile" `
    --add-data "${automationScript};gpttranslator" `
    --add-data "${icon128File};gpttranslator\assets" `
    --add-data "${checkMarkFile};gpttranslator\assets" `
    "$mainScript"

  $buildExitCode = $LASTEXITCODE
  $warningsFile = Join-Path $workPath "GPTTranslator\warn-GPTTranslator.txt"
  if (Test-Path -LiteralPath $warningsFile -PathType Leaf) {
    Copy-Item -LiteralPath $warningsFile -Destination (Join-Path $outputPath "build-warnings.txt") -Force
  }

  if ($buildExitCode -ne 0) {
    throw "Az EXE elkészítése sikertelen (kilépési kód: $buildExitCode)."
  }

  if (-not (Test-Path -LiteralPath $stagingExe -PathType Leaf) -or (Get-Item -LiteralPath $stagingExe).Length -eq 0) {
    throw "A build nem hozott létre használható EXE fájlt."
  }

  # A korábbi kiadás csak sikeres build után cserélődik, más EXE érintetlen marad.
  if (Test-Path -LiteralPath $outputExe -PathType Leaf) {
    [IO.File]::Replace($stagingExe, $outputExe, [NullString]::Value)
  } else {
    Move-Item -LiteralPath $stagingExe -Destination $outputExe
  }

  Write-Output "Az EXE elkészült: $outputExe"
} finally {
  $env:PATH = $originalSearchPath
  try {
    if (Test-Path -LiteralPath $stagingPath) {
      Assert-BuildChildPath -Path $stagingPath -Parent $outputPath
      Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
  } finally {
    Pop-Location
  }
}
