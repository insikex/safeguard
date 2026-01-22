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

---

## 🚀 Instalasi di VPS Debian 13

### Prasyarat
- VPS dengan Debian 13
- Python 3.10 atau lebih tinggi
- Git
- Token Bot Telegram (dari @BotFather)

### Langkah 1: Update Sistem

```bash
sudo apt update && sudo apt upgrade -y
```

### Langkah 2: Install Python dan Dependencies

```bash
# Install Python 3 dan pip
sudo apt install python3 python3-pip python3-venv git -y

# Verifikasi instalasi
python3 --version
pip3 --version
```

### Langkah 3: Clone Repository

```bash
# Buat direktori untuk bot
mkdir -p ~/bots
cd ~/bots

# Clone repository (ganti dengan URL repository Anda)
git clone https://github.com/USERNAME/safeguard-bot.git

# PENTING: Masuk ke folder project utama (safeguard_bot)
cd safeguard-bot/safeguard_bot
```

> ⚠️ **PERHATIAN**: Setelah clone, pastikan Anda masuk ke folder `safeguard_bot` di dalam folder hasil clone. Struktur foldernya adalah:
> ```
> safeguard-bot/           <- folder hasil clone
> └── safeguard_bot/       <- folder utama project (masuk ke sini!)
>     ├── requirements.txt
>     ├── run.py
>     ├── .env.example
>     └── bot/
> ```

### Langkah 4: Setup Virtual Environment

```bash
# Pastikan Anda sudah di folder safeguard_bot (cek dengan pwd)
pwd
# Output harus: /home/username/bots/safeguard-bot/safeguard_bot

# Buat virtual environment
python3 -m venv venv

# Aktifkan virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> 💡 **Tips**: Jika muncul error "No such file or directory: 'requirements.txt'", pastikan Anda sudah berada di folder yang benar. Jalankan `ls` untuk melihat apakah file `requirements.txt` ada di folder saat ini.

### Langkah 5: Konfigurasi Bot

```bash
# Copy file konfigurasi
cp .env.example .env

# Edit konfigurasi
nano .env
```

Isi file `.env` dengan nilai yang benar:

```env
BOT_TOKEN=your_actual_bot_token_here
ADMIN_IDS=your_telegram_id
```

**Cara mendapatkan BOT_TOKEN:**
1. Buka Telegram dan cari @BotFather
2. Kirim `/newbot`
3. Ikuti instruksi untuk membuat bot baru
4. Copy token yang diberikan

**Cara mendapatkan ADMIN_IDS:**
1. Buka Telegram dan cari @userinfobot
2. Kirim `/start`
3. Bot akan menampilkan User ID Anda

### Langkah 6: Test Run Bot

```bash
# Pastikan virtual environment aktif
source venv/bin/activate

# Jalankan bot
python run.py
```

Jika berhasil, Anda akan melihat:
```
🛡️  SAFEGUARD BOT - Telegram Group Protection
Bot started! Running polling...
```

### Langkah 7: Setup Systemd Service (Auto-start)

Buat file service:

```bash
sudo nano /etc/systemd/system/safeguard-bot.service
```

Isi dengan (ganti `USERNAME` dengan username VPS Anda):

```ini
[Unit]
Description=Safeguard Telegram Bot
After=network.target

[Service]
Type=simple
User=USERNAME
WorkingDirectory=/home/USERNAME/bots/safeguard-bot/safeguard_bot
Environment=PATH=/home/USERNAME/bots/safeguard-bot/safeguard_bot/venv/bin
ExecStart=/home/USERNAME/bots/safeguard-bot/safeguard_bot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

> ⚠️ **PERHATIAN**: Perhatikan bahwa `WorkingDirectory` dan path lainnya menunjuk ke folder `safeguard_bot` di dalam folder hasil clone.

Aktifkan dan jalankan service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start saat boot)
sudo systemctl enable safeguard-bot

# Start service
sudo systemctl start safeguard-bot

# Cek status
sudo systemctl status safeguard-bot
```

---

## 🚀 Instalasi Otomatis (Alternatif)

Jika Anda ingin cara yang lebih mudah, gunakan script instalasi otomatis:

```bash
# Clone repository
cd ~/bots
git clone https://github.com/USERNAME/safeguard-bot.git

# Masuk ke folder project
cd safeguard-bot/safeguard_bot

# Jalankan script instalasi otomatis
chmod +x scripts/install.sh
./scripts/install.sh
```

Script ini akan otomatis:
- Install dependencies sistem
- Membuat virtual environment
- Install Python packages
- Membuat file .env dari template
- Setup systemd service

Setelah script selesai, tinggal edit file `.env` dan tambahkan BOT_TOKEN Anda.

### Perintah Berguna untuk Mengelola Bot

```bash
# Lihat status bot
sudo systemctl status safeguard-bot

# Stop bot
sudo systemctl stop safeguard-bot

# Restart bot
sudo systemctl restart safeguard-bot

# Lihat logs
sudo journalctl -u safeguard-bot -f

# Lihat logs terakhir 100 baris
sudo journalctl -u safeguard-bot -n 100
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

# PENTING: Masuk ke folder safeguard_bot
cd safeguard-bot/safeguard_bot

# Lanjutkan dengan langkah instalasi (buat venv, install requirements, dll)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Edit dan tambahkan BOT_TOKEN
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

### Error: "No such file or directory: 'requirements.txt'"
Ini terjadi karena Anda berada di folder yang salah. Solusi:
```bash
# Cek posisi Anda sekarang
pwd
ls

# Jika tidak ada requirements.txt, masuk ke folder yang benar
cd safeguard_bot
ls  # Sekarang harus terlihat requirements.txt

# Lanjutkan install
pip install -r requirements.txt
```

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
