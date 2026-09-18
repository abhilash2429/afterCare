$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$out  = Join-Path $root "build\api"
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null
& "$root\.venv\Scripts\python.exe" -m pip install --target $out --platform manylinux2014_x86_64 --implementation cp `
  --python-version 3.12 --only-binary=:all: --upgrade PyJWT cryptography aiohttp requests py-vapid
if ($LASTEXITCODE) { exit $LASTEXITCODE }
# http-ece (pywebpush's dependency) ships no wheel at all (source-only on PyPI), so it can't be
# resolved under --only-binary=:all:. It's pure Python, so a normal (non-cross-platform) install
# is portable to Lambda's Linux runtime; --no-deps keeps this pass from re-touching the packages above.
& "$root\.venv\Scripts\python.exe" -m pip install --target $out --no-deps --upgrade http-ece pywebpush
if ($LASTEXITCODE) { exit $LASTEXITCODE }
Copy-Item -Recurse (Join-Path $root "api") (Join-Path $out "api")
Write-Host "bundled -> $out"
