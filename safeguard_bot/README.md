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

### 💎 Fitur Premium
- `/premium` - Akses fitur premium dengan pembayaran crypto via CryptoBot
- Broadcast pesan ke semua grup
- Fitur eksklusif lainnya

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

---

# 🚀 PANDUAN LENGKAP INSTALASI DI VPS DEBIAN

**Panduan ini SANGAT DETAIL untuk memastikan tidak ada error!**

## 📋 Prasyarat

- VPS dengan **Debian 11/12/13** (fresh install lebih baik)
- Akses **root** atau user dengan **sudo**
- Koneksi internet stabil
- Token Bot Telegram (dari @BotFather)

---

## 🔧 LANGKAH 1: Login ke VPS & Update Sistem

### 1.1 Login ke VPS via SSH

```bash
# Dari terminal komputer lokal
ssh root@IP_VPS_ANDA

# Atau jika menggunakan user biasa
ssh username@IP_VPS_ANDA
```

### 1.2 Update Sistem (WAJIB!)

```bash
# Update daftar paket
sudo apt update

# Upgrade semua paket yang ada
sudo apt upgrade -y

# Install paket dasar yang mungkin belum ada
sudo apt install -y curl wget nano
```

---

## 🐍 LANGKAH 2: Install Python dan Dependencies Sistem

### 2.1 Install Python 3 dan pip

```bash
# Install Python 3, pip, venv, dan git
sudo apt install -y python3 python3-pip python3-venv python3-dev git

# Verifikasi instalasi Python
python3 --version
# Output yang diharapkan: Python 3.9.x atau lebih tinggi

# Verifikasi instalasi pip
pip3 --version
# Output yang diharapkan: pip 22.x atau lebih tinggi
```

### 2.2 Install Build Tools (Penting untuk beberapa library)

```bash
# Install build tools yang diperlukan
sudo apt install -y build-essential libffi-dev libssl-dev
```

---

## 📥 LANGKAH 3: Download Bot

### OPSI A: Clone dari GitHub (Jika sudah ada repository)

```bash
# Buat direktori untuk bot
mkdir -p ~/bots
cd ~/bots

# Clone repository (ganti URL dengan repository Anda)
git clone https://github.com/USERNAME/safeguard-bot.git safeguard_bot
cd safeguard_bot
```

### OPSI B: Upload Manual via SCP (Jika belum ada repository)

Dari komputer lokal:
```bash
# Upload folder bot ke VPS
scp -r /path/to/safeguard_bot username@IP_VPS:~/bots/
```

Di VPS:
```bash
cd ~/bots/safeguard_bot
```

---

## 🔒 LANGKAH 4: Setup Virtual Environment

### 4.1 Buat Virtual Environment

```bash
# Pastikan berada di folder bot
cd ~/bots/safeguard_bot

# Buat virtual environment
python3 -m venv venv

# Jika error, install venv terlebih dahulu:
# sudo apt install python3-venv -y
# python3 -m venv venv
```

### 4.2 Aktifkan Virtual Environment

```bash
# Aktifkan venv
source venv/bin/activate

# Setelah aktif, prompt akan berubah menjadi:
# (venv) username@hostname:~/bots/safeguard_bot$
```

**⚠️ PENTING: Setiap kali Anda ingin menjalankan bot secara manual, SELALU aktifkan venv terlebih dahulu!**

### 4.3 Upgrade pip

```bash
# Upgrade pip ke versi terbaru
pip install --upgrade pip
```

### 4.4 Install Dependencies Python

```bash
# Install semua dependencies dari requirements.txt
pip install -r requirements.txt

# Tunggu sampai selesai. Jika ada error, coba:
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4.5 Verifikasi Instalasi

```bash
# Cek apakah python-telegram-bot terinstall
pip show python-telegram-bot

# Output yang diharapkan:
# Name: python-telegram-bot
# Version: 21.0.1
# ...
```

---

## ⚙️ LANGKAH 5: Konfigurasi Bot

### 5.1 Buat file .env

```bash
# Copy template konfigurasi
cp .env.example .env

# Edit file konfigurasi
nano .env
```

### 5.2 Isi Konfigurasi .env

**Edit file dan ubah nilai-nilai berikut:**

```env
# ===========================================
# KONFIGURASI WAJIB
# ===========================================

# Token Bot dari @BotFather (WAJIB!)
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ

# ID Telegram Anda sebagai owner (WAJIB!)
OWNER_ID=123456789

# ID Admin bot (bisa lebih dari satu, pisahkan dengan koma)
ADMIN_IDS=123456789,987654321

# ===========================================
# KONFIGURASI OPSIONAL (bisa dibiarkan default)
# ===========================================

# Database (default: SQLite)
DATABASE_URL=sqlite:///safeguard.db

# CryptoBot untuk Premium (opsional, kosongkan jika tidak pakai)
CRYPTOBOT_TOKEN=
CRYPTOBOT_TESTNET=false

# Harga Premium (dalam USD)
PREMIUM_PRICE_1_MONTH=10
PREMIUM_PRICE_3_MONTHS=18
PREMIUM_PRICE_6_MONTHS=50

# Timeout verifikasi (dalam detik)
VERIFICATION_TIMEOUT=120
MAX_VERIFICATION_ATTEMPTS=3

# Anti-Flood
FLOOD_LIMIT=5
FLOOD_TIME_WINDOW=10

# Max warning sebelum kick
MAX_WARNINGS=3

# Level log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

### 5.3 Cara Mendapatkan BOT_TOKEN

1. Buka Telegram
2. Cari dan chat ke **@BotFather**
3. Kirim `/newbot`
4. Masukkan nama bot (contoh: `Safeguard Bot`)
5. Masukkan username bot (contoh: `my_safeguard_bot`)
6. Copy token yang diberikan (format: `123456789:ABCdefGHI...`)

### 5.4 Cara Mendapatkan OWNER_ID / ADMIN_IDS

1. Buka Telegram
2. Cari dan chat ke **@userinfobot** atau **@getmyid_bot**
3. Kirim `/start`
4. Bot akan menampilkan User ID Anda (angka)

### 5.5 Simpan Konfigurasi

Tekan `Ctrl + X`, lalu `Y`, lalu `Enter` untuk menyimpan di nano.

---

## 🧪 LANGKAH 6: Test Jalankan Bot

### 6.1 Jalankan Bot Manual (untuk test)

```bash
# Pastikan venv aktif
source venv/bin/activate

# Jalankan bot
python run.py
```

### 6.2 Cek Output

Jika berhasil, Anda akan melihat:

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

### 6.3 Test Bot di Telegram

1. Buka Telegram
2. Cari bot Anda berdasarkan username
3. Kirim `/start`
4. Jika bot membalas, berarti **BERHASIL!**

### 6.4 Stop Bot Test

Tekan `Ctrl + C` untuk menghentikan bot.

---

## 🔄 LANGKAH 7: Setup Auto-Start dengan Systemd

Agar bot berjalan otomatis saat VPS restart dan berjalan di background.

### 7.1 Cek Username dan Path

```bash
# Cek username Anda
whoami
# Output contoh: root atau debian atau ubuntu

# Cek path lengkap folder bot
pwd
# Output contoh: /root/bots/safeguard_bot atau /home/debian/bots/safeguard_bot
```

### 7.2 Buat Service File

```bash
sudo nano /etc/systemd/system/safeguard-bot.service
```

### 7.3 Isi Service File

**PENTING: Ganti `USERNAME` dengan username Anda (hasil dari `whoami`)**

**Jika user adalah `root`:**

```ini
[Unit]
Description=Safeguard Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bots/safeguard_bot
Environment=PATH=/root/bots/safeguard_bot/venv/bin:/usr/bin:/bin
ExecStart=/root/bots/safeguard_bot/venv/bin/python run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Jika user biasa (contoh: `debian`):**

```ini
[Unit]
Description=Safeguard Telegram Bot
After=network.target

[Service]
Type=simple
User=debian
WorkingDirectory=/home/debian/bots/safeguard_bot
Environment=PATH=/home/debian/bots/safeguard_bot/venv/bin:/usr/bin:/bin
ExecStart=/home/debian/bots/safeguard_bot/venv/bin/python run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Simpan dengan `Ctrl + X`, lalu `Y`, lalu `Enter`.

### 7.4 Aktifkan Service

```bash
# Reload systemd untuk membaca service baru
sudo systemctl daemon-reload

# Enable service (auto-start saat boot)
sudo systemctl enable safeguard-bot

# Start service
sudo systemctl start safeguard-bot

# Cek status (PENTING!)
sudo systemctl status safeguard-bot
```

### 7.5 Cek Status

Output yang diharapkan (status **active (running)**):

```
● safeguard-bot.service - Safeguard Telegram Bot
     Loaded: loaded (/etc/systemd/system/safeguard-bot.service; enabled; ...)
     Active: active (running) since ...
   Main PID: 12345 (python)
     CGroup: /system.slice/safeguard-bot.service
             └─12345 /root/bots/safeguard_bot/venv/bin/python run.py
```

---

## 📚 LANGKAH 8: Perintah Manajemen Bot

### Perintah Dasar

```bash
# Lihat status bot
sudo systemctl status safeguard-bot

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
```

### Melihat Log Bot

```bash
# Lihat log real-time (Ctrl+C untuk keluar)
sudo journalctl -u safeguard-bot -f

# Lihat 100 baris log terakhir
sudo journalctl -u safeguard-bot -n 100

# Lihat log hari ini
sudo journalctl -u safeguard-bot --since today

# Lihat log dengan error saja
sudo journalctl -u safeguard-bot -p err

# Lihat file log bot
cat ~/bots/safeguard_bot/bot.log
```

---

## 📱 LANGKAH 9: Setup Bot di Telegram

### 9.1 Tambahkan Bot ke Grup

1. Buka grup Telegram yang ingin dilindungi
2. Tap nama grup → Edit → Add Member
3. Cari bot Anda berdasarkan username
4. Tambahkan ke grup

### 9.2 Jadikan Bot sebagai Admin

1. Buka pengaturan grup
2. Administrators → Add Administrator
3. Pilih bot Anda
4. Berikan izin berikut:
   - ✅ Change Group Info
   - ✅ Delete Messages
   - ✅ Ban Users
   - ✅ Invite Users via Link
   - ✅ Pin Messages
   - ✅ Manage Video Chats
   - ✅ Add New Admins (opsional)
   - ✅ **Restrict Members** (WAJIB untuk verifikasi!)

### 9.3 Konfigurasi Bot di Grup

1. Kirim `/settings` di grup
2. Atur fitur sesuai kebutuhan:
   - Aktifkan/nonaktifkan verifikasi
   - Pilih tipe CAPTCHA
   - Atur anti-flood
   - Dan lain-lain

---

## 🐛 TROUBLESHOOTING (Solusi Masalah)

### ❌ Error: "BOT_TOKEN is required!"

**Solusi:**
```bash
# Pastikan file .env ada dan berisi token
cat ~/bots/safeguard_bot/.env | grep BOT_TOKEN

# Jika kosong, edit dan tambahkan token
nano ~/bots/safeguard_bot/.env
```

### ❌ Error: "ModuleNotFoundError: No module named 'telegram'"

**Solusi:**
```bash
cd ~/bots/safeguard_bot
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ Error: "Permission denied"

**Solusi:**
```bash
# Berikan permission
chmod +x ~/bots/safeguard_bot/run.py
chmod -R 755 ~/bots/safeguard_bot
```

### ❌ Bot tidak merespons di grup

**Solusi:**
1. Pastikan bot adalah admin grup
2. Pastikan bot punya izin "Restrict members"
3. Cek log: `sudo journalctl -u safeguard-bot -f`
4. Restart bot: `sudo systemctl restart safeguard-bot`

### ❌ Service gagal start

**Solusi:**
```bash
# Cek detail error
sudo journalctl -u safeguard-bot -n 50

# Cek apakah path benar
ls -la /root/bots/safeguard_bot/
ls -la /root/bots/safeguard_bot/venv/bin/python

# Test manual dulu
cd ~/bots/safeguard_bot
source venv/bin/activate
python run.py
```

### ❌ Error database

**Solusi:**
```bash
# Hapus database dan restart
rm ~/bots/safeguard_bot/safeguard.db
sudo systemctl restart safeguard-bot
```

### ❌ Error saat pip install

**Solusi:**
```bash
# Update pip dan tools
pip install --upgrade pip setuptools wheel

# Install ulang
pip install -r requirements.txt --force-reinstall
```

---

## 🔄 UPDATE BOT

### Cara Update dari GitHub

```bash
cd ~/bots/safeguard_bot

# Stop bot
sudo systemctl stop safeguard-bot

# Pull update terbaru
git pull origin main

# Aktifkan venv dan update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Start bot
sudo systemctl start safeguard-bot

# Cek status
sudo systemctl status safeguard-bot
```

---

## 📤 Cara Upload ke GitHub (Opsional)

### 1. Buat Repository di GitHub

1. Buka https://github.com
2. Login → Klik **"+"** → **"New repository"**
3. Isi nama: `safeguard-bot`
4. Pilih Private atau Public
5. **JANGAN** centang "Add a README file"
6. Klik **"Create repository"**

### 2. Push ke GitHub

```bash
cd ~/bots/safeguard_bot

# Init git (jika belum)
git init

# Tambahkan semua file
git add .

# Commit
git commit -m "Initial commit: Safeguard Bot"

# Tambahkan remote
git remote add origin https://github.com/USERNAME/safeguard-bot.git

# Push
git push -u origin main
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
│   │   ├── moderation.py   # Handler moderasi otomatis
│   │   ├── broadcast.py    # Handler broadcast
│   │   └── premium.py      # Handler premium
│   ├── services/
│   │   ├── __init__.py
│   │   ├── language.py     # Service multi-bahasa
│   │   ├── database.py     # Service database SQLite
│   │   ├── captcha.py      # Service CAPTCHA
│   │   └── payment.py      # Service pembayaran
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py   # Decorators untuk handlers
│   │   └── helpers.py      # Fungsi bantuan
│   └── locales/
│       ├── id.json         # Bahasa Indonesia
│       └── en.json         # Bahasa Inggris
├── web/
│   ├── __init__.py
│   └── server.py           # Web server untuk portal
├── scripts/
│   ├── install.sh          # Script instalasi otomatis
│   └── update.sh           # Script update
├── run.py                  # Script runner
├── requirements.txt        # Dependencies
├── .env.example           # Template konfigurasi
├── .gitignore             # File yang diabaikan git
└── README.md              # Dokumentasi ini
```

---

## 🔧 Environment Variables Lengkap

| Variable | Deskripsi | Default | Wajib |
|----------|-----------|---------|-------|
| `BOT_TOKEN` | Token dari @BotFather | - | ✅ Ya |
| `OWNER_ID` | ID Telegram owner bot | - | ✅ Ya |
| `ADMIN_IDS` | ID admin (comma-separated) | - | Tidak |
| `DATABASE_URL` | URL database | sqlite:///safeguard.db | Tidak |
| `CRYPTOBOT_TOKEN` | Token CryptoBot | - | Untuk Premium |
| `CRYPTOBOT_TESTNET` | Mode testnet | false | Tidak |
| `PREMIUM_PRICE_1_MONTH` | Harga 1 bulan (USD) | 10 | Tidak |
| `PREMIUM_PRICE_3_MONTHS` | Harga 3 bulan (USD) | 18 | Tidak |
| `PREMIUM_PRICE_6_MONTHS` | Harga 6 bulan (USD) | 50 | Tidak |
| `VERIFICATION_TIMEOUT` | Timeout verifikasi (detik) | 120 | Tidak |
| `MAX_VERIFICATION_ATTEMPTS` | Max percobaan verifikasi | 3 | Tidak |
| `FLOOD_LIMIT` | Pesan untuk trigger flood | 5 | Tidak |
| `FLOOD_TIME_WINDOW` | Window waktu flood (detik) | 10 | Tidak |
| `MAX_WARNINGS` | Max warning sebelum kick | 3 | Tidak |
| `LOG_LEVEL` | Level logging | INFO | Tidak |
| `WEB_HOST` | Host web server | 0.0.0.0 | Tidak |
| `WEB_PORT` | Port web server | 8080 | Tidak |
| `WEB_URL` | URL web server | http://localhost:8080 | Tidak |

---

## 📞 Dukungan

Jika ada pertanyaan atau masalah:
1. Buat Issue di GitHub
2. Hubungi developer

---

## 📜 Lisensi

MIT License - Bebas digunakan dan dimodifikasi.

---

**Made with ❤️ for Telegram Community**
