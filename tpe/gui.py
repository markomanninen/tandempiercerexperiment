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
#from RangeSlider import QRangeSlider
from time import strftime, time as tm
#from operator import add
from collections import deque
from . functions import baseline_correct, filter_spectrum

VOLTAGE_RANGES = {
    '10MV' : 0.01,
    '20MV' : 0.02,
    '50MV' : 0.05,
    '100MV': 0.1,
    '200MV': 0.2,
    '500MV': 0.5,
    '1V'   : 1,
    '2V'   : 2,
    '5V'   : 5,
    '10V'  : 10,
    '20V'  : 20,
    '50V'  : 50
}

CHANNELS = {
    'A': 'Channel A',
    'B': 'Channel B',
    'C': 'Channel C (A SCA)',
    'D': 'Channel D (B SCA)',
    'E': 'Channels C+D'
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
    measurement1Action = menuSettings.addAction("Measurement 1 - Background rate")
    measurement1Action.triggered.connect(qtapplication.measurement1)
    measurement1Action.setShortcut('Ctrl+1')

    measurement2Action = menuSettings.addAction("Measurement 2 - True coincidence test")
    measurement2Action.triggered.connect(qtapplication.measurement2)
    measurement2Action.setShortcut('Ctrl+2')

    measurement3Action = menuSettings.addAction("Measurement 3 - Unquantum effect")
    measurement3Action.triggered.connect(qtapplication.measurement3)
    measurement3Action.setShortcut('Ctrl+3')

    measurement0Action = menuSettings.addAction("End measurements")
    measurement0Action.triggered.connect(qtapplication.end_measurements)
    measurement0Action.setShortcut('Ctrl+0')

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

    # Show results table window.
    resultAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Show results', qtapplication)
    menuData.addAction(resultAction)
    resultAction.triggered.connect(qtapplication.results)
    resultAction.setShortcut('Ctrl+W')

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
            'time_window': QtWidgets.QLineEdit(text = str(self.app.time_window)),
            'spectrum_time_window': QtWidgets.QLineEdit(text = str(self.app.spectrum_time_window)),
            'spectrum_queue_size': QtWidgets.QLineEdit(text = str(self.app.spectrum_queue_size)),
            'spectrum_low_limit_a': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[0])),
            'spectrum_low_limit_b': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[1])),
            'spectrum_low_limit_c': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[2])),
            'spectrum_low_limit_d': QtWidgets.QLineEdit(text = str(self.app.spectrum_low_limits[3]))
        }

        layout.addRow(QtWidgets.QLabel("Experiment name:"), QtWidgets.QLineEdit(text = ''))
        layout.addRow(QtWidgets.QLabel("Time histogram width:"), self.application_settings['time_window'])
        layout.addRow(QtWidgets.QLabel("Spectrum range:"), self.application_settings['spectrum_time_window'])
        layout.addRow(QtWidgets.QLabel("Spectrum queue size:"), self.application_settings['spectrum_queue_size'])

        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (A):"), self.application_settings['spectrum_low_limit_a'])
        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (B):"), self.application_settings['spectrum_low_limit_b'])
        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (C):"), self.application_settings['spectrum_low_limit_c'])
        layout.addRow(QtWidgets.QLabel("Spectrum low level limit (D):"), self.application_settings['spectrum_low_limit_d'])

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

            self.picoscopeGroupBox = QtWidgets.QGroupBox("Picoscope")
            layout = QtWidgets.QFormLayout()
            layout.addRow(QtWidgets.QLabel("Sleep time:"), self.picoscope_settings['sleep_time'])
            layout.addRow(QtWidgets.QLabel("Interval:"), self.picoscope_settings['interval'])
            layout.addRow(QtWidgets.QLabel("Units:"), self.picoscope_settings['units'])
            layout.addRow(QtWidgets.QLabel("Buffer size:"), self.picoscope_settings['buffer_size'])
            layout.addRow(QtWidgets.QLabel("Buffer count:"), self.picoscope_settings['buffer_count'])
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
        self.app.time_window = int(self.application_settings['time_window'].text())
        self.app.spectrum_time_window = int(self.application_settings['spectrum_time_window'].text())

        self.app.spectrum_low_limits = (
            int(self.application_settings['spectrum_low_limit_a'].text()),
            int(self.application_settings['spectrum_low_limit_b'].text()),
            int(self.application_settings['spectrum_low_limit_c'].text()),
            int(self.application_settings['spectrum_low_limit_d'].text())
        )

        self.app.spectrum_channels = (
            self.application_settings['spectrum_channel_1'].currentText(),
            self.application_settings['spectrum_channel_2'].currentText()
        )

        self.app.init_spectrum_histograms(int(self.application_settings['spectrum_queue_size'].text()))

        # Picoscope settings, after changing the values picoscope needs to be tarted over
        if self.app.has_picoscope:

            settings = self.app.settings_acquire_value['value']['picoscope']

            spectrum_low_limits = self.app.settings_acquire_value['value']['spectrum_low_limits']

            settings['sleep_time'] = float(self.picoscope_settings['sleep_time'].text())
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
               settings['sleep_time'] != self.original_picoscope_settings['sleep_time'] or \
               settings['interval'] != self.original_picoscope_settings['interval'] or \
               settings['units'] != self.original_picoscope_settings['units'] or \
               settings['buffer_size'] != self.original_picoscope_settings['buffer_size'] or \
               settings['buffer_count'] != self.original_picoscope_settings['buffer_count'] or \
               settings['voltage_range'] != self.original_picoscope_settings['voltage_range']:

                settings_acquire_value = self.app.settings_acquire_value['value']
                settings_acquire_value['spectrum_low_limits'] = self.app.spectrum_low_limits
                settings_acquire_value['picoscope'] = settings
                self.app.settings_acquire_value['value'] = settings_acquire_value
                self.app.settings_acquire_event.set()
                self.app.init_spectrum_histograms()
                self.app.init_pulse_rate_graph()

        self.accept()


class Signals(QtGui.QWidget):

    def __init__(self, app, *args):

        self.app = app

        QtGui.QWidget.__init__(self, *args)

        self.setWindowTitle("Tandem Piercer Experiment - Signals")

        self.layout = QtGui.QGridLayout()

        self.curves = [
            {'title': 'Channel A', 'curves': [], 'position': [0, 0], 'plot': None, 'pen': pg.mkPen('r', width=1)},
            {'title': 'Channel B', 'curves': [], 'position': [0, 1], 'plot': None, 'pen': pg.mkPen('g', width=1)},
            {'title': 'Channel C (A SCA)', 'curves': [], 'position': [1, 0], 'plot': None, 'pen': pg.mkPen('y', width=1)},
            {'title': 'Channel D (B SCA)', 'curves': [], 'position': [1, 1], 'plot': None, 'pen': pg.mkPen('w', width=1)},
        ]

        self.max_curves_in_plot = 100

        # Add curves deque and plot widget instance to the layout.
        for i, data in enumerate(self.curves):
            data['curves'] = deque([], maxlen=self.max_curves_in_plot)
            # TODO: could not find out the way to position title little bit lower.
            data['plot'] = pg.PlotWidget(title = data['title'])
            data['plot'].setYRange(-40000, 40000, padding=0)
            self.layout.addWidget(data['plot'], *data['position'])

        self.setLayout(self.layout)

        # Start refreshing the real time plot content.
        self.refresh = True

        #self.setContentsMargins(20., 20., 20., 20.)
        #self.layout.setContentsMargins(20., 20., 20., 20.)
        #self.layout.setSpacing(10.)

        #self.timer = QtCore.QTimer()
        # 50 frames per second.
        #self.timer.setInterval(100/24)
        #self.timer.timeout.connect(self.update)
        #self.timer.start()

    # Poll signal data from the main app.
    def update(self):
        if self.refresh:
            l = len(self.curves[0]['curves'])+1
            for channel, data in enumerate(self.app.signals_data):
                # Add new curve.
                self.curves[channel]['curves'].append(
                    self.curves[channel]['plot'].getPlotItem().plot(
                        pen = self.curves[channel]['pen']
                    )
                )
                self.curves[channel]['curves'][-1].setData(data)
                # If length of the curce stack is max, clear away the oldest curve.
                if l == self.max_curves_in_plot:
                    self.curves[channel]['curves'][0].clear()
                # Set alpha color of the curves to that they will eventually fade away from the graph.
                for i, curve in enumerate(self.curves[channel]['curves']):
                    curve.setAlpha((i+1)/l, False)

    def closeEvent(self, event):
        self.refresh = False
        event.accept()


class ResultsTable(QtWidgets.QTableWidget):

    def __init__(self, app, *args):

        self.app = app

        QtWidgets.QTableWidget.__init__(self, *args)

        self.setWindowTitle("Tandem Piercer Experiment - Results")

        self.refresh = True

        horizontal_headers = [
            'Background',
            'True coincidence',
            'UQE coincidence',
            'Test'
        ]
        self.setHorizontalHeaderLabels(horizontal_headers)

        vertical_headers = [
            'Time Window (ns)',
            'Background Rate',
            'Coincident Clicks',
            'Clicks Detector A',
            'Clicks Detector A',
            'Rate Detector A',
            'Rate Detector B',
            'Experiment Time (s)',
            'Change Rate',
            'Raw Experiment Rate',
            'Corrected Experiment Rate',
            'Unquantum Effect Ratio'
        ]
        self.setVerticalHeaderLabels(vertical_headers)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(100) # every 1.0 seconds
        self.timer.timeout.connect(self.update)
        self.timer.start()

        self.update()

    # Poll data from the main app.
    def update(self):
        if self.refresh:
            self.data = self.app.results_table
            self.set_data()

    def closeEvent(self, event):
        self.refresh = False
        event.accept()

    def set_data(self):
        for n, key in enumerate(sorted(self.data.keys())):
            for m, item in enumerate(self.data[key]):
                newitem = QtWidgets.QTableWidgetItem(item)
                self.setItem(m, n, newitem)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

# Graphical user interface for the application
class App(QtGui.QMainWindow):

    def __init__(self, application_configuration, multiprocessing_arguments, parent = None):

        super(App, self).__init__(parent)

        self.setWindowTitle("Tandem Piercer Experiment - Eric Reiter & Marko Manninen © 2021-2022")

        self.experiments_directory = 'experiments'
        self.experiment_directory = ''

        self.has_picoscope = True

        # Spectrum histogram width in milli voltage.
        self.spectrum_time_window = application_configuration["spectrum_time_window"]
        # Spectrum queue size.
        self.spectrum_queue_size = application_configuration["spectrum_queue_size"]
        # Time difference and spectrum histograms bin count.
        self.bin_count = application_configuration["bin_count"]
        # Time window in nanoseconds (T_w).
        self.time_window = application_configuration["time_window"]

        # Playback file.
        self.playback_file = application_configuration["playback_file"]

        self.results_table = {
            'measurement1': [],
            'measurement2': [],
            'measurement3': [],
            'test': []
        }

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

        self.topbox = QtGui.QWidget()
        layout.addWidget(self.topbox)

        self.canvas = pg.GraphicsLayoutWidget()
        layout.addWidget(self.canvas)

        self.label = QtGui.QLabel()
        layout.addWidget(self.label)

        self.mainbox.setLayout(layout)

        add_menu(self)
        add_bin_dial(self)

        self.spectrum_counter = 0

        self.spectrum1_counter = 0
        self.spectrum2_counter = 0
        self.spectrum3_counter = 0
        self.spectrum4_counter = 0

        self.spectrum_low_limits = application_configuration["spectrum_low_limits"]
        #self.spectrum_high_limits = application_configuration["spectrum_high_limits"]

        self.spectrum_channels = application_configuration["spectrum_channels"]

        #self.spectrum1_counter_limit = 15000
        #self.spectrum2_counter_limit = 15000
        #self.spectrum3_counter_limit = 1250
        #self.spectrum4_counter_limit = 1250

        #self.canvas.nextRow()

        #self.view = self.canvas.addViewBox()
        #self.view.setAspectLocked(True)
        #self.view.setRange(QtCore.QRectF(0, 0, 100, 100))

        # image plot
        #self.img = pg.ImageItem(border='w')
        #self.view.addItem(self.img)

        self.channels_pulse_height_value_data = []

        # Initialize measurement variables.
        self.start_measurement1 = False
        self.start_measurement2 = False
        self.start_measurement3 = False

        self.create_time_difference_histogram()

        self.create_pulse_rate_graph()

        self.canvas.nextRow()

        self.create_spectrum_histograms()

        self.create_line_graph()

        #discriminator_low_default = 15
        #discriminator_high_default = 45

        #self.set_discriminators((discriminator_low_default, discriminator_high_default))
        #self.discriminator_min = 0
        #self.discriminator_max = 100

        ## Now draw all points as a nicely-spaced scatter plot
        #y = pg.pseudoScatter(vals, spacing=0.15)
        #plt2.plot(vals, y, pen=None, symbol='o', symbolSize=5)
        #plt2.plot(vals, y, pen=None, symbol='o', symbolSize=5, symbolPen=(255,255,255,200), symbolBrush=(0,0,255,150))

        #  line plot
        #self.lineplot = self.canvas.addPlot()
        #self.h2 = self.lineplot.plot(pen = 'y')

        #self.graphWidget = pg.PlotWidget()
        #self.setCentralWidget(self.graphWidget)

        #### Set Data  #####################

        #self.x = np.linspace(0, 50., num = 100)

        #hour = [1,2,3,4,5,6,7,8,9,10]
        #self.x2 = np.linspace(0, 50., num = 100)

        #self.X, self.Y = np.meshgrid(self.x, self.x)

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

        self.mainbox.showMaximized()

    ###########################################################
    # Line plots for second based data retrieval and counting #
    ###########################################################

    def create_line_graph(self):

        self.lineplot1 = self.canvas.addPlot(
            colspan = 1,
            title = "Pulse rate per second (channels)",
            labels = {
                'right': "Rate / s",
                'bottom': "Time (s)"
            }
        )

        self.init_line_graph()

        leg = self.lineplot1.addLegend()

        # Replace legend paint settings.
        def paint(self, p, *args):
           p.setPen(pg.mkPen(255, 255, 255, 255))
           p.setBrush(pg.mkBrush(0, 0, 0, 255))
           p.drawRect(self.boundingRect())

        leg.paint = types.MethodType(paint, leg)

        # Initial x ticks starting from 0 in the right and having negative values up to the left
        self.pointer = -100

        self.lineplot1a = self.lineplot1.plot(pen = 'r', name = 'A', brush = pg.mkBrush((0,0,0,100)))
        self.lineplot1a.setPos(self.pointer, 0)

        self.lineplot1b = self.lineplot1.plot(pen = 'g', name = 'B')
        self.lineplot1b.setPos(self.pointer, 0)

        self.lineplot1c = self.lineplot1.plot(pen = 'y', name = 'C (SCA)')
        self.lineplot1c.setPos(self.pointer, 0)

        self.lineplot1d = self.lineplot1.plot(pen = 'w', name = 'D (SCA)')
        self.lineplot1d.setPos(self.pointer, 0)

        self.lineplot1e = self.lineplot1.plot(pen = 'b', name = 'C+D')
        self.lineplot1e.setPos(self.pointer, 0)

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.lineplot1.setMouseEnabled(x=False, y=False)

    def init_line_graph(self):
        # values for the line plots, repeat 0 n times
        self.plot_values = {0: [], 1: [], 2: [], 3: [], 4: []}
        plot_range = [0 for i in range(100)]
        self.plot_values[0] = plot_range[:]
        self.plot_values[1] = plot_range[:]
        self.plot_values[2] = plot_range[:]
        self.plot_values[3] = plot_range[:]
        self.plot_values[4] = plot_range[:]

        self.channels_pulse_height_value_data = []

    #####################################
    # Create signal spectrum histograms #
    #####################################

    def create_spectrum_histograms(self):

        self.spectrumplot = self.canvas.addPlot(
            colspan = 1,
            title = "Signal spectrum - detector A",
            labels = {
                'left': "Counts (%s)" % 0,
                'bottom': "Picoscope digital value"
            }
        )

        self.spectrum2plot = self.canvas.addPlot(
            colspan = 1,
            title = "Signal spectrum - detector B",
            labels = {
                'left': "Counts (%s)" % 0,
                'bottom': "Picoscope digital value"
            }
        )

        self.init_spectrum_histograms()

        y, x = np.histogram(self.spectrum_data, bins = np.linspace(0, self.spectrum_time_window, self.bin_count))

        self.spectrumplotp = self.spectrumplot.plot(x, y,
            stepMode = True,
            fillLevel = 0,
            brush = (0, 0, 255, 150),
            pen = pg.mkPen('b', width=0, style=None)
        )

        y, x = np.histogram(self.spectrum2_data, bins = np.linspace(0, self.spectrum_time_window, self.bin_count))

        self.spectrum2plotp = self.spectrum2plot.plot(x, y,
            stepMode = True,
            fillLevel = 0,
            brush = (0, 0, 255, 150),
            pen = pg.mkPen('b', width=0, style=None)
        )

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.spectrumplot.setMouseEnabled(x=False, y=False)
        self.spectrum2plot.setMouseEnabled(x=False, y=False)

    def init_spectrum_histograms(self, spectrum_queue_size = None):
        if spectrum_queue_size != self.spectrum_queue_size:
            queue_size = spectrum_queue_size if spectrum_queue_size != None else self.spectrum_queue_size
            self.spectrum_data = deque([], maxlen=queue_size)
            self.spectrum_data_count = 0
            self.spectrum2_data = deque([], maxlen=queue_size)
            self.spectrum2_data_count = 0

            self.spectrum1_counter = 0
            self.spectrum2_counter = 0
            self.spectrum3_counter = 0
            self.spectrum4_counter = 0

    #####################################################################
    # Create bargraph item for an average, current and max signal rates #
    #####################################################################

    def create_pulse_rate_graph(self):

        self.bargraph = self.canvas.addPlot(
            colspan = 1,
            title = "Pulse rate meter (channels)",
            labels = {
                'right': "Green=average, Red=Max, Blue=Real time"
            }
        )

        self.init_pulse_rate_graph()

        ax = self.bargraph.getAxis('bottom')
        ticks = [list(zip(range(6), ('', 'A', 'B', 'C (SCA)', 'D (SCA)', 'C+D')))]
        ax.setTicks(ticks)

        self.rate_bar_graph = pg.BarGraphItem(
            # channel count, initial values, width of the bar, color of the bar
            x = range(1, 6),
            height = [0,0,0,0,0],
            width = 0.75,
            brushes = ('r', 'g', 'y', 'w', 'b')
        )
        self.bargraph.addItem(self.rate_bar_graph)

        # Create a graph item for current rate indicators.

        self.rate_bar_graph_nodes = pg.GraphItem()
        self.bargraph.addItem(self.rate_bar_graph_nodes)

        # Define positions of the rate nodes.
        pos = np.array([[1, 0], [2, 0], [3, 0], [4, 0], [5, 0]])

        # Setting data to the graph item.
        self.symbolBrush = ['r', 'g', 'y', 'w', 'b']
        self.rate_bar_graph_nodes.setData(pos=pos, size=0.75, pxMode=False, symbol='+', symbolSize=1, symbolPen=self.symbolBrush)

        # Create a graph item for max rate indicators.
        self.max_rate_bar_graph_nodes = pg.GraphItem()
        self.bargraph.addItem(self.max_rate_bar_graph_nodes)

        # Define positions of the rate nodes.
        pos = np.array([[1, 0], [2, 0], [3, 0], [4, 0], [5, 0]])

        # Setting data to the graph item.
        self.max_rate_bar_graph_nodes.setData(pos=pos, size=0.75, pxMode=False, symbol='+', symbolSize=10, symbolPen=self.symbolBrush)

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.bargraph.setMouseEnabled(x=False, y=False)

        #self.bargraph.addLine(x=None, y=10, pen=pg.mkPen('r', width = 5))

    # Create a graph item for average rate indicators.
    def init_pulse_rate_graph(self):
        self.channels_signal_rate_value_data = {
            0: {'rate': 0, 'count': 0, 'max': 0}, # A
            1: {'rate': 0, 'count': 0, 'max': 0}, # B
            2: {'rate': 0, 'count': 0, 'max': 0}, # C (SCA)
            3: {'rate': 0, 'count': 0, 'max': 0}, # D (SCA)
            4: {'rate': 0, 'count': 0, 'max': 0}, # C+D
        }

    ####################################
    # Create time difference histogram #
    ####################################

    def create_time_difference_histogram(self):

        self.histogramplot = self.canvas.addPlot(
            colspan = 2,
            title = "Full pulse time interval histogram between detectors A & B",
            labels = {
                'left': "Total counts (%s)" % 0,
                'bottom': "Time interval (ns)"
            }
        )

        self.init_time_difference_histogram()

        # Stabilize and prevent graph from zooming when real time data is arriving.
        self.histogramplot.setMouseEnabled(x=False, y=False)

    def init_time_difference_histogram(self):

        self.histogram_data = []
        self.histogram_data_count = 0

        self.histogramplot.clear()

        # Initial values for histogram
        y, x = np.histogram(self.histogram_data, bins = np.linspace(0, self.time_window, self.bin_count))
        self.histogramplotp = self.histogramplot.plot(x, y, stepMode = True, fillLevel = 0, brush = (0, 0, 255, 150))


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
        # Measurement 1 - retrieves coincident clicks from the detectors
        # without radionuclei. Background coincidents are retrieved in the same
        # time window than the measurement 3.
        # Background rate will be used substracted from the experiment rate.
        self.background_rate = 0

        # Chance rate (R_c = R_1 * R_2 * T_w)
        # Change rate is calculated by multiplying detector a and b rates with the time window.
        # This is done with the set_change_rate method.
        self.change_rate = 0

        # Experiment rate (R_e = C_t ÷ T_t)
        # Total coincident clicks divided by time difference is done with the
        # set_experiment_rate method.
        self.experiment_rate = 0

        # Corrected experiment rate (R_r = R_e - R_b)
        # Adjustment is required to substract random coincidences caused by the background
        # radition. Background rate is substracted from the experiment rate with the
        # set_corrected_experiment_rate method.
        self.corrected_experiment_rate = 0

        # Unquantum Effect (UE = R_r ÷ R_c)
        # Measurement 3 - Final calculation is done with the ratio of the corrected rate
        # and the change rate. If corrected experiment rate is bigger than change
        # unquantum effect is greater than one. If UE rate is two or more, it indicates
        # anomaly that contradicts quantum mechanical model. QM predicts that
        # the experiment rate is about the change rate with some error margin.
        # Use set_unquantum_effect to calculate this value.
        self.unquantum_effect = 0

    def init_graphs(self):
        self.spectrum_counter = 0

        self.spectrum1_counter = 0
        self.spectrum2_counter = 0
        self.spectrum3_counter = 0
        self.spectrum4_counter = 0

        self.signals_data = [[],[],[],[]]
        self.init_line_graph()
        self.init_spectrum_histograms()
        self.init_pulse_rate_graph()
        self.init_time_difference_histogram()

    def init_detectors(self):

        # Reinitialize graphs data before starting each new measurement.
        self.init_graphs()

        # Stop collecting data, wait for new start.
        self.stop()

        # Start data collection timer. It will be running for the experiments
        # even the data file saver has not been started.
        self.collect_start_time = tm()

        # Total experiment time (T_t)
        # How long each of the experiments have been running in seconds?
        # Start clock from the experiment menu.
        self.total_experiment_time = 0

        # Total coincident clicks from detectors (C_t)
        # This value is dependant on the time window
        # We don't know how close and in which order the clicks happen in reality
        # since we don't have pico resolution, so we rely on the SCA module
        # which makes square wave pulses from the detector signals. If they happen
        # in a close enough time window, we consider them as coincident.
        # Time difference window shows the distribution of the coincident clicks
        # but the real calculation is done with the experiment and change rate comparison.
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

    # Measurement 2 - Sandwich (true coincidence) test is done by using two
    # detectors each side of the radinuclei. Only single gammas should be sent
    # by the isotope so that there are no coincident clicks in detectors except
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

    # EXPERIMENT MENU ACTIONS

    # Background coincidence rate
    def measurement1(self):
        self.init_measurements()
        self.init_data_saving()
        self.start_measurement1 = True
        self.start_measurement2 = False
        self.start_measurement3 = False

    # True coincidence test
    def measurement2(self):
        self.init_detectors()
        self.start_measurement1 = False
        self.start_measurement2 = True
        self.start_measurement3 = False

    # Unquantum effect
    def measurement3(self):
        self.init_detectors()
        self.start_measurement1 = False
        self.start_measurement2 = False
        self.start_measurement3 = True

    def end_measurements(self):
        # stop collecting data, wait for new start
        self.stop()
        self.start_measurement1 = False
        self.start_measurement2 = False
        self.start_measurement3 = False
        self.experiment_directory = ''
        self.results()

    # Measurement data is polled from the results window every .5 seconds.
    def update_results(self):
        self.results_table[self.measurement_name] = map(str, [
            self.time_window,
            round(self.background_rate, 1), # convert to seconds?
            self.total_coincident_clicks_detectors,
            self.total_single_clicks_detector_a,
            self.total_single_clicks_detector_b,
            round(self.total_singles_rate_detector_a, 1), # convert to seconds?
            round(self.total_singles_rate_detector_b, 1), # convert to seconds?
            round(self.total_experiment_time, 1),
            round(self.change_rate, 1), # convert to seconds?
            round(self.experiment_rate, 1), # convert to seconds?
            round(self.corrected_experiment_rate, 1), # convert to seconds?
            round(self.unquantum_effect, 1)
        ].copy())

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
            'low_limits': self.spectrum_low_limits,
            # Picoscope settings
            'picoscope': {}
        }

        self.settings_acquire_event.set()

        print('open_playback_file')


    # RESULTS MENU

    def results(self):
        if not self.table:
            self.table = ResultsTable(self, 12, 4, self)
            self.table.setWindowFlags(self.table.windowFlags() | QtCore.Qt.Window)
        self.table.refresh = True
        self.table.show()

    # SIGNALS MENU

    def signals(self):
        if not self.signal:
            self.signal = Signals(self)
            self.signal.setWindowFlags(self.signal.windowFlags() | QtCore.Qt.Window)
        self.signal.refresh = True
        self.signal.show()

    # SETTINGS MENU

    def settings(self):
        if not self.setting:
            self.setting = Settings(self)
            self.setting.setWindowFlags(self.setting.windowFlags() | QtCore.Qt.Window)
        self.setting.show()

    # Total experiment time must be set before calling single rates methods and
    # background rate. Total coincident clicks must be set before calling background
    # rate and experiment rate
    def set_background_rate(self):
        self.background_rate = self.total_coincident_clicks_detectors / self.total_experiment_time
        return self.background_rate

    # Total experiment time must be set before calling single rates methods
    def set_singles_rate_detector_a(self):
        self.total_singles_rate_detector_a = self.total_single_clicks_detector_a / self.total_experiment_time

    def set_singles_rate_detector_b(self):
        self.total_singles_rate_detector_b = self.total_single_clicks_detector_a / self.total_experiment_time

    # Change rate and experiment rates are used both the true coincidence test and
    # the unquantum measurement
    def set_change_rate(self):
        self.change_rate = self.total_singles_rate_detector_a * self.total_singles_rate_detector_b * self.time_window
        return self.change_rate

    def set_experiment_rate(self):
        self.set_change_rate()
        self.experiment_rate = self.total_coincident_clicks_detectors / self.total_experiment_time
        return self.experiment_rate

    def set_corrected_experiment_rate(self):
        self.set_experiment_rate()
        self.corrected_experiment_rate = self.experiment_rate - self.background_rate
        return self.corrected_experiment_rate

    # Unquantum effect measurement is used solely by the measurement 3
    def set_unquantum_effect(self):
        self.set_corrected_experiment_rate()
        self.unquantum_effect = 0 if self.change_rate == 0 else (self.corrected_experiment_rate / self.change_rate)
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
        text = 'Experiment started: ' + self.start_time_str
        text += '| Frame Rate:  {fps:.1f} FPS'.format(fps = self.fps)
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
            'low_limits': self.spectrum_low_limits,
            # Picoscope settings
            'picoscope': picoscope
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
            'low_limits': self.spectrum_low_limits,
            # Picoscope settings
            'picoscope': picoscope
        }
        self.settings_acquire_event.set()

    def stop(self):
        self.collect_data = False

    def start(self):

        self.collect_start_time = tm();
        self.collect_data = True

        if self.experiment_directory == '':
            self.init_data_saving()

        self.measurement_name = ''
        if self.start_measurement1:
            self.measurement_name = 'measurement1'
        elif self.start_measurement2:
            self.measurement_name = 'measurement2'
        elif self.start_measurement3:
            self.measurement_name = 'measurement3'
        else:
            # If measurement is not set, we are running in test mode.
            self.measurement_name = 'test'
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
                self.change_rate, # convert to seconds?
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
            'change_rate',
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
            'low_limits': (),
            # Picoscope settings
            'picoscope': {}
        }
        self.settings_acquire_event.set()
        # Native close method call.
        self.close()

    # Main program window close button.
    def closeEvent(self, event):
        self.quit()
        event.accept()

    # MAIN GUI UPDATE LOOP
    def _update(self):

        if not self.settings_acquire_value['value']['pause']:

            # Signal spectrum histogram event and GUI update.
            if self.signal_spectrum_acquire_event.is_set():

                data = self.signal_spectrum_acquire_value["value"]

                #self.signals_data = [
                #    list(map(lambda x: x if x > self.spectrum_low_limits[i] else 0, (lambda x: x - x.mean())(np.array(d)))) for i, d in enumerate(data)
                #]

                if max(data[0]) > 2048 or max(data[1]) > 2048:

                    self.signals_data = list(
                        map(
                            lambda x:
                                list(
                                    map(
                                        lambda x: x if abs(x) > 2048 else 0,
                                        x - x.mean()
                                    )
                                ),
                            np.array(data)
                        )
                    )

                    if self.signal and self.signal.refresh:
                        self.signal.update()

                    if self.collect_data:
                        for channel, value in enumerate(data):
                            self._save_channel_spectrums_data([str(channel), ','.join(map(str, value))])

                    np_data = np.array(data)

                    self.spectrum_data.extendleft(filter_spectrum(baseline_correct(np_data[0]), 'spectrum1_counter', self.spectrum_low_limits[2], self))
                    y, x = np.histogram(self.spectrum_data, bins = np.linspace(0, self.spectrum_time_window, self.bin_count))
                    self.spectrumplotp.setData(x, y)
                    self.spectrumplot.setLabel('left', "Counts (%s)" % self.spectrum1_counter)

                    self.spectrum2_data.extendleft(filter_spectrum(baseline_correct(np_data[1]), 'spectrum2_counter', self.spectrum_low_limits[3], self))
                    y, x = np.histogram(self.spectrum2_data, bins = np.linspace(0, self.spectrum_time_window, self.bin_count))
                    self.spectrum2plotp.setData(x, y)
                    self.spectrum2plot.setLabel('left', "Counts (%s)" % self.spectrum2_counter)

                self.signal_spectrum_acquire_event.clear()

            # Time difference histogram event and GUI update.
            if self.time_difference_acquire_event.is_set():

                data = self.time_difference_acquire_value["value"]

                if self.collect_data:
                    self._save_time_histogram_data(map(str, data))

                self.histogram_data.extend(data)
                self.histogram_data_count += len(data)
                y, x = np.histogram(self.histogram_data, bins = np.linspace(0, self.time_window, self.bin_count))
                self.histogramplotp.setData(x, y)
                self.histogramplot.setLabel('left', "Counts (%s)" % self.histogram_data_count)
                self.time_difference_acquire_event.clear()

            # Line graph event update.
            if self.channels_pulse_height_acquire_event.is_set():
                self.channels_pulse_height_value_data.append(self.channels_pulse_height_acquire_value['value'])
                self.channels_pulse_height_acquire_event.clear()

            # Signal rate meter graph event and GUI update.
            if self.channels_signal_rate_acquire_event.is_set():

                channels_signal_rate_value_latest = self.channels_signal_rate_acquire_value['value']

                if self.collect_data or any((self.start_measurement1, self.start_measurement2, self.start_measurement3)):

                    self.total_experiment_time = tm() - self.collect_start_time

                    self.total_single_clicks_detector_a += channels_signal_rate_value_latest[2]
                    self.total_single_clicks_detector_b += channels_signal_rate_value_latest[3]

                    self.total_coincident_clicks_detectors += channels_signal_rate_value_latest[4]

                    self.set_singles_rate_detector_a()
                    self.set_singles_rate_detector_b()

                # 1. background
                if self.start_measurement1:
                    self.set_background_rate()
                # 2. true coincidence test
                elif self.start_measurement2:
                    self.set_corrected_experiment_rate()
                # 3. unquantum effect
                elif self.start_measurement3:
                    self.set_unquantum_effect()

                average_rates = []
                max_rates = []

                # update average rate bar graph item with the latest rate indicator line
                # and the max rate line
                for channel, rate in enumerate(channels_signal_rate_value_latest):

                        channel_rate_data = self.channels_signal_rate_value_data[channel]
                        channel_rate_data['rate'] = (channel_rate_data['rate'] * channel_rate_data['count'] + rate) / \
                                                    (channel_rate_data['count'] + 1)
                        channel_rate_data['count'] += 1

                        if rate > channel_rate_data['max']:
                            channel_rate_data['max'] = rate

                        if self.collect_data:
                            self._save_pulse_rate_data(map(str, [channel, rate, channel_rate_data['rate']]))

                        average_rates.append(channel_rate_data['rate'])
                        max_rates.append(channel_rate_data['max'])

                self.rate_bar_graph.setOpts(height = average_rates)

                #print(channels_signal_rate_value_latest)

                # Setting data to the signal rate graph item.
                self.rate_bar_graph_nodes.setData(
                    pos = [[i+1, x] for i, x in enumerate(channels_signal_rate_value_latest)],
                    size=0.75, pxMode=False, symbol='+', symbolSize=1, symbolPen=self.symbolBrush
                )

                # Setting data to the signal max rate graph item.
                self.max_rate_bar_graph_nodes.setData(
                    pos = [[i+1, x] for i, x in enumerate(max_rates)],
                    size=0.75, pxMode=False, symbol='+', symbolSize=10, symbolPen=self.symbolBrush
                )

                # clear event and wait for the next one from the worker
                self.channels_signal_rate_acquire_event.clear()

            #self.data = np.sin(self.X / 3. + self.counter / 9.) * np.cos(self.Y / 3. + self.counter / 9.)
            #self.img.setImage(self.data)

            #self.ydata = np.sin(self.x / 3. + self.counter / 9.)
            #self.h2.setData(self.y in self.data)

            # Line graph GUI update - collect data for a second and then come here inside if clause
            now = tm()
            if now - self.lasttime > self.interval:

                #low, high = self.discriminator_values

                if self.collect_data:
                    self.update_results()
                    self.save_experiment_data()

                # channels 1-4 init data
                data = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

                # add all collected data from channels_pulse_height_value_data
                for channels_data in self.channels_pulse_height_value_data[:]:
                    for channel, value in enumerate(channels_data):
                        data[channel] += value

                # plot collected values as one
                for channel in range(5):
                    self.plot_values[channel].pop(0)
                    self.plot_values[channel].append(data[channel])
                    if self.collect_data:
                        self._save_time_graph_data(map(str, [now - self.collect_start_time, channel, data[channel]]))

                # reset values
                self.channels_pulse_height_value_data = []

                self.lasttime = tm();

                # update plots
                self.pointer += 1

                # Line plot 1 a, b, c, d
                self.lineplot1a.setPos(self.pointer, 0)
                self.lineplot1a.setData(self.plot_values[0])

                self.lineplot1b.setPos(self.pointer, 0)
                self.lineplot1b.setData(self.plot_values[1])

                self.lineplot1c.setPos(self.pointer, 0)
                self.lineplot1c.setData(self.plot_values[2])

                self.lineplot1d.setPos(self.pointer, 0)
                self.lineplot1d.setData(self.plot_values[3])

                self.lineplot1e.setPos(self.pointer, 0)
                self.lineplot1e.setData(self.plot_values[4])

                # window status bar
                self.set_window_status_bar()

        # update frames per second label
        self._fps()
        QtCore.QTimer.singleShot(1, self._update)
        self.counter += 1
