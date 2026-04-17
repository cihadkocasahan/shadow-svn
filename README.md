# Shadow SVN

> **v0.1.0** · Free & Open Source · MIT License

A lightweight, autonomous SVN mirroring engine. Clone any remote SVN repository to a fast, fully functional local mirror — with zero manual configuration after setup.

---

## 🇬🇧 English

### The Problem

Working with large or remote SVN repositories is slow. Every checkout, update, or branch switch hits the remote server. When the server is down or the network is slow, development stops entirely.

### The Solution

Shadow SVN creates and maintains a **local mirror** of any SVN repository. Your tools (IDE, TortoiseSVN, Jenkins) connect to the local mirror instead of the remote. Syncing happens automatically in the background.

- ✅ Any SVN URL supported (root, trunk, branch, tag)
- ✅ Automatic background sync (configurable interval)
- ✅ Smart credential caching — enter once per server, reused across all projects
- ✅ Web dashboard for managing mirrors
- ✅ Fully portable — all data in one `./data` folder
- ✅ Optional dashboard password (default: `admin`)

### Quick Start

**Requirements:** Git, Docker Desktop

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/main/install.ps1 | iex
```

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/main/install.sh | bash
```

Or clone and run manually:
```bash
git clone https://github.com/cihadkocasahan/shadow-svn.git
cd shadow-svn
./setup.sh        # Linux/macOS
.\setup.ps1       # Windows
```

### What Happens During Setup

The setup script (`setup.ps1` / `setup.sh`) will:

1. **Check prerequisites** — Verifies Git and Docker are installed. If not, prints the exact download link and command to fix it.
2. **Configure credentials** — Asks for your remote SVN username and password, and an optional dashboard password.
3. **Encrypt and store** — Credentials are **not** stored in plain text. The setup uses [Fernet symmetric encryption](https://cryptography.io/en/latest/fernet/) to encrypt all sensitive values before writing them to `.env`. A unique secret key is generated and saved to `data/.secret.key` (never committed to Git).
4. **Launch** — Runs `docker compose up --build` and starts both containers.

> 🔐 **Security note:** `.env` and `data/.secret.key` are both listed in `.gitignore` and will never be committed to your repository.

### Usage

1. Open the dashboard: `http://localhost:13081`
2. Login (default password: `admin`)
3. Click **+ Add Mirror**, enter the remote SVN URL and a project name
4. Your local checkout URL: `svn://localhost:13080/<ProjectName>`

### Tech Stack

- **App:** Python 3 · Flask · APScheduler · Gunicorn
- **Server:** Apache SVN · elleflorio/svn-server
- **Infrastructure:** Docker · Docker Compose

---

## 🇹🇷 Türkçe

### Problem

Büyük veya uzak SVN depolarıyla çalışmak yavaştır. Her checkout, güncelleme veya dal değişimi uzak sunucuya bağlanmak zorunda kalır. Sunucu erişilemez olduğunda ya da ağ yavaş çalıştığında geliştirme tamamen durur.

### Çözüm

Shadow SVN, herhangi bir SVN deposunun **yerel bir aynasını (mirror)** oluşturur ve otomatik olarak güncel tutar. IDE, TortoiseSVN veya Jenkins gibi araçlarınız uzak sunucu yerine yerel aynaya bağlanır. Senkronizasyon arka planda otomatik gerçekleşir.

- ✅ Her türlü SVN URL desteklenir (root, trunk, branch, tag)
- ✅ Otomatik arka plan senkronizasyonu (ayarlanabilir aralık)
- ✅ Akıllı kimlik bilgisi önbelleği — sunucu başına bir kez girilir, tüm projelerde geçerlidir
- ✅ Ayna projelerini yönetmek için web arayüzü
- ✅ Tamamen taşınabilir — tüm veriler `./data` klasöründe
- ✅ Opsiyonel dashboard şifresi (varsayılan: `admin`)

### Hızlı Kurulum

**Gereksinimler:** Git, Docker Desktop

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/main/install.ps1 | iex
```

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/main/install.sh | bash
```

Ya da manuel kurulum:
```bash
git clone https://github.com/cihadkocasahan/shadow-svn.git
cd shadow-svn
./setup.sh        # Linux/macOS
.\setup.ps1       # Windows
```

### Kurulum Sırasında Neler Olur?

Kurulum betiği (`setup.ps1` / `setup.sh`) sırayla şunları yapar:

1. **Gereksinim kontrolü** — Git ve Docker kurulu mu diye kontrol eder. Eksik varsa indirme linkini ve kurulum komutunu ekranda gösterir.
2. **Yapılandırma** — Uzak SVN kullanıcı adı, şifre ve opsiyonel dashboard şifresi sorulur.
3. **Şifrele ve kaydet** — Kimlik bilgileri düz metin olarak **saklanmaz**. Kurulum betiği, tüm hassas verileri `.env` dosyasına yazmadan önce [Fernet simetrik şifrelemesiyle](https://cryptography.io/en/latest/fernet/) şifreler. Benzersiz bir anahtar üretilir ve `data/.secret.key` dosyasına kaydedilir (Git'e hiçbir zaman gönderilmez).
4. **Başlat** — `docker compose up --build` komutu çalıştırılır, her iki konteyner başlatılır.

> 🔐 **Güvenlik notu:** `.env` ve `data/.secret.key` dosyaları `.gitignore` kapsamındadır ve deponuza hiçbir zaman eklenmez.

### Kullanım

1. Arayüzü açın: `http://localhost:13081`
2. Giriş yapın (varsayılan şifre: `admin`)
3. **+ Yeni Ayna Ekle** butonuna tıklayın, uzak SVN URL'sini ve proje adını girin
4. Yerel checkout URL'niz: `svn://localhost:13080/<ProjeAdı>`

---

## Contributing / Katkıda Bulunun

Contributions are welcome! Feel free to open an issue or submit a pull request.  
Katkılarınızı bekliyoruz! Issue açabilir veya pull request gönderebilirsiniz.

- 🐛 **Bug Report / Hata Bildirimi:** [GitHub Issues](https://github.com/cihadkocasahan/shadow-svn/issues)
- 💡 **Feature Request / Özellik İsteği:** [GitHub Issues](https://github.com/cihadkocasahan/shadow-svn/issues)
- 🔀 **Pull Request:** Always welcome

## Developer / Geliştirici

**Cihad Kocasahan**  
[github.com/cihadkocasahan](https://github.com/cihadkocasahan)

---

*Shadow SVN is free software released under the MIT License.*  
*Shadow SVN, MIT Lisansı kapsamında yayımlanan ücretsiz bir yazılımdır.*
