
$ErrorActionPreference = "Stop"

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host " NETARCHITECT FINAL SUBMISSION BUILD" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Ensure execution starts in the project root
$Root = Get-Location

if (!(Test-Path "pyproject.toml") -or !(Test-Path "src/netarchitect/main.py")) {
    throw "Run this script from the NetArchitect project root."
}

# 1. Remove old generated exports
Write-Host "[1/8] Cleaning old exports..." -ForegroundColor Yellow

if (Test-Path "exports") {
    Remove-Item "exports" -Recurse -Force
}

New-Item -ItemType Directory -Path "exports" | Out-Null

# 2. Remove Python caches
Write-Host "[2/8] Removing Python caches..." -ForegroundColor Yellow

Get-ChildItem -Path . -Directory -Recurse -Force |
    Where-Object {
        $_.Name -in @("__pycache__", ".pytest_cache", ".mypy_cache")
    } |
    Sort-Object { $_.FullName.Length } -Descending |
    Remove-Item -Recurse -Force

Get-ChildItem -Path . -File -Recurse -Filter "*.pyc" |
    Remove-Item -Force

# 3. Remove temporary development files
Write-Host "[3/8] Removing temporary files..." -ForegroundColor Yellow

$TemporaryFiles = @(
    "apply_cic307_acl_patch.ps1",
    "IMPROVEMENTS.md"
)

foreach ($File in $TemporaryFiles) {
    if (Test-Path $File) {
        Remove-Item $File -Force
    }
}

# 4. Ensure ignore rules exist
Write-Host "[4/8] Checking .gitignore..." -ForegroundColor Yellow

$IgnoreRules = @(
    ".venv/",
    "venv/",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".coverage",
    "htmlcov/",
    "build/",
    "dist/",
    "*.egg-info/",
    ".vscode/",
    ".idea/"
)

$ExistingRules = @()
if (Test-Path ".gitignore") {
    $ExistingRules = Get-Content ".gitignore"
}

foreach ($Rule in $IgnoreRules) {
    if ($Rule -notin $ExistingRules) {
        Add-Content ".gitignore" $Rule
    }
}

# 5. Install project
Write-Host "[5/8] Installing project..." -ForegroundColor Yellow

python -m pip install -e .

if ($LASTEXITCODE -ne 0) {
    throw "Project installation failed."
}

# 6. Run complete test suite
Write-Host "`n[6/8] Running automated tests..." -ForegroundColor Yellow

python -m pytest -v

if ($LASTEXITCODE -ne 0) {
    throw "Tests failed. Fix the failures before submission."
}

# 7. Generate all three mandatory preset exports
Write-Host "`n[7/8] Generating preset exports..." -ForegroundColor Yellow

$Profiles = @(
    @{ Name = "campus"; Folder = "exports/campus" },
    @{ Name = "metro"; Folder = "exports/metro" },
    @{ Name = "wan"; Folder = "exports/global" }
)

foreach ($Profile in $Profiles) {

    Write-Host "`nGenerating $($Profile.Name)..." -ForegroundColor Cyan

    python -m netarchitect.main `
        --preset $Profile.Name `
        --output-dir $Profile.Folder

    if ($LASTEXITCODE -ne 0) {
        throw "Generation failed for $($Profile.Name)."
    }
}

# Generate custom JSON demonstration
if (Test-Path "config/custom_test.json") {

    Write-Host "`nGenerating custom JSON output..." -ForegroundColor Cyan

    python -m netarchitect.main `
        --input config/custom_test.json `
        --output-dir exports/custom_test

    if ($LASTEXITCODE -ne 0) {
        throw "Custom JSON generation failed."
    }
}
else {
    Write-Warning "custom_test.json not found. Skipping custom demonstration."
}

# 8. Verify generated configuration files
Write-Host "`n[8/8] Verifying generated files..." -ForegroundColor Yellow

$RequiredFolders = @(
    "exports/campus",
    "exports/metro",
    "exports/global"
)

foreach ($Folder in $RequiredFolders) {

    if (!(Test-Path $Folder)) {
        throw "Missing output folder: $Folder"
    }

    $Configs = @(Get-ChildItem $Folder -Filter "*.cfg" -File)

    if ($Configs.Count -eq 0) {
        throw "No Cisco configuration files generated in $Folder"
    }

    Write-Host "$Folder : $($Configs.Count) configuration files" -ForegroundColor Green
}

Write-Host "`nGenerated exports:" -ForegroundColor Cyan
Get-ChildItem exports -Recurse -File |
    Select-Object FullName, Length |
    Format-Table -AutoSize

Write-Host "`n======================================" -ForegroundColor Green
Write-Host " FINAL BUILD COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "======================================`n" -ForegroundColor Green

Write-Host "Next: inspect Git status and commit your project." -ForegroundColor Cyan

git status --short
