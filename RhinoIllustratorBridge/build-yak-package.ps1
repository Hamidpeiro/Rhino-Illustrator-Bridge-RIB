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
Write-Host "[3/5] Building Yak package..." -ForegroundColor Yellow
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

# Step 4: Package the .macrhi installer
Write-Host "[4/5] Packaging .macrhi installer..." -ForegroundColor Yellow
$MacrhiStaging = Join-Path $ProjectDir "macrhi-staging"
$MacrhiFolder = Join-Path $MacrhiStaging "RhinoIllustratorBridge.rhp"
if (Test-Path $MacrhiStaging) { Remove-Item $MacrhiStaging -Recurse -Force }
New-Item -ItemType Directory -Path $MacrhiFolder | Out-Null

# Copy built files
Copy-Item (Join-Path $Net7Dir "*") -Destination $MacrhiFolder -Recurse

# Include RUI file if it exists in the project dir or resources
$RuiPath = Join-Path $ProjectDir "RhinoIllustratorBridge.rui"
if (Test-Path $RuiPath) {
    Copy-Item $RuiPath -Destination $MacrhiFolder
}

$ZipFile = Join-Path $ProjectDir "RhinoIllustratorBridge.zip"
if (Test-Path $ZipFile) { Remove-Item $ZipFile -Force }
Compress-Archive -Path $MacrhiFolder -DestinationPath $ZipFile

$MacrhiFile = Join-Path $ProjectDir "RhinoIllustratorBridge.macrhi"
if (Test-Path $MacrhiFile) { Remove-Item $MacrhiFile -Force }
Move-Item $ZipFile $MacrhiFile -Force
Remove-Item $MacrhiStaging -Recurse -Force
Write-Host "  Mac Rhino Installer (.macrhi) created: RhinoIllustratorBridge.macrhi" -ForegroundColor Green

# Step 5: Update the dist/mac and dist/windows files
Write-Host "[5/5] Updating files in dist/mac and dist/windows..." -ForegroundColor Yellow
$RootDir = (Get-Item $ProjectDir).Parent.FullName
$DistMac = Join-Path $RootDir "dist\mac"
if (Test-Path $DistMac) {
    Copy-Item (Join-Path $Net7Dir "RhinoIllustratorBridge.rhp") -Destination $DistMac -Force
    if (Test-Path $MacrhiFile) {
        Copy-Item $MacrhiFile -Destination $DistMac -Force
    }
    Write-Host "  Updated files in dist/mac" -ForegroundColor Green
}
$DistWin = Join-Path $RootDir "dist\windows"
if (Test-Path $DistWin) {
    Copy-Item (Join-Path $Net7Dir "RhinoIllustratorBridge.rhp") -Destination $DistWin -Force
    Write-Host "  Updated files in dist/windows" -ForegroundColor Green
}

# Step 6: Summary
Write-Host ""
Write-Host "[6/6] Summary" -ForegroundColor Yellow
Write-Host "  Staging dir : $StagingDir" -ForegroundColor Gray
Write-Host "  Build output: $BuildOutput" -ForegroundColor Gray
Write-Host ""
Write-Host "To publish to Food4Rhino:" -ForegroundColor Cyan
Write-Host '  "C:\Program Files\Rhino 8\System\Yak.exe" push <package-file>.yak' -ForegroundColor White
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
