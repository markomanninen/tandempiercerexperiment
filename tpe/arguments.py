#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from distutils.util import strtobool
from ast import literal_eval

class PicoScopeModes(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if value != "block" and value != "stream" and value != None:
            raise ValueError("PicoScope mode must be empty or one of these: block, stream.")
        setattr(namespace, self.dest, value)

def boolean_type(value):
    return strtobool(value)

def int_type(value):
    return literal_eval(value)

# Main python program executed when run from the console.
def load_args(default_config):

    parser = argparse.ArgumentParser(
        description = "Tandem Piercer Experiment simulator, playback and PicoScope data acquisition program. Do five measurements in steps, store data, and create a report file via Jupyter notebook document."
    )

    # In playback mode use prerecorded data file to simulate a real measurement situation. It is not possible to store configurations, settings, or to generate a new report in this mode.
    parser.add_argument("--file",
        dest = "playback_file",
        help = "Default playback file to run the application.")

    parser.add_argument("--bins",
        dest = "bin_count",
        default = default_config["bin_count"],
        help = "Bin count for histograms")

    parser.add_argument("--headless_mode",
        dest = "headless_mode",
        default = False,
        type = boolean_type,
        help = "Headless mode to start and run application without GUI. Options are: 0 = false, 1 = true. Default is: 0.")

    parser.add_argument("--chance_rate",
        dest = "chance_rate",
        default = 0.0,
        help = "Change rate measured in a separate measurement step 2.")

    parser.add_argument("--background_rate",
        dest = "background_rate",
        default = 0.0,
        help = "Background rate measured in a separate measurement step 3.")

    parser.add_argument("--experiment_name",
        dest = "experiment_name",
        default = default_config["experiment_name"],
        help = "Experiment name to identify it. Default is: Tandem Piercer Experiment")

    parser.add_argument("--experiment_dir",
        dest = "experiment_dir",
        default = default_config["experiment_dir"],
        help = "Experiment sub directory. Default is: " + default_config["experiment_dir"])

    parser.add_argument("--experiments_dir",
        dest = "experiments_dir",
        default = default_config["experiments_dir"],
        help = "Experiments main directory. Default is: " + default_config["experiments_dir"])

    parser.add_argument("--measurement_step",
        dest = "measurement_step",
        default = default_config["measurement_step"],
        help = "Measurement step 1-5. Default is: %s" % default_config["measurement_step"])

    parser.add_argument("--generate_report",
        dest = "generate_report",
        default = False,
        type = boolean_type,
        help = "Generate report from the measurement. Measurement data must be in the sub directory defined by measurement_dir. Options are: true|false. Default is: False")

    parser.add_argument("--generate_summary",
        dest = "generate_summary",
        default = False,
        type = boolean_type,
        help = "Generate summary report from the measurements in all experiments. Measurement data is collected from the measurements_dir. Options are: true|false. Default is: False")

    parser.add_argument("--store_waveforms",
        dest = "store_waveforms",
        default = default_config["store_waveforms"],
        type = int_type,
        help = "Store waveforms from buffers to csv files. Options are: 0=disabled, 1=only when coincident signals are found, 2=all triggered waveforms. Default is: %s" % default_config["store_waveforms"])

    parser.add_argument("--store_waveforms_channels",
        dest = "store_waveforms_channels",
        default = default_config["store_waveforms_channels"],
        help = "When store_waveforms from buffers to csv files is used, this option defines what channels are stored to the file. Options are some of these characters: ABCD. Default is: %s" % default_config["store_waveforms_channels"])

    parser.add_argument("--store_statistics",
        dest = "store_statistics",
        default = default_config["store_statistics"],
        type = int_type,
        help = "Store measurement statistics to csv files. 0=disabled, 1=only when coincident pulses are found, 2=if either or both channel A and B has a pulse, 3=everything. Default is: %s" % default_config["store_statistics"])

    parser.add_argument("--execution_time",
        dest = "execution_time",
        default = default_config["execution_time"],
        type = int_type,
        help = "Automatic halt for execution of the experiment. Options are: 0=for non-interrupting execution of the experiment, else define time in seconds, for example 3600 for an hour. Default is: %s seconds." % default_config["execution_time"])

    parser.add_argument("--pulse_source",
        dest = "pulse_source",
        default = default_config["pulse_source"],
        help = "Pulse radiation source label. For example: Cd-109 10μCi. Default is: " + default_config["pulse_source"])

    parser.add_argument("--spectrum_range",
        dest = "spectrum_range",
        default = default_config["adc_max"],
        help = "Voltage range for the spectrum histograms. Default is: %s" % default_config["adc_max"])

    parser.add_argument("--spectrum_queue_size",
        dest = "spectrum_queue_size",
        default = default_config["histogram_queue_size"],
        help = "Queue size for spectrum histogram. Default is: %a" % default_config["histogram_queue_size"])

    parser.add_argument("--picoscope_mode",
        dest = "picoscope_mode",
        default = "block",
        action = PicoScopeModes,
        help = "PicoScope mode for importing the data acquisition module. Options are: block, stream, None. Default is: block.")

    parser.add_argument("--simple_trigger",
        dest = "simple_trigger",
        default = default_config["simple_trigger"],
        type = int,
        choices = [0, 1],
        help = "PicoScope simple trigger. 0 = disabled, 1 = enabled. Default is: %s" % default_config["simple_trigger"])

    parser.add_argument("--simple_trigger_alternate",
        dest = "simple_trigger_alternate",
        default = default_config["simple_trigger_alternate"],
        type = int,
        choices = [0, 1],
        help = "PicoScope simple trigger. 0 = disabled, 1 = enabled. Default is: %s" % default_config["simple_trigger_alternate"])

    parser.add_argument("--simple_trigger_channel",
        dest = "simple_trigger_channel",
        default = default_config["simple_trigger_channel"],
        type = int,
        choices = [0, 1, 2, 3],
        help = "PicoScope simple trigger. 0 = sca channel zero, 1 = sca channel one. Default is: %s" % default_config["simple_trigger_channel"])

    parser.add_argument("--timebase",
        dest = "timebase",
        default = default_config["timebase"],
        type = int_type,
        help = "PicoScope timebase. Values from 0 to 60000. If value is 0, then step settings is used instead. Default is: %s" % default_config["timebase"])

    parser.add_argument("--pre_trigger_samples",
        dest = "pre_trigger_samples",
        default = default_config["pre_trigger_samples"],
        type = int_type,
        help = "PicoScope pre trigger sample size. Values from 0 to 6000. If value is 0, then step settings is used instead. Default is: %s" % default_config["pre_trigger_samples"])

    parser.add_argument("--post_trigger_samples",
        dest = "post_trigger_samples",
        default = default_config["post_trigger_samples"],
        type = int_type,
        help = "PicoScope post trigger sample size. Values from 0 to 6000. If value is 0, then step settings is used instead. Default is: %s" % default_config["post_trigger_samples"])

    parser.add_argument("--advanced_trigger",
        dest = "advanced_trigger",
        default = default_config["advanced_trigger"],
        type = int,
        choices = [0, 1],
        help = "PicoScope advanced trigger. 0 = disabled, 1 = enabled. Default is: %s" % default_config["advanced_trigger"])

    parser.add_argument("--pulse_detection_mode",
        dest = "pulse_detection_mode",
        default = default_config["pulse_detection_mode"],
        type = int,
        choices = [0, 1],
        help = "Pulse detection mode. 0 = detect pulse from the (SCA) square wave pulse. 1 = detect pulse from the raw pulse. Default is: %s" % default_config["pulse_detection_mode"])

    parser.add_argument("--detector_geometry",
        dest = "detector_geometry",
        default = default_config["detector_geometry"],
        type = str,
        choices = ["tandem", "top", "next", "apart"],
        help = "Detector position geometry. Default is: %s" % default_config["detector_geometry"])

    parser.add_argument("--channel_colors",
        dest = "channel_colors",
        default = default_config["channel_colors"],
        help = "Default is: %s" % default_config["channel_colors"])

    parser.add_argument("--sca_module_settings_a",
        dest = "sca_module_settings_a",
        default = "",
        help = "Override sca module settings for channel A. Format is: {coarse_gain},{fine_gain},{window},{lower_level}. Default is empty when settings are retrievved from the config.json file.")

    parser.add_argument("--sca_module_settings_b",
        dest = "sca_module_settings_b",
        default = "",
        help = "Override sca module settings for channel B. Format is: {coarse_gain},{fine_gain},{window},{lower_level}. Default is empty when settings are retrievved from the config.json file.")

    parser.add_argument("--verbose",
        dest = "verbose",
        default = False,
        type = boolean_type,
        help = "Verbose mode for showing for debug information in the console. Options are: true|false. Default is: False")

    return parser.parse_args()
