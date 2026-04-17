# Shadow SVN v3.1 Setup Wizard (Windows) - Encrypted .env Edition
# -----------------------------------------------------------------
Clear-Host
Write-Host "🛡️ Shadow SVN Setup Wizard" -ForegroundColor Cyan
Write-Host "-------------------------------------------------"

# 1. Prerequisite Checks
function Check-Req {
    param($cmd, $name, $link, $winget)
    if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "`n❌ HATA: $name bulunamadı!" -ForegroundColor Red
        Write-Host "💡 ÇÖZÜM: $name kurmanız gerekiyor." -ForegroundColor Yellow
        Write-Host "🔗 İndirme: $link" -ForegroundColor Cyan
        if ($winget) { Write-Host "⌨️  Komut : winget install $winget" }
        Write-Host "-------------------------------------------------"
        Pause; exit
    }
}

Check-Req "git"    "Git"            "https://git-scm.com/download/win"                    "git.git"
Check-Req "docker" "Docker Desktop" "https://www.docker.com/products/docker-desktop/"      "Docker.DockerDesktop"
Check-Req "python" "Python"         "https://www.python.org/downloads/"                    "Python.Python.3"

# 2. Ensure cryptography is installed on host for encryption
Write-Host "`n⚙️  Şifreleme motoru hazırlanıyor..." -ForegroundColor Yellow
python -m pip install cryptography --quiet

# 3. Collect credentials
$riouxUser = Read-Host "`nRioux SVN Kullanıcı Adı"
$riouxPass = Read-Host "Rioux SVN Şifresi"
$dashPass  = Read-Host "Dashboard Şifresi (Opsiyonel, boş = şifresiz)"

# 4. Encrypt via Python and write .env + secret key
Write-Host "`n🔐 Kimlik bilgileri şifreleniyor..." -ForegroundColor Yellow

if (!(Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }

python -c @"
from cryptography.fernet import Fernet
import os, json

# Generate or load key
key_path = 'data/.secret.key'
if os.path.exists(key_path):
    with open(key_path, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(key_path, 'wb') as f:
        f.write(key)

f = Fernet(key)
user_enc = f.encrypt(b'$riouxUser').decode()
pass_enc = f.encrypt(b'$riouxPass').decode()

with open('.env', 'w') as env:
    env.write(f'RIOUX_SVN_USER={user_enc}\n')
    env.write(f'RIOUX_SVN_PASS={pass_enc}\n')

# Write initial config
if not os.path.exists('data/config.json'):
    dash_enc = f.encrypt(b'$dashPass').decode() if '$dashPass' else ''
    with open('data/config.json', 'w') as c:
        json.dump({'projects': {}, 'credentials': {}, 'dashboard_pass': dash_enc}, c, indent=4)

print('OK')
"@

Write-Host "✅ Şifreli .env oluşturuldu." -ForegroundColor Green

# 5. Docker Launch
Write-Host "`n🚀 Docker servisleri başlatılıyor..." -ForegroundColor Yellow
docker compose -p shadow-svn up -d --build

Write-Host "`n✅ Shadow SVN Yayında!" -ForegroundColor Cyan
Write-Host "  Arayüz  : http://localhost:13081"
Write-Host "  SVN     : svn://localhost:13080"
Write-Host "-------------------------------------------------"
Pause
