$ErrorActionPreference = "Stop"

$python = "c:/projek/fastapi-fd/.venv/Scripts/python.exe"

Write-Host "[1/4] Upgrading pip tooling..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip setuptools wheel

Write-Host "[2/4] Installing top-level dependencies..." -ForegroundColor Cyan
& $python -m pip install -r requirements.txt

Write-Host "[3/4] Enforcing locked transitive versions via constraints..." -ForegroundColor Cyan
& $python -m pip install -c constraints.txt -r requirements.txt

Write-Host "[4/4] Running smoke tests..." -ForegroundColor Cyan
& $python -m pytest -q

Write-Host "Environment setup complete." -ForegroundColor Green
