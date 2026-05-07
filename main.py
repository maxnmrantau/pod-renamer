import sys
import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QFileDialog,
    QProgressBar, QMessageBox, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
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
        header = QLabel("POD Renamer - J&T Express  (NM Rantau)")
        header.setObjectName("header")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

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
        self.log_area.setFont(QFont("Consolas", 9))
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
                background-color: #1e1e2e;
            }
            QWidget {
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10pt;
            }
            #header {
                font-size: 16pt;
                font-weight: bold;
                color: #f38ba8;
                padding: 8px;
                margin-bottom: 4px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 18px;
                background-color: #181825;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #a6adc8;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #45475a;
                border-radius: 6px;
                background-color: #313244;
                color: #cdd6f4;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                padding: 8px 18px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                background-color: #45475a;
                color: #cdd6f4;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }
            #browseBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            #browseBtn:hover {
                background-color: #74c7ec;
            }
            #startBtn {
                background-color: #a6e3a1;
                color: #1e1e2e;
                font-size: 11pt;
            }
            #startBtn:hover {
                background-color: #94e2d5;
            }
            #startBtn:disabled {
                background-color: #313244;
                color: #6c7086;
            }
            #cancelBtn {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
            #cancelBtn:hover {
                background-color: #eba0ac;
            }
            #openBtn {
                background-color: #fab387;
                color: #1e1e2e;
            }
            #openBtn:hover {
                background-color: #f9e2af;
            }
            QProgressBar {
                border: 1px solid #45475a;
                border-radius: 6px;
                text-align: center;
                background-color: #313244;
                color: #cdd6f4;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 5px;
            }
            QTextEdit {
                border: 1px solid #45475a;
                border-radius: 6px;
                background-color: #11111b;
                color: #cdd6f4;
                padding: 6px;
            }
            QStatusBar {
                background-color: #181825;
                color: #6c7086;
                border-top: 1px solid #45475a;
            }
        """

    def check_tesseract(self):
        if not setup_tesseract():
            self.log_message(
                "⚠ Tesseract OCR tidak ditemukan! "
                "Install dari: https://github.com/UB-Mannheim/tesseract/wiki",
                "error"
            )
            self.statusBar().showMessage("⚠ Tesseract OCR tidak terdeteksi")

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
            "info": "#89b4fa",
            "ok": "#a6e3a1",
            "warn": "#f9e2af",
            "error": "#f38ba8",
        }
        prefix_map = {
            "info": "INFO",
            "ok": " OK ",
            "warn": "WARN",
            "error": " ERR",
        }

        color = color_map.get(level, "#cdd6f4")
        prefix = prefix_map.get(level, "INFO")
        timestamp = datetime.now().strftime("%H:%M:%S")

        if message.startswith("═") or message.startswith("─"):
            self.log_area.append(f'<span style="color:#6c7086">{message}</span>')
        else:
            self.log_area.append(
                f'<span style="color:#6c7086">[{timestamp}]</span> '
                f'<span style="color:{color}">[{prefix}]</span> '
                f'<span style="color:#cdd6f4">{message}</span>'
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
