from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .audio import PcmFramer, convert_capture, level_percent
from .client import AsrStreamClient, RecorderConfig

ASSET_DIRS = (
    Path(__file__).resolve().parents[2] / "assets",
    Path(getattr(sys, "_MEIPASS", "")) / "assets",
    Path.cwd() / "assets",
)


def asset_path(name: str) -> Path | None:
    for directory in ASSET_DIRS:
        path = directory / name
        if path.exists():
            return path
    return None


class MicCapture(QObject):
    frame_ready = pyqtSignal(bytes)
    level_changed = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, device=None, parent: QObject | None = None):
        super().__init__(parent)
        self._device = device
        self._source: QAudioSource | None = None
        self._io = None
        self._format: QAudioFormat | None = None
        self._framer = PcmFramer()
        self._raw = b""

    def start(self) -> bool:
        device = self._device or QMediaDevices.defaultAudioInput()
        if device is None or device.isNull():
            self.failed.emit("未找到麦克风设备")
            return False

        fmt = QAudioFormat()
        fmt.setSampleRate(16000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()

        self._format = fmt
        self._framer.reset()
        self._raw = b""
        self._source = QAudioSource(device, fmt, self)
        self._io = self._source.start()
        if self._io is None:
            self.failed.emit("无法启动麦克风")
            return False
        self._io.readyRead.connect(self._on_ready)
        return True

    def stop(self) -> None:
        if self._source is not None:
            self._source.stop()
            self._source.deleteLater()
            self._source = None
        self._io = None
        self._raw = b""

    def _on_ready(self) -> None:
        if self._io is None or self._format is None:
            return
        data = bytes(self._io.readAll())
        if not data:
            return

        self._raw += data
        fmt = self._format
        itemsize = {
            QAudioFormat.SampleFormat.Int16: 2,
            QAudioFormat.SampleFormat.Int32: 4,
            QAudioFormat.SampleFormat.Float: 4,
            QAudioFormat.SampleFormat.UInt8: 1,
        }.get(fmt.sampleFormat(), 2)
        block = itemsize * max(1, fmt.channelCount())
        usable = (len(self._raw) // block) * block
        if usable == 0:
            return
        chunk, self._raw = self._raw[:usable], self._raw[usable:]

        try:
            samples = convert_capture(
                chunk,
                fmt.sampleFormat().name,
                fmt.channelCount(),
                fmt.sampleRate(),
            )
        except Exception as exc:
            self.failed.emit(f"音频格式不支持：{exc}")
            self.stop()
            return
        for pcm in self._framer.push(samples):
            self.frame_ready.emit(pcm)
        if samples.size:
            self.level_changed.emit(level_percent(samples))


class ClientThread(QThread):
    event = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, cfg: RecorderConfig, parent: QObject | None = None):
        super().__init__(parent)
        self._client = AsrStreamClient(cfg, self.event.emit)

    def run(self) -> None:
        try:
            asyncio.run(self._client.run())
        except Exception as exc:  # pragma: no cover - runtime failure path
            self.failed.emit(str(exc))

    def send_audio(self, pcm: bytes) -> None:
        self._client.send(pcm)

    def stop(self) -> None:
        self._client.stop()


class RecorderWindow(QMainWindow):
    def __init__(self, cfg: RecorderConfig):
        super().__init__()
        self._cfg = cfg
        self._client: ClientThread | None = None
        self._mic: MicCapture | None = None
        self._started_at = 0.0

        self.setWindowTitle("FireRedASR2S 录音转写")
        self.resize(980, 680)
        window_icon = asset_path("icon-small.svg")
        if window_icon is not None:
            self.setWindowIcon(QIcon(str(window_icon)))

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_icon = asset_path("icon.svg")
        if title_icon is not None:
            logo = QLabel()
            logo.setPixmap(QIcon(str(title_icon)).pixmap(40, 40))
            title_row.addWidget(logo)
        title = QLabel("FireRedASR2S 录音转写")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        subtitle = QLabel("说完停顿约 0.5 秒，整句文字会逐条出现。")
        subtitle.setStyleSheet("color: #64748b;")
        layout.addWidget(subtitle)

        config_row = QHBoxLayout()
        self.url = QLineEdit(cfg.url)
        self.url.setMinimumWidth(320)
        self.mode = QComboBox()
        self.mode.addItems(["balanced", "accuracy"])
        self.mode.setCurrentText(cfg.mode)
        self.lang = QComboBox()
        self.lang.addItems(["auto", "zh", "yue", "en"])
        self.lang.setCurrentText(cfg.lang)
        self.device = QComboBox()
        config_row.addWidget(QLabel("后端"))
        config_row.addWidget(self.url, 1)
        config_row.addWidget(QLabel("模式"))
        config_row.addWidget(self.mode)
        config_row.addWidget(QLabel("语言"))
        config_row.addWidget(self.lang)
        config_row.addWidget(QLabel("麦克风"))
        config_row.addWidget(self.device, 1)
        layout.addLayout(config_row)

        controls = QHBoxLayout()
        self.record_btn = QPushButton("开始录音")
        self.record_btn.setObjectName("record")
        self.record_btn.clicked.connect(self.start_recording)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.status = QLabel("就绪")
        self.timer_label = QLabel("00:00")
        controls.addWidget(self.record_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.status, 1)
        controls.addWidget(self.timer_label)
        layout.addLayout(controls)

        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setTextVisible(False)
        self.level.setFixedHeight(8)
        layout.addWidget(self.level)

        self.draft = QLabel("")
        self.draft.setStyleSheet("color: #2563eb;")
        layout.addWidget(self.draft)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("转写文字会显示在这里…")
        layout.addWidget(self.transcript, 1)

        bottom = QHBoxLayout()
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.transcript.clear)
        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self._copy)
        bottom.addStretch(1)
        bottom.addWidget(self.clear_btn)
        bottom.addWidget(self.copy_btn)
        layout.addLayout(bottom)

        self._refresh_devices()
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { font-size: 14px; }
            QTextEdit {
                background: #0f172a; color: #e2e8f0;
                border: 1px solid #1e293b; border-radius: 10px;
                padding: 12px; font-size: 16px;
            }
            QLineEdit, QComboBox {
                padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 8px;
            }
            QPushButton { padding: 8px 16px; border-radius: 8px; }
            QPushButton#record { background: #dc2626; color: white; font-weight: 600; }
            QPushButton#record:disabled { background: #fca5a5; }
            QProgressBar { background: #e2e8f0; border: none; border-radius: 4px; }
            QProgressBar::chunk { background: #10b981; border-radius: 4px; }
            """
        )

    def _refresh_devices(self) -> None:
        self.device.clear()
        devices = QMediaDevices.audioInputs()
        if not devices:
            self.device.addItem("未检测到麦克风", None)
            return
        for device in devices:
            self.device.addItem(device.description() or "麦克风", device)

    def _selected_device(self):
        return self.device.currentData()

    def start_recording(self) -> None:
        if self._client is not None:
            return

        cfg = RecorderConfig(
            url=self.url.text().strip(),
            mode=self.mode.currentText(),
            lang=self.lang.currentText(),
            output_script=self._cfg.output_script,
        )
        if not cfg.url.startswith(("ws://", "wss://")):
            QMessageBox.warning(self, "地址无效", "后端地址需以 ws:// 或 wss:// 开头")
            return

        self._client = ClientThread(cfg, self)
        self._client.event.connect(self._on_event)
        self._client.failed.connect(self._on_failed)
        self._client.finished.connect(self._on_client_finished)
        self._client.start()

        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.url.setEnabled(False)
        self.mode.setEnabled(False)
        self.lang.setEnabled(False)
        self.device.setEnabled(False)
        self.status.setText("连接中…")

    def _start_mic(self) -> None:
        if self._mic is not None or self._client is None:
            return

        self._mic = MicCapture(self._selected_device(), self)
        self._mic.frame_ready.connect(self._client.send_audio)
        self._mic.level_changed.connect(self.level.setValue)
        self._mic.failed.connect(self._on_failed)
        if not self._mic.start():
            self.stop_recording()
            return

        self._started_at = time.monotonic()
        self._timer.start()
        self.status.setText("录音中")

    def stop_recording(self) -> None:
        if self._mic is not None:
            self._mic.stop()
            self._mic.deleteLater()
            self._mic = None

        if self._client is not None:
            self._client.stop()
            self._client.wait(5000)
            self._client.deleteLater()
            self._client = None

        self._timer.stop()
        self.level.setValue(0)
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.url.setEnabled(True)
        self.mode.setEnabled(True)
        self.lang.setEnabled(True)
        self.device.setEnabled(True)
        if self.status.text().startswith(("连接", "录音")):
            self.status.setText("已停止")

    def _on_event(self, event: dict) -> None:
        kind = event.get("type")
        if kind == "ready":
            self._start_mic()
        elif kind == "final":
            self._append_final(event)
        elif kind == "partial":
            self.draft.setText(f"正在识别：{event.get('text', '')}")
        elif kind == "error":
            self.status.setText(f"错误：{event.get('message', '')}")
            self.stop_recording()
        elif kind == "stopped":
            self.status.setText("已停止")

    def _append_final(self, event: dict) -> None:
        text = event.get("text", "").strip()
        if not text:
            return
        start_ms = int(event.get("start_ms", 0))
        stamp = f"{start_ms // 60000:02d}:{start_ms // 1000 % 60:02d}"
        if self.transcript.toPlainText():
            self.transcript.append("")
        self.transcript.append(f"[{stamp}] {text}")
        self._scroll_to_bottom()
        self.draft.setText("")

    def _scroll_to_bottom(self) -> None:
        self.transcript.moveCursor(QTextCursor.MoveOperation.End)
        self.transcript.ensureCursorVisible()
        scrollbar = self.transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_failed(self, message: str) -> None:
        self.status.setText(f"错误：{message}")
        if self._client is not None or self._mic is not None:
            self.stop_recording()

    def _on_client_finished(self) -> None:
        if self._client is not None:
            self.stop_recording()

    def _tick(self) -> None:
        elapsed = int(time.monotonic() - self._started_at)
        self.timer_label.setText(f"{elapsed // 60:02d}:{elapsed % 60:02d}")

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.transcript.toPlainText())

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop_recording()
        super().closeEvent(event)


def run_gui(cfg: RecorderConfig) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = RecorderWindow(cfg)
    window.show()
    return app.exec()
