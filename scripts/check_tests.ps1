param(
    [int]$MinCoverage = 50
)

Write-Host "Running Jehu-Reader Test Suite with Code Coverage Enforcement..."
Write-Host "Target Coverage: $MinCoverage%"

python -m pytest tests/ --cov=src --cov-fail-under=$MinCoverage --tb=short

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Tests failed or code coverage fell below $MinCoverage%." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[SUCCESS] All tests passed and coverage requirement met." -ForegroundColor Green
exit 0
