<img width="752" height="632" alt="image" src="https://github.com/user-attachments/assets/1b77b803-d3b6-4ec5-a3c4-2b49021811c9" />


# POD Renamer - J&T Express (NM Rantau)

Aplikasi desktop untuk membaca nomor resi J&T Express dari gambar POD (Proof of Delivery) menggunakan OCR, lalu otomatis me-rename dan menyalin gambar berdasarkan nomor resi yang terdeteksi.

## Fitur

- **OCR Otomatis** — Membaca teks dari gambar POD menggunakan Tesseract OCR
- **Deteksi Resi J&T** — Mendeteksi nomor resi prefix huruf (`JD`, `JP`, `JX`, `JZ`, `JO`, `JJ`) dan numerik (`11`, `12`, `13`)
- **Consensus Voting** — Multi-pass OCR + voting untuk akurasi tinggi
- **Auto Rename & Copy** — Gambar di-copy ke folder output dengan nama = nomor resi
- **Rekap Resi** — Semua nomor resi dikumpulkan ke file `rekap_resi.txt`
- **Log Proses** — Menampilkan progress real-time di GUI
- **Dark Cyberpunk UI** — Tema Developer Console dengan aksen hijau mint

## Prasyarat

### 1. Install Python 3.8+
Download dari [python.org](https://www.python.org/downloads/)

### 2. Install Tesseract OCR
Download dan install dari: https://github.com/UB-Mannheim/tesseract/wiki

> Aplikasi akan otomatis mendeteksi Tesseract. Jika terinstall di lokasi berbeda, klik tombol **⚙** di pojok kanan atas untuk mengarahkan ke `tesseract.exe`.

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
2. Jika Tesseract tidak terdeteksi, klik **⚙** di pojok kanan atas → arahkan ke `tesseract.exe`
3. Klik **▶ Mulai Proses** untuk memulai OCR dan rename
4. Lihat progress di **Log Proses** dan **Progress Bar**
5. Setelah selesai, klik **📂 Buka Output** untuk membuka folder hasil
6. File `rekap_resi.txt` berisi daftar semua nomor resi yang berhasil dideteksi

## Format Resi yang Didukung

| Prefix | Format | Contoh |
|--------|--------|--------|
| JD | JD + 10 digit | JD0012345678 |
| JP | JP + 10 digit | JP1234567890 |
| JX | JX + 10 digit | JX9876543210 |
| JZ | JZ + 10 digit | JZ0012345678 |
| JO | JO + 10 digit | JO1234567890 |
| JJ | JJ + 10 digit | JJ9876543210 |
| 11 | 10 digit (11xxxxxxxx) | 1176543210 |
| 12 | 10 digit (12xxxxxxxx) | 1276543210 |
| 13 | 10 digit (13xxxxxxxx) | 1376543210 |

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
## Semoga Bermanfaat 🔥🔥🔥
Traktir Coklat🍫 https://saweria.co/Makmurriansyah
