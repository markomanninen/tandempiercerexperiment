#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import os, subprocess
from time import sleep
from datetime import datetime
from tpe.workers import multi_worker, main_program
from multiprocessing import Process, Manager, Event
from tpe.configs import load_config
from tpe.arguments import load_args
from tpe.functions import step2_json_file, step3_json_file

# Add multi process targets to the list
def add_process(target, name = "", args = None):
    processes.append(Process(target=target, name=name, args=args))

# Start processes in the list
def start_sub_processes():
    for process in processes:
        process.start()
        print("Starting sub process: " + process.name + " PID=" + str(process.pid))
        sleep(.1)

# Stop processes in the list
def stop_sub_prosesses():
    print("\nStopping processes...")
    for process in processes:
        print("Stopping sub process: " + process.name + " PID=" + str(process.pid))
        process.terminate()
        sleep(.1)

# Multi threaded process list.
processes = []

# Main python program executed when run from the console.
def main():

    try:

        # Default configurations in json format.
        config = load_config()

        # Console arguments. Using defaults from config.
        args = load_args(config)

        # Measurement step number 1, 1.2, 1.3, 1.4, 2, 3, 4. Default is 1.
        step = args.measurement_step

        # Default experiment directory.
        experiment_dir = args.experiment_dir

        if config["experiment_dir"] == experiment_dir:
            pass

        # Create experiment project directory.
        if os.path.exists(os.path.join(args.experiments_dir, experiment_dir)):
            c = datetime.now()
            experiment_dir = "%s_%s" % (experiment_dir, "%s_%s_%s_%s_%s" % (c.year, c.month, c.day, c.hour, c.minute))
            os.makedirs(os.path.join(
                args.experiments_dir,
                experiment_dir
            ))
        else:
            os.makedirs(os.path.join(
                args.experiments_dir,
                experiment_dir
            ))

        # Steps from 1 to 4 are actual measurements. Final stage of the experiment is to create a report from all of the previous steps. There is no need to proceed further in in the main program in that case. Instead we open Jupyter notebook with a template file, initialize it with the current experiment sub directory and run all the cells to get a fine report of the measurements.
        if args.generate_report:
            # Jupyter notebook template is used to present all graphical, tabular and textual data.
            subprocess.call(["jupyter", "notebook", "./report_template/report_template.ipynb", "--NotebookApp.iopub_data_rate_limit=1000000"])
        elif args.generate_summary:
            # Jupyter notebook template is used to present all graphical, tabular and textual data.
            subprocess.call(["jupyter", "notebook", "./report_template/report_summary.ipynb", "--NotebookApp.iopub_data_rate_limit=1000000"])
        else:
            # Json configuration file keys are in string format, thus step is cast to string.
            step_config = config["steps"][str(step)]

            # Chance rate and background rate can be provided in the arguments.
            # But these will be replaced by the measurement steps 2 and 3 if they are available.
            chance_rate = args.chance_rate
            background_rate = args.background_rate

            # If measurement step is one of these, load low and high region limits from the experiment step 1 file.
            if step in (2, 3, 4):
                region_config_name = os.path.join(
                    args.experiments_dir,
                    experiment_dir,
                    "regions.json"
                )
                if os.path.exists(region_config_name):
                    region_config = json.load(region_config_name)
                    # Assuming here that the raw pulse channels are 2 and 3.
                    # Region config has both full and gamma regions. Index 0 corresponds to Channel A which raw pulse is in step_config index 2. 1 corresponds to 3 similarly.
                    step_config["spectrum_low_limits"][2] = region_config["gamma"]["spectrum_low_limits"][0]
                    step_config["spectrum_low_limits"][3] = region_config["gamma"]["spectrum_low_limits"][1]
                    step_config["spectrum_high_limits"][2] = region_config["gamma"]["spectrum_high_limits"][0]
                    step_config["spectrum_high_limits"][3] = region_config["gamma"]["spectrum_high_limits"][1]

                # It is possible to calculate and show unquantum effect ratio in the fourth measurement.
                if step == 4:
                    dir = os.path.join(
                        args.experiments_dir,
                        experiment_dir,
                        step2_json_file
                    )
                    if os.path.exists(dir):
                        step2 = show_step2_results(dir)
                        chance_rate = step2[""]["Chance Rate (1/s)"]

                    dir = os.path.join(
                        args.experiments_dir,
                        experiment_dir,
                        step3_json_file
                    )
                    if os.path.exists(dir):
                        step3 = show_step3_results(dir)
                        background_rate = step3[""]["Coincidence Rate (1/s)"]

            voltage_range = config["voltage_range"]
            sca_module_settings = step_config["sca_module_settings"]
            advanced_trigger_settings = step_config["advanced_trigger_settings"]
            advanced_trigger_settings["enabled"] = args.advanced_trigger

            block_mode_trigger_settings = step_config["simple_trigger_settings"]
            block_mode_trigger_settings["enabled"] = args.simple_trigger
            block_mode_trigger_settings["alternate_channel"] = args.simple_trigger_alternate == 1
            block_mode_trigger_settings["channel"] = args.simple_trigger_channel

            block_mode_timebase_settings = {
                "timebase_n": step_config["timebase_n"] if args.timebase == 0 else args.timebase,
                "pre_trigger_samples": step_config["pre_trigger_samples"] if args.pre_trigger_samples == 0 else args.pre_trigger_samples,
                "post_trigger_samples": step_config["post_trigger_samples"] if args.post_trigger_samples == 0 else args.post_trigger_samples
            }

            time_window = (block_mode_timebase_settings["pre_trigger_samples"] + block_mode_timebase_settings["post_trigger_samples"])

            picoscope_mode = args.picoscope_mode

            if args.sca_module_settings_a != "":
                coarse_gain_a, fine_gain_a, window_a, lower_level_a = map(lambad x: float(x.trim()), args.sca_module_settings_a.split(","))
                sca_module_settings["channel_a"]["coarse_gain"] = coarse_gain_a
                sca_module_settings["channel_a"]["fine_gain"] = fine_gain_a
                sca_module_settings["channel_a"]["window"] = window_a
                sca_module_settings["channel_a"]["lower_level"] = lower_level_a

            if args.sca_module_settings_b != "":
                coarse_gain_b, fine_gain_b, window_b, lower_level_b = map(lambad x: float(x.trim()), args.sca_module_settings_b.split(","))
                sca_module_settings["channel_b"]["coarse_gain"] = coarse_gain_b
                sca_module_settings["channel_b"]["fine_gain"] = fine_gain_b
                sca_module_settings["channel_b"]["window"] = window_b
                sca_module_settings["channel_b"]["lower_level"] = lower_level_b

            raw_spectrum_channels = (
                config["channels"][sca_module_settings["channel_a"]["raw_pulse_index"]],
                config["channels"][sca_module_settings["channel_b"]["raw_pulse_index"]]
            )

            # Multiprocessing value manager.
            # Only values declared with Manager can be shared between processes.
            manager = Manager()

            # Share application configuration dictionary between processes.
            application_configuration = manager.dict()
            # How many bins there are in the histogram by default?
            # Bin count can be adjusted from the GUI.
            application_configuration["bin_count"] = args.bin_count
            # Are we using GUI or headless mode i.e. only console for output?
            application_configuration["headless_mode"] = args.headless_mode
            # Change rate measured in a separate measurement step 2.
            application_configuration["chance_rate"] = chance_rate
            # Background rate measured in a separate measurement step 3.
            application_configuration["background_rate"] = background_rate
            # Experiment name for all measurements.
            application_configuration["experiment_name"] = args.experiment_name
            # What is the max value of the time difference x-axis in nanoseconds?
            application_configuration["time_window"] = time_window
            # What is the max adc value of the spectrum x-axis?
            application_configuration["spectrum_time_window"] = args.spectrum_range
            # What is the stack max size of the spectrum histogram?
            application_configuration["spectrum_queue_size"] = args.spectrum_queue_size
            # Main directory where all experiments are stored.
            application_configuration["experiments_dir"] = args.experiments_dir
            # Individual experiment sub directory.
            application_configuration["experiment_dir"] = experiment_dir
            # PicoScope on / off.
            # TODO: Final status of PicoScope depends on the initialization of the scope.
            # If it works, then it is really on. Information should then be updated to the GUI.
            application_configuration["has_picoscope"] = picoscope_mode != None
            # PicoScope mode.
            application_configuration["picoscope_mode"] = picoscope_mode
            # Pulse radiation source.
            application_configuration["pulse_source"] = args.pulse_source
            # Low value limits for channels 1-4.
            application_configuration["spectrum_low_limits"] = step_config["spectrum_low_limits"]
            # High value limits for channels 1-4.
            application_configuration["spectrum_high_limits"] = step_config["spectrum_high_limits"]
            # Selected channels for spectrum histogram.
            # Possible options are: 1=A, 2=B, 3=C, 4=D, 5=E where
            # the channel E is a combined rate channel from A and B.
            application_configuration["spectrum_channels"] = raw_spectrum_channels
            application_configuration["sca_module_settings"] = sca_module_settings
            # Verbose mode.
            application_configuration["verbose"] = args.verbose
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
            application_configuration["trigger_mode"] = "simple" if block_mode_trigger_settings["enabled"] == 1 else ("advanced" if advanced_trigger_settings["enabled"] == 1 else "none")
            # Which channels are triggered?
            trigger_channels = "A or B"
            if application_configuration["trigger_mode"] == "simple":
                if block_mode_trigger_settings["alternate_channel"]:
                    trigger_channels = "A or B alt"
                elif block_mode_trigger_settings["channel"] == 0:
                    trigger_channels = "A"
                else:
                    trigger_channels = "B"
            application_configuration["trigger_channels"] = trigger_channels

            application_configuration["store_waveforms"] = args.store_waveforms
            application_configuration["store_waveforms_channels"] = args.store_waveforms_channels
            application_configuration["store_statistics"] = args.store_statistics
            application_configuration["execution_time"] = args.execution_time
            application_configuration["pulse_detection_mode"] = args.pulse_detection_mode
            application_configuration["detector_geometry"] = args.detector_geometry
            application_configuration["channel_colors"] = args.channel_colors

            arguments = [
                # Share signal spectrum dictionary between processes.
                "signal_spectrum_acquire_",
                # Settings tobe shared between processes, app, and scope.
                # Can be modified in the GUI widget.
                "settings_acquire_"
            ]
            multiprocessing_arguments = {}

            for key in arguments:
                # Multiprocessing event instance.
                multiprocessing_arguments[key + "event"] = Event()
                multiprocessing_arguments[key + "value"] = manager.dict()

            playback_file = args.playback_file if args.playback_file != None else ""

            application_configuration["playback_file"] = playback_file

            multiprocessing_arguments["main_process_id"] = os.getpid()
            multiprocessing_arguments["time_window"] = time_window
            multiprocessing_arguments["headless_mode"] = application_configuration["headless_mode"]
            multiprocessing_arguments["pulse_source"] = application_configuration["pulse_source"]
            multiprocessing_arguments["chance_rate"] = application_configuration["chance_rate"]
            multiprocessing_arguments["background_rate"] = application_configuration["background_rate"]
            multiprocessing_arguments["store_waveforms"] = application_configuration["store_waveforms"]
            multiprocessing_arguments["store_waveforms_channels"] = application_configuration["store_waveforms_channels"]
            multiprocessing_arguments["store_statistics"] = application_configuration["store_statistics"]
            multiprocessing_arguments["pulse_detection_mode"] = application_configuration["pulse_detection_mode"]
            multiprocessing_arguments["execution_time"] = application_configuration["execution_time"]
            multiprocessing_arguments["experiments_dir"] = application_configuration["experiments_dir"]
            multiprocessing_arguments["experiment_dir"] = application_configuration["experiment_dir"]
            multiprocessing_arguments["detector_geometry"] = application_configuration["detector_geometry"]
            multiprocessing_arguments["channel_colors"] = application_configuration["channel_colors"]

            print("Main process started: %s" % multiprocessing_arguments["main_process_id"])

            picoscope_settings = {
                "sleep_time": config["sleep_time"],
                "voltage_range": voltage_range
            }

            if picoscope_mode == "stream":
                streaming_mode_settings = step_config["streaming_mode_settings"]
                picoscope_settings["interval"] = streaming_mode_settings["interval"]
                picoscope_settings["units"] = streaming_mode_settings["units"]
                picoscope_settings["buffer_size"] = streaming_mode_settings["buffer_size"]
                picoscope_settings["buffer_count"] = streaming_mode_settings["buffer_count"]
            elif picoscope_mode == "block":
                # Block mode settings:
                picoscope_settings["block_mode_trigger_settings"] = block_mode_trigger_settings
                picoscope_settings["block_mode_timebase_settings"] = block_mode_timebase_settings
                picoscope_settings["advanced_trigger_settings"] = advanced_trigger_settings

            # Note, these are settings that MUST be given from the application!
            settings = {
                "main_loop": True,
                "sub_loop": True,
                "pause": False,
                "sleep": config["sleep_interval"],
                "playback_file": playback_file,
                "spectrum_low_limits": step_config["spectrum_low_limits"],
                "spectrum_high_limits": step_config["spectrum_high_limits"],
                "spectrum_channels": raw_spectrum_channels,
                # PicoScope settings
                # TODO: simplify processes in GUI, these settings could be set empty
                # If scope cannot be initialized, or if playback of similator mode is used by default.
                "picoscope": picoscope_settings,
                "sca_module": sca_module_settings
            }

            multiprocessing_arguments["settings_acquire_value"]["value"] = settings
            multiprocessing_arguments["settings_acquire_event"].set()
            multiprocessing_arguments["settings_acquire_event"].clear()

            # Save configuration files.
            file_json = os.path.join(args.experiments_dir, experiment_dir, 'application_configuration.json')
            with open(file_json, "w") as file:
                json.dump({key: value for key, value in application_configuration.items()}, file, sort_keys = True, indent = 4)

            file_json = os.path.join(args.experiments_dir, experiment_dir, 'worker_configuration.json')
            with open(file_json, "w") as file:
                json.dump(settings, file, sort_keys = True, indent = 4)

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
                        args.verbose,)
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
        # Remove empty project directory.
        project_dir = os.path.join(args.experiments_dir, experiment_dir)
        if os.path.exists(project_dir) and not os.listdir(project_dir):
            os.rmdir(project_dir)

        # You can use also ctrl-c in console to exit graphical ui.
        # ctrl-q works as a shortcut to quit application from the GUI.
        # Terminate all processes that are stored to the global process list.
        stop_sub_prosesses()
