#!/bin/bash
# Shadow SVN v3.1 Setup Wizard (Linux/macOS) - Encrypted .env Edition
# -----------------------------------------------------------------

echo -e "\e[36m🛡️ Shadow SVN Setup Wizard\e[0m"
echo "-------------------------------------------------"

check_req() {
    if ! command -v $1 &> /dev/null; then
        echo -e "\n\e[31m❌ HATA: $2 bulunamadı!\e[0m"
        echo -e "\e[33m💡 ÇÖZÜM:\e[0m $3"
        echo "-------------------------------------------------"
        exit 1
    fi
}

check_req "git"    "Git"    "Debian: 'sudo apt install git' | macOS: 'brew install git'"
check_req "docker" "Docker" "Ubuntu: 'sudo apt install docker.io' | macOS: 'brew install --cask docker'"
check_req "python3" "Python3" "Debian: 'sudo apt install python3-pip' | macOS: 'brew install python3'"

echo -e "\n\e[33m⚙️  Şifreleme motoru hazırlanıyor...\e[0m"
pip3 install cryptography --quiet 2>/dev/null || pip install cryptography --quiet 2>/dev/null

read -p $'\nRioux SVN Kullanıcı Adı: ' riouxUser
read -s -p "Rioux SVN Şifresi: " riouxPass; echo
read -p "Dashboard Şifresi (Opsiyonel, boş = şifresiz): " dashPass

echo -e "\n\e[33m🔐 Kimlik bilgileri şifreleniyor...\e[0m"

mkdir -p data

python3 - << PYEOF
from cryptography.fernet import Fernet
import os, json

key_path = 'data/.secret.key'
if os.path.exists(key_path):
    with open(key_path, 'rb') as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(key_path, 'wb') as f:
        f.write(key)
    os.chmod(key_path, 0o600)

fn = Fernet(key)
user_enc = fn.encrypt(b'${riouxUser}').decode()
pass_enc = fn.encrypt(b'${riouxPass}').decode()

with open('.env', 'w') as env:
    env.write(f'RIOUX_SVN_USER={user_enc}\n')
    env.write(f'RIOUX_SVN_PASS={pass_enc}\n')

if not os.path.exists('data/config.json'):
    dash_enc = fn.encrypt(b'${dashPass}').decode() if '${dashPass}' else ''
    with open('data/config.json', 'w') as c:
        json.dump({'projects': {}, 'credentials': {}, 'dashboard_pass': dash_enc}, c, indent=4)

print('OK')
PYEOF

echo -e "\e[32m✅ Şifreli .env oluşturuldu.\e[0m"

echo -e "\n\e[33m🚀 Docker servisleri başlatılıyor...\e[0m"
docker compose -p shadow-svn up -d --build

echo -e "\n\e[32m✅ Shadow SVN Yayında!\e[0m"
echo "  Arayüz  : http://localhost:13081"
echo "  SVN     : svn://localhost:13080"
echo "-------------------------------------------------"
