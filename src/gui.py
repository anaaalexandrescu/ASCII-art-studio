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
    main application window: connects the sidebar to the preview,
    starts/stops the VideoWorker and calls the functions
    from image.py directly for image conversion
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
        connects all signals emitted by the sidebar to the corresponding methods in MainWindow
        """
        self.sidebar.open_requested.connect(self.open_file)
        self.sidebar.convert_requested.connect(self.convert)
        self.sidebar.play_requested.connect(self.play_video)
        self.sidebar.pause_requested.connect(self.pause_video)
        self.sidebar.stop_requested.connect(self.stop_video)
        self.sidebar.save_requested.connect(self.save_image)

    # how aggressively the color is quantized in the color preview,
    # so we get long runs and fewer drawText calls
    # 1 = exact color 24 = compromise,
    # 32-48 = even faster
    COLOR_QUANT_STEP = 32

    def _render_and_show_colored(self, text, rgb_mat):
        """
        renders the colored ASCII into a pixmap and
        sends it to the preview for display

        args:
            text: the ASCII string
            rgb_mat: the RGB color matrix aligned with the text
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
        entry point for conversion, called when the user presses
        convert - routes to start_video() if a video is loaded,
        or directly converts the static image via image.ascii()

        args:
            width: ASCII width in characters
            do_invert: if True, inverts the grayscale values
            is_colored: if True, displays the result in color mode
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
        stops any previous VideoWorker and starts a new one for the
        current video_path, with the given parameters

        args:
            width: ASCII width in characters
            do_invert: if True, inverts the grayscale values
            is_colored: if True, displays the result in color mode
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
        updates the preview
        (color or BW) and enables Save

        args:
            text: the ASCII string of the current frame
            rgb_mat: the RGB color matrix of the current frame
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
        resumes an existing VideoWorker if it's already running, or starts
        a new one, reading the current parameters directly from the sidebar
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
        permanently stops the current VideoWorker and waits for the
        thread to finish
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
        saves the current result as a
        PNG/JPEG image, using image.image() or image.image_colored()
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
        stops any running video before closing the window
        """
        self.stop_video()
        event.accept()