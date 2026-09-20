# Build web/ and push it to Amplify hosting (manual deployment, no GitHub connection).
# Run from the repo root:  .\scripts\deploy_web.ps1
$ErrorActionPreference = "Stop"
$appId = "d2nozesb14q5me"
$region = "ap-south-1"
$aws = "C:\Users\abhii\AppData\Local\Programs\Amazon\AWSCLIV2\aws.exe"

if (-not (Test-Path web\.env.local)) { Copy-Item web\env.example web\.env.local }
Push-Location web
npm run build
Pop-Location

# PowerShell's Compress-Archive produced a zip Amplify unpacked as index.html only; use .NET directly.
New-Item -ItemType Directory -Force build | Out-Null
$zip = (Resolve-Path .).Path + "\build\web.zip"
if (Test-Path $zip) { Remove-Item $zip }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory((Resolve-Path web\out).Path, $zip)

$dep = & $aws amplify create-deployment --region $region --app-id $appId --branch-name main --output json | ConvertFrom-Json
Invoke-WebRequest -Uri $dep.zipUploadUrl -Method Put -InFile $zip -ContentType "application/zip" | Out-Null
& $aws amplify start-deployment --region $region --app-id $appId --branch-name main --job-id $dep.jobId | Out-Null

do {
  Start-Sleep -Seconds 5
  $status = & $aws amplify get-job --region $region --app-id $appId --branch-name main --job-id $dep.jobId --query 'job.summary.status' --output text
  Write-Host $status
} while ($status -eq "PENDING" -or $status -eq "RUNNING")

Write-Host "https://main.$appId.amplifyapp.com"
