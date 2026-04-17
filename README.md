# Shadow SVN

> **v0.1.2** · Free & Open Source · MIT License

A lightweight, autonomous SVN mirroring engine. Clone any remote SVN repository to a fast, fully functional local mirror — with zero manual configuration after setup.

---

## 🇬🇧 English

### The Problem

Working with large or remote SVN repositories is slow. Every checkout, update, or branch switch requires a connection to the remote server. When the server is unreachable or the network is slow, development stops entirely.

Beyond performance, there are two more common pain points:
- **Free SVN hosting services** (like RiouxSVN) have no built-in backup. If the service shuts down, your history is gone.
- **Monorepo overload:** You only care about one branch or subfolder, but you're forced to deal with the entire repository structure.

### The Solution

Shadow SVN lets you create a **precise, local mirror** of exactly the part of an SVN repository you care about — not the whole thing. You define the remote URL (root, branch, tag — anything), and Shadow SVN mirrors just that.

- Back up your repos from free SVN hosting services automatically
- Mirror only the branch or subfolder you actually work with
- Organize multiple remotes locally, each with its own sync schedule
- Work offline — your local mirror is always available

### Who Is This For?

- Developers working with **free SVN hosting** (RiouxSVN, etc.) who want a local backup
- Teams dealing with **slow or unreliable remote SVN servers**
- Developers who want to **cherry-pick specific branches** from large monorepos
- Anyone who wants to organize and mirror multiple SVN sources **on their own terms**

- ✅ Any SVN URL supported (root, trunk, branch, tag)
- ✅ Automatic background sync (configurable interval)
- ✅ Real-time status tracking with visual indicators (Spinning icon)
- ✅ Smart Scheduler — incremental updates without mass restarts
- ✅ Smart credential caching — enter once per server, reused across all projects
- ✅ Asynchronous project deletion for instant UI response
- ✅ Web dashboard with modern SVG icons (Play, Pause, Resume, Settings)
- ✅ Home navigation link and flexible layout
- ✅ Fully portable — all data in one `./data` folder
- ✅ Optional dashboard password (default: `admin`)

### Quick Start

**Requirements:** Git, Docker Desktop

### Requirements

- [Git](https://git-scm.com/download/win)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/master/install.ps1 | iex
```

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/master/install.sh | bash
```

Or clone and run manually:
```bash
git clone https://github.com/cihadkocasahan/shadow-svn.git
cd shadow-svn
./setup.sh        # Linux/macOS
.\setup.ps1       # Windows
```

Alternative — **Docker only** (no clone needed):

```powershell
# Download docker-compose.yml and start
curl -o docker-compose.yml https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/master/docker-compose.yml
docker compose up -d
```

Or a single `docker run` command:

```powershell
docker run -d -p 13081:80 -v C:\ShadowSVN\data:/data -e SVN_USER=user -e SVN_PASS=pass ghcr.io/cihadkocasahan/shadow-svn:latest
```
> Data is stored in the folder you specify with `-v` (e.g. `C:\ShadowSVN\data`).

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

Performansın ötesinde, iki yaygın sorun daha var:
- Ücretsiz SVN barındırma hizmetlerinde **(RiouxSVN gibi)** yerleşik yedekleme yoktur. Hizmet kapanırsa geçmişiniz gider.
- **Monorepo yükü:** Yalnızca tek bir dal veya alt klasörle ilgileniyorsunuzdur; ancak reponun tamamıyla uğraşmak zorundasınız.

### Çözüm

Shadow SVN, bir SVN deposunun **tam olarak ilgilen diğiniz kısmının** yerel bir aynasını oluşturmanızı sağlar. Uzak URL'yi siz belirlersiniz (root, branch, tag — herhangi biri), Shadow SVN yalnızca o kısmı aynalar.

- Ücretsiz SVN barındırma hizmetlerindeki repolarınızı otomatik yedekleyin
- Yalnızca çalıştığınız dalı veya alt klasörü aynala
- Birden fazla uzak kaynağı her birine özel senkronizasyon takvimi ile lokalde organize edin
- Offline çalışın — yerel aynanız her zaman erişilebilirdir

### Kimler İçin?

- Ücretsiz SVN barındırma (RiouxSVN vb.) kullanan ve **yerel yedek** isteyen geliştiriciler
- **Yavaş veya güvenilmez uzak SVN sunucularıyla** çalışan takımlar
- Büyük monorepolarda **yalnızca belirli dalları** almak isteyen geliştiriciler
- Birden fazla SVN kaynağını **kendi düzenine göre** lokalde yönetmek isteyenler

- ✅ Her türlü SVN URL desteklenir (root, trunk, branch, tag)
- ✅ Otomatik arka plan senkronizasyonu (ayarlanabilir aralık)
- ✅ Gerçek zamanlı durum takibi ve görsel bildirimler (Yükleme simgesi)
- ✅ Akıllı Zamanlayıcı — sistemi yormayan kademeli güncellemeler
- ✅ Akıllı kimlik bilgisi önbelleği — sunucu başına bir kez girilir, tüm projelerde geçerlidir
- ✅ Asenkron proje silme — UI donmadan anında temizlik
- ✅ Modern SVG ikonları ile zenginleştirilmiş Dashboard
- ✅ Başlık üzerinden ana sayfaya hızlı dönüş
- ✅ Tamamen taşınabilir — tüm veriler `./data` klasöründe
- ✅ Opsiyonel dashboard şifresi (varsayılan: `admin`)

### Hızlı Kurulum

**Gereksinimler:** Git, Docker Desktop

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/master/install.ps1 | iex
```

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/cihadkocasahan/shadow-svn/master/install.sh | bash
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

---

### Roadmap / Yol Haritası
- [ ] **Multi-language Support:** English and Turkish dashboard switching. (Planned)
- [ ] **Email Notifications:** Get notified on sync errors.
- [ ] **Multiple Users:** Basic user management for the dashboard.
