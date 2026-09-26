import os
from PyQt6.QtWidgets import (
QApplication,
QFileDialog,
QHBoxLayout,
QMainWindow,
QMessageBox,
QWidget,
)

import src.image as image
from src.gui_widgets import (
STYLE_SHEET,
render_colored_pixmap,
VideoWorker,
SidebarPanel,
PreviewPanel,
)

# main window

class MainWindow(QMainWindow):
    """
    fereastra principala a aplicatiei: leaga sidebar ul de preview,
    porneste/opreste VideoWorker ul si apeleaza direct functiile
    din image.py pt conversia imaginilor
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASCII Art Studio")
        self.resize(1100, 750)

        self.image_path = None
        self.video_path = None

        self.ascii_text = None
        self.rgb_mat = None
        self.is_colored = False

        self.video_worker = None
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # sidebar

        self.sidebar = SidebarPanel()
        main_layout.addWidget(self.sidebar)

        # preview

        self.preview = PreviewPanel()
        main_layout.addWidget(self.preview)

        # status

        self._status_bar = self.statusBar()
        self._status_bar.showMessage("Ready. Open an image or video")
        self._connect_signals()

    def _connect_signals(self):
        """
        leaga toate semnalele emise de sidebar de metodele coresp din MainWindow
        """
        self.sidebar.open_requested.connect(self.open_file)
        self.sidebar.convert_requested.connect(self.convert)
        self.sidebar.play_requested.connect(self.play_video)
        self.sidebar.pause_requested.connect(self.pause_video)
        self.sidebar.stop_requested.connect(self.stop_video)
        self.sidebar.save_requested.connect(self.save_image)

    # cat de agresiv se cuantizeaza culoarea in preview ul color,
    # ca sa avem run uri lungi si putine apeluri drawText
    # 1 = culoare exacta 24 = compromis,
    # 32-48 = si mai rapid
    COLOR_QUANT_STEP = 32

    def _render_and_show_colored(self, text, rgb_mat):
        """
        randeaza ASCII ul colorat intr un pixmap si
        il trimite la preview pt afisare

        args:
            text: stringul ASCII
            rgb_mat: matricea de culori RGB aliniata la text
        """
        pixmap = render_colored_pixmap(text, rgb_mat, self.preview.mono_font, color_step=self.COLOR_QUANT_STEP)
        self.preview.show_colored_pixmap(pixmap)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image or Video", "",
            "Media (*.jpg *.jpeg *.png *.webp *.mp4 *.avi *.mov *.mkv *.webm)"
        )

        if not path:
            return

        self.stop_video()
        self.image_path = None
        self.video_path = None
        self.preview.clear()
        extension = os.path.splitext(path)[1].lower()
        video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

        if extension in video_extensions:
            self.video_path = path
            self.sidebar.set_video_loaded(True)
            self.sidebar.set_save_enabled(False)

            filename = os.path.basename(path)
            self._status_bar.showMessage(f"Video loaded: {filename}")
            return

        self.image_path = path
        self.sidebar.set_video_loaded(False)
        filename = os.path.basename(path)
        self._status_bar.showMessage(f"Image loaded: {filename}")

    def convert(self, width, do_invert, is_colored):
        """
        punctul de intrare pt conversie, apelat cand utilizatorul apasa
        convert - ruteaza spre start_video() daca avem un video incarcat,
        sau converteste direct imaginea statica prin image.ascii()

        args:
            width: latimea ASCII in caractere
            do_invert: daca True, inverseaza valorile grayscale
            is_colored: daca True, afiseaza rezultatul in mod color
        """
        self.is_colored = is_colored

        if self.video_path:
            self.start_video(width, do_invert, is_colored)
            return

        if not self.image_path:
            QMessageBox.warning(self, "Attention", "Open an image or video first")
            return

        try:
            self._status_bar.showMessage("Processing image...")
            QApplication.processEvents()

            self.ascii_text, self.rgb_mat = image.ascii(self.image_path, new_width=width, do_invert=do_invert)

        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", str(e))
            self._status_bar.showMessage("Conversion Error")
            return

        if is_colored:
            self._render_and_show_colored(self.ascii_text, self.rgb_mat)

        else:
            self.preview.show_text(self.ascii_text)

        self.sidebar.set_save_enabled(True)
        self._status_bar.showMessage("Conversion complete")

    def start_video(self, width, do_invert, is_colored):
        """
        opreste orice VideoWorker anterior si porneste unul nou pt
        video_path ul curent, cu parametrii dati

        args:
            width: latimea ASCII in caractere
            do_invert: daca True, inverseaza valorile grayscale
            is_colored: daca True, afiseaza rezultatul in mod color
        """
        self.stop_video()
        self.sidebar.set_save_enabled(False)
        self.preview.clear()

        self.video_worker = VideoWorker(self.video_path, new_width=width, do_invert=do_invert, colored=is_colored)
        self.video_worker.frame_ready.connect(self.video_frame_ready)
        self.video_worker.finished.connect(self.video_finished)
        self.video_worker.error.connect(self.video_error)

        self.sidebar.set_running(True)
        self._status_bar.showMessage("Playing video...")
        self.video_worker.start()

    def video_frame_ready(self, text, rgb_mat):
        """
        actualizeaza preview ul 
        (color sau BW) si activeaza Save

        args:
            text: stringul ASCII al cadrului curent
            rgb_mat: matricea de culori RGB a cadrului curent
        """
        if self.sender() is not self.video_worker:
            return
        self.ascii_text = text
        self.rgb_mat = rgb_mat

        if self.is_colored:
            self._render_and_show_colored(text, rgb_mat)
        else:
            self.preview.show_text(text)
        self.sidebar.set_save_enabled(True)

    def play_video(self):
        """
        reia un VideoWorker existent daca ruleaza deja, sau porneste
        unul nou, citind parametrii curenti direct din sidebar
        """
        if not self.video_path:
            return

        if self.video_worker is not None:
            if self.video_worker.isRunning():
                self.video_worker.resume()
                self.sidebar.set_running(True)
                self._status_bar.showMessage("Video playing")
                return

        try:
            width = int(self.sidebar.width_input.text())
        except ValueError:
            width = 150

        self.is_colored = self.sidebar.chk_colored.isChecked()
        self.start_video(width, self.sidebar.chk_invert.isChecked(), self.is_colored)

    def pause_video(self):
        if self.video_worker is None:
            return

        self.video_worker.pause()
        self.sidebar.set_running(False)
        self._status_bar.showMessage("Video paused")

    def stop_video(self):
        """
        opreste definitiv VideoWorker ul curent si asteapta sa se termine
        thread ul
        """
        if self.video_worker is None:
            return

        if self.video_worker.isRunning():
            self.video_worker.stop()
            finished_in_time = self.video_worker.wait(2000)
            if not finished_in_time:
                QApplication.processEvents()
                self.video_worker.wait(5000)
        self.video_worker = None
        self.sidebar.set_running(False)

    def video_finished(self):
        if self.sender() is not self.video_worker:
            return
        self.sidebar.set_running(False)
        self._status_bar.showMessage("Video finished")
        self.video_worker = None

    def video_error(self, message):
        if self.sender() is not self.video_worker:
            return
        self._status_bar.showMessage("Video error")

        QMessageBox.critical(self, "Video Error", message)

    def save_image(self):
        """
        salveaza rezultatul curent ca imagine
        PNG/JPEG, folosind image.image() sau image.image_colored()
        """
        if self.video_path:
            self.save_video()
            return

        if not self.ascii_text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "ascii_result.png", "PNG (*.png);;JPEG (*.jpg)")

        if not path:
            return

        try:
            if self.is_colored:
                result_image = image.image_colored(self.ascii_text, self.rgb_mat)
            else:
                result_image = image.image(self.ascii_text, bg_color=(0, 0, 0), text_color=(255, 255, 255))
            result_image.save(path)
            self._status_bar.showMessage(f"Saved successfully: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            
    def closeEvent(self, event):
        """
        opreste orice video care ruleaza inainte de a inchide fereastra
        """
        self.stop_video()
        event.accept()