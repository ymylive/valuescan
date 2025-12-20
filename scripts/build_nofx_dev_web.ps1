param(
    [string]$RepoUrl = $(if ($env:NOFX_REPO_URL) { $env:NOFX_REPO_URL } else { "https://github.com/NoFxAiOS/nofx.git" }),
    [string]$Branch = $(if ($env:NOFX_REPO_BRANCH) { $env:NOFX_REPO_BRANCH } else { "dev" })
)

$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ExternalDir = Join-Path $RootDir "external\\nofx-dev"
$DistOut = Join-Path $RootDir "web\\nofx_dist"

if (!(Test-Path (Join-Path $RootDir "external"))) {
    New-Item -ItemType Directory -Path (Join-Path $RootDir "external") | Out-Null
}

if (!(Test-Path (Join-Path $ExternalDir ".git"))) {
    Write-Host "[NOFX] Cloning $RepoUrl ($Branch) -> $ExternalDir"
    git clone --depth 1 --branch $Branch $RepoUrl $ExternalDir
} else {
    Write-Host "[NOFX] Updating $ExternalDir -> origin/$Branch"
    git -C $ExternalDir fetch origin $Branch --depth 1
    git -C $ExternalDir checkout $Branch
    git -C $ExternalDir reset --hard ("origin/" + $Branch)
}

$mainTsx = Join-Path $ExternalDir "web\\src\\main.tsx"
if (Test-Path $mainTsx) {
    $content = Get-Content -Path $mainTsx -Raw -Encoding UTF8
    if ($content -notmatch "basename=\\{import\\.meta\\.env\\.BASE_URL\\}") {
        Write-Host "[NOFX] Patching React Router basename for /nofx"
        $content = $content.Replace("<BrowserRouter>", "<BrowserRouter basename={import.meta.env.BASE_URL}>")
        Set-Content -Path $mainTsx -Value $content -Encoding UTF8
    }
}

Push-Location (Join-Path $ExternalDir "web")
try {
    Write-Host "[NOFX] Installing frontend dependencies (npm ci)"
    npm ci
    Write-Host "[NOFX] Building frontend (base=/nofx/)"
    npm run build -- --base=/nofx/
} finally {
    Pop-Location
}

if (Test-Path $DistOut) {
    Remove-Item -Recurse -Force $DistOut
}
New-Item -ItemType Directory -Path $DistOut | Out-Null

Copy-Item -Path (Join-Path $ExternalDir "web\\dist\\*") -Destination $DistOut -Recurse -Force
Write-Host "[NOFX] Done. Output: $DistOut"

