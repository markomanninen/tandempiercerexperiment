#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Native python modules including multiprocessing utilities
# Also numpy, PyQT4-6, and pyqtgraph are required
# Later picoscope2000a streaming library is loaded
# which requires picosdk installed from picoscope as well as
# python wrappers: picosdk-python-wrappers
import os, types, pyqtgraph as pg, numpy as np
from datetime import datetime
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pyqtgraph.graphicsItems.LegendItem import ItemSample
#from RangeSlider import QRangeSlider
from time import strftime, time as tm
#from operator import add
from datetime import timedelta
from collections import deque
from . functions import baseline_correction_and_limit, \
                        raising_edges_for_raw_pulses, \
                        raising_edges_for_square_pulses
from pandas import Series
from scipy.signal import find_peaks

# To prevent logaritmic scale error in spectrum plot.
np.seterr(divide = 'ignore')

fft = np.fft.fft

VOLTAGE_RANGES = {
    #'10MV' : 0.01,
    #'20MV' : 0.02,
    #'50MV' : 0.05,
    #'100MV': 0.1,
    #'200MV': 0.2,
    #'500MV': 0.5,
    '1V'   : 1,
    '2V'   : 2,
    '5V'   : 5,
    '10V'  : 10,
    '20V'  : 12, # 12V is max in Ortec SCA module
    #'50V'  : 50
}

CHANNELS = {
    'A': 'Channel A (SCA C)',
    'B': 'Channel B (SCA D)',
    'C': 'Channel C',
    'D': 'Channel D',
    'E': 'Channels A & B'
}

UNIT_RANGES = {
    'NS' : 0.000000001,
    'US' : 0.000001
}

# GUI window main menu
def add_menu(qtapplication):

    menubar = QtGui.QMenuBar(qtapplication)
    qtapplication.mainbox.layout().addWidget(menubar)

    # EXPERIMENT MENU
    menuSettings = menubar.addMenu("Experiment")
    measurement1Action = menuSettings.addAction("Control panel")
    measurement1Action.triggered.connect(qtapplication.results)
    measurement1Action.setShortcut('Ctrl+1')

    #menuSettings.addSeparator()
    # TODO: Do we need a collected view of the measurement variables,
    # for example pop up window with a table showing all measurement and final data?
    # Link to the csv files?

    # DATA MANU
    menuData = menubar.addMenu("Data")
    # Start saving data to the csv files.
    startAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Start saving', qtapplication)
    menuData.addAction(startAction)
    startAction.triggered.connect(qtapplication.start)
    startAction.setShortcut('Ctrl+S')
    # Stop saving data.
    stopAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Stop saving', qtapplication)
    menuData.addAction(stopAction)
    stopAction.triggered.connect(qtapplication.stop)
    stopAction.setShortcut('Ctrl+D')

    menuData.addSeparator()

    # Set projects folder

    # Open playback file
    # At the moment playback functionality is available only if
    # the source file is provided as a console argument.
    if qtapplication.playback_file != '':
        playbackAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Open playback file', qtapplication)
        menuData.addAction(playbackAction)
        playbackAction.triggered.connect(qtapplication.open_playback_file)
        playbackAction.setShortcut('Ctrl+B')

        menuData.addSeparator()


    # Show signals window.
    signalsAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Show signals', qtapplication)
    menuData.addAction(signalsAction)
    signalsAction.triggered.connect(qtapplication.signals)
    signalsAction.setShortcut('Ctrl+G')

    # Show settings window.
    settingsAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Show settings', qtapplication)
    menuData.addAction(settingsAction)
    settingsAction.triggered.connect(qtapplication.settings)
    settingsAction.setShortcut('Ctrl+E')

    # RUN MENU
    menuRun = menubar.addMenu("Run")
    # Pause GUI.
    pauseAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Pause', qtapplication)
    menuRun.addAction(pauseAction)
    pauseAction.triggered.connect(qtapplication.pause)
    pauseAction.setShortcut('Ctrl+P')
    # Resume GUI.
    resumeAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Resume', qtapplication)
    menuRun.addAction(resumeAction)
    resumeAction.triggered.connect(qtapplication.resume)
    resumeAction.setShortcut('Ctrl+R')

    # TODO: Do we need clear graphs menu?

    # QUIT MENU
    menuQuit = menubar.addMenu("Quit")
    quitAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Quit', qtapplication)
    menuQuit.addAction(quitAction)
    quitAction.triggered.connect(qtapplication.quit)
    quitAction.setShortcut('Ctrl+Q')


# GUI dial for bin counts
def add_bin_dial(qtapp, min_value = 16, max_value = 256, default_value = 64):

    dial = QtGui.QDial()
    dial.setMinimum(min_value)
    dial.setMaximum(max_value)
    dial.setValue(default_value)

    # creating a label
    label = QtGui.QLabel("Bins : " + str(default_value), qtapp)

    # setting geometry to the label
    label.setGeometry(220, 125, 200, 60)
    label.setAlignment(QtCore.Qt.AlignCenter)

    # making label multiline
    label.setWordWrap(True)

    def value_changed():
        qtapp.set_bin_count(dial.value())
        # setting text to the label
        label.setText("Bins : " + str(dial.value()))

    dial.valueChanged.connect(value_changed)
    qtapp.add_widget(dial)
    qtapp.add_widget(label)



# GUI range slider for < full, full and > full pulse limitter
def add_range_slider(qtapp, a, b):

    slider = QRangeSlider()
    slider.setRange(a, b)
    slider.setBackgroundStyle('background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #222, stop:1 #333);')
    slider.handle.setStyleSheet('background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282, stop:1 #393);')

    def value_changed():
        qtapp.set_discriminators(slider.getRange())

    slider.startValueChanged.connect(value_changed)
    slider.endValueChanged.connect(value_changed)
    qtapp.add_widget(slider)

class Settings(QtWidgets.QDialog):

    def __init__(self, app, *args):

        self.app = app

        QtWidgets.QDialog.__init__(self, *args)

        self.setWindowTitle("Tandem Piercer Experiment - Settings")

        self.formGroupBox = QtWidgets.QGroupBox("Application")
        layout = QtWidgets.QFormLayout()

        self.application_settings = {
            'experiment_name': QtWidgets.QLineEdit(text = self.app.experiment_name),
            'time_window': QtWidgets.QLineEdit(text = str(self.app.time_window)),
            'spectrum_time_window': QtWidgets.QLineEdit(text = str(self.app.spectrum_time_window)),
            'spectrum_queue_size': QtWidgets.QLineEdit(text = str(self.app.spectrum_queue_size)),
            'spectrum_low_limit_a': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[0])),
            'spectrum_low_limit_b': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[1])),
            'spectrum_low_limit_c': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[2])),
            'spectrum_low_limit_d': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[3])),
            'spectrum_high_limit_a': QtWidgets.QLineEdit(text = str(self.app.spectrum_high_limits[0])),
            'spectrum_high_limit_b': QtWidgets.QLineEdit(text = str(self.app.spectrum_high_limits[1])),
            'spectrum_high_limit_c': QtWidgets.QLineEdit(text = str(self.app.spectrum_high_limits[2])),
            'spectrum_high_limit_d': QtWidgets.QLineEdit(text = str(self.app.spectrum_high_limits[3]))
        }

        layout.addRow(QtWidgets.QLabel("Experiment name:"), self.application_settings['experiment_name'])
        layout.addRow(QtWidgets.QLabel("Time histogram width:"), self.application_settings['time_window'])
        layout.addRow(QtWidgets.QLabel("Spectrum range:"), self.application_settings['spectrum_time_window'])
        layout.addRow(QtWidgets.QLabel("Spectrum queue size:"), self.application_settings['spectrum_queue_size'])

        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (A):"), self.application_settings['spectrum_low_limit_a'])
        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (B):"), self.application_settings['spectrum_low_limit_b'])
        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (C):"), self.application_settings['spectrum_low_limit_c'])
        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (D):"), self.application_settings['spectrum_low_limit_d'])

        layout.addRow(QtWidgets.QLabel("Spectrum high level limit (A):"), self.application_settings['spectrum_high_limit_a'])
        layout.addRow(QtWidgets.QLabel("Spectrum high level limit (B):"), self.application_settings['spectrum_high_limit_b'])
        layout.addRow(QtWidgets.QLabel("Spectrum high level limit (C):"), self.application_settings['spectrum_high_limit_c'])
        layout.addRow(QtWidgets.QLabel("Spectrum high level limit (D):"), self.application_settings['spectrum_high_limit_d'])

        channels = list(CHANNELS.keys())

        for i, channel in enumerate(self.app.spectrum_channels):
            spectrum_channel = QtWidgets.QComboBox()
            spectrum_channel.addItems(channels)
            spectrum_channel.setCurrentIndex(channels.index(self.app.spectrum_channels[i]))
            self.application_settings['spectrum_channel_%s' % str(i+1)] = spectrum_channel
            layout.addRow(QtWidgets.QLabel("Spectrum channel %s" % str(i+1)), spectrum_channel)

        self.formGroupBox.setLayout(layout)

        if self.app.has_picoscope:

            self.original_picoscope_settings = self.app.settings_acquire_value['value']['picoscope']

            voltages = list(VOLTAGE_RANGES.keys())

            voltage_range1 = QtWidgets.QComboBox()
            voltage_range1.addItems(voltages)
            voltage_range1.setCurrentIndex(voltages.index(str(self.original_picoscope_settings['voltage_range'][0])))

            voltage_range2 = QtWidgets.QComboBox()
            voltage_range2.addItems(voltages)
            voltage_range2.setCurrentIndex(voltages.index(str(self.original_picoscope_settings['voltage_range'][1])))

            voltage_range3 = QtWidgets.QComboBox()
            voltage_range3.addItems(voltages)
            voltage_range3.setCurrentIndex(voltages.index(str(self.original_picoscope_settings['voltage_range'][2])))

            voltage_range4 = QtWidgets.QComboBox()
            voltage_range4.addItems(voltages)
            voltage_range4.setCurrentIndex(voltages.index(str(self.original_picoscope_settings['voltage_range'][3])))

            self.picoscope_settings = {
                'sleep_time': QtWidgets.QLineEdit(text = str(self.original_picoscope_settings['sleep_time'])),
                'voltage_range': (voltage_range1, voltage_range2, voltage_range3, voltage_range4)
            }
            self.picoscopeGroupBox = QtWidgets.QGroupBox("Picoscope")
            layout = QtWidgets.QFormLayout()

            if self.app.picoscope_mode == 'stream':

                units = list(UNIT_RANGES.keys())
                unit_range = QtWidgets.QComboBox()
                unit_range.addItems(units)
                unit_range.setCurrentIndex(units.index(str(self.original_picoscope_settings['units'])))

                self.picoscope_settings = {
                    'sleep_time': QtWidgets.QLineEdit(text = str(self.original_picoscope_settings['sleep_time'])),
                    'interval': QtWidgets.QLineEdit(text = str(self.original_picoscope_settings['interval'])),
                    'units': unit_range,
                    'buffer_size': QtWidgets.QLineEdit(text = str(self.original_picoscope_settings['buffer_size'])),
                    'buffer_count': QtWidgets.QLineEdit(text = str(self.original_picoscope_settings['buffer_count'])),
                    'voltage_range': (voltage_range1, voltage_range2, voltage_range3, voltage_range4)
                }
                layout.addRow(QtWidgets.QLabel("Interval:"), self.picoscope_settings['interval'])
                layout.addRow(QtWidgets.QLabel("Units:"), self.picoscope_settings['units'])
                layout.addRow(QtWidgets.QLabel("Buffer size:"), self.picoscope_settings['buffer_size'])
                layout.addRow(QtWidgets.QLabel("Buffer count:"), self.picoscope_settings['buffer_count'])

            # TODO: block mode simple and anvanced trigger settings
            elif self.app.picoscope_mode == 'block':
                pass

            layout.addRow(QtWidgets.QLabel("Sleep time:"), self.picoscope_settings['sleep_time'])
            layout.addRow(QtWidgets.QLabel("Voltage range A:"), self.picoscope_settings['voltage_range'][0])
            layout.addRow(QtWidgets.QLabel("Voltage range B:"), self.picoscope_settings['voltage_range'][1])
            layout.addRow(QtWidgets.QLabel("Voltage range C:"), self.picoscope_settings['voltage_range'][2])
            layout.addRow(QtWidgets.QLabel("Voltage range D:"), self.picoscope_settings['voltage_range'][3])
            self.picoscopeGroupBox.setLayout(layout)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self._accept)
        buttonBox.rejected.connect(self.reject)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(self.formGroupBox)
        if self.app.has_picoscope:
            mainLayout.addWidget(self.picoscopeGroupBox)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)

    def _accept(self):

        # Application settings
        self.app.experiment_name = int(self.application_settings['experiment_name'].text())
        self.app.time_window = int(self.application_settings['time_window'].text())
        self.app.spectrum_time_window = int(self.application_settings['spectrum_time_window'].text())

        self.app.spectrum_low_limits = [
            int(self.application_settings['spectrum_low_limit_a'].text()),
            int(self.application_settings['spectrum_low_limit_b'].text()),
            int(self.application_settings['spectrum_low_limit_c'].text()),
            int(self.application_settings['spectrum_low_limit_d'].text())
        ]

        self.app.spectrum_high_limits = [
            int(self.application_settings['spectrum_high_limit_a'].text()),
            int(self.application_settings['spectrum_high_limit_b'].text()),
            int(self.application_settings['spectrum_high_limit_c'].text()),
            int(self.application_settings['spectrum_high_limit_d'].text())
        ]

        self.app.spectrum_channels = (
            self.application_settings['spectrum_channel_1'].currentText(),
            self.application_settings['spectrum_channel_2'].currentText()
        )

        self.app.init_spectrum_histograms(int(self.application_settings['spectrum_queue_size'].text()))

        # Picoscope settings, after changing the values picoscope needs to be tarted over
        if self.app.has_picoscope:

            settings = self.app.settings_acquire_value['value']['picoscope']

            spectrum_low_limits = self.app.settings_acquire_value['value']['spectrum_low_limits']
            spectrum_high_limits = self.app.settings_acquire_value['value']['spectrum_high_limits']

            settings['sleep_time'] = float(self.picoscope_settings['sleep_time'].text())

            if self.app.picoscope_mode == 'stream':
                settings['interval'] = int(self.picoscope_settings['interval'].text())
                settings['units'] = self.picoscope_settings['units'].currentText()
                settings['buffer_size'] = int(self.picoscope_settings['buffer_size'].text())
                settings['buffer_count'] = int(self.picoscope_settings['buffer_count'].text())

            settings['voltage_range'] = (
                self.picoscope_settings['voltage_range'][0].currentText(),
                self.picoscope_settings['voltage_range'][1].currentText(),
                self.picoscope_settings['voltage_range'][2].currentText(),
                self.picoscope_settings['voltage_range'][3].currentText()
            )

            if self.app.spectrum_low_limits != spectrum_low_limits or \
               self.app.spectrum_high_limits != spectrum_high_limits or \
               settings['sleep_time'] != self.original_picoscope_settings['sleep_time'] or \
               (self.app.picoscope_mode == 'stream' and (
               settings['interval'] != self.original_picoscope_settings['interval'] or \
               settings['units'] != self.original_picoscope_settings['units'] or \
               settings['buffer_size'] != self.original_picoscope_settings['buffer_size'] or \
               settings['buffer_count'] != self.original_picoscope_settings['buffer_count'])) or \
               settings['voltage_range'] != self.original_picoscope_settings['voltage_range']:

                self.original_picoscope_settings['voltage_range'] = settings['voltage_range']
                settings_acquire_value = self.app.settings_acquire_value['value']
                settings_acquire_value['spectrum_low_limits'] = self.app.spectrum_low_limits
                settings_acquire_value['spectrum_high_limits'] = self.app.spectrum_high_limits
                settings_acquire_value['picoscope'] = settings
                self.app.settings_acquire_value['value'] = settings_acquire_value
                self.app.settings_acquire_event.set()
                self.app.set_signal_region_adc_a()
                self.app.set_signal_region_adc_b()
                self.app.init_spectrum_histograms()
                self.app.init_pulse_rate_graph()

        self.accept()


class Signals(QtGui.QWidget):

    def __init__(self, app, *args):

        self.app = app

        QtGui.QWidget.__init__(self, *args)

        self.setWindowTitle("Tandem Piercer Experiment - Triggered Signals from Detectors")

        self.layout = QtGui.QGridLayout()

        plot_labels = {'left': 'Volts', 'bottom': 'Time (ns)'}

        self.curves = [
            {'title': 'Channel A (SCA C)', 'curves': [], 'peaks': [], 'position': [0, 0], 'plot': None, 'pen': pg.mkPen('r', width=1), 'max': {'index': 0, 'value': 0}, 'labels': plot_labels},
            {'title': 'Channel B (SCA D)', 'curves': [], 'peaks': [], 'position': [0, 1], 'plot': None, 'pen': pg.mkPen('g', width=1), 'max': {'index': 0, 'value': 0}, 'labels': plot_labels},
            {'title': 'Channel C', 'curves': [], 'peaks': [], 'position': [1, 0], 'plot': None, 'pen': pg.mkPen('r', width=1), 'max': {'index': 0, 'value': 0}, 'labels': plot_labels},
            {'title': 'Channel D', 'curves': [], 'peaks': [], 'position': [1, 1], 'plot': None, 'pen': pg.mkPen('g', width=1), 'max': {'index': 0, 'value': 0}, 'labels': plot_labels},
        ]

        self.max_curves_in_plot = 25

        self.filter_coincidences = True

        # Add curves deque and plot widget instance to the layout.
        for i, data in enumerate(self.curves):
            data['curves'] = []
            # TODO: could not find out the way to position title little bit lower.
            data['plot'] = pg.PlotWidget(title = data['title'])
            data['plot'].setDownsampling(auto=True, mode='peak')
            voltage_range = VOLTAGE_RANGES[self.app.settings_acquire_value['value']['picoscope']['voltage_range'][i]]
            data['plot'].setYRange(-voltage_range, voltage_range, padding=0)
            data['plot'].showGrid(x=True, y=True, alpha=.5)
            for k, v in data['labels'].items():
                data['plot'].setLabel(k, v)
            self.layout.addWidget(data['plot'], *data['position'])

        self.buffer_selection = pg.ComboBox()
        self.init_buffer_items = {'All buffers': 0}
        self.buffer_selection.setItems(self.init_buffer_items.copy())
        self.buffer_selection.setValue(0)

        self.buffer_mode = 0
        self.max1 = 0
        self.max2 = 0

        def buffer_selection_changed(value):
            self.buffer_mode = value
            self.refresh_graph()

        self.buffer_selection.currentIndexChanged.connect(buffer_selection_changed)

        self.layout.addWidget(self.buffer_selection, 2, 0)

        clear_button = QtGui.QPushButton('Clear buffers')

        def clear_button_action(c):
            self.update_graph = False
            for channel in range(4):
                for curve in self.curves[channel]['curves']:
                    curve.clear()
                for curve in self.curves[channel]['peaks']:
                    curve.clear()
                self.curves[channel]['curves'] = []
                self.curves[channel]['peaks'] = []
                self.curves[channel]['max'] = {'index': 0, 'value': 0}
                self.curves[channel]['coincidence'] = False
                self.curves[channel]['pen'] = pg.mkPen('r', width=1) if (channel == 0 or channel == 2) else pg.mkPen('g', width=1)
            self.buffer_mode = 0
            self.buffer_selection.setItems(self.init_buffer_items.copy())
            self.buffer_selection.setValue(0)
            self.update_graph = True

        clear_button.clicked.connect(clear_button_action)
        self.layout.addWidget(clear_button, 2, 1)

        switch_on_button = QtGui.QPushButton('Switched on')
        switch_on_button.setEnabled(False)
        switch_on_button.setStyleSheet("background-color: green; color: white")
        def switch_on_button_action(c):
            self.update_graph = True
            switch_on_button.setEnabled(False)
            switch_on_button.setStyleSheet("background-color: green; color: white")
            switch_on_button.setText('Switched on')
            switch_off_button.setEnabled(True)
            switch_off_button.setStyleSheet("background-color: silver")
            switch_off_button.setText('Switch off')

        switch_on_button.clicked.connect(switch_on_button_action)
        #switch_on_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.layout.addWidget(switch_on_button, 3, 0)

        switch_off_button = QtGui.QPushButton('Switch off')
        switch_off_button.setStyleSheet("background-color: silver")
        def switch_off_button_action(c):
            self.update_graph = False
            switch_on_button.setEnabled(True)
            switch_on_button.setStyleSheet("background-color: silver")
            switch_on_button.setText('Switch on')
            switch_off_button.setEnabled(False)
            switch_off_button.setStyleSheet("background-color: red; color: white")
            switch_off_button.setText('Switched off')
        switch_off_button.clicked.connect(switch_off_button_action)
        #switch_off_button.setFocusPolicy(QtCore.Qt.NoFocus)

        self.layout.addWidget(switch_off_button, 3, 1)

        self.setLayout(self.layout)

        # Start refreshing the real time plot content.
        self.update_graph = True

    def refresh_graph(self):
        items = self.init_buffer_items.copy()
        for channel in range(4):
            # No need to handle the last curve, because it has 100% alpha and is shown in the graph.
            l = len(self.curves[channel]['curves'])
            for i, (curve, peak) in enumerate(zip(self.curves[channel]['curves'], self.curves[channel]['peaks'])):
                if self.buffer_mode > 0:
                    if i+1 != self.buffer_mode:
                        curve.hide()
                        #peak.hide()
                    else:
                        #peak.show()
                        curve.setPen('c')
                        curve.setAlpha(1, False)
                        curve.show()
                else:
                    #peak.clear()
                    #peak.hide()
                    if i == self.curves[channel]['max']['index']:
                        curve.setPen('w')
                        curve.setAlpha(1, False)
                        curve.setZValue(self.max_curves_in_plot)
                    else:
                        curve.setPen(self.curves[channel]['pen'])
                        curve.setAlpha((i+1)/l, False)
                    curve.show()
            if channel == 0:
                for j in range(1, l+1):
                    c = ' (oldest)' if (j == 2 and (self.curves[2]['max']['index'] == 0 and self.curves[3]['max']['index'] == 0)) or (j == 1 and (self.curves[2]['max']['index'] != 0 and self.curves[3]['max']['index'] != 0)) else ''
                    c += ' (newist)' if j == l else ''
                    c += ' (coincidence)' if self.curves[channel]['coincidence'] else ''
                    c += ' (max A)' if j-1 == self.curves[2]['max']['index'] else ''
                    c += ' (max B)' if j-1 == self.curves[3]['max']['index'] else ''
                    label_data = (str(j), c)
                    items['Buffer #%s%s' % label_data] = j

        self.buffer_selection.setItems(items)

    # Poll signal data from the main app.
    def update(self, coincidence = False):

        # self.update_graph is false when signal processing is in pause mode.
        # Also, if coincidence filter is set true, then coincidence argument must be true.
        # In that case only those signals, that has coincidence in both channels,
        # will be updated and drawn.
        if self.update_graph and (not self.filter_coincidences or coincidence):

            #blcd = map(lambda x: baseline_correction_and_limit(*x), zip(self.app.signals_data, self.app.spectrum_low_limits, self.app.spectrum_high_limits))

            for channel, data in enumerate(self.app.signals_data):

                ld = len(data)

                c = self.curves[channel]
                cc = c['curves']
                l = len(cc)
                color = c['pen']
                c['coincidence'] = coincidence

                m = max(data) if ld > 0 else 0
                if m > c['max']['value']:
                    # New max value for the next index.
                    c['max']['index'] = l
                    c['max']['value'] = m
                    # Use white color for pen.
                    color = 'w'

                # If length of the stack is max, clear away the oldest curve.
                if l == self.max_curves_in_plot:
                    # If maximum value curve resides in the first index, do not remove it,
                    # but the second last.
                    if c['max']['index'] == 0:
                        cc[1].clear()
                        cc.pop(1)
                    # Else remove the last curve.
                    else:
                        cc[0].clear()
                        cc.pop(0)
                        # Shift max curve index by decreasing it by one.
                        if c['max']['index'] > 0:
                            c['max']['index'] -= 1
                # If stack is still getting populated, we just add a new curve.
                cc.append(
                    c['plot'].getPlotItem().plot(pen = color)
                )

                c['peaks'].append(
                    self.curves[channel]['plot'].getPlotItem().plot(pen = 'y')
                )

                # Change ADC values to volts.
                if ld > 0:
                    voltage_range = VOLTAGE_RANGES[self.app.settings_acquire_value['value']['picoscope']['voltage_range'][channel]]
                    data = list(map(lambda x: voltage_range * x / self.app.spectrum_time_window, data))

                # Add data to the new curve.
                cc[-1].setData(data)

                # pdata = np.zeros(len(data))
                # peaks = raising_edges_for_raw_pulses(np.array(data) > 1, width=100, distance=100, threshold=0)
                # for peak in peaks:
                #     peak_corr = peak - len(data)/2
                #     if peak_corr > -10:
                #         pdata[peak] = 10 + ((10 + peak_corr) / 20)
                #     else:
                #         pdata[peak] = data[peak]
                # c['peaks'][-1].hide()
                # c['peaks'][-1].setData(pdata)

                # Resize plot to match max area.
                c['plot'].enableAutoRange(axis='y')
                c['plot'].setAutoVisible(y=True)

            self.refresh_graph()

    def closeEvent(self, event):
        self.update_graph = False
        event.accept()


class ExperimentSettingsForm(QtWidgets.QDialog):

    def __init__(self, control, mode, measurement_name, settings = {}, limit = None, *args):

        self.app = control.app
        self.measurement_name = measurement_name
        self.settings = settings
        self.parent = control

        super(QtWidgets.QDialog, self).__init__(*args)

        self.setWindowTitle("Tandem Piercer Experiment - Settings")

        layout = QtWidgets.QFormLayout()

        self.form_general_settings_group = QtWidgets.QGroupBox("General Settings")

        if self.measurement_name not in ['singles_find_spectrum', 'tandem_find_spectrum']:
            #layout.addRow("Experiment name", QtWidgets.QLineEdit(text = self.app.experiment_name)),
            layout.addRow("Measurement name", QtGui.QLabel(control.headers[mode][self.measurement_name]))
        else:
            layout.addRow("", QtGui.QLabel('%s Spectrum Settings' % (limit)))

        self.general_settings = [
            {
                'key': 'pulse_source',
                'label': "Isotope Source Name",
                'controller': QtWidgets.QLineEdit(
                    text = settings['pulse_source'] if 'pulse_source' in settings else self.app.pulse_source)
            },
            {
                'key': 'high_voltage',
                'label': "High Voltage Value",
                'controller': QtWidgets.QLineEdit(
                    text = settings['high_voltage'] if 'high_voltage' in settings else str(self.app.sca_module_settings['high_voltage']))
            },
            {
                'key': 'front_detector',
                'label': "Front Detector",
                'controller': QtWidgets.QLineEdit(
                    text = settings['front_detector'] if 'front_detector' in settings else self.app.sca_module_settings['front_detector'])
            }
        ]

        for item in self.general_settings:
            layout.addRow(item['label'], item['controller'])

        self.form_general_settings_group.setLayout(layout)

        layout = QtWidgets.QFormLayout()
        self.channel_a_settings_group = QtWidgets.QGroupBox("Channel A")
        settings_a = settings['channel_a'] if 'channel_a' in settings and 'coarse_gain' in settings['channel_a'] else self.app.sca_module_settings['channel_a']
        self.channel_a_settings = [
            {
                'key': 'coarse_gain',
                'label': "Coarse Gain",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_a['coarse_gain']))
            },
            {
                'key': 'fine_gain',
                'label': "Fine Gain",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_a['fine_gain']))
            },
            {
                'key': 'window',
                'label': "Window",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_a['window']))
            },
            {
                'key': 'lower_level',
                'label': "Lower Level",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_a['lower_level']))
            },
            {
                'key': 'mode',
                'label': "Mode",
                'controller': QtWidgets.QLineEdit(
                    text = settings_a['mode'])
            },
            {
                'key': 'spectrum_low_limit',
                'label': "Spectrum Low Limit",
                'controller': QtWidgets.QLineEdit(
                    text = settings_a['spectrum_low_limit'] if 'spectrum_low_limit' in settings_a else str(self.app.spectrum_low_limits[2]))
            },
            {
                'key': 'spectrum_high_limit',
                'label': "Spectrum High Limit",
                'controller': QtWidgets.QLineEdit(
                    text = settings_a['spectrum_high_limit'] if 'spectrum_high_limit' in settings_a else str(self.app.spectrum_high_limits[2]))
            }
        ]

        for item in self.channel_a_settings:
            layout.addRow(item['label'], item['controller'])

        def retrieve_new_channel_a_limits_action(x):
            low_limit = str(self.app.spectrum_low_limits[2])
            high_limit = str(self.app.spectrum_high_limits[2])
            self.channel_a_settings[-2]['controller'].setText(low_limit)
            self.channel_a_settings[-1]['controller'].setText(high_limit)
            settings_a['spectrum_low_limit'] = low_limit
            settings_a['spectrum_high_limit'] = high_limit

        retrieve_new_limits_button = QtGui.QPushButton('Get ADC Spectrum Limits')
        retrieve_new_limits_button.clicked.connect(retrieve_new_channel_a_limits_action)
        layout.addRow('', retrieve_new_limits_button)

        self.channel_a_settings_group.setLayout(layout)

        layout = QtWidgets.QFormLayout()
        self.channel_b_settings_group = QtWidgets.QGroupBox("Channel B")
        settings_b = settings['channel_b'] if 'channel_b' in settings and 'coarse_gain' in settings['channel_b'] else self.app.sca_module_settings['channel_b']
        self.channel_b_settings = [
            {
                'key': 'coarse_gain',
                'label': "Coarse Gain",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_b['coarse_gain']))
            },
            {
                'key': 'fine_gain',
                'label': "Fine Gain",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_b['fine_gain']))
            },
            {
                'key': 'window',
                'label': "Window",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_b['window']))
            },
            {
                'key': 'lower_level',
                'label': "Lower Level",
                'controller': QtWidgets.QLineEdit(
                    text = str(settings_b['lower_level']))
            },
            {
                'key': 'mode',
                'label': "Mode",
                'controller': QtWidgets.QLineEdit(
                    text = settings_b['mode'])
            },
            {
                'key': 'spectrum_low_limit',
                'label': "Spectrum Low Limit",
                'controller': QtWidgets.QLineEdit(
                    text = settings_b['spectrum_low_limit'] if 'spectrum_low_limit' in settings_b else str(self.app.spectrum_low_limits[3]))
            },
            {
                'key': 'spectrum_high_limit',
                'label': "Spectrum High Limit",
                'controller': QtWidgets.QLineEdit(
                    text = settings_b['spectrum_high_limit'] if 'spectrum_high_limit' in settings_b else str(self.app.spectrum_high_limits[3]))
            }
        ]

        for item in self.channel_b_settings:
            layout.addRow(item['label'], item['controller'])

        def retrieve_new_channel_b_limits_action(x):
            low_limit = str(self.app.spectrum_low_limits[3])
            high_limit = str(self.app.spectrum_high_limits[3])
            self.channel_b_settings[-2]['controller'].setText(low_limit)
            self.channel_b_settings[-1]['controller'].setText(high_limit)
            settings_b['spectrum_low_limit'] = low_limit
            settings_b['spectrum_high_limit'] = high_limit

        retrieve_new_limits_button = QtGui.QPushButton('Get ADC Spectrum Limits')
        retrieve_new_limits_button.clicked.connect(retrieve_new_channel_b_limits_action)
        layout.addRow('', retrieve_new_limits_button)

        self.channel_b_settings_group.setLayout(layout)

        layout = QtWidgets.QFormLayout()

        if self.measurement_name not in ['singles_find_spectrum', 'tandem_find_spectrum']:

            self.save_button = QtGui.QPushButton('Save Measurement')

            def callback(x):
                # Call master save method in the main app.
                #self.app.measurement_name = self.measurement_name
                self.app.save_measurement(self.general_settings, self.channel_a_settings, self.channel_b_settings, control, self.measurement_name)
                self.close()
        else:
            self.save_button = QtGui.QPushButton('Store Limits')
            callback = self.store_sca_settings

        self.save_button.clicked.connect(callback)
        self.save_button.setLayout(layout)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(self.form_general_settings_group)
        mainLayout.addWidget(self.channel_a_settings_group)
        mainLayout.addWidget(self.channel_b_settings_group)
        mainLayout.addWidget(self.save_button)
        self.setLayout(mainLayout)

    def store_sca_settings(self, x):
        # Call master save method in the main app.
        for item in self.general_settings:
            self.settings[item['key']] = item['controller'].text()

        for item in self.channel_a_settings:
            self.settings['channel_a'][item['key']] = item['controller'].text()

        for item in self.channel_b_settings:
            self.settings['channel_b'][item['key']] = item['controller'].text()

        self.close()


class ExperimentControlPanel(QtGui.QTabWidget):

    def __init__(self, app, *args):

        self.app = app

        super(QtGui.QTabWidget, self).__init__(*args)

        self.setWindowTitle("Tandem Piercer Experiment - Control Panel")

        self.experiment_settings_dialog = None
        self.refresh = True
        self.selected_tab = 'singles'

        self.full_limits = {
            'singles': {
                'dialog': None,
                'settings': {
                    'channel_a': {},
                    'channel_b': {}
                }
            },
            'tandem':  {
                'dialog': None,
                'settings': {
                    'channel_a': {},
                    'channel_b': {}
                }
            }
        }
        self.partial_limits = {
            'singles': {
                'dialog': None,
                'settings': {
                    'channel_a': {},
                    'channel_b': {}
                }
            },
            'tandem':  {
                'dialog': None,
                'settings': {
                    'channel_a': {},
                    'channel_b': {}
                }
            }
        }

        self.headers = {
            'singles': {},
            'tandem': {}
        }

        # Add tabs for each set of measurements.

        def callback(index):
            if index == 0:
                self.selected_tab = 'singles'
            else:
                self.selected_tab = 'tandem'

        self.currentChanged.connect(callback)

        # Singles / true coincidence / sandwich measurements.
        self.singles_tab = QtGui.QWidget()
        self.addTab(self.singles_tab, "Singles")
        self.singles_table_tab()

        # Tandem measurements.
        self.tandem_tab = QtGui.QWidget()
        self.addTab(self.tandem_tab, "Tandem")
        self.tandem_table_tab()

        self.singles_table.resizeColumnsToContents()
        self.singles_table.resizeRowsToContents()
        self.singles_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.singles_table.horizontalHeader().setStretchLastSection(True)

        self.tandem_table.resizeColumnsToContents()
        self.tandem_table.resizeRowsToContents()
        self.tandem_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.tandem_table.horizontalHeader().setStretchLastSection(True)

        self.setTablesWidth()

        self.update()

    def setTablesWidth(self):
        for table in [self.singles_table]:
            width = table.verticalHeader().width()
            width += table.horizontalHeader().length()
            if table.verticalScrollBar().isVisible():
                width += table.verticalScrollBar().width()
            width += table.frameWidth() * 2
            table.setFixedWidth(width)
            self.setFixedWidth(width)

    def resizeEvent(self, event):
        self.setTablesWidth()
        super(ExperimentControlPanel, self).resizeEvent(event)

    # Get data from the main app and populate the current measurement values.
    def update(self):
        measurement_name = self.app.measurement_name
        if self.refresh and self.app.measurement_name in self.app.results_table:
            self.data = self.app.results_table
            self.set_data()

    def set_data(self):
        # Depending on that measurement is done, certain values are populated to the cells.
        # Mark with na those cell that are not used in the experiment.
        if self.selected_tab == 'singles':
            table = self.singles_table
            horizontal_headers = self.singles_horizontal_headers
            vertical_headers = self.singles_vertical_headers
        else: # tandem
            table = self.tandem_table
            horizontal_headers = self.tandem_horizontal_headers
            vertical_headers = self.tandem_vertical_headers

        measurement_name = self.app.measurement_name
        d = self.data[measurement_name]

        for n, item in enumerate(horizontal_headers):
            horizontal_key = item['key']
            if horizontal_key == measurement_name:
                for m, item in enumerate(vertical_headers):
                    vertical_key = item['key']
                    cell_value = d[vertical_key] if vertical_key in d else ''
                    table.setItem(m, n, QtWidgets.QTableWidgetItem(cell_value))

    def singles_table_tab(self):

        self.singles_horizontal_headers = [

            {'key': 'singles_find_spectrum',
             'header': 'Find Spectrum (Full/Gamma)',
             'description': 'Step 1: Find spectrum limits for the full signal and gamma peak part of the signal. This must be done with a source between the detectors to get the correct settings in SCA NIM module and low/high filter in the Python app.'},

            {'key': 'singles_background_full_apart',
             'header': 'Background Full (Apart)',
             'description': 'Step 2: Take a source off. Set detectors one meter (three feet) away from each other. Take spectra for full and gamma photo peak part only.'},

            {'key': 'singles_background_gamma_apart',
             'header': 'Background Gamma (Apart)',
             'description': 'Background Full (Apart) description.'},

            {'key': 'singles_background_full_near',
             'header': 'Background Full (Near)',
             'description': 'Step 3: Set detectors neck by neck in true coincidence geometry with each other. Take spectra for full and gamma photo peak part only. Step 2 and 3 will give an idea, how much background radiation and noise there is and what part of it will be causing coincidence clicks in detectors. Detectors in apart position should give only a click or few in an hour. Detectors near to each other gives more pulses, maybe a click in two minutes depending on wheather the detectors are set to take whole spectrum or only the gamma peak of the signal.'},

            {'key': 'singles_background_gamma_near',
             'header': 'Background Gamma (Near)',
             'description': 'See Background Full (Near) description. This measurement is meant to gather data for gamma photo peak part of the spectrum only.'},

            {'key': 'singles_full',
             'header': self.app.pulse_source + ' Full Spectrum',
             'description': 'Step 4: Set the source back between the detectors for singles measurement. Take spectra for full and gamma photo peak part only. Results will show two important factors in the process. How much background radiation will affect to the measurement and if the source is producing single emit gammas. There is a slight posibility that the source is contaminated and will cauise multiple gammas emitted at the same time which will cause incorrect results in the final Tandem experiment. At the moment, Cd-109 and Co-57 are the only suitable sources known to produce single emit gammas, if they are pure sources without contamination.'},

            {'key': 'singles_gamma',
             'header': self.app.pulse_source + ' Gamma Spectrum',
             'description': 'See Full spectrum. This measurement is meant to gather data for gamma photo peak part of the spectrum only. That is the end of the true coincidence / singles / sandwich measurements. These measurements are a precursory tests before the tandem measurement, which which should be done next in the same manner.'}
        ]

        for item in self.singles_horizontal_headers:
            self.headers['singles'][item['key']] = item['header']

        self.singles_vertical_headers = [

            {'key': 'measurement_start_time',
             'header': 'Measurement Start Time'},

            {'key': 'elapsed_time',
             'header': 'Elapsed Time (hh:mm:ss)'},

            {'key': 'coincidence_time_window',
             'header': 'Coincidence Time Window (ns)'},

            {'key': 'click_in_detector_a',
             'header': 'Clicks in Detector A'},

            {'key': 'click_in_detector_b',
             'header': 'Clicks in Detector B'},

            {'key': 'click_rate_detector_a',
             'header': 'Rate of Detector A'},

            {'key': 'click_rate_detector_b',
             'header': 'Rate of Detector B'},

            {'key': 'coincidence_clicks',
             'header': 'Coincidence Clicks'},

            {'key': 'background_coincidence_rate',
             'header': 'Background Coincidence Rate'},
            # This can be calculated only when both near and apart bg has been done.
            # Value estimates the background radiation causing pulses per cube sentimeter.
            # since from the apart and near modes we know single clicks per detector and coincidence clicks
            # between both detectors, we can double check those values based on space angle and geometry of the
            # scintillators. Scintillators are set close to each other, so their common sides of the cubes is a
            # certain plane which has certain probability of getting straight line rays that pierces both detectors.
            # Other, bigger part of the radiation just goes through one detector. So, we can estimate and cross check
            # the values to both directions.

            # The first value is an estimation of the clicks in the detectors based on coincidence rates.
            # True value are measured, but they may differ based on the efficiency level of the scintillator.
            {'key': 'calculated_background_radiation_rate',
             'header': 'Calculated BG Radiation Rate'},

             # The second value is an estimation of the coincidence rate based on clicks in single detectors.
            {'key': 'calculated_background_coincidence_rate',
             'header': 'Calculated BG Coincidence Rate'},

            # These are special labels for true coincidence mode.
            {'key': 'chance_rate',
             'header': 'Chance Rate'},

            # Correction is done based on background radiation singles_background_full_near and gamma peak separately.
            {'key': 'corrected_chance_rate',
             'header': 'Corrected Chance Rate'},

            {'key': '', 'header': ''}, {'key': '', 'header': ''}, {'key': '', 'header': ''}
        ]

        """
            # There should be a form of elements for HV input, and SCA gains and discriminators for both detectors.
            # With an extra pop up window these values could be set so that in the final report values can be used.
            # Also the name / description of the experiment as well as the name of the source can be edited in the external form.
            # Save limits button opens a window with the form which can be used to save the data. Input fields are prefilled
            # with default values coming from the application settings. After the saving, values are saved to the application settings
            # as well as to the measurement settings.
            {'key': 'save_settings',
             'header': 'Save settings'},

            # Load settings button can be used to load settings from other project. HV, SCA and limits are
            # loaded to the current application settings which can be modified and stored again in the measurement flow.
            {'key': 'load_settings',
             'header': 'Load settings'},

            # In the background and singles modes, measurements can be saved and loaded.
            # Note that becaause the singles measurement uses background rate information for corrected
            # values, the background measurements must be done first.
            {'key': 'save_measurement',
             'header': 'Save measurement'},

            {'key': 'load_measurement',
             'header': 'Load measurement'}
        """

        self.singles_table = QtWidgets.QTableWidget(len(self.singles_vertical_headers), len(self.singles_horizontal_headers), self.singles_tab)
        self.singles_table.setVerticalHeaderLabels([item['header'] for item in self.singles_vertical_headers])
        self.singles_table.setHorizontalHeaderLabels([item['header'] for item in self.singles_horizontal_headers])
        self.setTabText(0, "True coincidence measurements")

        self.set_restart_buttons('singles', self.singles_table, len(self.singles_vertical_headers) - 3)
        self.set_limits_buttons('singles', self.singles_table, len(self.singles_vertical_headers) - 2)
        self.set_save_buttons('singles', self.singles_table, len(self.singles_vertical_headers) - 2)

    def tandem_table_tab(self):

        self.tandem_horizontal_headers = [

            {'key': 'tandem_find_spectrum',
             'header': 'Find Spectrum (Full/Gamma)',
             'description': 'Step 1: Find spectrum limits for the full signal and gamma peak part of the signal. This must be done with a source in tandem geometry to get the correct settings in SCA NIM module and low/high filter in the Python app.'},

            {'key': 'tandem_background_full_apart',
             'header': 'Background Full (Apart)',
             'description': 'Step 2: Take a source off. Set detectors one meter (three feet) away from each other. Take spectra for full and gamma photo peak part only.'},

            {'key': 'tandem_background_gamma_apart',
             'header': 'Background Gamma (Apart)',
             'description': 'See Background Full (Apart) description.'},

            {'key': 'tandem_background_full_near',
             'header': 'Background Full (Near)',
             'description': 'Step 3: Set detectors neck by neck in tandem geometry with each other. Take spectra for full and gamma photo peak part only. Step 2 and 3 will give an idea, how much background radiation and noise there is and what part of it will be causing coincidence clicks in detectors. Detectors in apart position should give only a click or few in an hour. Detectors near to each other gives more pulses, maybe a click in two minutes depending on wheather the detectors are set to take whole spectrum or only the gamma peak of the signal.'},

            {'key': 'tandem_background_gamma_near',
             'header': 'Background Gamma (Near)',
             'description': 'See Background Full (Near) description. This measurement is meant to gather data for gamma photo peak part of the spectrum only.'},

            {'key': 'tandem_full',
             'header': self.app.pulse_source + ' Full Spectrum',
             'description': 'Step 4: Set detectors in tandem position, and the source in front of the front detector so that the back detector will get only radiation that is let through the front detector. Set the source in front of the front detector in the tandem experiment and repeat this part with different set ups. Main one is the source collimated with a lead object that has a hole in the middle so that only a certain amount of radiation in a controlled size of beam is let through the front and the rear detector. Take spectra for full and gamma photo peak part only for each variation of the measurement.'},

            {'key': 'tandem_gamma',
             'header': self.app.pulse_source + ' Gamma Spectrum',
             'description': 'See Full spectrum. This measurement is meant to gather data for gamma photo peak part of the spectrum only. That is the end of the series of measurement both in sandwich and tandem geometry. Each step has generated a document with tabular data and screenshots. All documents can be collected to a single one document as a base of the final report.'}
        ]

        for item in self.tandem_horizontal_headers:
            self.headers['tandem'][item['key']] = item['header']

        self.tandem_vertical_headers = [

            {'key': 'measurement_start_time',
             'header': 'Measurement Start Time'},

            {'key': 'elapsed_time',
             'header': 'Elapsed Time (hh:mm:ss)'},

            {'key': 'coincidence_time_window',
             'header': 'Coincidence Time Window (ns)'},

            {'key': 'click_in_detector_a',
             'header': 'Clicks in Detector A'},

            {'key': 'click_in_detector_b',
             'header': 'Clicks in Detector B'},

            {'key': 'click_rate_detector_a',
             'header': 'Rate of Detector A'},

            {'key': 'click_rate_detector_b',
             'header': 'Rate of Detector B'},

            {'key': 'coincidence_clicks',
             'header': 'Coincidence Clicks'},

            {'key': 'background_coincidence_rate',
             'header': 'Background Coincidence Rate'},
            # This can be calculated only when both near and apart bg has been done.
            # Value estimates the background radiation causing pulses per cube sentimeter.
            # since from the apart and near modes we know single clicks per detector and coincidence clicks
            # between both detectors, we can double check those values based on space angle and geometry of the
            # scintillators. Scintillators are set close to each other, so their common sides of the cubes is a
            # certain plane which has certain probability of getting straight line rays that pierces both detectors.
            # Other, bigger part of the radiation just goes through one detector. So, we can estimate and cross check
            # the values to both directions.

            # The first value is an estimation of the clicks in the detectors based on coincidence rates.
            # True value are measured, but they may differ based on the efficiency level of the scintillator.
            {'key': 'calculated_background_radiation_rate',
             'header': 'Calculated BG Radiation Rate'},

             # The second value is an estimation of the coincidence rate based on clicks in single detectors.
            {'key': 'calculated_background_coincidence_rate',
             'header': 'Calculated BG Coincidence Rate'},

            # These are special labels for true coincidence mode.
            {'key': 'chance_rate',
             'header': 'Chance Rate'},

            # Correction is done based on background radiation singles_background_full_near and gamma peak separately.
            {'key': 'corrected_chance_rate',
             'header': 'Corrected Chance Rate'},

            {'key': 'tandem_experiment_rate',
             'header': 'Experiment Rate'},

            {'key': 'corrected_tandem_experiment_rate',
             'header': 'Corrected Experiment Rate'},

            {'key': 'unquantum_effect_ratio',
             'header': 'Unquantum Effect Ratio'},

             {'key': '', 'header': ''}, {'key': '', 'header': ''}, {'key': '', 'header': ''}
        ]

        self.tandem_table = QtWidgets.QTableWidget(len(self.tandem_vertical_headers), len(self.tandem_horizontal_headers), self.tandem_tab)
        self.tandem_table.setVerticalHeaderLabels([item['header'] for item in self.tandem_vertical_headers])
        self.tandem_table.setHorizontalHeaderLabels([item['header'] for item in self.tandem_horizontal_headers])
        self.setTabText(1, "Tandem coincidence measurements")

        self.set_restart_buttons('tandem', self.tandem_table, len(self.tandem_vertical_headers) - 3)
        self.set_limits_buttons('tandem', self.tandem_table, len(self.tandem_vertical_headers) - 2)
        self.set_save_buttons('tandem', self.tandem_table, len(self.tandem_vertical_headers) - 2)


    def set_restart_buttons(self, mode, table, pos):

        for measurement_index, callback in enumerate([
            lambda x: self.app.restart_measurement(mode + '_find_spectrum'),
            lambda x: self.app.restart_measurement(mode + '_background_full_apart', self.full_limits[mode]['settings']),
            lambda x: self.app.restart_measurement(mode + '_background_gamma_apart', self.partial_limits[mode]['settings']),
            lambda x: self.app.restart_measurement(mode + '_background_full_near', self.full_limits[mode]['settings']),
            lambda x: self.app.restart_measurement(mode + '_background_gamma_near', self.partial_limits[mode]['settings']),
            lambda x: self.app.restart_measurement(mode + '_full', self.full_limits[mode]['settings']),
            lambda x: self.app.restart_measurement(mode + '_gamma', self.partial_limits[mode]['settings'])
            ]):
            qw = QtGui.QWidget()
            layout = QtGui.QHBoxLayout(qw)

            restart_button = QtGui.QPushButton('(Re)start')
            restart_button.clicked.connect(callback)
            table.setCellWidget(pos, measurement_index, qw)
            layout.addWidget(restart_button)

            layout.setContentsMargins(0, 0, 0, 0)
            qw.setLayout(layout)

    def set_limits_buttons(self, mode, table, pos):

        qw = QtGui.QWidget()
        layout = QtGui.QHBoxLayout(qw)
        button = QtGui.QPushButton(' Set Full Limits ')

        def callback1(tab):
            if not self.full_limits[tab]['dialog']:
                self.full_limits[tab]['dialog'] = ExperimentSettingsForm(self, tab, tab + '_find_spectrum', self.full_limits[tab]['settings'], 'Full')
                self.full_limits[tab]['dialog'].setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
            self.full_limits[tab]['dialog'].show()

        button.clicked.connect(lambda x: callback1(mode))
        table.setCellWidget(pos, 0, qw)
        layout.addWidget(button)

        button = QtGui.QPushButton(' Set Gamma Limits ')

        def callback2(tab):
            if not self.partial_limits[tab]['dialog']:
                self.partial_limits[tab]['dialog'] = ExperimentSettingsForm(self, tab, tab + '_find_spectrum', self.partial_limits[tab]['settings'], 'Gamma')
                self.partial_limits[tab]['dialog'].setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
            self.partial_limits[tab]['dialog'].show()

        button.clicked.connect(lambda x: callback2(mode))
        table.setCellWidget(pos, 0, qw)
        layout.addWidget(button)

        layout.setContentsMargins(0, 0, 0, 0)
        qw.setLayout(layout)

    def set_save_buttons(self, mode, table, pos):

        def open_settings_dialog(measurement_name, mode):

            settings = {}
            if measurement_name in [
                mode + '_background_full_apart',
                mode + '_background_full_near',
                mode + '_full'
                ]:
                settings = self.full_limits[mode]['settings']
            elif measurement_name in [
                mode + '_background_gamma_apart',
                mode + '_background_gamma_near',
                mode + '_gamma'
                ]:
                settings = self.partial_limits[mode]['settings']

            self.experiment_settings_dialog = ExperimentSettingsForm(self, mode, measurement_name, settings)
            self.experiment_settings_dialog.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
            self.experiment_settings_dialog.show()

        for i, callback in enumerate([
            lambda x: open_settings_dialog(mode + '_background_full_apart', mode),
            lambda x: open_settings_dialog(mode + '_background_gamma_apart', mode),
            lambda x: open_settings_dialog(mode + '_background_full_near', mode),
            lambda x: open_settings_dialog(mode + '_background_gamma_near', mode),
            lambda x: open_settings_dialog(mode + '_full', mode),
            lambda x: open_settings_dialog(mode + '_gamma', mode)
            ]):
            qw = QtGui.QWidget()
            layout = QtGui.QHBoxLayout(qw)
            button = QtGui.QPushButton('Save Measurement')
            button.clicked.connect(callback)
            table.setCellWidget(pos, i+1, qw)
            layout.addWidget(button)
            layout.setContentsMargins(0, 0, 0, 0)
            qw.setLayout(layout)


class LegendItem(pg.LegendItem):

    clicked = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self._group = QtWidgets.QButtonGroup()

    def addItem(self, item, name):
        # QRadioButton requires QButtonGroup for switch handler.
        # Commented here because using CheckBox instead.
        widget = QtWidgets.QCheckBox(name)
        palette = widget.palette()
        # Original colors from the plot items?
        palette.setColor(QtGui.QPalette.Window, QtCore.Qt.transparent)
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        widget.setPalette(palette)
        widget.setChecked(True)
        #self._group.addButton(widget)

        row = self.layout.rowCount()
        widget.clicked.connect(lambda: self.clicked.emit(row))
        proxy = item.scene().addWidget(widget)
        if isinstance(item, ItemSample):
            sample = item
        else:
            sample = ItemSample(item)

        self.layout.addItem(proxy, row, 0)
        self.layout.addItem(sample, row, 1)
        self.items.append((proxy, sample))
        #self.updateSize()

    def addPlotsForLegends(self, plots):
        self.plots = plots
        for plot in self.plots:
            self.addItem(plot['plot'], plot['name'])
        self.clicked.connect(self.toggleItem)

    def toggleItem(self, index):
        if self.plots[index]['show'] == 1:
            self.plots[index]['plot'].hide()
            if 'region' in self.plots[index]:
                self.plots[index]['region'].hide()
            if 'fit' in self.plots[index]:
                self.plots[index]['fit'].hide()
            if 'lines' in self.plots[index]:
                for line in self.plots[index]['lines']:
                    line.hide()
            self.plots[index]['show'] = 0

        else:
            self.plots[index]['plot'].show()
            if 'region' in self.plots[index]:
                self.plots[index]['region'].show()
            if 'fit' in self.plots[index]:
                self.plots[index]['fit'].show()
            if 'lines' in self.plots[index]:
                for line in self.plots[index]['lines']:
                    line.show()
            self.plots[index]['show'] = 1

# Graphical user interface for the application
class App(QtGui.QMainWindow):

    def __init__(self, application_configuration, multiprocessing_arguments, parent = None):

        super(App, self).__init__(parent)

        self.setWindowTitle("Tandem Piercer Experiment - Eric Reiter & Marko Manninen © 2021-2022")

        self.experiments_directory = 'experiments'
        self.experiment_directory = ''

        self.has_picoscope = application_configuration["has_picoscope"]
        self.picoscope_mode = application_configuration["picoscope_mode"]

        # Time window in nanoseconds (T_w).
        self.experiment_name = application_configuration["experiment_name"]
        # Spectrum histogram width in milli voltage.
        self.spectrum_time_window = application_configuration["spectrum_time_window"]
        # Spectrum queue size.
        self.spectrum_queue_size = application_configuration["spectrum_queue_size"]
        # Time difference and spectrum histograms bin count.
        self.bin_count = application_configuration["bin_count"]
        # Time window in nanoseconds (T_w).
        self.time_window = application_configuration["time_window"]
        # Logarithmic (1) or linear (0) y axis mode for spectrums and time histogram.
        self.logarithmic_y_scale = application_configuration["logarithmic_y_scale"]
        # Trigger channel info.
        self.trigger_channels = application_configuration["trigger_channels"]
        # Pulse radiation source.
        self.pulse_source = application_configuration["pulse_source"]
        # Playback file.
        self.playback_file = application_configuration["playback_file"]
        # SCA NIM Module settings.
        self.sca_module_settings = application_configuration["sca_module_settings"]
        # Pulse detection mode.
        self.pulse_detection_mode = application_configuration["pulse_detection_mode"]

        self.results_table = {}

        # Multiprocessing events and values that are shared between the processes.
        self.set_multiprocessing_arguments(multiprocessing_arguments)

        # Results table window.
        self.table = None
        # Signal plot window.
        self.signal = None
        self.signals_data = [[],[],[],[]]
        # Application settings window.
        self.setting = None

        #######################
        # Create Gui Elements #
        #######################

        self.mainbox = QtGui.QWidget()
        self.setCentralWidget(self.mainbox)

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5);

        #self.topbox = QtGui.QWidget()
        #layout.addWidget(self.topbox)

        self.canvas = pg.GraphicsLayoutWidget()
        layout.addWidget(self.canvas)

        # Status bar label.
        self.label = QtGui.QLabel()
        layout.addWidget(self.label)

        self.mainbox.setLayout(layout)

        add_menu(self)
        #add_bin_dial(self, min_value = 16, max_value = 1024, default_value = self.bin_count)

        # How many times data has been gathered in seconds?
        self.clicks_detector_n = 1

        # Total clicks in detectors.
        self.clicks_detector_a_avg = 0
        self.clicks_detector_b_avg = 0
        self.clicks_detector_a_b_avg = 0

        # Seconds rates.
        self.clicks_detector_b_s = 0
        self.clicks_detector_a_s = 0
        self.clicks_detector_a_b_s = 0

        self.signal_spectrum_clicks_detector_a = 0
        self.signal_spectrum_clicks_detector_b = 0
        self.signal_spectrum_clicks_coincidences = 0

        self.max_rate_bar_graph_nodes_yrange = 1

        self.spectrum_low_limits = application_configuration["spectrum_low_limits"]
        self.spectrum_high_limits = application_configuration["spectrum_high_limits"]

        self.spectrum_channels = application_configuration["spectrum_channels"]

        self.channels_pulse_height_value_data = []

        # Initialize measurement variables.
        self.start_measurement0 = True
        self.start_measurement1 = False
        self.start_measurement2 = False
        self.start_measurement3 = False

        self.rate_timeline = 120

        self.logarithmic_scale_threshold = 10
        #self.logarithmic_scale = ' - lin(y)'
        self.logarithmic_scale = ''
        # Natural logarithm.
        if self.logarithmic_y_scale == 1:
            self.logarithmic_scale = ' - log<sub style="font-size:14pt">e</sub>(y)'
        # Logarithm 2.
        elif self.logarithmic_y_scale == 2:
            self.logarithmic_scale = ' - log<sub style="font-size:14pt">2</sub>(y)'
        # Logarithm 10.
        elif self.logarithmic_y_scale == 3:
            self.logarithmic_scale = ' - log<sub style="font-size:14pt">10</sub>(y)'
        # Amplitude spectrum.
        elif self.logarithmic_y_scale == 4:
            self.logarithmic_scale = ' - abs(fft(y))'
        # Power spectrum.
        elif self.logarithmic_y_scale == 5:
            self.logarithmic_scale = ' - abs(fft(y))<sup style="font-size:14pt">2</sup>'
        # Phase spectrum.
        elif self.logarithmic_y_scale == 6:
            self.logarithmic_scale = ' - angle(fft(y))'

        self.signal_spectrum_plot_left_label = "Channel A counts (%s)%s"
        self.signal_spectrum_plot_right_label = "Channel B counts (%s)%s"
        self.coincidence_count_graph_label = "Coincidence counts (%s)%s"
        self.spectrum_plot_bottom_label = "Volts (A & B)"

        self.timeline_bottom_label = 'Time elapsed (%s)'

        self.plot_title_style = {'color': '#eee', 'font-size': '12pt'}
        self.plot_label_style = {'color': '#ccc', 'font-size': '10pt'}

        self.measurement_name = 'singles_find_spectrum'

        self.singles_near_and_apart_full_background_measured = False
        self.singles_near_and_apart_gamma_background_measured = False
        self.tandem_near_and_apart_full_background_measured = False
        self.tandem_near_and_apart_gamma_background_measured = False

        # Start data collection timer. It will be running for the experiments
        # even the data file saver has not been started.
        self.collect_start_time = tm()
        self.collect_start_time_str = strftime("%Y-%m-%d %H:%M:%S")

        self.create_time_difference_histogram()

        self.create_time_difference_scatter()

        self.create_pulse_rate_graph()

        self.canvas.nextRow()

        self.create_spectrum_histograms()

        self.create_line_graph()

        self.init_measurements()

        #### Set Data  #####################

        #add_range_slider(self, discriminator_low_default, discriminator_high_default)

        #self.running = True

        # Collect / save data to the csv files.
        self.collect_data = False
        # Two sspectroscope spectrum histograms are plotted with this data.
        self.channel_spectrums_csv = ''
        # Time difference histogram is plotted with this data.
        self.time_histogram_csv = ''
        # Running second based full height pulse clicks are plotted with this data.
        self.time_graph_csv = ''
        # Pulse monitor rate meter is plotted with this data.
        self.pulse_rate_csv = ''
        # Experiment data from all three measurements.
        self.experiment_data_csv = ''

        # Application start time, different than measurement start time.
        self.start_time = tm()
        self.start_time_str = strftime("%Y-%m-%d %H:%M:%S")
        # Frames per second indicator initial values.
        self.counter = 0
        self.fps = 0.
        self.lastupdate = tm()
        # How often graphs will be updated in seconds?
        self.interval = 1.
        self.lasttime = tm()

        self.canvas.ci.layout.setColumnStretchFactor(0, 4)
        self.canvas.ci.layout.setColumnStretchFactor(1, 4)
        self.canvas.ci.layout.setColumnStretchFactor(2, 1)

        self.showMaximized()

    ###########################################################
    # Line plots for second based data retrieval and counting #
    ###########################################################

    def create_line_graph(self):

        self.lineplot = self.canvas.addPlot(colspan = 1)
        self.lineplot.setTitle('Pulse rate time line', **self.plot_title_style)
        self.lineplot.setLabel('right', 'Rate / s', **self.plot_label_style)
        self.lineplot.setLabel('bottom', self.timeline_bottom_label % 0, **self.plot_label_style)
        self.lineplot.showGrid(x=False, y=True, alpha=.5)

        self.init_line_graph()

        # Initial x ticks starting from 0 in the right and having negative values up to the left
        self.pointer = -self.rate_timeline

        self.lineplota = self.lineplot.plot(pen = 'r', name = 'A (SCA)')
        self.lineplota.setPos(self.pointer, 0)

        self.lineplotb = self.lineplot.plot(pen = 'g', name = 'B (SCA)')
        self.lineplotb.setPos(self.pointer, 0)
        self.lineplotb.setAlpha(0.40, False)

        self.lineplotc = self.lineplot.plot(pen = 'c', name = 'Coincidence')
        self.lineplotc.setPos(self.pointer, 0)
        self.lineplotc.setAlpha(0.40, False)

        legend = LegendItem((120, 60), offset=(15,15))
        legend.setParentItem(self.lineplot.getViewBox())
        self.lineplot.legend = legend
        # TODO: could be automatic without need of specifying plots (or anything) in list...
        legend.addPlotsForLegends([
            {'plot': self.lineplota, 'show': 1, 'name': 'A (SCA)'},
            {'plot': self.lineplotb, 'show': 1, 'name': 'B (SCA)'},
            {'plot': self.lineplotc, 'show': 1, 'name': 'Coincidence'}
        ])

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.lineplot.setMouseEnabled(x=False, y=False)

    def init_line_graph(self):
        # values for the line plots, repeat 0 n times
        self.plot_values = {0: [], 1: [], 2: []}
        plot_range = [0 for i in range(self.rate_timeline)]
        self.plot_values[0] = plot_range[:]
        self.plot_values[1] = plot_range[:]
        self.plot_values[2] = plot_range[:]

        self.channels_pulse_height_value_data = []

    #####################################
    # Create signal spectrum histograms #
    #####################################

    def create_spectrum_histograms(self):

        self.signal_spectrum_plot = self.canvas.addPlot(colspan = 1)

        self.signal_spectrum_plot.setTitle('Pulse height spectrum', **self.plot_title_style)
        self.signal_spectrum_plot.setLabel('left', self.signal_spectrum_plot_left_label % (0, self.logarithmic_scale), **self.plot_label_style)
        self.signal_spectrum_plot.setLabel('right', self.signal_spectrum_plot_right_label % (0, self.logarithmic_scale), **self.plot_label_style)
        self.signal_spectrum_plot.setLabel('bottom', self.spectrum_plot_bottom_label, **self.plot_label_style)

        self.time_difference_spectrum_plot = self.canvas.addPlot(colspan = 1)
        self.time_difference_spectrum_plot.setTitle('Coincidence pulse height spectrum', **self.plot_title_style)
        self.time_difference_spectrum_plot.setLabel('bottom', self.spectrum_plot_bottom_label, **self.plot_label_style)

        # Linear region items for signal spectra.
        self.signal_spectrum_region_a = pg.LinearRegionItem(
            orientation = pg.LinearRegionItem.Vertical,
            brush = (220, 20, 60, 20) # Crimson Red
        )
        self.signal_spectrum_region_b = pg.LinearRegionItem(
            orientation = pg.LinearRegionItem.Vertical,
            brush = (0, 128, 0, 20) # Green
        )
        self.set_signal_region_adc_a()
        self.set_signal_region_adc_b()
        self.signal_spectrum_plot.addItem(self.signal_spectrum_region_a, ignoreBounds=True)
        self.signal_spectrum_plot.addItem(self.signal_spectrum_region_b, ignoreBounds=True)
        self.signal_spectrum_region_a.sigRegionChangeFinished.connect(self.region_changed_a)
        self.signal_spectrum_region_b.sigRegionChangeFinished.connect(self.region_changed_b)
        #self.signal_spectrum_region_a.sigRegionChanged.connect(self.region_update_a)
        #self.signal_spectrum_region_b.sigRegionChanged.connect(self.region_update_b)

        self.init_spectrum_histograms()

        # Signal spectrum plots.
        # y, x = np.histogram(
        #     self.signal_spectrum_data_a,
        #     bins = np.linspace(0, VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][2]], self.bin_count)
        # )

        self.lines_a = []
        self.lines_b = []

        self.spectra_bin_count = 64
        y, x = np.histogram(
            self.signal_spectrum_data_a,
            bins = np.linspace(0, VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][2]], self.spectra_bin_count)
        )

        #x = np.zeros(len(self.signal_spectrum_data_a))
        #y = self.signal_spectrum_data_a

        self.signal_spectrum_plot_a = self.signal_spectrum_plot.plot(x, y,
            name = 'A',
            stepMode = True,
            fillLevel = 0,
            brush = 'r',
            pen = pg.mkPen('r', width=0, style=None),
        )

        self.orange_color = (217, 83, 25)
        self.histogramplotp_curve_a = self.signal_spectrum_plot.plot(
            pen = pg.mkPen(self.orange_color, width=0, style=None),
            brush = self.orange_color
        )

        y, x = np.histogram(
            self.signal_spectrum_data_b,
            bins = np.linspace(0, VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][3]], self.spectra_bin_count)
        )

        self.signal_spectrum_plot_b = self.signal_spectrum_plot.plot(x, y,
            name = 'B',
            stepMode = True,
            fillLevel = 0,
            brush = 'g',
            pen = pg.mkPen('g', width=0, style=None)
        )

        self.signal_spectrum_plot_b.setAlpha(0.40, False)

        self.histogramplotp_curve_b = self.signal_spectrum_plot.plot(
            pen = pg.mkPen('g', width=0, style=None),
            brush = 'g'
        )

        legend = LegendItem((80, 60), offset=(15, 15))
        legend.setParentItem(self.signal_spectrum_plot.getViewBox())
        self.signal_spectrum_plot.legend = legend
        # TODO: could be automatic without need of specifying plots in list...
        legend.addPlotsForLegends([
            {'plot': self.signal_spectrum_plot_a, 'show': 1, 'name': 'A', 'region': self.signal_spectrum_region_a, 'fit': self.histogramplotp_curve_a, 'lines': self.lines_a},
            {'plot': self.signal_spectrum_plot_b, 'show': 1, 'name': 'B', 'region': self.signal_spectrum_region_b, 'fit': self.histogramplotp_curve_b, 'lines': self.lines_b}
        ])

        # Time difference spectrum plots.
        y, x = np.histogram(
            self.time_difference_spectrum_data_a,
            bins = np.linspace(0, VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][2]], self.bin_count)
        )

        self.time_difference_spectrum_plot_a = self.time_difference_spectrum_plot.plot(x, y,
            name = 'A',
            stepMode = True,
            fillLevel = 0,
            brush = 'r',
            pen = pg.mkPen('r', width=0, style=None)
        )

        y, x = np.histogram(
            self.time_difference_spectrum_data_b,
            bins = np.linspace(0, VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][3]], self.bin_count)
        )

        self.time_difference_spectrum_plot_b = self.time_difference_spectrum_plot.plot(x, y,
            name = 'B',
            stepMode = True,
            fillLevel = 0,
            brush = 'g',
            pen = pg.mkPen('g', width=0, style=None)
        )

        self.time_difference_spectrum_plot_b.setAlpha(0.40, False)

        legend = LegendItem((80, 60), offset=(15, 15))
        legend.setParentItem(self.time_difference_spectrum_plot.getViewBox())
        self.time_difference_spectrum_plot.legend = legend
        # TODO: could be automatic without need of specifying plots in list...
        legend.addPlotsForLegends([
            {'plot': self.time_difference_spectrum_plot_a, 'show': 1, 'name': 'A'},
            {'plot': self.time_difference_spectrum_plot_b, 'show': 1, 'name': 'B'}
        ])

        # Show vertical grids.
        self.signal_spectrum_plot.showGrid(x=False, y=True, alpha=.5)
        self.time_difference_spectrum_plot.showGrid(x=False, y=True, alpha=.5)

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.signal_spectrum_plot.setMouseEnabled(x=False, y=False)
        self.time_difference_spectrum_plot.setMouseEnabled(x=False, y=False)

    def region_update_a(self, regionItem):
        pass

    def region_update_b(self, regionItem):
        pass

    def set_signal_region_adc_a(self):
        self.set_signal_region_adc(self.signal_spectrum_region_a, 2)

    def set_signal_region_adc_b(self):
        self.set_signal_region_adc(self.signal_spectrum_region_b, 3)

    def set_signal_region_adc(self, region, ind):
        voltage_range = VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][ind]]
        region.setRegion([
            voltage_range * self.spectrum_low_limits[ind] / self.spectrum_time_window,
            voltage_range * self.spectrum_high_limits[ind] / self.spectrum_time_window
        ])

    def region_changed_a(self, regionItem):
        self.set_spectrum_region_volts(regionItem.getRegion(), 2)

    def region_changed_b(self, regionItem):
        self.set_spectrum_region_volts(regionItem.getRegion(), 3)

    def set_spectrum_region_volts(self, limits, ind):
        voltage_range = VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][ind]]
        self.spectrum_low_limits[ind] = int(limits[0] * self.spectrum_time_window / voltage_range)
        self.spectrum_high_limits[ind] = int(limits[1] * self.spectrum_time_window / voltage_range)
        # Restart Picoscope multiprocess worker with new settings.
        settings_acquire_value = self.settings_acquire_value['value']
        settings_acquire_value['spectrum_low_limits'] = self.spectrum_low_limits
        settings_acquire_value['spectrum_high_limits'] = self.spectrum_high_limits
        self.settings_acquire_value['value'] = settings_acquire_value
        self.settings_acquire_event.set()


    def init_spectrum_histograms(self, spectrum_queue_size = None):

        queue_size = spectrum_queue_size if spectrum_queue_size != None else self.spectrum_queue_size

        self.signal_spectrum_data_a = deque([], maxlen=queue_size)
        self.signal_spectrum_data_b = deque([], maxlen=queue_size)

        self.time_difference_spectrum_data_a = deque([], maxlen=queue_size)
        self.time_difference_spectrum_data_b = deque([], maxlen=queue_size)

        self.time_difference_spectrum_plot.setLabel('right', self.coincidence_count_graph_label % (0, self.logarithmic_scale), **self.plot_label_style)

    def clear_time_difference_histograms(self):
        try:
            self.time_difference_spectrum_plot_a.clear()
        except Exception as e:
            pass
        try:
            self.time_difference_spectrum_plot_b.clear()
        except Exception as e:
            pass


    #####################################################################
    # Create bargraph item for an average, current and max signal rates #
    #####################################################################

    def create_pulse_rate_graph(self):

        self.bargraph = self.canvas.addPlot(colspan = 1, labels = {'right': ''})
        self.bargraph.setTitle("Pulse rate meter (trigger %s) - Source: %s" % (self.trigger_channels, self.pulse_source), **self.plot_title_style)
        self.bargraph.showGrid(x=False, y=True, alpha=.5)
        self.bargraph.setYRange(0, 1)

        self.init_pulse_rate_graph()

        ax = self.bargraph.getAxis('bottom')
        ticks = [list(zip(range(6), ('', 'A (SCA)', 'B (SCA)', 'Coincidence')))]
        ax.setTicks(ticks)

        self.rate_bar_graph = pg.BarGraphItem(
            # Channel count, initial values, width of the bar, color of the bar.
            x = range(1, 4),
            height = [0,0,0],
            width = 0.75,
            brushes = ('r', 'g', 'c')
        )
        self.bargraph.addItem(self.rate_bar_graph)

        # Create a graph item for current rate indicators.

        self.rate_bar_size = .75
        self.symbolBrush = ['r', 'g', 'c']

        self.rate_graph_labels = [{
            'pen': 'r',
            'pos': (1, 0),
            'value': '0.00'
        },{
            'pen': 'g',
            'pos': (2, 0),
            'value': '0.00'
        },{
            'pen': 'c',
            'pos': (3, 0),
            'value': '0.00'
        }]

        font = QtGui.QFont()
        font.setPixelSize(16)

        for label in self.rate_graph_labels:
            label['item'] = pg.TextItem(color = label['pen'])
            label['item'].setZValue(2)
            label['item'].setPos(*label['pos'])
            label['item'].setFont(font)
            label['item'].setText(str(label['value']))
            self.bargraph.addItem(label['item'])

        # # Create a graph item for max rate indicators.
        # self.max_rate_bar_graph_nodes = pg.GraphItem()
        # self.bargraph.addItem(self.max_rate_bar_graph_nodes)

        # # Define positions of the rate nodes.
        # pos = np.array([[1, 0], [2, 0]])

        # # Setting data to the graph item.
        # self.max_rate_bar_graph_nodes.setData(
        #     pos=pos, size=self.rate_bar_size, pxMode=False, symbol='t', symbolSize=.1, symbolPen=self.symbolBrush[:2], symbolBrush='w'
        # )

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.bargraph.setMouseEnabled(x=False, y=False)

        #self.bargraph.addLine(x=None, y=10, pen=pg.mkPen('r', width = 5))

    # Create a graph item for average rate indicators.
    def init_pulse_rate_graph(self):
        self.channels_signal_rate_value_data = {
            0: {'rate': 0, 'count': 0, 'max': 0}, # A (SCA)
            1: {'rate': 0, 'count': 0, 'max': 0}, # B (SCA)
            2: {'rate': 0, 'count': 0, 'max': 0}, # A & B
        }

    ####################################
    # Create time difference histogram #
    ####################################

    def create_time_difference_histogram(self):

        self.histogramplot = self.canvas.addPlot(colspan = 1, labels = {'right': ''})
        self.histogramplot.setTitle('Coincidence pulse time interval', **self.plot_title_style)
        self.histogramplot.setLabel('bottom', "Time (ns)", **self.plot_label_style)
        self.histogramplot.showGrid(x=False, y=True, alpha=.5)

        self.init_time_difference_histogram()

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.histogramplot.setMouseEnabled(x=False, y=False)

    ####################################
    # Create time difference scatter   #
    ####################################

    def create_time_difference_scatter(self):

        self.scatterplot = self.canvas.addPlot(colspan = 1)

        self.scatterplot.setTitle('Coincidence pulse height scatter', **self.plot_title_style)
        self.scatterplot.setLabel('bottom', "Volts (A)", **self.plot_label_style)
        self.scatterplot.setLabel('right', "Volts (B)", **self.plot_label_style)

        self.scatterplot.setXRange(0, VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][2]])
        self.scatterplot.setYRange(0, VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][3]])

        self.scatterplot.showGrid(x=True, y=True, alpha=.5)

        self.init_time_difference_scatter()

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.scatterplot.setMouseEnabled(x=False, y=False)

    def init_time_difference_histogram(self, spectrum_queue_size = None):

        queue_size = spectrum_queue_size if spectrum_queue_size != None else self.spectrum_queue_size

        self.histogram_data = deque([], maxlen=queue_size)

        self.histogramplot.clear()

        # Initial values for histogram.
        y, x = np.histogram(self.histogram_data, bins = np.linspace(-self.time_window, self.time_window, self.bin_count))
        self.histogramplotp = self.histogramplot.plot(x, y, stepMode = True, fillLevel = 0, brush = (0, 0, 255, 150))

        self.histogramplot.setLabel('left', self.coincidence_count_graph_label % (0, self.logarithmic_scale), **self.plot_label_style)


    def init_time_difference_scatter(self):
        self.scatterplot.clear()


    #####################################
    #         EXPERIMENT STEPS
    #####################################
    #
    # 1. Measure the background rate
    # 2. Make the true coincidence test
    # 3. Measure the unquantum effect
    #
    #####################################
    def init_measurements(self):
        self.init_detectors()
        # Background rate (R_b)
        # Measurement 1 - retrieves coincidence clicks from the detectors
        # without radionuclei. Background coincidents are retrieved in the same
        # time window than the measurement 3.
        # Background rate will be used substracted from the experiment rate.
        self.background_rate = 0

        # Chance rate (R_c = R_1 * R_2 * T_w)
        # Chance rate is calculated by multiplying detector a and b rates with the time window.
        # This is done with the set_chance_rate method.
        self.chance_rate = 0
        self.corrected_chance_rate = 0

        # Experiment rate (R_e = C_t ÷ T_t)
        # Total coincidence clicks divided by time difference is done with the
        # set_experiment_rate method.
        self.experiment_rate = 0

        # Corrected experiment rate (R_r = R_e - R_b)
        # Adjustment is required to substract random coincidences caused by the background
        # radition. Background rate is substracted from the experiment rate with the
        # set_corrected_experiment_rate method.
        self.corrected_experiment_rate = 0

        # Unquantum Effect (UE = R_r ÷ R_c)
        # Measurement 3 - Final calculation is done with the ratio of the corrected rate
        # and the chance rate. If corrected experiment rate is bigger than chance
        # unquantum effect is greater than one. If UE rate is two or more, it indicates
        # anomaly that contradicts quantum mechanical model. QM predicts that
        # the experiment rate is about the chance rate with some error margin.
        # Use set_unquantum_effect to calculate this value.
        self.unquantum_effect = 0

    def init_graphs(self):

        self.signals_data = [[],[],[],[]]

        self.init_line_graph()
        self.init_spectrum_histograms()
        self.init_pulse_rate_graph()
        self.init_time_difference_histogram()
        self.clear_time_difference_histograms()
        self.init_time_difference_scatter()

    def init_detectors(self):

        # Reinitialize graphs data before starting each new measurement.
        self.init_graphs()

        # Stop collecting data, wait for new start.
        self.stop()

        # Start data collection timer. It will be running for the experiments
        # even the data file saver has not been started.
        self.collect_start_time = tm()
        self.collect_start_time_str = strftime("%Y-%m-%d %H:%M:%S")

        # Total experiment time (T_t)
        # How long each of the experiments have been running in seconds?
        # Start clock from the experiment menu.
        self.total_experiment_time = 0

        # Total coincidence clicks from detectors (C_t)
        # This value is dependant on the time window
        # We don't know how close and in which order the clicks happen in reality
        # since we don't have pico resolution, so we rely on the SCA module
        # which makes square wave pulses from the detector signals. If they happen
        # in a close enough time window, we consider them as coincident.
        # Time difference window shows the distribution of the coincidence clicks
        # but the real calculation is done with the experiment and chance rate comparison.
        self.total_coincident_clicks_detectors = 0

        # Singles count from the detector a (C_1)
        # Independent full pulse count from the detector a
        self.total_single_clicks_detector_a = 0

        # Singles count from the detector b (C_2)
        # Independent full pulse count from the detector b
        self.total_single_clicks_detector_b = 0

        # Singles rate from the detector a (R_1 = C_1 / T_t)
        # Independent full pulse rate from the detector a
        self.total_singles_rate_detector_a = 0

        # Singles rate from the detector b (R_2 = C_2 / T_t)
        # Independent full pulse rate from the detector b
        self.total_singles_rate_detector_b = 0

        self.signal_spectrum_clicks_detector_a = 0
        self.signal_spectrum_clicks_detector_b = 0
        self.signal_spectrum_clicks_coincidences = 0

        self.clicks_detector_a_avg = 0
        self.clicks_detector_b_avg = 0
        self.clicks_detector_a_b_avg = 0

        self.clicks_detector_n = 1

        self.max_rate_bar_graph_nodes_yrange = 1

    # Measurement 2 - Sandwich (true coincidence) test is done by using two
    # detectors each side of the radinuclei. Only single gammas should be sent
    # by the isotope so that there are no coincidence clicks in detectors except
    # those that are caused randomly by the background radiation.
    def true_coincidence_test_measured(self):
        return False

    def init_data_saving(self):

        c = datetime.now()

        if not os.path.exists(self.experiments_directory):
            os.makedirs(self.experiments_directory)

        self.experiment_directory = os.path.join(
            self.experiments_directory,
            '%s_%s_%s_%s_%s' % (c.year, c.month, c.day, c.hour, c.minute)
        )

        if not os.path.exists(self.experiment_directory):
            os.makedirs(self.experiment_directory)

    def restart_measurement(self, measurement_name, measurement_settings = None):

        self.measurement_name = measurement_name

        if measurement_settings != None:

            if 'spectrum_low_limit' in measurement_settings['channel_a']:

                self.spectrum_low_limits[2] = int(measurement_settings['channel_a']['spectrum_low_limit'])
                self.spectrum_high_limits[2] = int(measurement_settings['channel_a']['spectrum_high_limit'])

                self.spectrum_low_limits[3] = int(measurement_settings['channel_b']['spectrum_low_limit'])
                self.spectrum_high_limits[3] = int(measurement_settings['channel_b']['spectrum_high_limit'])

        settings_acquire_value = self.settings_acquire_value['value']
        settings_acquire_value['spectrum_low_limits'] = self.spectrum_low_limits
        settings_acquire_value['spectrum_high_limits'] = self.spectrum_high_limits
        self.settings_acquire_value['value'] = settings_acquire_value
        self.settings_acquire_event.set()

        self.set_signal_region_adc_a()
        self.set_signal_region_adc_b()

        if measurement_name in (
            'singles_find_spectrum',
            'tandem_find_spectrum',
            'singles_background_full_near',
            'tandem_background_full_near',
            'singles_background_gamma_near',
            'tandem_background_gamma_near',
            'singles_background_full_apart',
            'tandem_background_full_apart',
            'singles_background_gamma_apart',
            'tandem_background_gamma_apart'):
            self.init_measurements()
        else:
            self.init_detectors()

        # Initial state measurements, find spectrum and settings for full and gamma peak.
        self.start_measurement0 = False
        # Background measurements.
        self.start_measurement1 = False
        # True coincidence measurements.
        self.start_measurement2 = False
        # Tandem coincidence measurement.
        self.start_measurement3 = False

        if self.measurement_name in (
            'singles_find_spectrum',
            'tandem_find_spectrum'):
            self.start_measurement0 = True

        elif self.measurement_name in (
            'singles_background_full_near',
            'tandem_background_full_near',
            'singles_background_gamma_near',
            'tandem_background_gamma_near',
            'singles_background_full_apart',
            'tandem_background_full_apart',
            'singles_background_gamma_apart',
            'tandem_background_gamma_apart'):
            self.start_measurement1 = True

        elif self.measurement_name in (
            'singles_full',
            'singles_gamma'):
            self.start_measurement2 = True

        elif self.measurement_name in (
            'tandem_full',
            'tandem_gamma'):
            self.start_measurement3 = True


    def save_measurement(self, general_settings, channel_a_settings, channel_b_settings, control_panel, measurement_name):

        if self.experiment_directory == '':
            self.init_data_saving()

        import csv
        import pandas as pd
        import pyqtgraph.exporters

        # After everything has been done, use Generate report from Measurement menu to collect
        # all measurements to the same markdown file. It will contain headers, descriptions, images, and
        # data tables for the whole experiment.

        # Select table and headers based on selected tab (singles/tandem).

        table = control_panel.singles_table if control_panel.selected_tab == 'singles' else control_panel.tandem_table

        vertical_headers = control_panel.singles_vertical_headers if control_panel.selected_tab == 'singles' else control_panel.tandem_vertical_headers

        horizontal_headers = control_panel.singles_horizontal_headers if control_panel.selected_tab == 'singles' else control_panel.tandem_horizontal_headers

        rows = {
            '': [item['header'] for item in vertical_headers if item['header'] != '']
        }

        csv_path = os.path.join(self.experiment_directory, measurement_name + '.csv')

        with open(csv_path, 'w') as stream:
            writer = csv.writer(stream)
            # Write header row to csv.
            # Set only current column header name.
            writer.writerow([item['header'] for item in horizontal_headers if item['key'] == measurement_name])
            for row in range(table.rowCount()):
                rowdata = []
                for column in range(table.columnCount()):
                    # Set only current column values.
                    if horizontal_headers[column]['key'] == measurement_name and vertical_headers[row]['header'] != '':
                        item = table.item(row, column)
                        cell_value = ''
                        if item is not None:
                            cell_value = item.text()
                        rowdata.append(cell_value)
                        # Collect row items for markdown file.
                        if horizontal_headers[column]['header'] not in rows:
                            rows[horizontal_headers[column]['header']] = []
                        rows[horizontal_headers[column]['header']].append(cell_value)
                # Write data row to csv.
                writer.writerow(rowdata)

        df = pd.DataFrame(rows)
        df = df.set_index('')
        md1 = df.to_markdown()

        is_full_measurement = measurement_name in [
            'singles_background_full_near',
            'tandem_background_full_near',
            'singles_background_full_apart',
            'tandem_background_full_apart',
            'singles_full',
            'tandem_full']

        is_gamma_measurement = measurement_name in [
            'singles_background_gamma_near',
            'tandem_background_gamma_near',
            'singles_background_gamma_apart',
            'tandem_background_gamma_apart',
            'singles_gamma',
            'tandem_gamma']

        data = {
            '': [item['label'] for item in channel_a_settings],
            'Channel A': [item['controller'].text() for item in channel_a_settings],
            'Channel B': [item['controller'].text() for item in channel_b_settings]
        }
        df = pd.DataFrame(data)
        df.set_index('')
        md2 = df.to_markdown()

        md_path = os.path.join(self.experiment_directory, measurement_name + '.md')

        measurement_label = control_panel.headers[control_panel.selected_tab][measurement_name]

        with open(md_path, 'w') as file:

            # TODO: Add settings from SCA, Picoscope and application to the beginning of the file.
            # In tandem geometry, we need to specify and show front and back detector identifications.

            # Title.
            file.write('# ' + measurement_label)

            file.write('\n\n## Results')
            file.write('\n\n' + md1)

            file.write('\n\nSource CSV File [%s](%s)' % (measurement_name + '.csv', measurement_name + '.csv'))

            if is_full_measurement or is_gamma_measurement:
                file.write('\n\n## %s' % 'SCA Settings and ADC Limits')
                file.write('\n\n' + md2)

        # Adjust sizes for each image
        coincidence_time_histogram_filename = measurement_name + '_coincidence_time_histogram.png'
        exporter = pg.exporters.ImageExporter(self.histogramplot)
        exporter.export(os.path.join(self.experiment_directory, coincidence_time_histogram_filename))

        # Two versions, single channels and channels in same.
        # Hide one channel, take picture...
        signal_spectrum_a_and_b_filename = measurement_name + '_signal_spectrum_a_and_b.png'
        exporter = pg.exporters.ImageExporter(self.signal_spectrum_plot)
        exporter.export(os.path.join(self.experiment_directory, signal_spectrum_a_and_b_filename))

        #signal_spectrum_a_filename = os.path.join(image_dir, '_signal_spectrum_a.png')
        #signal_spectrum_b_filename = os.path.join(image_dir, '_signal_spectrum_b.png')

        # Get the current settings of spectrum plot selection and take to temp variable.

        # Hide both plots and show plot A.

        # Deactivate A and activate plot B.

        # Restore original show-hide state.

        coincidence_spectrum_filename = measurement_name + '_coincidence_spectrum.png'
        exporter = pg.exporters.ImageExporter(self.time_difference_spectrum_plot)
        exporter.export(os.path.join(self.experiment_directory, coincidence_spectrum_filename))

        coincidence_scatter_filename = measurement_name + '_coincidence_scatter.png'
        exporter = pg.exporters.ImageExporter(self.scatterplot)
        exporter.export(os.path.join(self.experiment_directory, coincidence_scatter_filename))

        pulse_timeline_filename = measurement_name + '_pulse_timeline.png'
        exporter = pg.exporters.ImageExporter(self.lineplot)
        exporter.export(os.path.join(self.experiment_directory, pulse_timeline_filename))

        pulse_rate_meter_filename = measurement_name + '_pulse_rate_meter.png'
        exporter = pg.exporters.ImageExporter(self.bargraph)
        exporter.export(os.path.join(self.experiment_directory, pulse_rate_meter_filename))

        # Signal wave forms for all 4 channels, the one that has all 4 buffers in it.
        # This requires new way of handling buffers, update in the background, not only when the
        # singal wave window is opened...

        with open(md_path, 'a') as file:
            # Add some text description before of after each plot.
            file.write('\n\n![Signal Spectrum](%s "%s")' % (signal_spectrum_a_and_b_filename, "Signal Spectrum"))
            file.write('\n\n![Coincidence Spectrum](%s "%s")' % (coincidence_spectrum_filename, "Coincidence Spectrum"))
            file.write('\n\n![Coincidence Scatter](%s "%s")' % (coincidence_scatter_filename, "Coincidence Scatter"))
            file.write('\n\n![Coincidence Time Histogram](%s "%s")' % (coincidence_time_histogram_filename, "Coincidence Time Histogram"))
            file.write('\n\n![Pulse Time Line](%s "%s")' % (pulse_timeline_filename, "Pulse Time Line"))
            file.write('\n\n![Pulse Rate](%s "%s")' % (pulse_rate_meter_filename, "Pulse Rate"))

            #file.write('\n\n![Waveform Samples](%s "%s")' % (pulse_rate_meter_filename, "Waveform Samples"))



        # Add end notes for measurement

        # Collect general data
        # - Experiment started datetime
        # - Source used in the experiment
        # - Experiment name and description

        # Collect data from table to csv and to .md file. Markdown files are used for primary report
        # Collect data from plots
        # Collect data from settings
        # Ssve all data to the measurement directory
        # When all measurements are done, collect all data to same report.

        # Add closure for the report: Generated datetime by Tandem Piercer Experiment Python Application (c) Marko Manninen
        # Other Endnotes to Essay and Websites and Reiter's docs and videos.
        # Once general document is ready, make pdf with calypso? And send generated files to other online services
        # and send by email.

    # Measurement data is polled once in a second.
    def update_results(self):

        calculated_background_radiation_rate = calculated_background_coincidence_rate = '-'
        if self.start_measurement1 and (
            (self.singles_near_and_apart_full_background_measured and
            self.measurement_name in (
                'singles_background_full_near',
                'singles_background_full_apart')) or
            (self.singles_near_and_apart_gamma_background_measured and
            self.measurement_name in (
                'singles_background_gamma_near',
                'singles_background_full_apart')) or
            (self.tandem_near_and_apart_full_background_measured and
            self.measurement_name in (
                'tandem_background_full_near',
                'tandem_background_full_apart')) or
            (self.tandem_near_and_apart_gamma_background_measured and
            self.measurement_name in (
                'tandem_background_gamma_near',
                'tandem_background_full_apart'))):
            calculated_background_radiation_rate = '+'
            calculated_background_coincidence_rate = '+'

        chance_rate = corrected_chance_rate = '-'
        if self.start_measurement2 or self.start_measurement3:
            chance_rate = str(round(self.chance_rate, 6)) # convert to seconds?
            corrected_chance_rate = str(round(self.corrected_chance_rate, 6)) # convert to seconds?

        tandem_experiment_rate = corrected_tandem_experiment_rate = unquantum_effect_ratio = '-'
        if self.start_measurement3:
            tandem_experiment_rate = str(round(self.experiment_rate, 6)) # convert to seconds?
            corrected_tandem_experiment_rate = str(round(self.corrected_experiment_rate, 6)) # convert to seconds?
            unquantum_effect_ratio = str(round(self.unquantum_effect, 1))

        self.results_table[self.measurement_name] = {
            'measurement_start_time': str(self.collect_start_time_str),
            'elapsed_time': str(timedelta(seconds = int(round(self.total_experiment_time, 0)))),
            'coincidence_time_window': str(self.time_window * 2),
            'click_in_detector_a': str(self.total_single_clicks_detector_a),
            'click_in_detector_b': str(self.total_single_clicks_detector_b),
            'click_rate_detector_a': str(round(self.total_singles_rate_detector_a, 1)), # convert to seconds?
            'click_rate_detector_b': str(round(self.total_singles_rate_detector_b, 1)), # convert to seconds?
            'coincidence_clicks': str(self.total_coincident_clicks_detectors),
            'background_coincidence_rate': str(round(self.background_rate, 6)), # convert to seconds?
            'calculated_background_radiation_rate': calculated_background_radiation_rate,
            'calculated_background_coincidence_rate': calculated_background_coincidence_rate,
            'chance_rate': chance_rate,
            'corrected_chance_rate': corrected_chance_rate,
            'tandem_experiment_rate': tandem_experiment_rate,
            'corrected_tandem_experiment_rate': corrected_tandem_experiment_rate,
            'unquantum_effect_ratio': unquantum_effect_ratio
        }.copy()

        # If results table window has been opened, update the content.
        if self.table:
            self.table.update()


    # PLAYBACK MENU

    def open_playback_file(self):

        playback_file = QtGui.QFileDialog.getOpenFileName(self, 'Open playback file', '', "Data files (*.dat)")

        self.playback_file = playback_file[0]

        self.init_graphs()

        # Close worker and main program loops and processes.
        self.settings_acquire_value["value"] = {
            'sub_loop': False,
            'main_loop': True,
            'pause': True,
            'sleep': (.1, .1),
            'playback_file': self.playback_file,
            'spectrum_low_limits': self.spectrum_low_limits,
            'spectrum_high_limits': self.spectrum_high_limits,
            # Picoscope settings
            'picoscope': {},
            'sca_module_settings': {}
        }

        self.settings_acquire_event.set()

    # RESULTS MENU / WINDOW

    def results(self):
        if not self.table:
            self.table = ExperimentControlPanel(self)
            self.table.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
        self.table.refresh = True
        self.table.show()


    # SIGNALS MENU

    def signals(self):
        if not self.signal:
            self.signal = Signals(self)
            self.signal.setWindowFlags(self.signal.windowFlags() | QtCore.Qt.Window)
        self.signal.update_graph = True
        self.signal.show()

    # SETTINGS MENU

    def settings(self):
        if not self.setting:
            self.setting = Settings(self)
            self.setting.setWindowFlags(self.setting.windowFlags() | QtCore.Qt.Window)
        else:
            self.setting.application_settings['spectrum_low_limit_c'].setText(str(self.spectrum_low_limits[2]))
            self.setting.application_settings['spectrum_low_limit_d'].setText(str(self.spectrum_low_limits[3]))
            self.setting.application_settings['spectrum_high_limit_c'].setText(str(self.spectrum_high_limits[2]))
            self.setting.application_settings['spectrum_high_limit_d'].setText(str(self.spectrum_high_limits[3]))
        self.setting.show()

    # Total experiment time must be set before calling single rates methods and
    # background rate. Total coincidence clicks must be set before calling background
    # rate and experiment rate
    def set_background_rate(self):
        self.background_rate = (self.total_coincident_clicks_detectors / self.total_experiment_time) if self.total_experiment_time > 0 else 0
        return self.background_rate

    # Total experiment time must be set before calling single rates methods
    def set_singles_rate_detector_a(self):
        self.total_singles_rate_detector_a = (self.total_single_clicks_detector_a / self.total_experiment_time) if self.total_experiment_time > 0 else 0

    def set_singles_rate_detector_b(self):
        self.total_singles_rate_detector_b = (self.total_single_clicks_detector_b / self.total_experiment_time) if self.total_experiment_time > 0 else 0

    # Chance rate and experiment rates are used both the true coincidence test and
    # the unquantum measurement
    def set_chance_rate(self):
        # * 2 for two nanoseconds
        self.chance_rate = self.total_singles_rate_detector_a * self.total_singles_rate_detector_b * ((self.time_window * 2) / 10**9)
        return self.chance_rate

    def set_experiment_rate(self):
        self.set_chance_rate()
        self.experiment_rate = (self.total_coincident_clicks_detectors / self.total_experiment_time) if self.total_experiment_time > 0 else 0
        return self.experiment_rate

    def set_corrected_experiment_rate(self):
        self.set_experiment_rate()
        self.corrected_experiment_rate = self.experiment_rate - self.background_rate
        return self.corrected_experiment_rate

    # Unquantum effect measurement is used solely by the measurement 3
    def set_unquantum_effect(self):
        self.set_corrected_experiment_rate()
        self.unquantum_effect = 0 if self.chance_rate == 0 else (self.corrected_experiment_rate / self.chance_rate)
        return self.unquantum_effect

    def set_multiprocessing_arguments(self, arguments):
        for key, value in arguments.items():
            self.__dict__[key] = value

    # Start the main GUI window refresh loop
    def start_update(self):
        self._update()

    # Calculate frames per seconds
    def _fps(self):
        now = tm()
        dt = now - self.lastupdate
        if dt <= 0:
            dt = 0.000000000001
        self.lastupdate = now
        self.fps = self.fps * 0.9 + (1.0 / dt) * 0.1

    def set_window_status_bar(self):
        text = 'Start time: ' + self.start_time_str
        text += ' | Now: ' + strftime("%H:%M:%S")
        text += ' | Frame Rate:  {fps:.1f} FPS'.format(fps = self.fps)
        self.label.setText(text)

    def set_discriminators(self, values):
        self.discriminator_values = values

    def set_bin_count(self, count):
        self.bin_count = count

    def add_widget(self, widget):
        self.mainbox.layout().addWidget(widget)

    # DATA MENU ACTIONS
    def pause(self):
        picoscope = self.settings_acquire_value['value']['picoscope']
        self.settings_acquire_value["value"] = {
            'sub_loop': True,
            'main_loop': True,
            'pause': True,
            'sleep': (.1, .1),
            'playback_file': self.playback_file,
            'spectrum_low_limits': self.spectrum_low_limits,
            'spectrum_high_limits': self.spectrum_high_limits,
            # Picoscope settings
            'picoscope': picoscope,
            'sca_module_settings': self.sca_module_settings
        }
        self.settings_acquire_event.set()

    def resume(self):
        picoscope = self.settings_acquire_value['value']['picoscope']
        self.settings_acquire_value["value"] = {
            'sub_loop': True,
            'main_loop': True,
            'pause': False,
            'sleep': (.1, .1),
            'playback_file': self.playback_file,
            'spectrum_low_limits': self.spectrum_low_limits,
            'spectrum_high_limits': self.spectrum_high_limits,
            # Picoscope settings
            'picoscope': picoscope,
            'sca_module_settings': self.sca_module_settings
        }
        self.settings_acquire_event.set()

    def stop(self):
        self.collect_data = False

    # TODO: Measurement names has changed radically.
    def start(self):

        self.collect_start_time = tm();
        self.collect_start_time_str = strftime("%Y-%m-%d %H:%M:%S")
        self.collect_data = True

        if self.experiment_directory == '':
            self.init_data_saving()

        self.measurement_name = 'measurement0'
        if self.start_measurement1:
            self.measurement_name = 'measurement1'
        elif self.start_measurement2:
            self.measurement_name = 'measurement2'
        elif self.start_measurement3:
            self.measurement_name = 'measurement3'
        else:
            # If measurement is not set, we are running in test mode.
            self.init_measurements()

        self.time_histogram_csv = os.path.join(self.experiment_directory, self.measurement_name + '_histogram_data.csv')
        if not os.path.exists(self.time_histogram_csv):
            self.save_time_histogram_data_headers()

        self.channel_spectrums_csv = os.path.join(self.experiment_directory, self.measurement_name + '_spectrum_data.csv')
        if not os.path.exists(self.channel_spectrums_csv):
            self.save_channel_spectrums_data_headers()

        self.time_graph_csv = os.path.join(self.experiment_directory, self.measurement_name + '_graph_data.csv')
        if not os.path.exists(self.time_graph_csv):
            self.save_time_graph_data_headers()

        self.pulse_rate_csv = os.path.join(self.experiment_directory, self.measurement_name + '_rate_data.csv')
        if not os.path.exists(self.pulse_rate_csv):
            self.save_pulse_rate_data_headers()

        self.experiment_data_csv = os.path.join(self.experiment_directory, self.measurement_name + '_data.csv')
        if not os.path.exists(self.experiment_data_csv):
            self.save_experiment_data_headers()

    def save_time_histogram_data_headers(self):
        self._save_time_histogram_data([
            'time_difference'
        ])

    def _save_time_histogram_data(self, data):
        with open(self.time_histogram_csv, 'a') as file:
            file.write('\n'.join(data))
            file.write('\n')

    def save_channel_spectrums_data_headers(self):
        self._save_channel_spectrums_data([
            'channel',
            'value'
        ])

    def _save_channel_spectrums_data(self, data):
        with open(self.channel_spectrums_csv, 'a') as file:
            file.write(";".join(data))
            file.write('\n')

    def save_time_graph_data_headers(self):
        self._save_time_graph_data([
            'time',
            'channel',
            'pulse_count'
        ])

    def _save_time_graph_data(self, data):
        with open(self.time_graph_csv, 'a') as file:
            file.write(";".join(data))
            file.write('\n')

    def save_pulse_rate_data_headers(self):
        self._save_pulse_rate_data([
            'channel',
            'pulse_count',
            'pulse_rate'
        ])

    def _save_pulse_rate_data(self, data):
        with open(self.pulse_rate_csv, 'a') as file:
            file.write(";".join(data))
            file.write('\n')

    # Save experiment from all three measurements.
    # This is called from the update method once in a second interval.
    def save_experiment_data(self):
        self._save_experiment_data(
            map(str, [
                self.time_window,
                self.background_rate, # convert to seconds?
                self.total_coincident_clicks_detectors,
                self.total_single_clicks_detector_a,
                self.total_single_clicks_detector_b,
                self.total_singles_rate_detector_a, # convert to seconds?
                self.total_singles_rate_detector_b, # convert to seconds?
                self.total_experiment_time,
                self.chance_rate, # convert to seconds?
                self.experiment_rate, # convert to seconds?
                self.corrected_experiment_rate, # convert to seconds?
                self.unquantum_effect
            ])
        )

    def save_experiment_data_headers(self):
        self._save_experiment_data([
            'time_window',
            'background_rate',
            'total_coincident_clicks_detectors',
            'total_single_clicks_detector_a',
            'total_single_clicks_detector_b',
            'total_singles_rate_detector_a',
            'total_singles_rate_detector_b',
            'total_experiment_time',
            'chance_rate',
            'experiment_rate',
            'corrected_experiment_rate',
            'unquantum_effect'
        ])

    def _save_experiment_data(self, data):
        with open(self.experiment_data_csv, 'a') as file:
            file.write(";".join(data))
            file.write('\n')

    # QUIT MENU ACTION
    def quit(self):
        # Close worker and main program loops and processes.
        self.settings_acquire_value["value"] = {
            'sub_loop': False,
            'main_loop': False,
            'pause': True,
            'sleep': (1, 1),
            'playback_file': '',
            'spectrum_low_limits': [],
            'spectrum_high_limits': [],
            # Picoscope settings
            'picoscope': {},
            'sca_module_settings': {}
        }
        self.settings_acquire_event.set()
        # Native close method call.
        self.close()

    # Main program window close button.
    def closeEvent(self, event):
        self.quit()
        event.accept()

    def log(self, x, y, voltage_range, voltage_range_start = 0):
        if self.logarithmic_y_scale == 0 or max(y) < self.logarithmic_scale_threshold:
            return x, y
        elif self.logarithmic_y_scale == 1:
            # Data requires a clip to handle zero point.
            # Old version: np.log(y.clip(min=0.9999999999))
            # Better use 1 + y to bypass need for clip above.
            return x, np.log1p(y)
        elif self.logarithmic_y_scale == 2:
            # Log 2 instead of natural (e) log.
            return x, np.log2(y.clip(min=0.9999999999))
        elif self.logarithmic_y_scale == 3:
            # Log 10 instead of natural (e) log.
            return x, np.log10(y.clip(min=0.9999999999))
        else:
            # Using fourier transform for aplitude, power and angle spectrums.
            A = fft(y)
            # Symmetric fft data can be reduced to cotain only quarter of the signal.
            N = round(len(A) / 4) + 1
            yF = A[:N-1]
            xF = np.linspace(voltage_range_start, voltage_range, N)
            if self.logarithmic_y_scale == 4:
                # Amplitude spectrum.
                return xF, np.abs(yF)
            elif self.logarithmic_y_scale == 5:
                # Power spectrum.
                return xF, np.abs(yF)**2
            elif self.logarithmic_y_scale == 6:
                # Phase spectrum.
                return xF, np.angle(yF)

    # MAIN GUI UPDATE LOOP
    def _update(self):

        if not self.settings_acquire_value['value']['pause']:

            # Signal spectrum histogram event and GUI update.
            if self.signal_spectrum_acquire_event.is_set():

                data, triggers = self.signal_spectrum_acquire_value["value"]

                if self.collect_data:
                    for channel, value in enumerate(data):
                        self._save_channel_spectrums_data([str(channel), ','.join(map(str, value))])

                time_differences = triggers[2]

                self.signal_spectrum_clicks_detector_a += triggers[0]
                self.signal_spectrum_clicks_detector_b += triggers[1]

                voltage_range_a = VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][2]]
                voltage_range_b = VOLTAGE_RANGES[self.settings_acquire_value['value']['picoscope']['voltage_range'][3]]

                self.signals_data = [[],[],[],[]]

                maxes = [[], []]

                if triggers[0] > 0 or triggers[1] > 0:

                    if self.pulse_detection_mode == 0:
                        maxes = [triggers[3], triggers[4]]
                    else:

                        # TODO: use get_max_heights_and_time_differences, check that maxes come in same format!

                        time_differences = []
                        #m1 = max(data[2])
                        #m2 = max(data[3])
                        peaks_a, peaks_b = [], []
                        # For timebase 52 these are 1, for timebase 2 these are 10...
                        pulse_width = 1
                        pulse_distance = 1
                        threshold = 0
                        #if triggers[0] > 0:
                        #if m1 < self.spectrum_high_limits[2]:
                        d1 = baseline_correction_and_limit(data[2], self.spectrum_low_limits[2], self.spectrum_high_limits[2])
                        # Width and distance parameters depends of the timebase. Bigger the timebase (smaller the resolution)
                        # smaller the width and distance needs to be in the find_peak algorithm used in the raising edges finder.
                        peaks_a = raising_edges_for_raw_pulses(d1 > 0, width=pulse_width, distance=pulse_distance, threshold=threshold)
                        #if triggers[1] > 0:
                        #if m2 < self.spectrum_high_limits[3]:
                        d2 = baseline_correction_and_limit(data[3], self.spectrum_low_limits[3], self.spectrum_high_limits[3])
                        peaks_b = raising_edges_for_raw_pulses(d2 > 0, width=pulse_width, distance=pulse_distance, threshold=threshold)

                        # Center position of the buffers.
                        ld1 = len(d1) / 2
                        ld2 = len(d2) / 2

                        peaks_left = [
                            [(i, abs(i - ld1), d1[i]) for i in peaks_a if i > ld1 and d1[i] < self.spectrum_high_limits[2]][:1],
                            [(i, abs(i - ld2), d2[i]) for i in peaks_b if i > ld2 and d2[i] < self.spectrum_high_limits[3]][:1]
                        ]

                        peaks_right = [
                            [(i, abs(ld1 - i), d1[i]) for i in peaks_a if i < ld1 and d1[i] < self.spectrum_high_limits[2]][-1:],
                            [(i, abs(ld2 - i), d2[i]) for i in peaks_b if i < ld2 and d2[i] < self.spectrum_high_limits[3]][-1:]
                        ]

                        peaks_left[0].extend(peaks_right[0])
                        peaks_left[1].extend(peaks_right[1])

                        peaks = [
                            (lambda a: [([a[0][0], a[0][2]] if a[0][1] > a[1][1] else [a[1][0], a[1][2]]) if len(a) > 1 else [a[0][0], a[0][2]]] if len(a) > 0 else [])(peaks_left[0]),
                            (lambda a: [([a[0][0], a[0][2]] if a[0][1] > a[1][1] else [a[1][0], a[1][2]]) if len(a) > 1 else [a[0][0], a[0][2]]] if len(a) > 0 else [])(peaks_left[1])
                        ]

                        # maxes = [
                        #     (lambda a: [(a[0][2] if a[0][1] > a[1][1] else a[1][2]) if len(a) > 1 else a[0][2]] if len(a) > 0 else [])(peaks_left[0]),
                        #     (lambda a: [(a[0][2] if a[0][1] > a[1][1] else a[1][2]) if len(a) > 1 else a[0][2]] if len(a) > 0 else [])(peaks_left[1])
                        # ]

                        maxes = [[a[1] for a in peaks[0][-1:]], [a[1] for a in peaks[1][-1:]]]

                        for i, t in peaks[0]:
                            for j, u in peaks[1]:
                                # timebase_n per unit!
                                time_differences.append((i-j))

                        # maxes = [
                        #     [d1[i] for i in peaks_a if d1[i] < self.spectrum_high_limits[2]],
                        #     [d2[i] for i in peaks_b if d2[i] < self.spectrum_high_limits[3]]
                        # ]

                        #if 0 < (len(peaks_a) * len(peaks_b)):
                        # for i in peaks_a:
                        #     for j in peaks_b:
                        #         if d1[i] < self.spectrum_high_limits[2] and d2[j] < self.spectrum_high_limits[3]:
                        #             time_differences.append((i-j)) # 2ns per unit!

                time_differences_n = len(time_differences)

                self.signal_spectrum_clicks_coincidences += time_differences_n

                self.clicks_detector_a_s += len(maxes[0])
                self.clicks_detector_b_s += len(maxes[1])
                self.clicks_detector_a_b_s += time_differences_n

                self.channels_pulse_height_value_data.append((len(maxes[0]), len(maxes[1]), time_differences_n))

                def fit_function(x, *coeffs):
                    return np.polyval(coeffs, x)

                if len(maxes[0]) > 0:

                    self.signals_data[0] = data[0]
                    self.signals_data[2] = data[2]

                    new_maxes = [(voltage_range_a * m / self.spectrum_time_window) for m in maxes[0]]
                    self.signal_spectrum_data_a.extendleft(new_maxes)

                    #y, x = np.histogram(self.signal_spectrum_data_a, bins = np.linspace(0, voltage_range_a, self.bin_count))
                    y, x = np.histogram(self.signal_spectrum_data_a, bins = np.linspace(0, voltage_range_a, self.spectra_bin_count))
                    if self.logarithmic_y_scale == 0 or len(self.signal_spectrum_data_a) < 2:
                        self.signal_spectrum_plot_a.setData(x, y)
                    else:
                        self.signal_spectrum_plot_a.setData(*self.log(x, y, voltage_range_a))
                    self.signal_spectrum_plot.setLabel('left', self.signal_spectrum_plot_left_label % (self.signal_spectrum_clicks_detector_a, self.logarithmic_scale if max(y) > self.logarithmic_scale_threshold else ""))

                    if True:
                        centers = x[:-1] + np.diff(x)[0] / 2
                        norm_y = y / y.sum()
                        norm_y_ma = Series(norm_y).rolling(1, center=True).mean().values * ((max(y) * 20) if max(y) < self.logarithmic_scale_threshold else (max(y)/2))
                        self.histogramplotp_curve_a.setData(centers, norm_y_ma)

                    if False:
                        peaks = find_peaks(norm_y_ma, width = 2, distance = 2, threshold = 0.2)[0]

                        for i, peak in enumerate(peaks[:5]):
                            if i < len(self.lines_a)-1:
                                self.lines_a[i].setValue(centers[peak])
                                self.lines_a[i].setZValue(9999)
                            else:
                                center_line = pg.InfiniteLine(
                                    pos=centers[peak],
                                    angle=90,
                                    pen=self.orange_color,
                                    movable=False
                                )
                                self.lines_a.append(center_line)
                                self.signal_spectrum_plot.addItem(center_line)

                    #def f(x, N, a):
                        #return N * x ** a

                    #def f(x, *coeffs):
                    #    return np.polyval(coeffs, x)

                    # Optimize.
                    #popt, pcov = scipy.optimize.curve_fit(fit_function, x[:-1], y, p0 = np.ones(12))
                    #self.histogramplotp_curve_a.setData(x[:-1], fit_function(x[:-1], *popt))

                    #perr = np.sqrt(np.diag(pcov))
                    #self.histogramplotp_curve_a.setData(x[:-1], popt[0] * x[:-1] ** popt[1])
                    #self.histogramplotp_curve_b.setData(x[:-1], (popt[0]+perr[1]) * x[:-1] ** (popt[1]+perr[1]))

                if len(maxes[1]) > 0:

                    self.signals_data[1] = data[1]
                    self.signals_data[3] = data[3]

                    new_maxes = [(voltage_range_b * m / self.spectrum_time_window) for m in maxes[1]]
                    self.signal_spectrum_data_b.extendleft(new_maxes)

                    y, x = np.histogram(self.signal_spectrum_data_b, bins = np.linspace(0, voltage_range_b, self.spectra_bin_count))
                    if self.logarithmic_y_scale == 0 or len(self.signal_spectrum_data_b) < 2:
                        self.signal_spectrum_plot_b.setData(x, y)
                    else:
                        self.signal_spectrum_plot_b.setData(*self.log(x, y, voltage_range_b))
                    self.signal_spectrum_plot.setLabel('right', self.signal_spectrum_plot_right_label % (self.signal_spectrum_clicks_detector_b, self.logarithmic_scale if max(y) > self.logarithmic_scale_threshold else ""))

                    if True:
                        centers = x[:-1] + np.diff(x)[0] / 2
                        norm_y = y / y.sum()
                        norm_y_ma = Series(norm_y).rolling(1, center=True).mean().values * ((max(y) * 20) if max(y) < self.logarithmic_scale_threshold else (max(y)/2))
                        self.histogramplotp_curve_b.setData(centers, norm_y_ma)

                    if False:
                        peaks = find_peaks(norm_y_ma, width = 2, distance = 2, threshold = 0.2)[0]

                        for i, peak in enumerate(peaks[:5]):
                            if i < len(self.lines_b)-1:
                                self.lines_b[i].setValue(centers[peak])
                                self.lines_a[i].setZValue(9999)
                            else:
                                center_line = pg.InfiniteLine(
                                    pos=centers[peak],
                                    angle=90,
                                    pen='g',
                                    movable=False
                                )
                                self.lines_b.append(center_line)
                                self.signal_spectrum_plot.addItem(center_line)

                if len(maxes[0]) > 0 or len(maxes[1]) > 0:
                    if self.signal and self.signal.update_graph:
                        self.signal.update(coincidence = (len(peaks_a) * len(peaks_b) > 0))

                if time_differences_n > 0:

                    if self.collect_data:
                        self._save_time_histogram_data(map(str, time_differences))

                    # COINCIDENCE SPECTRUM A
                    new_maxes = [(voltage_range_a * x / self.spectrum_time_window) for x in maxes[0]]
                    self.time_difference_spectrum_data_a.extendleft(new_maxes)
                    y, x = np.histogram(self.time_difference_spectrum_data_a, bins = np.linspace(0, voltage_range_a, self.spectra_bin_count))
                    if self.logarithmic_y_scale == 0 or len(self.time_difference_spectrum_data_a) < 2:
                        self.time_difference_spectrum_plot_a.setData(x, y)
                    else:
                        self.time_difference_spectrum_plot_a.setData(*self.log(x, y, voltage_range_a))
                    #self.time_difference_spectrum_plot.setLabel('left', "Channel A counts (%s)" % len(self.time_difference_spectrum_data_a))

                    # COINCIDENCE SPECTRUM B
                    new_maxes = [(voltage_range_b * x / self.spectrum_time_window) for x in maxes[1]]
                    self.time_difference_spectrum_data_b.extendleft(new_maxes)
                    y, x = np.histogram(self.time_difference_spectrum_data_b, bins = np.linspace(0, voltage_range_b, self.spectra_bin_count))
                    if self.logarithmic_y_scale == 0 or len(self.time_difference_spectrum_data_b) < 2:
                        self.time_difference_spectrum_plot_b.setData(x, y)
                    else:
                        self.time_difference_spectrum_plot_b.setData(*self.log(x, y, voltage_range_b))

                    self.time_difference_spectrum_plot.setLabel('right', self.coincidence_count_graph_label % (self.signal_spectrum_clicks_coincidences, self.logarithmic_scale if max(y) > self.logarithmic_scale_threshold else ""))

                    # TIME DIFFERENCE HISTOGRAM
                    self.histogram_data.extend(time_differences)
                    y, x = np.histogram(self.histogram_data, bins = np.linspace(-self.time_window, self.time_window, self.bin_count))
                    if self.logarithmic_y_scale == 0 or len(self.histogram_data) < 2:
                        self.histogramplotp.setData(x, y)
                    else:
                        self.histogramplotp.setData(*self.log(x, y, self.time_window))

                    self.histogramplot.setLabel('left', self.coincidence_count_graph_label % (self.signal_spectrum_clicks_coincidences, self.logarithmic_scale if max(y) > self.logarithmic_scale_threshold else ""))

                    # Adding spots to the scatter plot.
                    scatter = pg.ScatterPlotItem(pxMode=False)
                    for a, b in zip(maxes[0], maxes[1]):
                        scatter.addPoints([{
                            'pos': (
                                # Change digital value to voltage.
                                voltage_range_a * a / self.spectrum_time_window,
                                voltage_range_b * b / self.spectrum_time_window
                            ),
                            'pen': None,
                            'size': .25,
                            # Change color of the spot depending on what channel was triggered.
                            'brush': self.symbolBrush[triggers[5]] if triggers[5] != None else 'w'
                        }])
                    self.scatterplot.addItem(scatter)

                self.signal_spectrum_acquire_event.clear()

            # Line graph GUI update - collect data for a second and then come here inside if clause.
            now = tm()


            if now - self.lasttime > self.interval:

                self.total_experiment_time = tm() - self.collect_start_time
                self.total_single_clicks_detector_a = self.signal_spectrum_clicks_detector_a
                self.total_single_clicks_detector_b = self.signal_spectrum_clicks_detector_b
                self.total_coincident_clicks_detectors = self.signal_spectrum_clicks_coincidences

                self.set_singles_rate_detector_a()
                self.set_singles_rate_detector_b()

                self.update_results()

                if self.collect_data:
                    self.save_experiment_data()

                # Init plot data.
                data = [0, 0, 0]

                # Add all collected data from channels_pulse_height_value_data.
                for channels_data in self.channels_pulse_height_value_data[:]:
                    for channel, value in enumerate(channels_data):
                        data[channel] += value

                # Remove last value and add new to the start of the stack.
                for channel in range(3):
                    self.plot_values[channel].pop(0)
                    self.plot_values[channel].append(data[channel])
                    if self.collect_data:
                        self._save_time_graph_data(map(str, [now - self.collect_start_time, channel, data[channel]]))

                # Reset values.
                self.channels_pulse_height_value_data = []
                self.lasttime = now;

                # Forward pointer in the line graph.
                self.pointer += 1

                self.lineplot.setLabel('bottom', self.timeline_bottom_label % timedelta(seconds = int(round(self.total_experiment_time, 0))))

                # A (SCA C).
                self.lineplota.setPos(self.pointer, 0)
                self.lineplota.setData(self.plot_values[0])
                # B (SCA D).
                self.lineplotb.setPos(self.pointer, 0)
                self.lineplotb.setData(self.plot_values[1])
                # A & B coincidence.
                self.lineplotc.setPos(self.pointer, 0)
                self.lineplotc.setData(self.plot_values[2])

                self.rate_bar_graph.setOpts(height = data)

                for channel, label in enumerate(self.rate_graph_labels):
                    label['item'].setColor('w' if data[channel] > 0 else label['pen'])

                m = max((self.clicks_detector_a_s, self.clicks_detector_b_s, self.clicks_detector_a_b_s))
                if m > self.max_rate_bar_graph_nodes_yrange:
                    self.bargraph.setYRange(0, m)
                    self.max_rate_bar_graph_nodes_yrange = m

                self.clicks_detector_a_avg = self.total_single_clicks_detector_a / self.clicks_detector_n
                self.clicks_detector_b_avg = self.total_single_clicks_detector_b / self.clicks_detector_n
                self.clicks_detector_a_b_avg = self.total_coincident_clicks_detectors / self.clicks_detector_n

                self.clicks_detector_n += 1

                # # Setting data to the signal max rate graph item.
                # self.max_rate_bar_graph_nodes.setData(
                #     pos = [[1, self.clicks_detector_a_avg], [2, self.clicks_detector_b_avg]],
                #     size = self.rate_bar_size,
                #     pxMode = False,
                #     symbol = 't',
                #     symbolSize = .1,
                #     symbolPen = self.symbolBrush[:2],
                #     symbolBrush = 'w'
                # )

                labels = [self.clicks_detector_a_avg, self.clicks_detector_b_avg, self.clicks_detector_a_b_avg]
                for channel, label in enumerate(self.rate_graph_labels):
                    label['item'].setPos(channel + 1 - .15, self.max_rate_bar_graph_nodes_yrange / 8)
                    label['item'].setText(str(round(labels[channel], 2)))

                # 1. background
                if self.start_measurement1:
                    self.set_background_rate()
                # 2. true coincidence test
                elif self.start_measurement2:
                    self.set_corrected_experiment_rate()
                # 3. unquantum effect
                elif self.start_measurement3:
                    self.set_unquantum_effect()
                else:
                    self.set_background_rate()

                self.clicks_detector_a_s = 0
                self.clicks_detector_b_s = 0
                self.clicks_detector_a_b_s = 0

                self.set_window_status_bar()

        # Update frames per second label in status bar.
        self._fps()
        QtCore.QTimer.singleShot(1, self._update)
        self.counter += 1
