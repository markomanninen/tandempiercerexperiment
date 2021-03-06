#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np
import sys, os, signal
# Prevent long console error output on quit
# forrtl: error (200): program aborting due to control-C event
# Still some lines are output but better than without this fix.
os.environ["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"

from datetime import datetime
from random import randint as random, uniform
from pyqtgraph.Qt import QtGui
from time import sleep, time as tm
from . gui import App
from . functions import baseline_correction_and_limit, \
                        raising_edges_for_raw_pulses, \
                        raising_edges_for_square_pulses, \
                        get_max_heights_and_time_differences, \
                        load_buffers, write_buffers

# For nicer console output.
import colorama
colorama.init()

# Make random number more random with the seed.
np.random.seed(19680801)

def process_buffers(buffers, settings, arguments, trigger_channel,
                    signal_spectrum_acquire_value, signal_spectrum_acquire_event):

    l1, l2, m1, m2, pulse_heights, time_differences = \
        get_max_heights_and_time_differences(
            buffers,
            settings["spectrum_low_limits"],
            settings["spectrum_high_limits"],
            arguments["pulse_detection_mode"]
        )
    # Auto trigger setting forces trigger to release in Picoscope after certain amount of time,
    # if there was no activity, and PS will try again.
    # Thus, data may be empty and it will be unnecessary to send it to GUI.
    if (l1 > 0 or l2 > 0) and not arguments["headless_mode"]:
        # Pass raw signal data without any correction and limits to the plotter and
        # spectrum. Actually, the time difference part can also be moved to the GUI
        # multi processing thread so that this part of the retrieving data from picoscope
        # is as simple and streamlined as possible.
        signal_spectrum_acquire_value["value"] = (
            buffers,
            (l1, l2, time_differences,
                #[bcl[2][i] for i in a1],
                #[bcl[3][i] for i in a2],
                [m1] if l1 > 0 else [],
                [m2] if l2 > 0 else [],
                trigger_channel
            )
        )
        signal_spectrum_acquire_event.set()

    return (l1, l2, time_differences, pulse_heights)

def __process_buffers(buffers, settings, arguments, trigger_channel,
                    signal_spectrum_acquire_value, signal_spectrum_acquire_event):

    time_differences = [] #(np.random.normal(size=1)[0] * 25)
    pulse_heights = [] #(np.random.normal(size=1)[0] * 25)

    #bcl = list(map(lambda x: baseline_correction_and_limit(*x), zip(buffers, settings["spectrum_low_limits"], settings["spectrum_high_limits"])))
    bcl = buffers
    #a1 = raising_edges_for_raw_pulses(bcl[2])
    #a2 = raising_edges_for_raw_pulses(bcl[3])
    a1 = raising_edges_for_square_pulses(np.array(bcl[0]), 8192)
    a2 = raising_edges_for_square_pulses(np.array(bcl[1]), 8192)

    l1 = len(a1)
    l2 = len(a2)

    m1 = max(bcl[2])
    m2 = max(bcl[3])

    pulse_heights.append((m1, m2))

    #if m1 < settings["spectrum_low_limits"][2] or m1 > settings["spectrum_high_limits"][2]:
    #    l1 = 0
    #if m2 < settings["spectrum_low_limits"][3] or m2 > settings["spectrum_high_limits"][3]:
    #    l2 = 0

    # If there is a square pulse on both SCA channels,
    # calculate the time difference between the pulses.
    if l1 > 0 and l2 > 0:
        for i in a1:
            for j in a2:
                time_differences.append((i-j)) # 2ns!
                if bcl[2][i] == 0 or bcl[3][j] == 0:
                    pass
                    # Debug possible empty raw data channels, even if they were triggered.
                    # There might be occasional cases when in that certain index there is zero value
                    # but then just before or after there is currant value.
                    # print(
                    #     "empty",
                    #     "idx", (i, j, i-j),
                    #     "val", (bcl[0][i], bcl[1][j], bcl[2][i], bcl[3][j]),
                    #     "max", (max(bcl[0]), max(bcl[1]), max(bcl[2]), max(bcl[3]))
                    # )

    # Auto trigger setting forces trigger to release in Picoscope after certain amount of time,
    # if there was no activity, and PS will try again.
    # Thus, data may be empty and it will be unnecessary to send it to GUI.
    if (l1 > 0 or l2 > 0) and not arguments["headless_mode"]:
        #print("valid","max", (max(bcl[0]), max(bcl[1]), max(bcl[2]), max(bcl[3])))

        # Pass raw signal data without any correction and limits to the plotter and
        # spectrum. Actually, the time difference part can also be moved to the GUI
        # multi processing thread so that this part of the retrieving data from picoscope
        # is as simple and streamlined as possible.
        signal_spectrum_acquire_value["value"] = (
            buffers,
            (l1, l2, time_differences,
                #[bcl[2][i] for i in a1],
                #[bcl[3][i] for i in a2],
                [m1] if l1 > 0 else [],
                [m2] if l2 > 0 else [],
                trigger_channel
            )
        )
        signal_spectrum_acquire_event.set()

    return (l1, l2, time_differences, pulse_heights)

# Simulator worker for pulse rate meter, channel line graph,
# time difference and detector spectrum histograms.
def simulator_worker(arguments, verbose):

    print("Simulator worker starting...")

    # Gather events and values to lessen dictionary loop ups in the while loop.
    settings_acquire_event = arguments["settings_acquire_event"]
    settings_acquire_value = arguments["settings_acquire_value"]

    signal_spectrum_acquire_event = arguments["signal_spectrum_acquire_event"]
    signal_spectrum_acquire_value = arguments["signal_spectrum_acquire_value"]

    settings = settings_acquire_value["value"]

    start_time = tm()

    execution_time = (start_time + arguments["execution_time"]) if arguments["execution_time"] > 0 else 0

    try:

        while settings["sub_loop"] and settings["main_loop"]:

            trigger_channel = 0
            # It is possible to pause data retrieval from the application menu.
            if not settings["pause"]:
                # random value weighting normal distribution, gives values from -0.5, 0.5
                # * 25 + 100 to shift to 0 - 200
                time_differences = [(np.random.normal(size=1)[0] * 25) + (arguments["time_window"]/2)]

                buffers = ([random(0, 20000) for i in range(1000)],
                           [random(0, 20000) for i in range(1000)],
                           [random(0, 20000) for i in range(1000)],
                           [random(0, 20000) for i in range(1000)])

                l1 = random(0, 20)
                l2 = random(0, 20)
                m1 = max(buffers[2])
                m2 = max(buffers[3])
                # Pass raw signal data without any correction and limits to the plotter and
                # spectrum. Actually, the time difference part can also be moved to the GUI
                # multi processing thread so that this part of the retrieving data from picoscope
                # is as simple and streamlined as possible.
                signal_spectrum_acquire_value["value"] = (
                    buffers,
                    (l1, l2, time_differences,
                        [m1] if l1 > 0 else [],
                        [m2] if l2 > 0 else [],
                        trigger_channel
                    )
                )
                signal_spectrum_acquire_event.set()

                # If execution time has exceeded, stop loops and application.
                if execution_time > 0 and tm() > execution_time:
                    print("Execution time (%ss) of the experiment has ended." % arguments["execution_time"])
                    settings["sub_loop"] = False
                    settings["main_loop"] = False

            # Pause, sub loop or main loop can be triggers in the application.
            # In those cases other new settings might be arriving too like
            # a new playback file etc.
            if settings_acquire_event.is_set():
                settings = settings_acquire_value["value"]
                if verbose:
                    print(settings)
                settings_acquire_event.clear()

            # Sleep a moment in a while loop to prevent halting the process.
            sleep(uniform(*settings["sleep"]))

    except Exception as e:
        print(e)
        pass

    return settings

def _playback_worker(playback_buffers, arguments, settings, verbose):

    # Gather events and values to lessen dictionary loop ups in the while loop.
    settings_acquire_event = arguments["settings_acquire_event"]
    settings_acquire_value = arguments["settings_acquire_value"]

    signal_spectrum_acquire_event = arguments["signal_spectrum_acquire_event"]
    signal_spectrum_acquire_value = arguments["signal_spectrum_acquire_value"]

    # Reset settings to update values in the processes.
    settings_acquire_value["value"] = settings
    settings_acquire_event.set()

    # We will loop playback buffers meaning original data will be started again
    # from the beginning in the playback mode.
    work_buffers = playback_buffers[:]

    start_time = tm()

    execution_time = (start_time + arguments["execution_time"]) if arguments["execution_time"] > 0 else 0

    while settings["sub_loop"]:

        # It is possible to pause data retrieval from the application menu.
        if not settings["pause"]:

            if len(work_buffers) < 1:
                print("reload playback buffers")
                work_buffers = playback_buffers[:]

            # Retrieve stored playback buffers in the same order than they were saved.
            # TODO: By using rotating index, we could find out the line from the file and parse
            # it for more robust and scalable version of using playback files...
            buffers = work_buffers.pop(0)

            process_buffers(buffers, settings, arguments, None,
                signal_spectrum_acquire_value, signal_spectrum_acquire_event)

            # If execution time has exceeded, stop loops and application.
            if execution_time > 0 and tm() > execution_time:
                print("Execution time (%ss) of the experiment has ended." % arguments["execution_time"])
                settings["sub_loop"] = False
                settings["main_loop"] = False

        # Pause, sub loop or main loop can be triggers in the application.
        # In those cases other new settings might be arriving too like
        # a new playback file etc.
        if settings_acquire_event.is_set():
            settings = settings_acquire_value["value"]
            if verbose:
                print(settings)
            settings_acquire_event.clear()

        # Sleep a moment in a while loop to prevent halting the process.
        sleep(uniform(*settings["sleep"]))

    return settings

# Playback worker for playing stored detector data from csv files
def playback_worker(arguments, playback_file, verbose, playback_fail = False):

    settings_acquire_event = arguments["settings_acquire_event"]
    settings_acquire_value = arguments["settings_acquire_value"]

    # Note, these are settings that MUST be given from the application!
    settings = settings_acquire_value["value"]

    while settings["main_loop"]:

        if playback_fail:

            # Wait for action from the application and try using playback file again.
            if settings_acquire_event.is_set():
                settings = settings_acquire_value["value"]
                settings_acquire_event.clear()
                playback_fail = False

            # If there are no setting events coming from the application,
            # we just continue in the loop and wait.

        else:
            # If DAQ has been paused, turn it on again.
            if settings["pause"]:
                settings["pause"] = False
            # Also if sub loop has been paused, turn it on.
            if not settings["sub_loop"]:
                settings["sub_loop"] = True

            print("Playback file: %s" % settings["playback_file"])

            try:

                # Load playback buffer data to memory and run _worker helper.
                # TODO: At the moment array.pop is ued to retrieve four channels
                # data from the momery. More scalable versions requires retrieving
                # data from file by increasing and restarted index.
                # Thus playback feature is useful for testing and development purposes
                # only since collecting real experiment data may take gigabytes of data,
                # because three measurements will take time from minutes to hours.
                playback_buffers = load_buffers(settings["playback_file"])

                # _playback_worker has a while loop as long as sub_loop is True.
                # Only when sub loop stops, settings are returned and main loop starts the phase.
                settings = _playback_worker(playback_buffers, arguments, settings, verbose)

                # If main_loop is true, we will continue and recall _playback_worker.
                # If not, then we are about to quit the application.

            except Exception as e:
                print("Could not open playback file: %" % settings["playback_file"])
                # Start waiting new playback file event.
                playback_fail = True

        # Sleep a moment in the main while loop to prevent halting the process.
        sleep(uniform(*settings["sleep"]))

    return settings

def picoscope_worker(arguments, ps, picoscope_mode, verbose):

    # Gather events and values to lessen dictionary loop ups in the while loop.
    settings_acquire_event = arguments["settings_acquire_event"]
    settings_acquire_value = arguments["settings_acquire_value"]

    signal_spectrum_acquire_event = arguments["signal_spectrum_acquire_event"]
    signal_spectrum_acquire_value = arguments["signal_spectrum_acquire_value"]

    settings = settings_acquire_value["value"]

    csv_waveform_file = os.path.join(arguments["experiments_dir"], arguments["experiment_dir"], "waveform.csv")
    csv_statistics_file = os.path.join(arguments["experiments_dir"], arguments["experiment_dir"], "statistics.csv")

    pulse_source = arguments["pulse_source"]
    chance_rate = arguments["chance_rate"]
    background_rate = arguments["background_rate"]

    while settings["main_loop"]:

        try:

            settings["sub_loop"] = True

            # TODO: Own voltage for each channel!
            ps.set_channels(voltage_range = settings["picoscope"]["voltage_range"])

            block_mode_trigger_settings = settings["picoscope"]["block_mode_trigger_settings"]

            init = True

            timebase_n = 0

            start_channel = block_mode_trigger_settings["channel"]

            rate_a, rate_b, rate_ab, counts_max_a, counts_max_b, counts_min_a, counts_min_b, rate_a_avg, rate_b_avg, rate_ab_avg = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

            rate_count = 0

            start_time = tm()

            execution_time = (start_time + arguments["execution_time"]) if arguments["execution_time"] > 0 else 0

            coincidence_count = 0

            if picoscope_mode == "stream":
                init = ps.set_buffers(buffer_size = settings["picoscope"]["buffer_size"],
                                      buffer_count = settings["picoscope"]["buffer_count"],
                                      interval = settings["picoscope"]["interval"],
                                      units = settings["picoscope"]["units"])
            elif picoscope_mode == "block":

                init = ps.set_buffers(
                        block_mode_trigger_settings,
                        settings["picoscope"]["block_mode_timebase_settings"],
                        settings["picoscope"]["advanced_trigger_settings"]
                )
                timebase_n = settings["picoscope"]["block_mode_timebase_settings"]["timebase_n"]

                if timebase_n == 2:
                    buffer_length_ns = arguments["time_window"] * 2 / 500000000
                else:
                    buffer_length_ns = arguments["time_window"] * (timebase_n - 2) / 125000000

                timebase_conversion = 1 / buffer_length_ns

                print("\n")
                console_line = "Source: %s Timebase: %s Time window: %sns Buffer length: %ss Time conversion: 1/%d"
                print(console_line % (pulse_source, timebase_n, arguments["time_window"], buffer_length_ns, timebase_conversion))
                print("\n")
            else:
                print("Picoscope mode not supported. Halting the main loop.")
                settings["main_loop"] = False
                settings["sub_loop"] = False

            if not init:
                print("Could not set buffers. Check timebase and other Picoscope settings.")
                settings["main_loop"] = False
                settings["sub_loop"] = False

            td, ph1, ph2 = (0, 0, 0)

            while settings["sub_loop"]:

                # It is possible to pause data retrieval from the application menu.
                if not settings["pause"]:

                    ps.start_capture(sleep_time = settings["picoscope"]["sleep_time"])

                    buffers = list(ps.get_buffers())

                    trigger_channel = None if block_mode_trigger_settings["enabled"] == 0 else block_mode_trigger_settings["channel"]
                    sca_a_pulse_count, sca_b_pulse_count, time_differences, pulse_heights = \
                        process_buffers(
                            buffers,
                            settings,
                            arguments,
                            trigger_channel,
                            signal_spectrum_acquire_value,
                            signal_spectrum_acquire_event
                        )

                    # Get recording flag from application (initialized from argument parser).
                    if (arguments["store_waveforms"] == 1 and sca_a_pulse_count > 0 and sca_b_pulse_count > 0) or \
                        arguments["store_waveforms"] == 2:
                        store = []
                        if "A" in arguments["store_waveforms_channels"]:
                            store.append(buffers[0])
                        if "B" in arguments["store_waveforms_channels"]:
                            store.append(buffers[1])
                        if "C" in arguments["store_waveforms_channels"]:
                            store.append(buffers[2])
                        if "D" in arguments["store_waveforms_channels"]:
                            store.append(buffers[3])
                        write_buffers(store, csv_waveform_file)

                    coincidence_count += (sca_a_pulse_count * sca_b_pulse_count)

                    # Take rate count from the other channel than the triggered.
                    # Trigger channel will always contain at least one pulse but in reality pulses are
                    # randomly distributed in time. Thus, taking a number of pulses at random places
                    # over time should give us best idea of the average pulse rate.
                    # This will require some good length of the buffer because too small buffer
                    # would reduce the average hit of the pulses if pulse rate is very low...

                    if False:
                        if start_channel == block_mode_trigger_settings["channel"]:
                            rate_count += 1

                        if block_mode_trigger_settings["channel"] == 1:
                            rate_a += sca_a_pulse_count
                            if counts_max_a < sca_a_pulse_count:
                                counts_max_a = sca_a_pulse_count
                            if counts_min_a > sca_a_pulse_count:
                                counts_min_a = sca_a_pulse_count
                            rate_a_avg = timebase_conversion * rate_a / rate_count

                            rate_ab = rate_a + rate_b
                            rate_ab_avg = timebase_conversion * rate_ab / (rate_count * 2)
                        else:
                            rate_b += sca_b_pulse_count
                            if counts_max_b < sca_b_pulse_count:
                                counts_max_b = sca_b_pulse_count
                            if counts_min_b > sca_b_pulse_count:
                                counts_min_b = sca_b_pulse_count
                            rate_b_avg = timebase_conversion * rate_b / rate_count
                    else:
                        rate_count += 1

                        rate_a += sca_a_pulse_count
                        if counts_max_a < sca_a_pulse_count:
                            counts_max_a = sca_a_pulse_count
                        if counts_min_a > sca_a_pulse_count:
                            counts_min_a = sca_a_pulse_count
                        rate_a_avg = timebase_conversion * rate_a / rate_count

                        rate_b += sca_b_pulse_count
                        if counts_max_b < sca_b_pulse_count:
                            counts_max_b = sca_b_pulse_count
                        if counts_min_b > sca_b_pulse_count:
                            counts_min_b = sca_b_pulse_count
                        rate_b_avg = timebase_conversion * rate_b / rate_count

                        rate_ab = rate_a + rate_b
                        rate_ab_avg = timebase_conversion * rate_ab / (rate_count * 2)

                    # Calculate, how many pulses there are in a second in average?
                    # Time window is in nanoseconds, so this needs to be converted to seconds by multiplying with 1000000000.
                    # Problem of getting real rate is difficult. We count number of pulses per every sweep with a trigger.
                    # So there will be at least opne pulse per every sweep. But we are not getting data for every time point
                    # so we miss a lot of data. One way of trying to get around this is to have a long time window and count all
                    # pulses in there. But it can still have same problem because for high precision buffer we have a limit of 20000ns
                    # for every bugger and if the rate of the interesting signals is much slower than once in a 20 micro seconds
                    # the calculation will be biassed. But for high rate constant signals, that should be ok.
                    # Question for Tandem Experiment is, if there are gamma peaks coming once in every 20 microseconds so that
                    # the rate calculated here is correct?
                    console_line = "Samples: %s/%ss Elapsed: %ss | A: %s/s (cnt/min/max: %s/%s/%s) | B: %s/s (cnt/min/max: %s/%s/%s) | CHC rate: %s (500ns) | CNC rate elps/smpl: %s/%s (cnt: %s) | %s-%s-%s \033[A"

                    time_now = tm()

                    elapsed_time = time_now - start_time

                    td = td if len(time_differences) < 1 else time_differences[0]
                    ph1 = ph1 if len(pulse_heights) < 1 else pulse_heights[0][0]
                    ph2 = ph2 if len(pulse_heights) < 1 else pulse_heights[0][1]

                    data = (
                        rate_count,
                        round(buffer_length_ns * rate_count, 1),
                        round(elapsed_time, 1),
                        round(rate_a_avg, 1),
                        rate_a,
                        counts_min_a,
                        counts_max_a,
                        round(rate_b_avg, 1),
                        rate_b,
                        counts_min_b,
                        counts_max_b,
                        round(rate_a_avg * rate_b_avg * 5*10**-7, 3),
                        round(coincidence_count / elapsed_time, 3),
                        round(coincidence_count / (buffer_length_ns * rate_count), 3),
                        coincidence_count,
                        td,
                        round(ph1, 1),
                        round(ph2, 1)
                    )

                    print(console_line % data)

                    if arguments["store_statistics"] > 0:
                        if (arguments["store_statistics"] == 1 and sca_a_pulse_count > 0 and sca_b_pulse_count > 0) or \
                           (arguments["store_statistics"] == 2 and (sca_a_pulse_count > 0 or sca_b_pulse_count > 0)) or \
                            arguments["store_statistics"] == 3:
                            data = (
                                rate_count,
                                time_now,
                                elapsed_time,
                                sca_a_pulse_count,
                                sca_b_pulse_count,
                                rate_a,
                                rate_b,
                                rate_a_avg,
                                rate_b_avg,
                                sca_a_pulse_count * sca_b_pulse_count,
                                coincidence_count,
                                coincidence_count / elapsed_time,
                                coincidence_count / (buffer_length_ns * rate_count),
                                "" if len(time_differences) < 1 else time_differences[0],
                                "" if len(pulse_heights) < 1 else pulse_heights[0][0],
                                "" if len(pulse_heights) < 1 else pulse_heights[0][1],
                                buffer_length_ns * rate_count,
                                block_mode_trigger_settings["channel"]
                            )
                            f = open(csv_statistics_file, "a")
                            print(*data, sep = ";", file = f)
                            f.close()
                    # If single channel trigger is set to alternate,
                    # swap the trigger channel between 0 and 1.
                    if block_mode_trigger_settings["alternate_channel"] == True:
                        block_mode_trigger_settings["channel"] = 1 if block_mode_trigger_settings["channel"] == 0 else 0
                        # Revoke trigger only if it is enabled.
                        if block_mode_trigger_settings["enabled"] == 1:
                            ps.set_trigger(**block_mode_trigger_settings)
                    ps.init_capture()

                    # If execution time has exceeded, stop loops and application.
                    if execution_time > 0 and tm() > execution_time:
                        print("\n")
                        print("Execution time (%ss) of the experiment has ended." % arguments["execution_time"])
                        settings["sub_loop"] = False
                        settings["main_loop"] = False

                # Pause, sub loop or main loop can be triggers in the application.
                # In those cases other new settings might be arriving too like
                # a new playback file etc.
                if settings_acquire_event.is_set():
                    settings = settings_acquire_value["value"]
                    # Temporarily get out from the loop.
                    settings["sub_loop"] = False
                    if verbose:
                        print(settings)
                    settings_acquire_event.clear()

                # Sleep a moment in a while loop to prevent halting the process.
                sleep(uniform(*settings["sleep"]))

        except Exception as e:
            print(e)
            settings["main_loop"] = False

    print("\r\n")

# Picoscope worker for pulse rate meter, channel line graph,
# time difference and detector spectrum histograms.
def multi_worker(picoscope_mode, arguments, playback_file = "", verbose = False):

    # Suppress traceback messages on application quit / ctrl-c in console.
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

    has_picoscope = False

    if picoscope_mode != None:

        import ctypes
        from ctypes import cdll
        from ctypes.util import find_library

        picoscope_model = "ps2000"

        try:
            if sys.platform == "win32":
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

        if picoscope_mode == "stream":
            from . import PS2000aStreamMode as ps
        elif picoscope_mode == "block":
            from . import PS2000aBlockMode as ps
        elif picoscope_mode == "rapid":
            # TODO
            print("Rapid mode not implemented yet!")
            sys.exit(0)
            from . import PS2000aRapidMode as ps

        print("Opening Picoscope...")
        has_picoscope = ps.open_picoscope()

    if not has_picoscope and playback_file == "":

        print("Could not find Picoscope and playback file not given, starting simulator...")

        simulator_worker(arguments, verbose)

    elif playback_file != "":

        print("Opening playback file...")

        playback_worker(arguments, playback_file, verbose)

    elif has_picoscope:

        print("Picoscope data acquisition starting...")

        picoscope_worker(arguments, ps, picoscope_mode, verbose)

        ps.stop_picoscope()

    else:

        print("Could not start simulator, playback mode, or picoscope. Quiting application.")

    os.kill(arguments["main_process_id"], signal.CTRL_C_EVENT)

# Start PyQT application
def main_program(application_configuration, multiprocessing_arguments):

    # Suppress traceback messages on application quit / ctrl-c in console.
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))

    if not application_configuration["headless_mode"]:

        from pyqtgraph.Qt import QtGui
        from . gui import App

        app = QtGui.QApplication(sys.argv)
        # Init QT app with configuration.
        c = App(application_configuration, multiprocessing_arguments)
        # Show GUI.
        c.show()
        # Start colleting data to the graphs from multiprocessing workers.
        c.start_update()
        sys.exit(app.exec_())
