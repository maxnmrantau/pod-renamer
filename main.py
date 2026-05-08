import sys
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QFileDialog,
    QProgressBar, QMessageBox, QGroupBox, QFrame, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCharFormat

from ocr_engine import (
    setup_tesseract, get_image_files, create_output_folder,
    process_single_image, write_rekap
)


class WorkerThread(QThread):
    """Background thread for processing images."""
    log_signal = pyqtSignal(str, str)  # message, level (info/ok/warn/error)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(int, int, int)  # success_count, total_count, resi_count

    def __init__(self, source_folder, output_folder):
        super().__init__()
        self.source_folder = source_folder
        self.output_folder = output_folder
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        image_files = get_image_files(self.source_folder)
        total = len(image_files)

        if total == 0:
            self.log_signal.emit("Tidak ada file gambar ditemukan di folder sumber.", "warn")
            self.finished_signal.emit(0, 0, 0)
            return

        self.log_signal.emit(f"Ditemukan {total} file gambar.", "info")
        self.log_signal.emit(f"Output folder: {self.output_folder}", "info")
        self.log_signal.emit("─" * 50, "info")

        success_count = 0
        all_resi = []

        for i, image_path in enumerate(image_files):
            if self._is_cancelled:
                self.log_signal.emit("Proses dibatalkan oleh pengguna.", "warn")
                break

            filename = os.path.basename(image_path)
            self.log_signal.emit(f"Memproses ({i+1}/{total}): {filename}", "info")

            success, resi_list, messages = process_single_image(image_path, self.output_folder)

            if success:
                for msg in messages:
                    self.log_signal.emit(f"  ✓ {msg}", "ok")
                if len(resi_list) > 1:
                    self.log_signal.emit(f"  → {len(resi_list)} resi ditemukan dalam 1 gambar", "info")
                success_count += 1
                all_resi.extend(resi_list)
            else:
                for msg in messages:
                    self.log_signal.emit(f"  ✗ {msg}", "warn")

            self.progress_signal.emit(i + 1, total)

        # Write rekap file
        if all_resi:
            rekap_path = write_rekap(self.output_folder, all_resi)
            self.log_signal.emit("─" * 50, "info")
            self.log_signal.emit(f"Rekap resi disimpan: {os.path.basename(rekap_path)} ({len(all_resi)} resi)", "ok")

        self.finished_signal.emit(success_count, total, len(all_resi))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.output_folder = None
        self.init_ui()
        self.check_tesseract()

    def init_ui(self):
        self.setWindowTitle("POD Renamer - J&T Express  (NM Rantau)")
        self.setMinimumSize(750, 600)
        self.setStyleSheet(self.get_stylesheet())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ── Header ──
        header_row = QHBoxLayout()
        header = QLabel("POD Renamer - J&T Express  (NM Rantau)")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignCenter)
        header_row.addStretch(1)
        header_row.addWidget(header)
        header_row.addStretch(1)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("settingsBtn")
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.setToolTip("Pengaturan Tesseract OCR")
        self.btn_settings.clicked.connect(self.open_settings)
        header_row.addWidget(self.btn_settings, alignment=Qt.AlignRight)
        main_layout.addLayout(header_row)

        # ── Source Folder ──
        source_group = QGroupBox("Folder Sumber (Gambar POD)")
        source_layout = QHBoxLayout(source_group)
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Pilih folder yang berisi gambar POD...")
        self.source_input.setReadOnly(True)
        btn_browse_source = QPushButton("📁 Pilih Folder")
        btn_browse_source.setObjectName("browseBtn")
        btn_browse_source.clicked.connect(self.browse_source)
        source_layout.addWidget(self.source_input, stretch=1)
        source_layout.addWidget(btn_browse_source)
        main_layout.addWidget(source_group)

        # ── Action Buttons ──
        action_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶  Mulai Proses")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.setMinimumHeight(42)
        self.btn_start.clicked.connect(self.start_process)
        self.btn_start.setEnabled(False)

        self.btn_cancel = QPushButton("■  Batal")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setMinimumHeight(42)
        self.btn_cancel.clicked.connect(self.cancel_process)
        self.btn_cancel.setEnabled(False)

        self.btn_open_output = QPushButton("📂 Buka Output")
        self.btn_open_output.setObjectName("openBtn")
        self.btn_open_output.setMinimumHeight(42)
        self.btn_open_output.clicked.connect(self.open_output_folder)
        self.btn_open_output.setEnabled(False)

        action_layout.addWidget(self.btn_start, stretch=2)
        action_layout.addWidget(self.btn_cancel, stretch=1)
        action_layout.addWidget(self.btn_open_output, stretch=1)
        main_layout.addLayout(action_layout)

        # ── Progress Bar ──
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("Siap")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m (%p%)")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar, stretch=1)
        main_layout.addLayout(progress_layout)

        # ── Log Area ──
        log_group = QGroupBox("Log Proses")
        log_layout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Space Mono", 9))
        log_layout.addWidget(self.log_area)

        btn_clear_log = QPushButton("🗑 Bersihkan Log")
        btn_clear_log.clicked.connect(self.log_area.clear)
        log_layout.addWidget(btn_clear_log, alignment=Qt.AlignRight)

        main_layout.addWidget(log_group, stretch=1)

        # ── Status Bar ──
        self.statusBar().showMessage("Siap digunakan")

    def get_stylesheet(self):
        return """
            QMainWindow {
                background-color: #0f1117;
            }
            QWidget {
                color: #e8eaf0;
                font-family: 'DM Sans', 'Segoe UI', sans-serif;
                font-size: 10pt;
            }
            #header {
                font-family: 'Space Mono', 'Consolas', monospace;
                font-size: 15pt;
                font-weight: bold;
                color: #63d2a8;
                padding: 8px;
                margin-bottom: 4px;
                letter-spacing: 1px;
            }
            QGroupBox {
                font-family: 'Space Mono', 'Consolas', monospace;
                font-weight: bold;
                font-size: 9pt;
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 20px;
                background-color: #181c27;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QLineEdit {
                padding: 10px 14px;
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 12px;
                background-color: #1e2235;
                color: #e8eaf0;
                font-family: 'DM Sans', 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                border-color: #63d2a8;
            }
            QPushButton {
                padding: 9px 20px;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-family: 'Space Mono', 'Consolas', monospace;
                font-size: 9pt;
                background-color: #1e2235;
                color: #e8eaf0;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #252b40;
            }
            QPushButton:disabled {
                background-color: #181c27;
                color: #6b7280;
            }
            #browseBtn {
                background-color: #1e2235;
                color: #63d2a8;
                border: 1px solid rgba(99,210,168,0.3);
            }
            #browseBtn:hover {
                background-color: #252b40;
                border-color: #63d2a8;
            }
            #startBtn {
                background-color: #63d2a8;
                color: #0f1117;
                font-size: 10pt;
                letter-spacing: 1px;
            }
            #startBtn:hover {
                background-color: #7ddfba;
            }
            #startBtn:disabled {
                background-color: #181c27;
                color: #6b7280;
                border: 1px solid rgba(255,255,255,0.07);
            }
            #cancelBtn {
                background-color: #ff6b6b;
                color: #0f1117;
            }
            #cancelBtn:hover {
                background-color: #ff8787;
            }
            #cancelBtn:disabled {
                background-color: #181c27;
                color: #6b7280;
            }
            #settingsBtn {
                background-color: #1e2235;
                color: #6b7280;
                font-size: 14pt;
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 10px;
            }
            #settingsBtn:hover {
                background-color: #252b40;
                color: #63d2a8;
                border-color: #63d2a8;
            }
            #openBtn {
                background-color: #f5c542;
                color: #0f1117;
            }
            #openBtn:hover {
                background-color: #f7d46b;
            }
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 12px;
                text-align: center;
                background-color: #1e2235;
                color: #e8eaf0;
                height: 24px;
                font-family: 'Space Mono', 'Consolas', monospace;
                font-size: 8pt;
            }
            QProgressBar::chunk {
                background-color: #63d2a8;
                border-radius: 10px;
            }
            QTextEdit {
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 12px;
                background-color: #0f1117;
                color: #e8eaf0;
                padding: 10px;
                font-family: 'Space Mono', 'Consolas', monospace;
                font-size: 9pt;
            }
            QStatusBar {
                background-color: #181c27;
                color: #6b7280;
                border-top: 1px solid rgba(255,255,255,0.07);
                font-family: 'Space Mono', 'Consolas', monospace;
                font-size: 8pt;
            }
            QScrollBar:vertical {
                background: #0f1117;
                width: 8px;
                margin: 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #1e2235;
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #252b40;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """

    def check_tesseract(self):
        settings = QSettings("NMRantau", "PODRenamer")
        saved_path = settings.value("tesseract_path", "")

        if setup_tesseract(saved_path):
            self.statusBar().showMessage("✅ Tesseract OCR siap")
        else:
            self.statusBar().showMessage("⚠ Tesseract OCR tidak terdeteksi — klik ⚙")
            self.log_message(
                "⚠ Tesseract OCR tidak ditemukan!\n"
                "   Install dari: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "   Lalu klik tombol ⚙ di pojok kanan atas untuk mengarahkan ke tesseract.exe",
                "error"
            )

    def open_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Pengaturan Tesseract OCR")
        dialog.setFixedSize(480, 180)
        dialog.setStyleSheet(self.get_stylesheet())

        layout = QVBoxLayout(dialog)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Lokasi Tesseract OCR")
        title.setObjectName("header")
        title.setAlignment(Qt.AlignLeft)
        layout.addWidget(title)

        desc = QLabel("Arahkan ke file tesseract.exe jika tidak terdeteksi otomatis.")
        desc.setStyleSheet("color: #6b7280; font-family: 'DM Sans', 'Segoe UI', sans-serif;")
        layout.addWidget(desc)

        path_row = QHBoxLayout()
        self.settings_path = QLineEdit()
        settings = QSettings("NMRantau", "PODRenamer")
        saved = settings.value("tesseract_path", "")
        if saved:
            self.settings_path.setText(saved)
        else:
            self.settings_path.setPlaceholderText("tesseract.exe terdeteksi otomatis di sistem")
        self.settings_path.setReadOnly(True)
        path_row.addWidget(self.settings_path, stretch=1)

        btn_browse = QPushButton("📁 Cari")
        btn_browse.setObjectName("browseBtn")
        btn_browse.clicked.connect(lambda: self._browse_tesseract_in_dialog(dialog))
        path_row.addWidget(btn_browse)
        layout.addLayout(path_row)

        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

        dialog.exec_()

    def _browse_tesseract_in_dialog(self, dialog):
        path, _ = QFileDialog.getOpenFileName(
            dialog, "Pilih tesseract.exe",
            "C:\\Program Files\\Tesseract-OCR",
            "tesseract.exe (tesseract.exe)"
        )
        if path and os.path.isfile(path):
            if setup_tesseract(path):
                self.settings_path.setText(path)
                settings = QSettings("NMRantau", "PODRenamer")
                settings.setValue("tesseract_path", path)
                self.log_message(f"Tesseract OCR diatur: {path}", "ok")
                self.statusBar().showMessage("✅ Tesseract OCR siap")

    def browse_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Sumber Gambar POD")
        if folder:
            self.source_input.setText(folder)
            self.btn_start.setEnabled(True)
            self.log_message(f"Folder sumber dipilih: {folder}", "info")

            # Count images
            from ocr_engine import get_image_files
            images = get_image_files(folder)
            self.log_message(f"Ditemukan {len(images)} file gambar.", "info")
            self.statusBar().showMessage(f"Folder dipilih — {len(images)} gambar ditemukan")

    def start_process(self):
        source = self.source_input.text()
        if not source or not os.path.isdir(source):
            QMessageBox.warning(self, "Peringatan", "Pilih folder sumber terlebih dahulu!")
            return

        # Create output folder
        self.output_folder = create_output_folder(source)

        # Reset UI
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_open_output.setEnabled(False)

        self.log_message("═" * 50, "info")
        self.log_message(f"Memulai proses pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")

        # Start worker thread
        self.worker = WorkerThread(source, self.output_folder)
        self.worker.log_signal.connect(self.log_message)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def cancel_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.log_message("Membatalkan proses...", "warn")

    def open_output_folder(self):
        if self.output_folder and os.path.isdir(self.output_folder):
            os.startfile(self.output_folder)

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Proses: {current}/{total}")

    def on_finished(self, success, total, resi_count):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_open_output.setEnabled(True)

        self.log_message("═" * 50, "info")
        if total > 0:
            self.log_message(
                f"Selesai! {success}/{total} gambar berhasil diproses → {resi_count} resi terdeteksi.",
                "ok" if success > 0 else "warn"
            )
            failed = total - success
            if failed > 0:
                self.log_message(f"{failed} gambar gagal (resi tidak ditemukan).", "warn")
        else:
            self.log_message("Tidak ada gambar untuk diproses.", "warn")

        self.statusBar().showMessage(f"Selesai — {success}/{total} gambar, {resi_count} resi")

    def log_message(self, message, level="info"):
        color_map = {
            "info": "#63d2a8",
            "ok": "#63d2a8",
            "warn": "#f5c542",
            "error": "#ff6b6b",
        }
        prefix_map = {
            "info": "INFO",
            "ok": " OK ",
            "warn": "WARN",
            "error": " ERR",
        }

        color = color_map.get(level, "#e8eaf0")
        prefix = prefix_map.get(level, "INFO")
        timestamp = datetime.now().strftime("%H:%M:%S")

        if message.startswith("═") or message.startswith("─"):
            self.log_area.append(f'<span style="color:#6b7280">{message}</span>')
        else:
            self.log_area.append(
                f'<span style="color:#6b7280">[{timestamp}]</span> '
                f'<span style="color:{color}">[{prefix}]</span> '
                f'<span style="color:#e8eaf0">{message}</span>'
            )

        # Auto-scroll to bottom
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set app icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
