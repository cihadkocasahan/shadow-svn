#!/bin/bash
# Shadow SVN v2.9 Global Installer (Linux/macOS) - Friendly Edition
# -----------------------------------------------------------

echo -e "\e[36m🛡️ Shadow SVN Global Installer\e[0m"
echo "--------------------------------------------------"

# 1. Prerequisite Checks with Guidance
check_req() {
    if ! command -v $1 &> /dev/null; then
        echo -e "\n\e[31m❌ Hata: $2 kurulu değil!\e[0m"
        echo -e "\e[33m💡 ÇÖZÜM:\e[0m Lütfen $2 kurulumunu yapın."
        echo -e "📖 \e[36mTalimat:\e[0m $3"
        echo "--------------------------------------------------"
        exit 1
    fi
}

check_req "git" "Git" "Debian: 'sudo apt install git' | macOS: 'brew install git'"
check_req "docker" "Docker" "Ubuntu: 'sudo apt install docker.io' | macOS: 'brew install --cask docker'"

# 2. Clone Repository
TARGET_DIR="Shadow-SVN"
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "\e[33m🚀 Repo çekiliyor...\e[0m"
    git clone https://github.com/cihadkocasahan/Shadow-SVN.git "$TARGET_DIR"
fi

# 3. Enter and Run Internal Setup
cd "$TARGET_DIR" || exit
chmod +x setup.sh
./setup.sh
