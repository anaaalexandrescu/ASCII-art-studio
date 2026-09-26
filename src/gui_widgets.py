import time
import cv2
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import (
    QFont,
    QFontDatabase,
    QFontMetrics,
    QPainter,
    QImage,
    QPixmap,
    QColor,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

import src.video as video

STYLE_SHEET = """
QMainWindow {
    background: #0B0D0F;
}

QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #D8DCE2;
}

QWidget#SidebarPanel {
    background: #101215;
    border-right: 1px solid #25282D;
}

QLabel#AppTitle {
    color: #F1F3F5;
    font-size: 19px;
    font-weight: 700;
}

QLabel#AppSubtitle {
    color: #737981;
    font-size: 11px;
}

QLabel#SectionLabel {
    color: #737981;
    font-size: 10px;
    font-weight: 700;
}

QPushButton {
    background: #171A1F;
    color: #DDE1E6;
    border: 1px solid #2A2E34;
    border-radius: 3px;
    padding: 9px 12px;
    min-height: 20px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background: #1D2127;
    border-color: #3A4048;
}

QPushButton:pressed {
    background: #13161A;
}

QPushButton:disabled {
    background: #131518;
    color: #50565E;
    border-color: #202328;
}

QPushButton#PrimaryButton {
    background: #E7E9EC;
    color: #101214;
    border: 1px solid #E7E9EC;
    border-radius: 3px;
    font-weight: 700;
}

QPushButton#PrimaryButton:hover {
    background: #FFFFFF;
    border-color: #FFFFFF;
}

QPushButton#PrimaryButton:pressed {
    background: #D2D5D9;
}

QPushButton#OpenButton {
    background: #171A1F;
    border-color: #30353C;
    border-radius: 3px;
}

QPushButton#TransportButton {
    min-height: 18px;
    padding: 8px 10px;
    border-radius: 3px;
}

QLineEdit {
    background: #0D0F12;
    border: 1px solid #292D33;
    border-radius: 3px;
    padding: 8px 10px;
    color: #E7E9EC;
    font-weight: 600;
}

QLineEdit:focus {
    border-color: #555C65;
}

QCheckBox {
    color: #D1D5DA;
    font-weight: 600;
    spacing: 8px;
    padding: 3px 0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3A4048;
    background: #0D0F12;
    border-radius: 2px;
}

QCheckBox::indicator:hover {
    border-color: #5A616A;
}

QCheckBox::indicator:checked {
    background: #E7E9EC;
    border-color: #E7E9EC;
}

QScrollArea#AsciiPreviewArea {
    background: #050608;
    border: 1px solid #22262B;
    border-radius: 3px;
}

QLabel#MonoPreviewLabel {
    background: #050608;
    color: #E5E8EB;
}

QScrollArea#ColorPreviewArea {
    background: #050608;
    border: 1px solid #22262B;
    border-radius: 3px;
}

QLabel#ColorPreviewLabel {
    background: #000000;
}

QScrollBar:vertical {
    background: #0B0D0F;
    width: 10px;
    border: none;
}

QScrollBar:horizontal {
    background: #0B0D0F;
    height: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #343940;
    min-height: 30px;
    border-radius: 2px;
}

QScrollBar::handle:horizontal {
    background: #343940;
    min-width: 30px;
    border-radius: 2px;
}

QScrollBar::handle:hover {
    background: #454B53;
}

QScrollBar::add-page,
QScrollBar::sub-page {
    background: transparent;
}

QScrollBar::add-line,
QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}

QStatusBar {
    background: #101215;
    color: #6F767F;
    font-size: 11px;
    border-top: 1px solid #25282D;
}
"""

def _quantize_channel(value, step):
    """
    rotunjeste un singur canal de culoare (R, G sau B) la cel mai apropiat
    multiplu de step, cu clamping la 255

    args:
        value: valoarea canalului 0-255
        step: pasul de cuantizare

    returns:
        valoarea cuantizata, tot in 0-255
    """
    half = step // 2
    bucket = (value + half) // step
    quantized = bucket * step
    if quantized > 255:
        quantized = 255
    return quantized

def _quantize_color(color, step):
    """
    aplica _quantize_channel pe toate cele 3 canale ale unei culori RGB

    args:
        color: tuplu (r, g, b)
        step: pasul de cuantizare, daca e <= 1 culoarea e returnata neschimbata

    returns:
        tuplu (r, g, b) cuantizat
    """
    if step <= 1:
        return color
    r, g, b = color
    return (_quantize_channel(r, step), _quantize_channel(g, step), _quantize_channel(b, step))

def render_mono_pixmap(text, font):
    """
    randeaza ASCII bw pe acelasi canvas/metrici ca preview ul rgb
    QPixmap + QPainter si pentru bw, astfel incat dimensiunile
    caracterelor sa fie identice si scroll ul sa fie gestionat de QScrollArea
    """
    lines = text.split("\n")
    metrics = QFontMetrics(font)

    char_w = max(1, metrics.horizontalAdvance("W"))
    char_h = max(1, metrics.height())
    max_line = max((len(line) for line in lines), default=0)

    image = QImage(
        max(1, char_w * max_line),
        max(1, char_h * len(lines)),
        QImage.Format.Format_RGB32,
    )
    image.fill(QColor(5, 6, 8))

    painter = QPainter(image)
    painter.setFont(font)
    painter.setPen(QColor(238, 241, 245))
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)

    for row_index, line in enumerate(lines):
        if not line:
            continue
        y = row_index * char_h
        painter.drawText(
            0,
            y + metrics.ascent(),
            char_w * len(line),
            metrics.height(),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            line,
        )

    painter.end()
    return QPixmap.fromImage(image)

def render_colored_pixmap(text, rgb_mat, font, color_step=24):
    """
    deseneaza ASCII ul colorat direct pe un QImage folosind
    QPainter

    gruparea characterelorconsecutive cu aceeasi culoare 
    intr un singur drawText ajuta pe culori plate/uniforme,
    dar pe un cadru foto/video real aproape fiecare pixel are 
    o culoare usor diferita de vecinul lui;

    color_step cuantizeaza fiecare canal R G B la cel mai
    apropiat multiplu de `color_step`
    """
    lines = text.split("\n")
    metrics = QFontMetrics(font)

    char_w = metrics.horizontalAdvance("W")
    if char_w <= 0:
        char_w = 6

    char_h = metrics.height()
    if char_h <= 0:
        char_h = 10

    max_line = max((len(line) for line in lines), default=0)
    img_w = max(1, char_w * max_line)
    img_h = max(1, char_h * len(lines))

    image = QImage(img_w, img_h, QImage.Format.Format_RGB32)
    image.fill(QColor(0, 0, 0))
    painter = QPainter(image)
    painter.setFont(font)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)

    for row_index, line in enumerate(lines):
        y = row_index * char_h
        row_colors = rgb_mat[row_index] if row_index < len(rgb_mat) else []
        run_color = None
        run_start_col = 0
        run_chars = []

        def flush_run():
            if not run_chars:
                return
            x = run_start_col * char_w
            r, g, b = run_color
            painter.setPen(QColor(r, g, b))
            painter.drawText(
                x, y + metrics.ascent(), char_w * len(run_chars), metrics.height(),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "".join(run_chars)
            )

        for col_index, ch in enumerate(line):
            if col_index < len(row_colors):
                color = _quantize_color(row_colors[col_index], color_step)
            else:
                color = (255, 255, 255)

            if color == run_color:
                run_chars.append(ch)
            else:
                flush_run()
                run_color = color
                run_start_col = col_index
                run_chars = [ch]
        flush_run()
    painter.end()
    return QPixmap.fromImage(image)

# video

class VideoWorker(QThread):
    """
    thread separat care citeste si converteste un fisier video in ASCII,
    cadru cu cadru, ca sa nu blocheze interfata grafica

    emite un semnal frame_ready(text, rgb_mat) pt fiecare cadru procesat,
    finished cand videoclipul s-a terminat sau a fost oprit, si error daca
    apare o problema la deschidere sau la procesare
    """
    frame_ready = pyqtSignal(str, object)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, path, new_width=150, do_invert=False, colored=False):
        super().__init__()

        self.path = path
        self.new_width = new_width
        self.do_invert = do_invert
        self.running = True
        self.paused = False

    def run(self):
        """
        bucla principala a thread ului: citeste cadre din video, le converteste
        in ASCII si emite frame_ready pt fiecare

        playback ul e sincronizat cu ceasul real al videoclipului,
        nu doar cu FPS ul nominal: daca procesarea ASCII e prea lenta si ramanem
        in urma, sarim peste cadrele acumulate cu cap.grab() ca sa nu se ajunga 
        la a randa tot videoclipul in slow motion
        """
        cap = cv2.VideoCapture(self.path)

        if not cap.isOpened():
            self.error.emit(f"Could not open video: {self.path}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        frame_interval = 1.0 / fps
        playback_start = time.perf_counter()
        next_frame_time = 0.0

        while self.running:
            if self.paused:
                playback_start = time.perf_counter() - next_frame_time
                self.msleep(10)
                continue
            ret, frame = cap.read()
            if not ret:
                break

            try:
                text, rgb_mat = video.frame_to_ascii(frame, new_width=self.new_width, do_invert=self.do_invert)
                self.frame_ready.emit(text, rgb_mat)
            except Exception as e:
                self.error.emit(str(e))
                break

            next_frame_time += frame_interval
            now = time.perf_counter() - playback_start
            lag = now - next_frame_time

            if lag < 0:
                self.msleep(max(1, int((-lag) * 1000)))
            elif lag > frame_interval:
                frames_to_skip = min(int(lag / frame_interval), 8)
                for _ in range(frames_to_skip):
                    if not cap.grab():
                        self.running = False
                        break
                    next_frame_time += frame_interval

        cap.release()
        self.finished.emit()

    def pause(self):
        """pune playback ul pe pauza, fara sa opreasca thread ul"""
        self.paused = True

    def resume(self):
        """reia playback ul dupa o pauza"""
        self.paused = False

    def stop(self):
        """opreste definitiv thread ul, iese din bucla din run()"""
        self.running = False
        self.paused = False

# sidebar

class SidebarPanel(QWidget):
    """
    panoul din stanga cu toate controalele
    """
    open_requested = pyqtSignal()
    convert_requested = pyqtSignal(int, bool, bool)
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    save_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("SidebarPanel")
        self.setMinimumWidth(250)
        self.setMaximumWidth(270)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("ASCII ART STUDIO")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        layout.addSpacing(10)

        section_input = QLabel("MEDIA")
        section_input.setObjectName("SectionLabel")
        layout.addWidget(section_input)

        self.open_button = QPushButton("OPEN IMAGE/VIDEO")
        self.open_button.setObjectName("OpenButton")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.clicked.connect(self.open_requested.emit)
        layout.addWidget(self.open_button)

        width_container = QVBoxLayout()
        width_container.setSpacing(4)

        lbl_width = QLabel("ASCII WIDTH")
        width_container.addWidget(lbl_width)

        self.width_input = QLineEdit("200")
        self.width_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        width_container.addWidget(self.width_input)
        layout.addLayout(width_container)

        self.chk_colored = QCheckBox("Color Mode (RGB)")
        layout.addWidget(self.chk_colored)

        self.chk_invert = QCheckBox("Invert Colors")
        layout.addWidget(self.chk_invert)

        layout.addSpacing(8)

        section_render = QLabel("RENDER")
        section_render.setObjectName("SectionLabel")
        layout.addWidget(section_render)

        self.convert_button = QPushButton("CONVERT")
        self.convert_button.setObjectName("PrimaryButton")
        self.convert_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_button.clicked.connect(self._on_convert_clicked)
        layout.addWidget(self.convert_button)

        layout.addSpacing(8)

        section_video = QLabel("PLAYBACK")
        section_video.setObjectName("SectionLabel")
        layout.addWidget(section_video)

        self.play_button = QPushButton("PLAY")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.setObjectName("TransportButton")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_requested.emit)
        layout.addWidget(self.play_button)

        self.pause_button = QPushButton("PAUSE")
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_button.setObjectName("TransportButton")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_requested.emit)
        layout.addWidget(self.pause_button)

        self.stop_button = QPushButton("STOP")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.setObjectName("TransportButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        layout.addWidget(self.stop_button)

        self.save_button = QPushButton("SAVE")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.setObjectName("TransportButton")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_requested.emit)
        layout.addWidget(self.save_button)

        layout.addStretch()

    def _on_convert_clicked(self):
        """
        citeste valorile curente din UI (latime, invert, color), le valideaza
        si emite convert_requested cu ele
        """
        try:
            width = int(self.width_input.text())
            if width < 20:
                width = 20
            if width > 500:
                width = 500
        except ValueError:
            width = 150
        do_invert = self.chk_invert.isChecked()
        is_colored = self.chk_colored.isChecked()
        self.convert_requested.emit(width, do_invert, is_colored)

    def set_video_loaded(self, enabled):
        """
        activeaza/ dezactiveaza butoanele play si stop
        """
        self.play_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)

    def set_running(self, running):
        """
        comuta starea butoanelor play/pause
        """
        self.pause_button.setEnabled(running)
        self.play_button.setEnabled(not running)

    def set_save_enabled(self, enabled):
        """
        activeaza/dezactiveaza butonul save, dupa ce exista un rezultat de salvat
        """
        self.save_button.setEnabled(enabled)

class PreviewPanel(QWidget):
    """
    preview pentru ambele moduri:
      - bw: QPixmap + QScrollArea
      - rgb: QPixmap + QScrollArea

    ambele sunt randate cu aceleasi QFontMetrics, deci un caracter
    are aceeasi latime si aceeasi inaltime in ambele moduri
    """
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        self.stack = QStackedLayout()
        layout.addLayout(self.stack)

        try:
            font = QFontDatabase.systemFont(
                QFontDatabase.SystemFont.FixedFont
            )
        except Exception:
            font = QFont("Monospace")
            font.setStyleHint(QFont.StyleHint.Monospace)

        font.setPointSize(7)
        self.mono_font = font

        self.text_label = QLabel()
        self.text_label.setObjectName("MonoPreviewLabel")
        self.text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.text_label.setFont(font)
        self.text_label.setContentsMargins(0, 0, 0, 0)

        self.text_scroll = QScrollArea()
        self.text_scroll.setObjectName("AsciiPreviewArea")
        self.text_scroll.setWidget(self.text_label)
        self.text_scroll.setWidgetResizable(False)
        self.text_scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.text_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.text_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.stack.addWidget(self.text_scroll)

        self.color_label = QLabel()
        self.color_label.setObjectName("ColorPreviewLabel")
        self.color_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self.color_scroll = QScrollArea()
        self.color_scroll.setObjectName("ColorPreviewArea")
        self.color_scroll.setWidget(self.color_label)
        self.color_scroll.setWidgetResizable(False)
        self.color_scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.color_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.color_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.stack.addWidget(self.color_scroll)
        self.stack.setCurrentWidget(self.text_scroll)

    def _restore_scroll(self, area, horizontal, vertical):
        area.horizontalScrollBar().setValue(horizontal)
        area.verticalScrollBar().setValue(vertical)

    def show_text(self, text):
        horizontal = self.text_scroll.horizontalScrollBar().value()
        vertical = self.text_scroll.verticalScrollBar().value()
        pixmap = render_mono_pixmap(text, self.mono_font)

        self.text_label.setPixmap(pixmap)
        self.text_label.resize(pixmap.size())
        self.stack.setCurrentWidget(self.text_scroll)
        self._restore_scroll(self.text_scroll, horizontal, vertical)

    def show_colored_pixmap(self, pixmap):
        horizontal = self.color_scroll.horizontalScrollBar().value()
        vertical = self.color_scroll.verticalScrollBar().value()

        self.color_label.setPixmap(pixmap)
        self.color_label.resize(pixmap.size())

        self.stack.setCurrentWidget(self.color_scroll)
        self._restore_scroll(self.color_scroll, horizontal, vertical)

    def clear(self):
        self.text_label.clear()
        self.color_label.clear()