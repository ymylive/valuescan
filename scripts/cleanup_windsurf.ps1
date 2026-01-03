param(
    [switch]$IncludeWorkspaceArtifacts,
    [string[]]$WorkspacePaths = @(),
    [switch]$DryRun
)

function Resolve-PathSafe {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }
    try {
        return (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    } catch {
        return $Path  # Return original path if it doesn't exist yet
    }
}

function Remove-Target {
    param(
        [string]$Target,
        [switch]$DryRunMode
    )

    if (-not $Target) { return }
    if (-not (Test-Path -LiteralPath $Target)) {
        Write-Host "[skip] $Target (not found)"
        return
    }

    $resolved = Resolve-PathSafe $Target
    if ($DryRunMode) {
        Write-Host "[dry-run] Would remove $resolved"
        return
    }

    try {
        Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction Stop
        Write-Host "[removed] $resolved"
    } catch {
        Write-Warning "Failed to remove $resolved: $($_.Exception.Message)"
    }
}

$userProfile = $env:USERPROFILE
$appData = $env:APPDATA
$localAppData = $env:LOCALAPPDATA

$coreTargets = @(
    Join-Path $userProfile ".codeium\windsurf",
    Join-Path $userProfile ".codeium",
    Join-Path $appData "Codeium",
    Join-Path $localAppData "Codeium",
    Join-Path $appData "Windsurf",
    Join-Path $localAppData "Programs\Windsurf",
    Join-Path $appData "Code\User\globalStorage\windsurf"
)

Write-Host "=== Windsurf / Codeium Cleanup Script ==="
Write-Host "Dry run:`t$($DryRun.IsPresent)"
Write-Host ""

foreach ($target in $coreTargets | Sort-Object -Unique) {
    Remove-Target -Target $target -DryRunMode:$DryRun
}

if ($IncludeWorkspaceArtifacts -and $WorkspacePaths.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Workspace Artifacts ==="
    foreach ($workspace in $WorkspacePaths) {
        if ([string]::IsNullOrWhiteSpace($workspace)) { continue }
        $artifactPaths = @(
            Join-Path $workspace ".windsurfrules",
            Join-Path $workspace ".ask_continue_port",
            Join-Path $workspace ".ask_continue_response.txt",
            Join-Path $workspace "ask_continue_http.ps1"
        )
        foreach ($artifact in $artifactPaths) {
            Remove-Target -Target $artifact -DryRunMode:$DryRun
        }
    }
}

Write-Host ""
Write-Host "Cleanup complete."
