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
    QFrame,
    QGridLayout,
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
from .storage import TranscriptCsvWriter

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
        self._csv = TranscriptCsvWriter()

        self.setWindowTitle("灵枢-录音器")
        self.resize(1180, 780)
        self.setMinimumSize(980, 680)
        window_icon = asset_path("icon-small.svg")
        if window_icon is not None:
            self.setWindowIcon(QIcon(str(window_icon)))

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(24, 28, 24, 24)
        side.setSpacing(16)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        brand_icon = asset_path("icon.svg")
        if brand_icon is not None:
            logo = QLabel()
            logo.setPixmap(QIcon(str(brand_icon)).pixmap(46, 46))
            brand_row.addWidget(logo)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_title = QLabel("灵枢")
        brand_title.setObjectName("brandTitle")
        brand_sub = QLabel("录音器")
        brand_sub.setObjectName("brandSub")
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_sub)
        brand_row.addLayout(brand_text)
        brand_row.addStretch(1)
        side.addLayout(brand_row)
        side.addSpacing(18)

        flow_title = QLabel("工作流")
        flow_title.setObjectName("sideSection")
        side.addWidget(flow_title)
        nav_record = QLabel("录音")
        nav_record.setObjectName("navActive")
        side.addWidget(nav_record)
        side.addSpacing(10)
        nav_hint = QLabel("句尾出字 · 本地留存")
        nav_hint.setObjectName("sideMuted")
        side.addWidget(nav_hint)

        side.addSpacing(18)
        local_title = QLabel("本地")
        local_title.setObjectName("sideSection")
        side.addWidget(local_title)
        local_hint = QLabel("GPU 后端\nCSV 自动保存")
        local_hint.setObjectName("sideMuted")
        side.addWidget(local_hint)
        side.addStretch(1)
        footer = QLabel("本地模型 · 可信内网")
        footer.setObjectName("sideMuted")
        side.addWidget(footer)
        root.addWidget(sidebar)

        main = QWidget()
        main.setObjectName("main")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(40, 28, 40, 28)
        main_layout.setSpacing(16)

        top_row = QHBoxLayout()
        crumbs = QLabel("录音 / 个人听写")
        crumbs.setObjectName("crumb")
        top_row.addWidget(crumbs)
        top_row.addStretch(1)
        top_right = QLabel("灵枢 · 本机")
        top_right.setObjectName("crumb")
        top_row.addWidget(top_right)
        main_layout.addLayout(top_row)

        title = QLabel("录音")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)
        subtitle = QLabel("开始录音，句尾自动出字，并同步写入本地 CSV。")
        subtitle.setObjectName("pageSub")
        main_layout.addWidget(subtitle)

        self.config_card = QFrame()
        self.config_card.setObjectName("card")
        self.config_card.setVisible(False)
        config_card = self.config_card
        form = QGridLayout(config_card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.url = QLineEdit(cfg.url)
        self.url.setMinimumWidth(300)
        self.mode = QComboBox()
        self.mode.addItems(["balanced", "accuracy"])
        self.mode.setCurrentText(cfg.mode)
        self.lang = QComboBox()
        self.lang.addItems(["auto", "zh", "yue", "en"])
        self.lang.setCurrentText(cfg.lang)
        self.device = QComboBox()
        form.addWidget(QLabel("后端"), 0, 0)
        form.addWidget(self.url, 0, 1, 1, 3)
        form.addWidget(QLabel("模式"), 1, 0)
        form.addWidget(self.mode, 1, 1)
        form.addWidget(QLabel("语言"), 1, 2)
        form.addWidget(self.lang, 1, 3)
        form.addWidget(QLabel("麦克风"), 2, 0)
        form.addWidget(self.device, 2, 1, 1, 3)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.record_btn = QPushButton("开始录音")
        self.record_btn.setObjectName("record")
        self.record_btn.setMinimumWidth(132)
        self.record_btn.clicked.connect(self.start_recording)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.status = QLabel("就绪")
        self.status.setObjectName("status")
        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timer")
        self.settings_btn = QPushButton("连接设置")
        self.settings_btn.setObjectName("secondary")
        self.settings_btn.setCheckable(True)
        self.settings_btn.toggled.connect(self.config_card.setVisible)
        controls.addWidget(self.record_btn)
        controls.addWidget(self.stop_btn)
        controls.addSpacing(8)
        controls.addWidget(self.status, 1)
        controls.addWidget(self.timer_label)
        controls.addWidget(self.settings_btn)
        main_layout.addLayout(controls)

        main_layout.addWidget(self.config_card)

        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setTextVisible(False)
        self.level.setFixedHeight(6)
        main_layout.addWidget(self.level)

        self.draft = QLabel("")
        self.draft.setObjectName("draft")
        main_layout.addWidget(self.draft)

        transcript_card = QFrame()
        transcript_card.setObjectName("card")
        transcript_layout = QVBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(20, 18, 20, 18)
        transcript_layout.setSpacing(10)
        transcript_header = QHBoxLayout()
        transcript_title = QLabel("转写内容")
        transcript_title.setObjectName("cardTitle")
        transcript_header.addWidget(transcript_title)
        transcript_header.addStretch(1)
        self.csv_label = QLabel("CSV：未开始")
        self.csv_label.setObjectName("hint")
        self.csv_label.setToolTip("每收到一条 final 会立即写入本地 CSV")
        transcript_header.addWidget(self.csv_label)
        transcript_layout.addLayout(transcript_header)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("转写文字会显示在这里…")
        transcript_layout.addWidget(self.transcript, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.clear_btn = QPushButton("清空文本")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.clicked.connect(self.transcript.clear)
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setObjectName("secondary")
        self.copy_btn.clicked.connect(self._copy)
        bottom.addWidget(self.clear_btn)
        bottom.addWidget(self.copy_btn)
        transcript_layout.addLayout(bottom)
        main_layout.addWidget(transcript_card, 1)
        root.addWidget(main, 1)

        self._refresh_devices()
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
                font-size: 14px;
                color: #0f172a;
            }
            QFrame#sidebar { background: #0b1220; }
            QLabel#brandTitle { color: #f8fafc; font-size: 26px; font-weight: 700; }
            QLabel#brandSub { color: #94a3b8; font-size: 13px; }
            QLabel#sideSection { color: #64748b; font-size: 12px; font-weight: 600; }
            QLabel#navActive {
                background: #2563eb; color: #ffffff;
                border-radius: 10px; padding: 10px 14px; font-weight: 600;
            }
            QLabel#sideMuted { color: #94a3b8; font-size: 12px; }
            QWidget#main { background: #f8fafc; }
            QLabel#crumb { color: #64748b; font-size: 13px; }
            QLabel#pageTitle { color: #0f172a; font-size: 32px; font-weight: 700; }
            QLabel#pageSub { color: #64748b; font-size: 14px; }
            QLabel#cardTitle { color: #0f172a; font-size: 16px; font-weight: 600; }
            QLabel#hint { color: #64748b; font-size: 12px; }
            QLabel#status { color: #475569; }
            QLabel#timer { color: #0f172a; font-size: 15px; font-weight: 600; }
            QLabel#draft { color: #2563eb; }
            QFrame#card {
                background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px;
            }
            QLineEdit, QComboBox {
                background: #ffffff; color: #0f172a;
                border: 1px solid #cbd5e1; border-radius: 8px;
                padding: 8px 10px; min-height: 20px;
            }
            QPushButton {
                border: none; border-radius: 9px;
                padding: 10px 18px; font-weight: 600;
            }
            QPushButton#record { background: #2563eb; color: #ffffff; }
            QPushButton#record:disabled { background: #93c5fd; }
            QPushButton#stop {
                background: #ffffff; color: #334155; border: 1px solid #cbd5e1;
            }
            QPushButton#stop:disabled { color: #94a3b8; border-color: #e2e8f0; }
            QPushButton#secondary {
                background: #ffffff; color: #334155; border: 1px solid #cbd5e1;
            }
            QTextEdit {
                background: #ffffff; color: #0f172a;
                border: 1px solid #e2e8f0; border-radius: 10px;
                padding: 14px; font-size: 15px;
            }
            QProgressBar { background: #e2e8f0; border: none; border-radius: 3px; }
            QProgressBar::chunk { background: #2563eb; border-radius: 3px; }
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

        try:
            csv_path = self._csv.start()
        except OSError as exc:
            QMessageBox.critical(self, "无法保存转写", f"CSV 文件创建失败：{exc}")
            return
        self.csv_label.setText(f"CSV：{csv_path.name}")
        self.csv_label.setToolTip(str(csv_path))

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

        self._csv.close()
        self._timer.stop()
        self.level.setValue(0)
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.url.setEnabled(True)
        self.mode.setEnabled(True)
        self.lang.setEnabled(True)
        self.device.setEnabled(True)
        if self.status.text().startswith(("连接", "录音")):
            if self._csv.path is not None:
                self.status.setText(f"已停止；CSV 已保存：{self._csv.path.name}")
            else:
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
        end_ms = int(event.get("end_ms", start_ms))
        try:
            self._csv.write(start_ms, end_ms, text)
        except OSError as exc:
            self.status.setText(f"CSV 写入失败：{exc}")
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
