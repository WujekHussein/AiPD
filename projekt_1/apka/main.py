import sys
import numpy as np
import wave
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSlider,
                             QTabWidget, QCheckBox, QLineEdit)
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from feature_functions import *


class WAVViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sound analysis tool")
        self.setGeometry(100, 100, 900, 500)

        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget()
        self.mainTab = QWidget()
        self.acfTab = QWidget()
        self.tabs.addTab(self.mainTab, "Main functionalities")
        self.tabs.addTab(self.acfTab, "ACF & AMDF")

        self.initMainTab()
        self.initACFTab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def initMainTab(self):
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        plot_layout = QVBoxLayout()
        slider_layout = QVBoxLayout()
        param_layout = QVBoxLayout()

        self.plotWidget = pg.PlotWidget()
        plot_layout.addWidget(self.plotWidget)

        self.infoLabel = QLabel("No file loaded.")
        plot_layout.addWidget(self.infoLabel)

        self.loadButton = QPushButton("Load WAV File")
        self.loadButton.clicked.connect(self.load_wav)
        plot_layout.addWidget(self.loadButton)

        self.playButton = QPushButton("Play Audio")
        self.playButton.clicked.connect(self.play_audio)
        self.playButton.setEnabled(False)
        plot_layout.addWidget(self.playButton)

        # Frame duration slider (ms)
        self.frameDurationLabel = QLabel("Frame Duration: 10 ms")
        self.frameDurationSlider = QSlider(Qt.Orientation.Horizontal)
        self.frameDurationSlider.setRange(10, 100)  # Frame duration in ms
        self.frameDurationSlider.setValue(10)
        self.frameDurationSlider.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self.frameDurationSlider.setTickInterval(10)
        self.frameDurationSlider.valueChanged.connect(self.update_frame_duration)

        # Frame start slider (0 to 1 scale)
        self.frameStartLabel = QLabel("Frame Start: 0.0")
        self.frameStartSlider = QSlider(Qt.Orientation.Horizontal)
        self.frameStartSlider.setRange(0, 100)  # Scaled 0-100 (divide by 100 for actual value)
        self.frameStartSlider.setValue(0)
        self.frameStartSlider.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self.frameStartSlider.setTickInterval(10)
        self.frameStartSlider.valueChanged.connect(self.update_frame_start)

        slider_layout.addWidget(self.frameDurationLabel)
        slider_layout.addWidget(self.frameDurationSlider)
        slider_layout.addWidget(self.frameStartLabel)
        slider_layout.addWidget(self.frameStartSlider)

        self.highlightSilenceCheckbox = QCheckBox("Highlight Silence")
        self.highlightSilenceCheckbox.stateChanged.connect(self.toggle_silence_highlight)
        plot_layout.addWidget(self.highlightSilenceCheckbox)

        self.highlightVoicedCheckbox = QCheckBox("Highlight Voiced Segments")
        self.highlightVoicedCheckbox.stateChanged.connect(self.toggle_voiced_highlight)
        plot_layout.addWidget(self.highlightVoicedCheckbox)

        # Parameter fields (Volume, STE, ZCR, SR, F0)
        self.paramFields = {}
        param_names = ["Volume", "STE", "ZCR", "SR", "F0"]
        for name in param_names:
            label = QLabel(name)
            field = QLineEdit("0.0")
            field.setReadOnly(True)
            param_layout.addWidget(label)
            param_layout.addWidget(field)
            self.paramFields[name] = field

        self.calcButton = QPushButton("Calculate Parameters")
        self.calcButton.clicked.connect(self.calculate_parameters)
        param_layout.addWidget(self.calcButton)

        left_layout.addLayout(plot_layout)
        left_layout.addLayout(slider_layout)
        main_layout.addLayout(left_layout)
        main_layout.addLayout(param_layout)
        self.mainTab.setLayout(main_layout)

        self.frame_region = None
        self.silence_regions = []
        self.audio_data = None
        self.sample_rate = None

        # container = QWidget()
        # container.setLayout(main_layout)
        # self.setCentralWidget(container)

    def initACFTab(self):
        layout = QVBoxLayout()
        self.acfPlot = pg.PlotWidget(title="Autocorrelation Function")
        self.amdfPlot = pg.PlotWidget(title="Average Magnitude Difference Function")
        layout.addWidget(self.acfPlot)
        layout.addWidget(self.amdfPlot)
        self.acfTab.setLayout(layout)

    def update_frame_duration(self):
        value = self.frameDurationSlider.value()
        self.frameDurationLabel.setText(f"Frame Duration: {value} ms")
        self.update_frame_highlight()

    def update_frame_start(self):
        value = self.frameStartSlider.value() / 100
        self.frameStartLabel.setText(f"Frame Start: {value:.2f}")
        self.update_frame_highlight()

    def update_frame_highlight(self):
        if self.frame_region:
            self.plotWidget.removeItem(self.frame_region)

        start_time = (self.frameStartSlider.value() / 100) * self.audio_duration
        end_time = start_time + (self.frameDurationSlider.value() / 1000)

        self.frame_region = pg.LinearRegionItem([start_time, end_time], brush=(255, 0, 0, 50))
        self.plotWidget.addItem(self.frame_region)

    def calculate_parameters(self):
        if self.audio_data is None or self.sample_rate is None:
            return

        start_time = (self.frameStartSlider.value() / 100) * self.audio_duration
        end_time = start_time + (self.frameDurationSlider.value() / 1000)

        start_index = int(start_time * self.sample_rate)
        end_index = int(end_time * self.sample_rate)
        frame_data = self.audio_data[start_index:end_index]

        if len(frame_data) == 0:
            return

        # Placeholder for actual calculations
        f0 = calculate_f0(frame_data, self.sample_rate)
        ste = np.mean(frame_data**2)
        volume = ste ** 0.5
        ZCR = calculate_zcr(frame_data)

        self.paramFields["Volume"].setText(f"{volume:.6f}")
        self.paramFields["STE"].setText(f"{ste:.6f}")
        self.paramFields["ZCR"].setText(f"{ZCR:.6f}")
        self.paramFields["F0"].setText(f"{f0:.6f} [Hz]")
        # for name in self.paramFields:
        #     self.paramFields[name].setText(f"{np.random.uniform(0, 1):.2f}")

    def mark_silent_regions(self):
        for region in self.silence_regions:
            self.plotWidget.removeItem(region)
        self.silence_regions.clear()

        for start_idx, end_idx in self.silent_idx:
            start_time = start_idx / self.sample_rate
            end_time = end_idx / self.sample_rate
            region = pg.LinearRegionItem([start_time, end_time], brush=None, pen=(0, 255, 0))
            self.plotWidget.addItem(region)
            self.silence_regions.append(region)

    def load_wav(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open WAV File", "", "WAV Files (*.wav)")
        if file_path:
            self.plot_wav(file_path)

    def plot_wav(self, file_path):
        with wave.open(file_path, 'rb') as wav_file:
            n_channels = wav_file.getnchannels()
            self.sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            self.audio_duration = n_frames / self.sample_rate
            self.audio_data = np.frombuffer(wav_file.readframes(n_frames), \
                                            dtype=np.int16)
            self.audio_data = (self.audio_data.astype(np.float32) / np.iinfo(np.int16).max)


            if n_channels == 2:
                self.audio_data = self.audio_data[::2]
            self.maxv = calculate_max_vol(self.audio_data)

            time_axis = np.linspace(0, self.audio_duration, num=len(self.audio_data))

            self.plotWidget.clear()
            self.plotWidget.plot(time_axis, self.audio_data, pen='b')

            self.infoLabel.setText(
                f"File: {file_path}\nSample Rate: {self.sample_rate} Hz, Duration: {self.audio_duration:.2f} sec {self.maxv:.2f}")

            self.playButton.setEnabled(True)
            self.update_frame_highlight()
            SR, self.silent_idx, self.voiced_idx, self.unvoiced_idx = calculate_silence_ratio_voiced_unvoiced(self.audio_data)
            self.paramFields["SR"].setText(str(SR))

            self.plot_acf_amdf()

    def plot_acf_amdf(self):
        acf_values = acf(self.audio_data)
        amdf_values = amdf(self.audio_data)

        self.acfPlot.clear()
        self.acfPlot.plot(np.arange(len(acf_values)), acf_values, pen='r')
        self.amdfPlot.clear()
        self.amdfPlot.plot(np.arange(len(amdf_values)), amdf_values, pen='g')

    def toggle_silence_highlight(self):
        if self.highlightSilenceCheckbox.isChecked():
            self.mark_silent_regions()
        else:
            for region in getattr(self, 'silence_regions', []):
                self.plotWidget.removeItem(region)
            self.silence_regions = []

    def toggle_voiced_highlight(self):
        if self.highlightVoicedCheckbox.isChecked():
            self.mark_voiced_regions()
        else:
            for region in getattr(self, 'voiced_regions', []):
                self.plotWidget.removeItem(region)
            self.voiced_regions = []

    def mark_voiced_regions(self):
        self.voiced_regions = []
        for start_idx, end_idx in getattr(self, 'voiced_idx', []):
            start_time = start_idx / self.sample_rate
            end_time = end_idx / self.sample_rate
            region = pg.LinearRegionItem([start_time, end_time], brush=(255, 165, 0, 50))
            self.plotWidget.addItem(region)
            self.voiced_regions.append(region)

    def play_audio(self):
        if self.audio_data is not None and self.sample_rate is not None:
            sd.play(self.audio_data, samplerate=self.sample_rate)
            sd.wait()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WAVViewer()
    window.show()
    sys.exit(app.exec())

