# Unknown Face Alert

Aplikasi deteksi dan pengenalan wajah real-time berbasis OpenCV.
- Memberi **label nama** pada wajah yang terdaftar di database.
- Membunyikan **alert**, menyimpan **screenshot**, dan mencatat **log** jika mendeteksi wajah tidak dikenal.
- Tombol ON/OFF (tekan `P` atau klik tombol pojok kanan atas).

## Struktur Direktori
```text
Unknown Face Alert/
├── dataset/                       # Database wajah (folder per orang)
│   ├── Linggar/
│   │   ├── 1.jpg
│   │   └── 2.jpg
│   └── Suryo/
│       ├── 1.jpg
│       └── 2.jpg
├── logs/                          # Log teks kejadian (auto-generate)
├── screenshots/                   # Bukti tangkapan layar (auto-generate)
├── alert.wav                      # File suara peringatan
├── haarcascade_frontalface_default.xml   # Auto-download saat pertama kali training
├── trainer.yml                    # Model hasil training (auto-generate)
├── labels.txt                     # Mapping ID → Nama (auto-generate)
├── train.py                       # Script training (jalankan 1x)
├── unknown_face_alert.py          # Aplikasi utama
├── requirements.txt
└── README.md
```

## Instalasi

> **Catatan:** Solusi ini **tidak memerlukan Visual Studio Build Tools** atau compiler C++ apapun.

1. Pastikan Python sudah terinstal, lalu buat virtual environment (opsional tapi disarankan):
   ```bash
   python -m venv env
   env\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Cara Menjalankan

### 1. Siapkan Dataset
Letakkan foto wajah di folder `dataset/<NamaOrang>/`.
- Format: `.jpg` atau `.png`
- Foto menghadap depan, pencahayaan cukup, resolusi minimal 150x150 px
- Disarankan 2–5 foto per orang dengan ekspresi/sudut sedikit berbeda

### 2. Training (Jalankan 1x, atau ulang setiap dataset berubah)
```bash
python train.py
```
File `trainer.yml` dan `labels.txt` akan dibuat otomatis. Haar cascade XML juga akan diunduh otomatis jika belum ada.

### 3. Jalankan Aplikasi Utama
```bash
python unknown_face_alert.py
```
- Sesuaikan `TARGET_CAMERA_NAME` di dalam script dengan nama webcam Anda.
- Tekan `P` atau klik tombol di pojok kanan atas untuk ON/OFF.

## Kontrol Aplikasi
| Aksi | Fungsi |
|------|--------|
| Tekan `P` | Toggle ON/OFF detektor |
| Klik tombol pojok kanan atas | Toggle ON/OFF detektor |
| Tutup window | Keluar dari aplikasi |

## Maintenance Otomatis
- Screenshot lebih tua dari **24 jam** akan dihapus otomatis.
- Pembersihan dijadwalkan setiap **1 jam**.

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `No module named 'cv2'` | Jalankan `pip install -r requirements.txt` di dalam virtual environment |
| `Can't open file haarcascade...` | Script `train.py` akan auto-download. Pastikan koneksi internet aktif saat pertama kali training |
| Tidak ada wajah terdeteksi saat training | Pastikan foto jelas, tidak gelap, dan wajah terlihat penuh |
| Wajah dikenal salah / sering "Unknown" | Tambah foto di dataset lalu jalankan ulang `python train.py`. Turunkan `THRESHOLD_KONFIDENSI` (misal ke 50) untuk lebih ketat |
| Kamera tidak ditemukan | Cek nama webcam di Device Manager, lalu sesuaikan `TARGET_CAMERA_NAME` di script |

## Menambah Orang Baru
1. Buat folder baru di `dataset/` dengan nama orang tersebut.
2. Isi dengan foto wajahnya.
3. Jalankan ulang `python train.py`.
4. Jalankan ulang `unknown_face_alert.py`.