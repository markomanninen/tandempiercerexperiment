#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, argparse
from multiprocessing import Process, Manager, Event
from time import strftime, sleep
from tpe.workers import multi_worker, main_program

# Add multi process targets to the list
def add_process(target, name = '', args = None):
    processes.append(Process(target=target, name=name, args=args))

# Start processes in the list
def start_sub_processes():
    for process in processes:
        process.start()
        print("Starting sub process: " + process.name + ' PID=' + str(process.pid))
        sleep(.1)

# Stop processes in the list
def stop_sub_prosesses():
    print("\nStopping processes...")
    for process in processes:
        print("Stopping sub process: " + process.name + ' PID=' + str(process.pid))
        process.terminate()
        sleep(.1)

# Process list
processes = []

class PicoScopeModes(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if value != "block" and value != "stream" and value != None:
            raise ValueError("PicoScope mode must be empty or one of these: block, stream.")
        setattr(namespace, self.dest, value)

# Main python program executed when run from the console.
def main():

    try:

        # TODO: use configuration file for start up application settings.

        # Streaming mode settings.
        buffer_size = 250
        buffer_count = 2
        units = 'NS'

        # Voltage range for each 4 channels.
        voltage_range = ('10V', '10V', '20V', '20V')

        # Block mode settings for both simple and advanced strigger.
        block_mode_timebase_settings = {
            # 10000 * (n – 2) / 125,000,000 -> n=127 -> 0.01, n=15 -> 0.00104

            # 'timebase_n': 52,
            # 'pre_trigger_samples': 6132,
            # 'post_trigger_samples': 6132,

            'timebase_n': 52,
            'pre_trigger_samples': 6132,
            'post_trigger_samples': 6132,

            #'timebase_n': 255,
            #'pre_trigger_samples': 6132,
            #'post_trigger_samples': 6132
        }

        # Set enabled 1, if you want to use simple one channel trigger.
        block_mode_trigger_settings = {
            'enabled': 1,
            'alternate_channel': True,
            'channel': 0, # 0=A, 1=B, 2=C, 3=D
            'threshold': 1024*16, #adc value
            'direction': 2, # raising
            'delay': 0,
            # With 600ms auto trigger setting we can get equal amount of triggers and data coming from both channels.
            # Value lessr than this my favor other channel.
            'auto_trigger': 1000
        }

        # Special trigger for block mode.
        # Triggers if either channel has a raising voltage over given threshold,
        # By hysteresis it is possible to wait for lowering edge under given
        # percentage until the next trigger is used.
        # Set enabled 1, if you want to use this.
        advanced_trigger_settings = {
            'enabled': 1,
            'channels': ('A', 'B'),
            'upper_threshold': 20, # mV
            'upper_hysteresis': 2.5, # %
            'auto_trigger_ms': 1000
        }

        time_window = (block_mode_timebase_settings['pre_trigger_samples'] + block_mode_timebase_settings['post_trigger_samples'])

        sca_module_settings = {
            'high_voltage': -1100,
            'front_detector': 'channel_a',
            'channel_a': {
                'coarse_gain': 8,
                'fine_gain': 3.0,
                'window': 10.0,
                'lower_level': 0.10,
                'mode': 'diff' # int
            },
            'channel_b': {
                'coarse_gain': 8,
                'fine_gain': 3.0,
                'window': 10.0,
                'lower_level': 0.10,
                'mode': 'diff' # int
            }
        }

        parser = argparse.ArgumentParser(
            description = 'Tandem Piercer Experiment similators, playback and picoscope data acquisition program.'
        )

        parser.add_argument('--file', dest='playback_file',
                            help='Default playback file to run the application')

        parser.add_argument('--bins', dest='bin_count', default=256,
                            help='Bin count for histograms')

        parser.add_argument('--time_window', dest='time_window', default=time_window,
                            help='Time window for the time difference histogram.')

        parser.add_argument('--experiment_name', dest='experiment_name', default='Tandem Piercer Experiment ' + strftime("%Y-%m-%d %H:%M:%S"),
                            help='Experiment name to identify it Default is Tandem Piercer Experiment - {datetime}.')

        parser.add_argument('--pulse_source', dest='pulse_source', default='Background',
                            help='Pulse radiation source label. For example: Cd-109 10mci. Default background.')

        if voltage_range[2] == '20V':
            default_spectrum_range = 19660 # 19660 for 12V (20V)
        else:
            default_spectrum_range = 32767 # 32767 for 10
        parser.add_argument('--spectrum_range', dest='spectrum_range', default=default_spectrum_range,
                            help='Voltage range for the spectrum histograms. Default 32767 = 2^15.')

        parser.add_argument('--spectrum_queue_size', dest='spectrum_queue_size', default=30000,
                            help='Queue size for spectrum histogram. Default 2500.')

        parser.add_argument('--picoscope_mode', dest='picoscope_mode', default=None, action=PicoScopeModes,
                            help='Picoscope mode for importing the data acqution module. \
                            Options are: block, stream. Default None.')

        parser.add_argument('--verbose', dest='verbose', default=None,
                            help='Verbose mode for showing for debug information in the console. \
                            Options are: 1, else considering false. Default None.')

        args = parser.parse_args()

        verbose = args.verbose == 1

        # Multiprocessing value manager.
        # Only values declared with Manager can be shared between processes.
        manager = Manager()

        # share application configuration dictionary between processes
        application_configuration = manager.dict()
        # how many bins there are in the histogram by default
        # bin count can be adjusted from the ui
        application_configuration["bin_count"] = args.bin_count
        # Experiment name for all measurements.
        application_configuration["experiment_name"] = args.experiment_name
        # what is the max value of the time difference in nanoseconds?
        application_configuration["time_window"] = args.time_window
        # what is the max value of the spectrum in milli voltage?
        application_configuration["spectrum_time_window"] = args.spectrum_range
        # what is the stack max size of the spectrum histogram?
        application_configuration["spectrum_queue_size"] = args.spectrum_queue_size
        # Picoscope on / off.
        # TODO: Final status of picoscope depends on the initialization of the scope.
        # If it works, then it is really on. Information should then be updated to the GUI.
        application_configuration["has_picoscope"] = args.picoscope_mode != None
        # Picoscope mode.
        application_configuration["picoscope_mode"] = args.picoscope_mode
        # Pulse radiation source.
        application_configuration["pulse_source"] = args.pulse_source
        # Low value limits for channels 1-4.
        #application_configuration["spectrum_low_limits"] = [4096, 4096, 8300, 8000]
        #application_configuration["spectrum_low_limits"] = [4096, 4096, 500, 500]
        application_configuration["spectrum_low_limits"] = [4096, 4096, 500, 500]
        #application_configuration["spectrum_high_limits"] = [default_spectrum_range, default_spectrum_range, 12850, 11920]
        #application_configuration["spectrum_high_limits"] = [default_spectrum_range, default_spectrum_range, 19660, 19660]
        application_configuration["spectrum_high_limits"] = [default_spectrum_range, default_spectrum_range, 19660, 19660]
        # Selected channels for spectrum histogram.
        # Possible options are: 1=A, 2=B, 3=C, 4=D, 5=E where
        # the channel E is a combined rate channel from A and B.
        application_configuration["spectrum_channels"] = ('A', 'B')
        application_configuration["sca_module_settings"] = sca_module_settings
        # Verbose mode.
        application_configuration["verbose"] = verbose == 1
        # Logaritmic scale for y axis.
        # 0 = linear scale
        # 1 = natural logaritm (e) (np.log1p)
        # 2 = log2
        # 3 = log10
        # 4 = amplitude spectrum (fft+abs)
        # 5 = power spectrum (fft+abs+^2)
        # 6 = phase spectrum (fft+angle).
        # TODO: there is no way to set log in GUI yet.
        # Also, it should be enabled for each graph individually.
        application_configuration["logarithmic_y_scale"] = 3
        # Is simple or advanced trigger used?
        application_configuration["trigger_mode"] = 'simple' if block_mode_trigger_settings['enabled'] == 1 else 'advanced' if advanced_trigger_settings['enabled'] else 'none'
        # Which channels are triggered?
        trigger_channels = 'A or B'
        if application_configuration["trigger_mode"] == 'simple':
            if block_mode_trigger_settings['alternate_channel']:
                trigger_channels = 'A or B alt'
            elif block_mode_trigger_settings['channel'] == 0:
                trigger_channels = 'A'
            else:
                trigger_channels = 'B'
        application_configuration["trigger_channels"] = trigger_channels

        arguments = [
            # Share signal spectrum dictionary between processes.
            'signal_spectrum_acquire_',
            # Settings tobe shared between processes, app, and scope.
            # Can be modified in the GUI widget.
            'settings_acquire_'
        ]
        multiprocessing_arguments = {}

        for key in arguments:
            # Multiprocessing event instance.
            multiprocessing_arguments[key + 'event'] = Event()
            multiprocessing_arguments[key + 'value'] = manager.dict()

        playback_file = args.playback_file if args.playback_file != None else ''

        application_configuration["playback_file"] = playback_file

        multiprocessing_arguments["main_process_id"] = os.getpid()

        multiprocessing_arguments["time_window"] = application_configuration["time_window"]

        print('Main process started: %s' % multiprocessing_arguments["main_process_id"])

        picoscope_settings = {
            'sleep_time': 0.01,
            'voltage_range': voltage_range
        }

        if application_configuration["picoscope_mode"] == 'stream':
            # Streaming mode settings:
            picoscope_settings['interval'] = 128
            picoscope_settings['units'] = units
            picoscope_settings['buffer_size'] = buffer_size
            picoscope_settings['buffer_count'] = buffer_count
        elif application_configuration["picoscope_mode"] == 'block':
            # Block mode settings:
            picoscope_settings['block_mode_trigger_settings'] = block_mode_trigger_settings
            picoscope_settings['block_mode_timebase_settings'] = block_mode_timebase_settings
            picoscope_settings['advanced_trigger_settings'] = advanced_trigger_settings

        # Note, these are settings that MUST be given from the application!
        settings = {
            'main_loop': True,
            'sub_loop': True,
            'pause': False,
            'sleep': (.00001, .00001),
            'playback_file': playback_file,
            'spectrum_low_limits': application_configuration["spectrum_low_limits"],
            'spectrum_high_limits': application_configuration["spectrum_high_limits"],
            'spectrum_channels': application_configuration["spectrum_channels"],
            # Picoscope settings
            # TODO: simplify processes in GUI, these settings could be set empty
            # If scope cannot be initialized, or if playback of similator mode is used by default.
            'picoscope': picoscope_settings,
            'sca_module': sca_module_settings
        }

        multiprocessing_arguments['settings_acquire_value']['value'] = settings
        multiprocessing_arguments['settings_acquire_event'].set()

        # Add main program and worker processes to the list.
        add_process(
            name = "main_program",
            target = main_program,
            # Args must have appended comma for multiprocessing event manager to work.
            args = (application_configuration,
                    multiprocessing_arguments,)
        )

        add_process(
            name = "multi_worker",
            target = multi_worker,
            # Args must have appended comma for multiprocessing event manager to work.
            args = (args.picoscope_mode,
                    multiprocessing_arguments,
                    playback_file,
                    verbose,)
        )

        # Start all processes that are stored to the global list.
        start_sub_processes()
        # Must have this while loop in the main program instance
        # to prevent script ending all processes.
        # This makes possible the unopened sub processes to be opened.
        while True:
            sleep(.1)

    # Catch argument parser errors.
    except ValueError as e:
        print(e)

    # Main CTRL-C interruption error handler.
    except KeyboardInterrupt:
        # You can use also ctrl-c in console to exit graphical ui.
        # ctrl-q works as a shortcut to quit application from the GUI.
        # Terminate all processes that are stored to the global process list.
        stop_sub_prosesses()
