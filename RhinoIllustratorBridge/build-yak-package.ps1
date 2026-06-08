# build-yak-package.ps1
# Builds the RhinoIllustratorBridge plugin and packages it as a .yak file for Food4Rhino

param(
    [string]$Configuration = "Release",
    [string]$YakPath = "C:\Program Files\Rhino 8\System\Yak.exe"
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
$ProjectFile = Join-Path $ProjectDir "RhinoIllustratorBridge.csproj"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Rhino-Illustrator Sync - Yak Packager" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build the project
Write-Host "[1/4] Building project ($Configuration)..." -ForegroundColor Yellow
dotnet build $ProjectFile -c $Configuration --nologo
if ($LASTEXITCODE -ne 0) {
    Write-Host "BUILD FAILED!" -ForegroundColor Red
    exit 1
}
Write-Host "  Build succeeded." -ForegroundColor Green

# Step 2: Prepare staging directory
$BuildOutput = Join-Path $ProjectDir "bin\$Configuration\net7.0"
$StagingDir = Join-Path $ProjectDir "yak-staging"

Write-Host "[2/4] Preparing staging directory..." -ForegroundColor Yellow
if (Test-Path $StagingDir) { Remove-Item $StagingDir -Recurse -Force }
New-Item -ItemType Directory -Path $StagingDir | Out-Null

# Create net7.0 subfolder for Rhino 8 multi-targeting
$Net7Dir = Join-Path $StagingDir "net7.0"
New-Item -ItemType Directory -Path $Net7Dir | Out-Null

# Copy built files
$FilesToCopy = @("*.rhp", "*.dll", "*.pdb")
foreach ($pattern in $FilesToCopy) {
    $files = Get-ChildItem -Path $BuildOutput -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        # Skip RhinoCommon and Eto references (provided by Rhino runtime)
        if ($f.Name -match "^(RhinoCommon|Eto\.|Eto\.)" ) { continue }
        Copy-Item $f.FullName -Destination $Net7Dir
        Write-Host "  Copied: $($f.Name)" -ForegroundColor Gray
    }
}

# Copy manifest
Copy-Item (Join-Path $ProjectDir "manifest.yml") -Destination $StagingDir
Write-Host "  Copied: manifest.yml" -ForegroundColor Gray

# Copy icon
$IconSrc = Join-Path $ProjectDir "Resources\sync_icon.png"
if (Test-Path $IconSrc) {
    Copy-Item $IconSrc -Destination (Join-Path $StagingDir "icon.png")
    Write-Host "  Copied: icon.png" -ForegroundColor Gray
}

Write-Host "  Staging complete." -ForegroundColor Green

# Step 3: Build the Yak package
Write-Host "[3/4] Building Yak package..." -ForegroundColor Yellow
if (Test-Path $YakPath) {
    Push-Location $StagingDir
    & $YakPath build
    Pop-Location
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Yak build failed! You may need to run 'yak build' manually." -ForegroundColor Red
    } else {
        # Move .yak file to project root
        $yakFile = Get-ChildItem -Path $StagingDir -Filter "*.yak" | Select-Object -First 1
        if ($yakFile) {
            $destYak = Join-Path $ProjectDir $yakFile.Name
            Move-Item $yakFile.FullName -Destination $destYak -Force
            Write-Host "  Package created: $($yakFile.Name)" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  Yak.exe not found at: $YakPath" -ForegroundColor Yellow
    Write-Host "  Skipping Yak packaging. You can run it manually:" -ForegroundColor Yellow
    Write-Host "    cd $StagingDir" -ForegroundColor White
    Write-Host '    "C:\Program Files\Rhino 8\System\Yak.exe" build' -ForegroundColor White
}

# Step 4: Summary
Write-Host ""
Write-Host "[4/4] Summary" -ForegroundColor Yellow
Write-Host "  Staging dir : $StagingDir" -ForegroundColor Gray
Write-Host "  Build output: $BuildOutput" -ForegroundColor Gray
Write-Host ""
Write-Host "To publish to Food4Rhino:" -ForegroundColor Cyan
Write-Host '  "C:\Program Files\Rhino 8\System\Yak.exe" push <package-file>.yak' -ForegroundColor White
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
