[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if (-not (Get-Command kaggle -ErrorAction SilentlyContinue)) {
    throw 'Kaggle CLI is not available on PATH. Use the already authenticated Python installation.'
}

$kernelFolder = $PSScriptRoot
$kernelId = 'nurs2005/doclens-gpu-smoke'
Write-Output "Submitting $kernelId from $kernelFolder (private, GPU, internet disabled)."
$pushOutput = & kaggle kernels push -p $kernelFolder --accelerator NvidiaTeslaT4 2>&1
$pushExitCode = $LASTEXITCODE
$pushOutput | ForEach-Object { Write-Output $_ }
# Kaggle CLI 2.2.4 can print a server-side push error while returning exit code zero.
if ($pushExitCode -ne 0 -or ($pushOutput -join "`n") -match 'Kernel push error:') {
    throw "Kaggle submission failed (exit code $pushExitCode). See the error above."
}

$outputFolder = Join-Path $PSScriptRoot 'outputs'
Write-Output "Status:   kaggle kernels status $kernelId"
Write-Output "Logs:     kaggle kernels logs $kernelId"
Write-Output "Follow:   kaggle kernels logs $kernelId --follow"
Write-Output "Download: kaggle kernels output $kernelId -p `"$outputFolder`""
