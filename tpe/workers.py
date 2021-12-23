#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np
import sys, os, signal
from datetime import datetime
from random import randint as random, uniform
from pyqtgraph.Qt import QtGui
from time import sleep
from . gui import App
from . functions import baseline_correct, filter_spectrum

# Make random number more random with the seed.
np.random.seed(19680801)

# Simulator worker for pulse rate meter, channel line graph,
# time difference and detector spectrum histograms.
def simulator_worker(arguments, verbose):

    print("Simulator worker starting...")

    # Gather events and values to lessen dictionary loop ups in the while loop.
    settings_acquire_event = arguments['settings_acquire_event']
    settings_acquire_value = arguments['settings_acquire_value']

    time_difference_acquire_event = arguments['time_difference_acquire_event']
    time_difference_acquire_value = arguments['time_difference_acquire_value']

    channels_pulse_height_acquire_event = arguments['channels_pulse_height_acquire_event']
    channels_pulse_height_acquire_value = arguments['channels_pulse_height_acquire_value']

    channels_signal_rate_acquire_event = arguments['channels_signal_rate_acquire_event']
    channels_signal_rate_acquire_value = arguments['channels_signal_rate_acquire_value']

    signal_spectrum_acquire_event = arguments['signal_spectrum_acquire_event']
    signal_spectrum_acquire_value = arguments['signal_spectrum_acquire_value']

    settings = settings_acquire_value['value']

    try:

        while settings['sub_loop']:

            # It is possible to pause data retrieval from the application menu.
            if not settings['pause']:

                # retrieve channel 3 and 4 data for the time difference histogram

                # random value weighting normal distribution, gives values from -0.5, 0.5
                # * 25 + 100 to shift to 0 - 200
                time_difference_acquire_value["value"] = [
                    np.random.normal(size=1)[0] * 25 + 100
                ]
                time_difference_acquire_event.set()

                # retrieve channel 1 and 2 data for the spectrum
                signal_spectrum_acquire_value["value"] = (
                    [random(0, 20000) for i in range(1000)],
                    [random(0, 20000) for i in range(1000)],
                    [random(0, 20000) for i in range(1000)],
                    [random(0, 20000) for i in range(1000)]
                )
                signal_spectrum_acquire_event.set()

                # retrieve channel 1-4 data for the pulse rate meter
                # TODO: channels 1-2 are not needed until there is a programmable
                # trigger made to determine pulse rate
                channels_signal_rate_acquire_value["value"] = (
                    # channel 1-2 are raw signal counters
                    random(0, 20),
                    random(0, 15),
                    # channel 3-4 are SCA square wave pulse signal counters
                    random(0, 20),
                    random(0, 25),
                    # channel 5 is channel 3+4 time difference counter
                    random(0, 5)
                )
                channels_signal_rate_acquire_event.set()

                # channels 1-4, 3+4
                channels_pulse_height_acquire_value["value"] = (
                    random(10, 20),
                    random(20, 50),
                    random(30, 40),
                    random(15, 35),
                    random(0, 5)
                )
                channels_pulse_height_acquire_event.set()

            # Pause, sub loop or main loop can be triggers in the application.
            # In those cases other new settings might be arriving too like
            # a new playback file etc.
            if settings_acquire_event.is_set():
                settings = settings_acquire_value['value']
                if verbose:
                    print(settings)
                settings_acquire_event.clear()

            # Sleep a moment in a while loop to prevent halting the process.
            sleep(uniform(settings['sleep'][0], settings['sleep'][1]))

    except Exception as e:
        pass

def _playback_worker(playback_buffers, arguments, settings, verbose):

    # Gather events and values to lessen dictionary loop ups in the while loop.
    settings_acquire_event = arguments['settings_acquire_event']
    settings_acquire_value = arguments['settings_acquire_value']

    time_difference_acquire_event = arguments['time_difference_acquire_event']
    time_difference_acquire_value = arguments['time_difference_acquire_value']

    channels_pulse_height_acquire_event = arguments['channels_pulse_height_acquire_event']
    channels_pulse_height_acquire_value = arguments['channels_pulse_height_acquire_value']

    channels_signal_rate_acquire_event = arguments['channels_signal_rate_acquire_event']
    channels_signal_rate_acquire_value = arguments['channels_signal_rate_acquire_value']

    signal_spectrum_acquire_event = arguments['signal_spectrum_acquire_event']
    signal_spectrum_acquire_value = arguments['signal_spectrum_acquire_value']

    # Reset settings to update values in the processes.
    settings_acquire_value['value'] = settings
    settings_acquire_event.set()

    # We will loop playback buffers meaning original data will be started again
    # from the beginning in the playback mode.
    work_buffers = playback_buffers[:]

    while settings['sub_loop']:

        # It is possible to pause data retrieval from the application menu.
        if not settings['pause']:

            if len(work_buffers) < 1:
                print('reload playback buffers')
                work_buffers = playback_buffers[:]

            # Retrieve stored playback buffers in the same order than they were saved.
            buffers = work_buffers.pop(0)

            time_difference_value = 0

            # How big buffer should be? Now it is 2 * 500 nanoseconds?
            # making one microsecond, gammas are sent one every 3,7 secs,
            # so maybe 10 microseconds is good? Time histogram width would
            # then be 10000, one bin for each nano second
            # In the final calculation, time histogram is not actually needed
            # but the rates from corected experiment and change rate compared
            # which makes unquantum effect ratio...
            # in a playback mode we don't know the inverval, time etc, so they
            # should be stored to the separate log file
            noise_level_a = 2500
            noise_level_b = 2500
            noise_level_c = 10000
            noise_level_d = 10000

            try:

                nexta = next(x[0] for x in enumerate(buffers[0]) if abs(x[1]) > noise_level_a)

                while nexta:

                        nextb = next(x[0] for x in enumerate(buffers[1]) if abs(x[1]) > noise_level_b)

                        while nextb:

                            #if nextb - nexta > 1500:

                            #print([nexta, nextb, abs(((nextb - nexta) / 10))])

                            time_difference_acquire_value["value"] = [
                                # time difference
                                abs(((nextb - nexta) / 5))
                                # random value weighting normal distribution, gives values from -0.5, 0.5
                                # * 25 + 100 to shift to 0 - 200
                                #np.random.normal(size=1)[0] * 25 + 100
                            ]
                            time_difference_acquire_event.set()

                            nextb = next(x[0] for x in enumerate(buffers[1]) if abs(x[1]) > noise_level_b and x[0] > nextb)

                        nexta = next(x[0] for x in enumerate(buffers[0]) if abs(x[1]) > noise_level_a and x[0] > nexta)

                """
                if time_difference_value == 0:

                    nexta = next(x[0] for x in enumerate(buffers[1]) if x[1] > 0)

                    if nexta:

                        #nextb = next(x[0] for x in enumerate(buffers[1]) if x[1] > 255 and x[0] > nexta)
                        nextb = next(x[0] for x in enumerate(buffers[0]) if x[1] > 255)
                        #if nextb and nextb - nexta > 1500:
                        if nextb:
                            print([nexta, nextb, nextb - nexta])
                            # time difference
                            time_difference_value = ((nextb - nexta) / 10)
                """
            except Exception as e:
                pass

            # retrieve channel 1 and 2 data for the spectrum
            signal_spectrum_acquire_value["value"] = buffers
            signal_spectrum_acquire_event.set()

            # Retrieve channel 1-4 data for the pulse rate meter
            # TODO: channels 1-2 are not needed until there is a programmable
            # trigger made to determine pulse rate
            channels_signal_rate_acquire_value["value"] = (
                # channel 1-2 are raw signal counters
                (lambda x: x if abs(x) > noise_level_a else 0)(max(buffers[0])),
                (lambda x: x if abs(x) > noise_level_b else 0)(max(buffers[1])),
                # channel 3-4 are SCA square wave pulse signal counters
                (lambda x: x if abs(x) > noise_level_c else 0)(max(buffers[2])),
                (lambda x: x if abs(x) > noise_level_d else 0)(max(buffers[3])),
                # channel 5 is channel 3+4 time difference counter
                time_difference_value
            )
            channels_signal_rate_acquire_event.set()

            # channels 1-4, 3+4
            channels_pulse_height_acquire_value["value"] = (
                # channel 1-2 are raw signal counters
                #(lambda x: 1 if x > noise_level_a else 0)(max(buffers[0])),
                #(lambda x: 1 if x > noise_level_b else 0)(max(buffers[1])),
                len(list(filter(lambda x: abs(x) > noise_level_a, buffers[0]))),
                len(list(filter(lambda x: abs(x) > noise_level_b, buffers[1]))),
                # channel 3-4 are SCA square wave pulse signal counters
                len(list(filter(lambda x: abs(x) > noise_level_c, buffers[2]))),
                len(list(filter(lambda x: abs(x) > noise_level_d, buffers[3]))),
                # channel 5 is channel 3+4 time difference counter
                time_difference_value
            )
            channels_pulse_height_acquire_event.set()

        # Pause, sub loop or main loop can be triggers in the application.
        # In those cases other new settings might be arriving too like
        # a new playback file etc.
        if settings_acquire_event.is_set():
            settings = settings_acquire_value['value']
            if verbose:
                print(settings)
            settings_acquire_event.clear()

        # Sleep a moment in a while loop to prevent halting the process.
        sleep(uniform(settings['sleep'][0], settings['sleep'][1]))

    return settings

# Playback worker
def playback_worker(arguments, playback_file, verbose):

    settings_acquire_event = arguments['settings_acquire_event']
    settings_acquire_value = arguments['settings_acquire_value']

    # Note, these are settings that MUST be given from the application!
    settings = settings_acquire_value['value']

    playback_fail = False

    while settings['main_loop']:

        if playback_fail:

            # Wait for action from the application and try using playback file again.
            if settings_acquire_event.is_set():
                settings = settings_acquire_value['value']
                settings_acquire_event.clear()
                playback_fail = False
            # If there are no setting events coming from the application,
            # we just continue in the loop and wait...

        else:

            if settings['pause']:
                settings['pause'] = False
            if not settings['sub_loop']:
                settings['sub_loop'] = True

            print('Playback file: %s' % settings['playback_file'])

            try:

                #TODO!
                print('change pickle to use csv files!')
                sys.exit(0)
                f = open(settings['playback_file'], 'rb')
                playback_buffers = pk.load(f)
                f.close()

                # _playback_worker has a while loop as long as sub_loop is True
                settings = _playback_worker(playback_buffers, arguments, settings, verbose)

                # If main_loop is true, we will continue and recall _playback_worker.
                # If not, then we are about to quit the application.

            except Exception as e:
                print("Could not open playback file: %" % settings['playback_file'])
                # Start waiting new playback file event.
                playback_fail = True

        #print(len(work_buffers))
        #print(work_buffers[0][0])
        #print(np.mean(work_buffers[0][0]))

        """

        for buffers in work_buffers:
            write_buffers(buffers, 'picoscope_data_2021_12_17_12_36.csv')

        b = load_buffers('picoscope_data_2021_12_17_12_36.csv')
        print(len(b))
        """

        # Sleep a moment in the main while loop to prevent halting the process.
        sleep(uniform(settings['sleep'][0], settings['sleep'][1]))

    return settings

# retrieve channel 1-4 data for the pulse rate meter
# 1 and 2 are voltage meters for channels A and B
# 3 and 4 are individual pulse rates for channels C and D
# 5 is a coincident pulse rate from channels C and D
# TODO: trigger made to determine pulse rate
def bc(data, limit):
    return (lambda x: x if x > limit else 0)(np.max(baseline_correct(data)))

def bf(data, limit):
    return len(list(filter(lambda x: abs(x) > limit, baseline_correct(data))))

def crossings_nonzero_pos2neg(data):
    return len(crossings_nonzero_pos2neg_list(data))

def crossings_nonzero_pos2neg_list(data):
    pos = data > 0
    return (pos[:-1] & ~pos[1:]).nonzero()[0]

def picoscope_worker(arguments, ps, picoscope_mode, verbose):

    # Gather events and values to lessen dictionary loop ups in the while loop.
    settings_acquire_event = arguments['settings_acquire_event']
    settings_acquire_value = arguments['settings_acquire_value']

    time_difference_acquire_event = arguments['time_difference_acquire_event']
    time_difference_acquire_value = arguments['time_difference_acquire_value']

    channels_pulse_height_acquire_event = arguments['channels_pulse_height_acquire_event']
    channels_pulse_height_acquire_value = arguments['channels_pulse_height_acquire_value']

    channels_signal_rate_acquire_event = arguments['channels_signal_rate_acquire_event']
    channels_signal_rate_acquire_value = arguments['channels_signal_rate_acquire_value']

    signal_spectrum_acquire_event = arguments['signal_spectrum_acquire_event']
    signal_spectrum_acquire_value = arguments['signal_spectrum_acquire_value']

    settings = settings_acquire_value['value']

    c = datetime.now()

    # Move csv file to experiment directory, might it have been finished.
    # Directory from the application or multiprocessing settings?
    csv_data_file = 'picoscope_data_%s_%s_%s_%s_%s.csv' % (c.year, c.month, c.day, c.hour, c.minute)

    while settings['main_loop']:

        try:

            settings['sub_loop'] = True

            # TODO: Own voltage for each channel!
            ps.set_channels(voltage_range = settings['picoscope']['voltage_range'])

            if picoscope_mode == 'stream':
                ps.set_buffers(buffer_size = settings['picoscope']['buffer_size'],
                               buffer_count = settings['picoscope']['buffer_count'],
                               interval = settings['picoscope']['interval'],
                               units = settings['picoscope']['units'])
            elif picoscope_mode == 'block':
                ps.set_buffers(
                    settings['picoscope']['block_mode_trigger_settings'],
                    settings['picoscope']['block_mode_timebase_settings'],
                    settings['picoscope']['advanced_trigger_settings']
                )
            else:
                print('Picoscope mode not supported. Halting the main loop.')
                settings['main_loop'] = False
                settings['sub_loop'] = False

            while settings['sub_loop']:

                # It is possible to pause data retrieval from the application menu.
                if not settings['pause']:

                    ps.start_capture(sleep_time = settings['picoscope']['sleep_time'])

                    buffers = list(ps.get_buffers())

                    noise_level_a = settings['spectrum_low_limits'][0]
                    noise_level_b = settings['spectrum_low_limits'][1]
                    noise_level_c = settings['spectrum_low_limits'][2]
                    noise_level_d = settings['spectrum_low_limits'][3]

                    time_difference_counts = 0

                    array = np.array(buffers)

                    a1 = crossings_nonzero_pos2neg_list(
                        np.array(list(
                            map(
                                lambda x: x if x > noise_level_c else 0,
                                baseline_correct(array[2])
                            )
                        ))
                    )

                    a2 = crossings_nonzero_pos2neg_list(
                        np.array(list(
                            map(
                                lambda x: x if x > noise_level_c else 0,
                                baseline_correct(array[3])
                            )
                        ))
                    )

                    time_differences = []

                    for i in a1:
                        for j in a2:
                            time_differences.append(abs(i-j))
                            time_difference_counts += 1

                    if time_difference_counts > 0:
                        time_difference_acquire_value["value"] = time_differences
                        time_difference_acquire_event.set()

                    #buffers = list(ps.get_buffers_adc2mv())
                    """

                    coincidence_channel1_counts = 0

                    # Get coincidences from A+B or C+D
                    coincidence_channel1 = buffers[2][:]
                    coincidence_channel2 = buffers[3][:]
                    coincidence_level1 = noise_level_c
                    coincidence_level2 = noise_level_d

                    time_differences = []

                    try:

                        nexta = next(x[0] for x in enumerate(coincidence_channel1) if abs(x[1]) > coincidence_level1)

                        while nexta:

                            coincidence_channel1_counts += 1

                            #print(nexta, np.mean(buffers[0]), np.mean(buffers[1]), np.mean(buffers[2]), np.mean(buffers[3]))
                            # Signal window will show only the data when it has been triggered!
                            signal_spectrum_acquire_value["value"] = buffers
                            # Save buffers as a csv file.
                            #write_buffers(buffers, csv_data_file)
                            signal_spectrum_acquire_event.set()

                            nextb = next(x[0] for x in enumerate(coincidence_channel2) if abs(x[1]) > coincidence_level2)

                            while nextb:
                                time_difference = abs(nextb - nexta)
                                #if time_difference < 1000:
                                time_differences.append(time_difference)
                                time_difference_counts += 1
                                nextb = next(x[0] for x in enumerate(coincidence_channel2) if abs(x[1]) > coincidence_level2 and x[0] > nextb)
                            nexta = next(x[0] for x in enumerate(coincidence_channel1) if abs(x[1]) > coincidence_level1 and x[0] > nexta)

                    except Exception as e:
                        pass

                    if time_difference_counts > 0:

                        time_difference_acquire_value["value"] = time_differences
                        time_difference_acquire_event.set()

                    # We might still have signal rate information in the second channel even if the
                    # coincidence trigger didn't match.

                    if coincidence_channel1_counts == 0:

                        try:
                            nexta = next(x[0] for x in enumerate(coincidence_channel2) if abs(x[1]) > coincidence_level2)

                            while nexta:

                                # Signal window will show only the data when it has been triggered!
                                #signal_spectrum_acquire_value["value"] = buffers[:]
                                # Save buffers as a csv file.
                                #write_buffers(buffers, csv_data_file)
                                #signal_spectrum_acquire_event.set()

                                nexta = next(x[0] for x in enumerate(coincidence_channel2) if abs(x[1]) > coincidence_level2 and x[0] > nexta)
                        except Exception as e:
                            pass
                    """

                    # channels_signal_rate_acquire_value and channels_pulse_height_acquire_value
                    # can be done in the GUI side with the below value...
                    signal_spectrum_acquire_value["value"] = buffers
                    # Save buffers as a csv file.
                    #write_buffers(buffers, csv_data_file)
                    signal_spectrum_acquire_event.set()

                    if np.max(array[0]) > 2048 or np.max(array[1]) > 2048:

                        channels_signal_rate_acquire_value["value"] = (
                            # channel 1-2 are raw signal counters
                            #bc(array[0], noise_level_a),
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_a else 0,
                                        baseline_correct(array[0])
                                    )
                                ))
                            ),
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_b else 0,
                                        baseline_correct(array[1])
                                    )
                                ))
                            ),
                            #bc(array[1], noise_level_b),
                            # channel 3-4 are SCA square wave pulse signal counters
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_c else 0,
                                        baseline_correct(array[2])
                                    )
                                ))
                            ),
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_d else 0,
                                        baseline_correct(array[3])
                                    )
                                ))
                            ),
                            #(lambda x: x if abs(x) > noise_level_d else 0)(max(buffers[3])),
                            # channel 5 is channel 3+4 time difference counter
                            time_difference_counts
                        )
                        channels_signal_rate_acquire_event.set()

                        # same as rate meter but now collected to the animated line graph
                        # that presents data in a second
                        channels_pulse_height_acquire_value["value"] = (
                             # channel 1-2 are raw signal counters
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_a else 0,
                                        baseline_correct(array[0])
                                    )
                                ))
                            ),
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_b else 0,
                                        baseline_correct(array[1])
                                    )
                                ))
                            ),
                            # channel 3-4 are SCA square wave pulse signal counters
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_c else 0,
                                        baseline_correct(array[2])
                                    )
                                ))
                            ),
                            crossings_nonzero_pos2neg(
                                np.array(list(
                                    map(
                                        lambda x: x if x > noise_level_d else 0,
                                        baseline_correct(array[3])
                                    )
                                ))
                            ),
                            #len(list(filter(lambda x: abs(x) > noise_level_d, buffers[3]))),
                            # channel 5 is channel 3+4 time difference counter
                            time_difference_counts
                        )
                        channels_pulse_height_acquire_event.set()

                    ps.init_capture()

                # Pause, sub loop or main loop can be triggers in the application.
                # In those cases other new settings might be arriving too like
                # a new playback file etc.
                if settings_acquire_event.is_set():
                    settings = settings_acquire_value['value']
                    # Temporarily get out from the loop.
                    settings['sub_loop'] = False
                    if verbose:
                        print(settings)
                    settings_acquire_event.clear()

                # Sleep a moment in a while loop to prevent halting the process.
                sleep(uniform(settings['sleep'][0], settings['sleep'][1]))

        except Exception as e:
            print(e)
            settings['main_loop'] = False

# Picoscope worker for pulse rate meter, channel line graph,
# time difference and detector spectrum histograms.
def multi_worker(picoscope_mode, arguments, playback_file = '', verbose = False):

    # Suppress traceback messages on application quit / ctrl-c in console.
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

    has_picoscope = False

    if picoscope_mode != None:

        import ctypes
        from ctypes import cdll
        from ctypes.util import find_library

        picoscope_model = 'ps2000'

        try:
            if sys.platform == 'win32':
                result = ctypes.WinDLL(find_library(picoscope_model))
            else:
                result = cdll.LoadLibrary(find_library(picoscope_model))
        except OSError:
            print("Please install the PicoSDK in order to use this application in oscilloscope mode."
                  "Visit: https://www.picotech.com/downloads"
                  "Tandem Piercer Experiment application is designed to work with Picoscope model 2000a."
                  "Also, make sure to install Python packages mentioned in the requirements.txt file."
                  "For graphical user interface QT4 is used which you may need to install from: https://www.qt.io/")
            exit(1)

        if picoscope_mode == 'stream':
            from . import PS2000aStreamMode as ps
        elif picoscope_mode == 'block':
            from . import PS2000aBlockMode as ps
        elif picoscope_mode == 'rapid':
            # TODO
            print('Rapid mode not implemented yet!')
            sys.exit(0)
            from . import PS2000aRapidMode as ps

        print('Opening Picoscope...')
        has_picoscope = ps.open_picoscope()

    if not has_picoscope and playback_file == '':

        print('Could not find Picoscope and playback file not given, starting simulator...')

        simulator_worker(arguments, verbose)

    elif playback_file != '':

        print('Could not find Picoscope, opening playback file...')

        playback_worker(arguments, playback_file, verbose)

    elif has_picoscope:

        print("Picoscope data acquisition starting...")

        picoscope_worker(arguments, ps, picoscope_mode, verbose)

        ps.stop_picoscope()

    else:

        print("Coul not start simulator, playback mode, or picoscope. Quiting application.")

    os.kill(arguments['main_process_id'], signal.CTRL_C_EVENT)

def write_buffers(buffers, file):
    f = open(file, 'a')
    for i, b in enumerate(buffers):
        print(*([i]+list(b)), sep = ";", file = f)
    f.close()

def load_buffers(file, buffers = [], b = []):
    with open(file, 'r') as f:
        for line in f:
            items = line.strip().split(';')
            if len(b) < 1 or items[0] != '0':
                b.append(items[1:])
            else:
                buffers.append(b)
                b = []
        if len(b) > 0:
            buffers.append(b)
    return buffers

# Start PyQT application
def main_program(application_configuration, multiprocessing_arguments):

    # Suppress traceback messages on application quit / ctrl-c in console.
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

    app = QtGui.QApplication(sys.argv)
    # Init qt app with configuration.
    c = App(application_configuration, multiprocessing_arguments)
    # Show GUI.
    c.show()
    # Start colleting data to the graphs from multiprocessing workers.
    c.start_update()
    sys.exit(app.exec_())
