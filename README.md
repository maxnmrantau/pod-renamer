<img width="752" height="632" alt="image" src="https://github.com/user-attachments/assets/f91e2ad2-353f-430f-ae21-e3f3ec743bc3" />

# POD Renamer - J&T Express (NM Rantau)

Aplikasi desktop untuk membaca nomor resi J&T Express dari gambar POD (Proof of Delivery) menggunakan OCR, lalu otomatis me-rename dan menyalin gambar berdasarkan nomor resi yang terdeteksi.

## Fitur

- **OCR Otomatis** — Membaca teks dari gambar POD menggunakan Tesseract OCR
- **Deteksi Resi J&T** — Mendeteksi nomor resi dengan awalan: `JD`, `JP`, `JX`, `JZ`, `JO`, `JJ`
- **Auto Rename & Copy** — Gambar di-copy ke folder output dengan nama = nomor resi
- **Rekap Resi** — Semua nomor resi dikumpulkan ke file `rekap_resi.txt`
- **Log Proses** — Menampilkan progress real-time di GUI
- **Modern Dark UI** — Tampilan modern berbasis Catppuccin Mocha theme

## Prasyarat

### 1. Install Python 3.8+
Download dari [python.org](https://www.python.org/downloads/)

### 2. Install Tesseract OCR
Download dan install dari: https://github.com/UB-Mannheim/tesseract/wiki

> **Penting:** Pastikan path instalasi default: `C:\Program Files\Tesseract-OCR\tesseract.exe`

### 3. Install Dependencies Python

```bash
pip install -r requirements.txt
```

## Cara Menjalankan

```bash
python main.py
```

## Cara Penggunaan

1. Klik **📁 Pilih Folder** untuk memilih folder yang berisi gambar POD
2. Klik **▶ Mulai Proses** untuk memulai OCR dan rename
3. Lihat progress di **Log Proses** dan **Progress Bar**
4. Setelah selesai, klik **📂 Buka Output** untuk membuka folder hasil
5. File `rekap_resi.txt` berisi daftar semua nomor resi yang berhasil dideteksi

## Format Resi yang Didukung

| Prefix | Contoh |
|--------|--------|
| JD | JD0012345678 |
| JP | JP1234567890123 |
| JX | JX9876543210 |
| JZ | JZ0012345678 |
| JO | JO1234567890 |
| JJ | JJ9876543210 |

## Format Gambar yang Didukung

`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`, `.webp`

## Struktur Output

```
Folder_Sumber/
├── foto1.jpg
├── foto2.png
└── Output_20250507_093000/
    ├── JD0012345678.jpg
    ├── JP1234567890.png
    └── rekap_resi.txt
```
