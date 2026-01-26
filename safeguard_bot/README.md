# 🛡️ Safeguard Bot - Telegram Group Protection

Bot Telegram profesional untuk perlindungan grup dari spam, bot, dan pengguna berbahaya dengan dukungan multi-bahasa (Indonesia/English).

## ✨ Fitur Utama

### 🔐 Verifikasi Member Baru
- **Button CAPTCHA** - Verifikasi sederhana dengan tombol
- **Math CAPTCHA** - Tantangan matematika
- **Emoji CAPTCHA** - Pilih emoji yang benar
- **Portal Web** - Verifikasi melalui website

### 🛡️ Perlindungan Otomatis
- **Anti-Flood** - Deteksi dan mute user yang spam pesan
- **Anti-Link** - Blokir link tidak diizinkan
- **Anti-Spam** - Deteksi pola spam otomatis
- **Anti-Bot** - Kick bot yang ditambahkan non-admin

### 👮 Moderasi Admin
- `/warn` - Beri peringatan ke user
- `/unwarn` - Hapus peringatan
- `/kick` - Kick user dari grup
- `/ban` - Ban user dari grup
- `/unban` - Unban user
- `/mute` - Bisukan user
- `/unmute` - Aktifkan kembali user
- `/stats` - Statistik grup

### 🌐 Multi-Bahasa
- Deteksi otomatis bahasa user
- Bahasa Indonesia 🇮🇩 untuk user Indonesia
- English 🇺🇸 untuk user lainnya
- Bisa diubah manual lewat settings

### ⚙️ Pengaturan Fleksibel
- Dashboard pengaturan dengan inline keyboard
- Toggle fitur on/off
- Pilih tipe verifikasi
- Atur batas peringatan
- Pilih bahasa bot

### 💎 Fitur Premium (Opsional)
- Pembayaran via CryptoBot (cryptocurrency)
- Fitur tambahan untuk grup premium

---

## 🚀 Panduan Lengkap Instalasi di VPS Debian 13

Panduan ini menjelaskan langkah demi langkah untuk menginstal dan menjalankan Safeguard Bot di VPS dengan sistem operasi Debian 13 (Trixie).

### 📋 Prasyarat

**Kebutuhan Sistem:**
- VPS dengan Debian 13 (minimal 512MB RAM, 1 CPU)
- Akses root atau user dengan sudo
- Koneksi internet yang stabil

**Yang Perlu Disiapkan:**
- Token Bot Telegram (dari @BotFather)
- ID Telegram Anda (untuk admin)
- Token CryptoBot (opsional, untuk fitur premium)

---

### 📝 LANGKAH 1: Persiapan Awal - Login ke VPS

Login ke VPS Anda menggunakan SSH:

```bash
ssh root@IP_VPS_ANDA
# atau jika menggunakan key
ssh -i ~/.ssh/key_anda root@IP_VPS_ANDA
```

**Tips:** Jika ini VPS baru, pertimbangkan untuk membuat user non-root:

```bash
# Buat user baru (opsional tapi direkomendasikan)
adduser botuser
usermod -aG sudo botuser

# Login dengan user baru
su - botuser
```

---

### 📝 LANGKAH 2: Update Sistem Debian 13

```bash
# Update daftar paket
sudo apt update

# Upgrade paket yang terinstal
sudo apt upgrade -y

# Install paket yang direkomendasikan
sudo apt install -y curl wget nano unzip htop
```

---

### 📝 LANGKAH 3: Install Python dan Dependencies

Debian 13 sudah menyertakan Python 3.11+ secara default:

```bash
# Install Python 3, pip, venv, dan git
sudo apt install -y python3 python3-pip python3-venv python3-dev git

# Verifikasi instalasi Python
python3 --version
# Output: Python 3.11.x atau lebih tinggi

# Verifikasi pip
pip3 --version
# Output: pip 23.x.x atau lebih tinggi

# Verifikasi git
git --version
# Output: git version 2.x.x
```

**Jika Python versi lebih rendah dari 3.10:**

```bash
# Tambahkan repository deadsnakes (untuk Ubuntu/Debian derivatif)
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

---

### 📝 LANGKAH 4: Dapatkan Token Bot dari BotFather

1. Buka Telegram dan cari **@BotFather**
2. Kirim perintah `/newbot`
3. Ikuti instruksi:
   - Masukkan nama bot (contoh: "Safeguard Bot")
   - Masukkan username bot (contoh: "MySafeguardBot" - harus diakhiri dengan "bot")
4. BotFather akan memberikan **token** seperti: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
5. **Simpan token ini!** Anda akan membutuhkannya nanti.

**Konfigurasi tambahan di BotFather (opsional tapi direkomendasikan):**

```
/setprivacy - Pilih bot Anda - Disable (agar bot bisa membaca semua pesan di grup)
/setjoingroups - Pilih bot Anda - Enable
/setcommands - Pilih bot Anda - Lalu kirim:
start - Mulai bot dan lihat bantuan
help - Tampilkan bantuan
settings - Pengaturan grup (admin only)
stats - Statistik grup (admin only)
warn - Beri peringatan ke user
unwarn - Hapus peringatan
kick - Kick user dari grup
ban - Ban user dari grup
unban - Unban user
mute - Bisukan user
unmute - Aktifkan kembali user
```

---

### 📝 LANGKAH 5: Dapatkan ID Telegram Anda

1. Buka Telegram dan cari **@userinfobot** atau **@getmyid_bot**
2. Kirim `/start`
3. Bot akan menampilkan ID Anda (angka seperti: `123456789`)
4. **Catat ID ini!** Ini akan menjadi OWNER_ID dan ADMIN_IDS

---

### 📝 LANGKAH 6: Download/Clone Bot ke VPS

```bash
# Buat direktori untuk menyimpan bot
mkdir -p ~/bots
cd ~/bots

# Opsi 1: Clone dari repository (ganti URL dengan repository Anda)
git clone https://github.com/USERNAME/safeguard-bot.git safeguard_bot
cd safeguard_bot

# Opsi 2: Upload manual menggunakan SCP (dari komputer lokal)
# scp -r /path/to/safeguard_bot user@IP_VPS:~/bots/

# Opsi 3: Download dari release (jika tersedia)
# wget https://github.com/USERNAME/safeguard-bot/archive/main.zip
# unzip main.zip
# mv safeguard-bot-main safeguard_bot
# cd safeguard_bot
```

---

### 📝 LANGKAH 7: Setup Virtual Environment Python

```bash
# Pastikan Anda di direktori project
cd ~/bots/safeguard_bot

# Buat virtual environment
python3 -m venv venv

# Aktifkan virtual environment
source venv/bin/activate

# Anda akan melihat (venv) di awal prompt:
# (venv) user@vps:~/bots/safeguard_bot$

# Upgrade pip ke versi terbaru
pip install --upgrade pip

# Install semua dependencies
pip install -r requirements.txt
```

**Verifikasi instalasi dependencies:**

```bash
pip list | grep telegram
# Output: python-telegram-bot   21.0.1
```

---

### 📝 LANGKAH 8: Konfigurasi Bot (.env file)

```bash
# Copy file contoh konfigurasi
cp .env.example .env

# Edit file konfigurasi
nano .env
```

**Isi file `.env` dengan konfigurasi Anda:**

```env
# ===========================================
# Safeguard Bot Configuration
# ===========================================

# Telegram Bot Token (WAJIB)
# Dapatkan dari @BotFather
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Bot Owner ID (WAJIB)
# ID Telegram Anda
OWNER_ID=123456789

# Bot Admin IDs (Opsional)
# Bisa lebih dari satu, pisahkan dengan koma
ADMIN_IDS=123456789,987654321

# Database URL (Opsional)
# Default menggunakan SQLite
DATABASE_URL=sqlite:///safeguard.db

# ===========================================
# CryptoBot Payment Settings (Opsional - untuk Premium)
# ===========================================
# Dapatkan dari @CryptoBot -> Crypto Pay -> Create App
CRYPTOBOT_TOKEN=your_cryptobot_token_here
CRYPTOBOT_TESTNET=false

# ===========================================
# Premium Pricing (dalam USD)
# ===========================================
PREMIUM_PRICE_1_MONTH=10
PREMIUM_PRICE_3_MONTHS=18
PREMIUM_PRICE_6_MONTHS=50

# ===========================================
# Verification Settings
# ===========================================
VERIFICATION_TIMEOUT=120
MAX_VERIFICATION_ATTEMPTS=3

# Anti-Flood Settings
FLOOD_LIMIT=5
FLOOD_TIME_WINDOW=10

# Warning Settings
MAX_WARNINGS=3

# Logging Level
LOG_LEVEL=INFO

# Web Server (Opsional - untuk Portal Verification)
WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_URL=http://IP_VPS_ANDA:8080
```

**Simpan file:** Tekan `Ctrl+X`, lalu `Y`, lalu `Enter`

---

### 📝 LANGKAH 9: Test Jalankan Bot (Manual)

```bash
# Pastikan virtual environment aktif
source ~/bots/safeguard_bot/venv/bin/activate

# Masuk ke direktori project
cd ~/bots/safeguard_bot

# Jalankan bot
python run.py
```

**Jika berhasil, Anda akan melihat:**

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🛡️  SAFEGUARD BOT - Telegram Group Protection          ║
║                                                           ║
║   Version: 1.0.0                                          ║
║   Multi-language: Indonesian 🇮🇩 / English 🇺🇸            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

Bot started! Running polling...
```

**Test bot Anda:**
1. Buka Telegram dan cari bot Anda
2. Kirim `/start`
3. Bot harus merespons

**Hentikan bot:** Tekan `Ctrl+C`

---

### 📝 LANGKAH 10: Setup Systemd Service (Auto-start)

Agar bot berjalan otomatis dan restart jika crash:

```bash
# Buat file service
sudo nano /etc/systemd/system/safeguard-bot.service
```

**Isi dengan konfigurasi berikut:**

```ini
[Unit]
Description=Safeguard Telegram Bot
Documentation=https://github.com/USERNAME/safeguard-bot
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=botuser
Group=botuser
WorkingDirectory=/home/botuser/bots/safeguard_bot
Environment="PATH=/home/botuser/bots/safeguard_bot/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/botuser/bots/safeguard_bot/venv/bin/python run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security options
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**PENTING:** Ganti `botuser` dengan username VPS Anda. Jika menggunakan root, ganti dengan `root` dan path menjadi `/root/bots/safeguard_bot`

**Simpan dan aktifkan service:**

```bash
# Reload systemd untuk membaca service baru
sudo systemctl daemon-reload

# Aktifkan auto-start saat boot
sudo systemctl enable safeguard-bot

# Jalankan bot
sudo systemctl start safeguard-bot

# Cek status
sudo systemctl status safeguard-bot
```

**Output yang diharapkan:**

```
● safeguard-bot.service - Safeguard Telegram Bot
     Loaded: loaded (/etc/systemd/system/safeguard-bot.service; enabled; preset: enabled)
     Active: active (running) since ...
```

---

### 📝 LANGKAH 11: Menggunakan Script Instalasi Otomatis (Alternatif)

Jika Anda sudah clone repository, Anda bisa menggunakan script instalasi otomatis:

```bash
# Masuk ke direktori project
cd ~/bots/safeguard_bot

# Beri izin eksekusi
chmod +x scripts/install.sh

# Jalankan script instalasi
./scripts/install.sh
```

Script ini akan:
1. Update sistem
2. Install Python dan dependencies
3. Buat virtual environment
4. Install requirements
5. Copy .env.example ke .env
6. Setup systemd service

---

### 🔧 Perintah Pengelolaan Bot

```bash
# === STATUS & LOGS ===

# Lihat status bot
sudo systemctl status safeguard-bot

# Lihat logs real-time (follow)
sudo journalctl -u safeguard-bot -f

# Lihat 100 baris log terakhir
sudo journalctl -u safeguard-bot -n 100

# Lihat logs hari ini
sudo journalctl -u safeguard-bot --since today

# === KONTROL BOT ===

# Stop bot
sudo systemctl stop safeguard-bot

# Start bot
sudo systemctl start safeguard-bot

# Restart bot
sudo systemctl restart safeguard-bot

# Disable auto-start
sudo systemctl disable safeguard-bot

# Enable auto-start
sudo systemctl enable safeguard-bot

# === UPDATE BOT ===

# Stop bot dulu
sudo systemctl stop safeguard-bot

# Masuk ke direktori
cd ~/bots/safeguard_bot

# Aktifkan venv
source venv/bin/activate

# Pull perubahan terbaru (jika dari git)
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Start bot lagi
sudo systemctl start safeguard-bot
```

---

### 🔥 Setup Firewall (Opsional tapi Direkomendasikan)

```bash
# Install UFW (Uncomplicated Firewall)
sudo apt install -y ufw

# Allow SSH (PENTING - jangan skip ini!)
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS jika menggunakan web portal
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp

# Aktifkan firewall
sudo ufw enable

# Cek status
sudo ufw status
```

---

## 📤 Cara Memindahkan ke Repository GitHub Anda

### Langkah 1: Buat Repository Baru di GitHub

1. Buka https://github.com
2. Login ke akun Anda
3. Klik tombol **"+"** di pojok kanan atas
4. Pilih **"New repository"**
5. Isi nama repository (contoh: `safeguard-bot`)
6. Pilih **Public** atau **Private**
7. **JANGAN** centang "Add a README file"
8. Klik **"Create repository"**

### Langkah 2: Push ke Repository Anda

Di terminal VPS atau komputer lokal:

```bash
# Masuk ke folder project
cd /path/to/safeguard_bot

# Inisialisasi git (jika belum)
git init

# Tambahkan semua file
git add .

# Commit perubahan
git commit -m "Initial commit: Safeguard Bot"

# Tambahkan remote repository (ganti dengan URL Anda)
git remote add origin https://github.com/USERNAME/safeguard-bot.git

# Push ke GitHub
git push -u origin main
```

**Jika menggunakan branch master:**
```bash
git push -u origin master
```

### Langkah 3: Clone di VPS dari Repository Anda

```bash
# Di VPS
cd ~/bots
git clone https://github.com/USERNAME/safeguard-bot.git
cd safeguard-bot

# Setup seperti langkah instalasi di atas
```

---

## 📋 Struktur Project

```
safeguard_bot/
├── bot/
│   ├── __init__.py
│   ├── config.py           # Konfigurasi bot
│   ├── main.py             # Entry point aplikasi
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py        # Handler /start, /help
│   │   ├── admin.py        # Handler admin commands
│   │   ├── verification.py # Handler verifikasi
│   │   ├── settings.py     # Handler pengaturan
│   │   └── moderation.py   # Handler moderasi otomatis
│   ├── services/
│   │   ├── __init__.py
│   │   ├── language.py     # Service multi-bahasa
│   │   ├── database.py     # Service database SQLite
│   │   └── captcha.py      # Service CAPTCHA
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py   # Decorators untuk handlers
│   │   └── helpers.py      # Fungsi bantuan
│   └── locales/
│       ├── id.json         # Bahasa Indonesia
│       └── en.json         # Bahasa Inggris
├── run.py                  # Script runner
├── requirements.txt        # Dependencies
├── .env.example           # Contoh konfigurasi
└── README.md              # Dokumentasi
```

---

## 🔧 Konfigurasi

### Environment Variables

| Variable | Deskripsi | Default |
|----------|-----------|---------|
| `BOT_TOKEN` | Token dari BotFather | *Required* |
| `ADMIN_IDS` | ID admin bot (comma-separated) | - |
| `DATABASE_URL` | URL database | sqlite:///safeguard.db |
| `VERIFICATION_TIMEOUT` | Timeout verifikasi (detik) | 120 |
| `MAX_VERIFICATION_ATTEMPTS` | Max percobaan verifikasi | 3 |
| `FLOOD_LIMIT` | Jumlah pesan untuk trigger flood | 5 |
| `FLOOD_TIME_WINDOW` | Window waktu flood (detik) | 10 |
| `MAX_WARNINGS` | Max peringatan sebelum kick | 3 |
| `LOG_LEVEL` | Level logging | INFO |

---

## 📝 Cara Menggunakan Bot

### 1. Tambahkan Bot ke Grup
- Cari bot Anda di Telegram
- Klik "Add to Group"
- Pilih grup yang diinginkan

### 2. Jadikan Bot sebagai Admin
- Buka pengaturan grup
- Administrators > Add Administrator
- Pilih bot Anda
- Berikan izin yang diperlukan:
  - ✅ Delete messages
  - ✅ Ban users
  - ✅ Invite users via link
  - ✅ Restrict members

### 3. Konfigurasi Bot
- Kirim `/settings` di grup
- Atur fitur sesuai kebutuhan

---

## 🐛 Troubleshooting

### Bot tidak merespons
1. Pastikan BOT_TOKEN benar
2. Pastikan bot sudah menjadi admin grup
3. Cek logs: `sudo journalctl -u safeguard-bot -f`

### Verifikasi tidak bekerja
1. Pastikan bot punya izin "Restrict members"
2. Pastikan fitur verifikasi diaktifkan di `/settings`

### Database error
1. Hapus file `safeguard.db`
2. Restart bot

### Permission error
1. Pastikan bot adalah admin
2. Berikan izin yang diperlukan

---

## 📜 Lisensi

MIT License - Bebas digunakan dan dimodifikasi.

---

## 🤝 Kontribusi

Kontribusi selalu diterima! Silakan buat Pull Request atau Issue di repository.

---

## 📞 Dukungan

Jika ada pertanyaan atau masalah:
1. Buat Issue di GitHub
2. Hubungi developer

---

**Made with ❤️ for Telegram Community**
