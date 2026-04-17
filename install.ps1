# Shadow SVN v2.9 Global Installer (Windows) - Friendly Edition
# -----------------------------------------------------------
Clear-Host
Write-Host "🛡️ Shadow SVN Global Installer" -ForegroundColor Cyan
Write-Host "--------------------------------------------------"

function Check-Req {
    param($cmd, $name, $link)
    if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Hata: $name kurulu değil!" -ForegroundColor Red
        Write-Host "💡 ÇÖZÜM: Lütfen $name kurulumunu yapın." -ForegroundColor Yellow
        Write-Host "🔗 Link: $link" -ForegroundColor Cyan
        exit
    }
}

Check-Req "git" "Git" "https://git-scm.com/download/win"
Check-Req "docker" "Docker Desktop" "https://www.docker.com/products/docker-desktop/"

# 2. Clone Repository
$targetDir = "Shadow-SVN"
if (!(Test-Path $targetDir)) {
    Write-Host "🚀 Repo çekiliyor..." -ForegroundColor Yellow
    git clone https://github.com/cihadkocasahan/Shadow-SVN.git $targetDir
}

# 3. Enter and Run Internal Setup
Set-Location $targetDir
powershell -ExecutionPolicy Bypass -File .\setup.ps1
