#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, argparse
from multiprocessing import Process, Manager, Event
from time import sleep
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
    print("Stopping processes...")
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

        # TODO use configuration file for start up application settings.

        buffer_size = 500
        buffer_count = 4
        units = 'US'
        voltage_range = ('10V', '10V', '10V', '10V')

        block_mode_trigger_settings = {
            'enabled': 1,
            'channel': 2, # 0=A, 1=B, 2=C, 3=D
            'threshold': 1024*16, #adc value
            'direction': 2, # raising
            'delay': 0,
            'auto_trigger': 100
        }

        block_mode_timebase_settings = {
            'timebase_n': 8,
            'pre_trigger_samples': 5000,
            'post_trigger_samples': 5000
        }

        # Special trigger for channels C and D.
        # Triggers if either channel has raising over given threshold,
        # By hysteresis it is possible to wait for lowering edge under given
        # percentage until next trigger is used.
        advanced_trigger_settings = {
            'upper_threshold': 20,
            'upper_hysteresis': 2.5,
            'auto_trigger_ms': 100
        }

        parser = argparse.ArgumentParser(
            description = 'Tandem Piercer Experiment similators, playback and picoscope data acquisition program.'
        )

        parser.add_argument('--file', dest='playback_file',
                            help='Default playback file to run the application')

        parser.add_argument('--bins', dest='bin_count', default=128,
                            help='Bin count for histograms')

        parser.add_argument('--time_window', dest='time_window', default=buffer_size*buffer_count,
                            help='Time window for time difference histogram. Default 500 ns.')

        parser.add_argument('--spectrum_range', dest='spectrum_range', default=35000,
                            help='Voltage range for spectrum histogram. Default 35000adc.')

        parser.add_argument('--spectrum_queue_size', dest='spectrum_queue_size', default=10000,
                            help='Queue size for spectrum histogram. Default 10000.')

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
        # what is the max value of the time difference in nanoseconds?
        application_configuration["time_window"] = args.time_window
        # what is the max value of the spectrum in milli voltage?
        application_configuration["spectrum_time_window"] = args.spectrum_range
        # what is the stack max size of the spectrum histogram?
        application_configuration["spectrum_queue_size"] = args.spectrum_queue_size
        # Picoscope on / off
        application_configuration["has_picoscope"] = args.picoscope_mode != None
        # Low value limits for channels 1-4.
        application_configuration["spectrum_low_limits"] = (512, 512, 512, 512)
        # Selected channels for spectrum histogram.
        # Possible options are: 1=A, 2=B, 3=C, 4=D, 5=E where
        # the channel E is a combined rate channel from C and D.
        application_configuration["spectrum_channels"] = ('A', 'B')
        # Verbose mode.
        application_configuration["verbose"] = verbose == 1

        arguments = [
            # Share time difference dictionary between processes.
            'time_difference_acquire_',
            # Share channel pulse height dictionary between processes.
            'channels_pulse_height_acquire_',
            # Share channel signal rate dictionary between processes.
            'channels_signal_rate_acquire_',
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

        print('Main process started: %s' % multiprocessing_arguments["main_process_id"])

        # Note, these are settings that MUST be given from the application!
        settings = {
            'main_loop': True,
            'sub_loop': True,
            'pause': False,
            'sleep': (.01, .1),
            'playback_file': playback_file,
            'spectrum_low_limits': application_configuration["spectrum_low_limits"],
            'spectrum_channels': application_configuration["spectrum_channels"],
            # Picoscope settings
            'picoscope': {
                'voltage_range': voltage_range,
                # Streaming mode settings:
                'sleep_time': 0.01,
                'interval': 128,
                'units': units,
                'buffer_size': buffer_size,
                'buffer_count': buffer_count,
                'block_mode_trigger_settings': block_mode_trigger_settings,
                'block_mode_timebase_settings': block_mode_timebase_settings,
                'advanced_trigger_settings': advanced_trigger_settings,
            }
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
