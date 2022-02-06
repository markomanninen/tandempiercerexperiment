#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
from distutils.util import strtobool

class PicoScopeModes(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if value != "block" and value != "stream" and value != None:
            raise ValueError("PicoScope mode must be empty or one of these: block, stream.")
        setattr(namespace, self.dest, value)

def boolean_type(value):
    return strtobool(value)

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
        help = "Headless mode to start and run application without GUI. Options are: true|false. Default is: False.")

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

    parser.add_argument("--pulse_source",
        dest = "pulse_source",
        default = default_config["pulse_source"],
        help = "Pulse radiation source label. For example: Cd-109 10mci. Default is: " + default_config["pulse_source"])

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
        help = "PicoScope mode for importing the data acqution module. Options are: block, stream, None. Default is: block.")

    parser.add_argument("--verbose",
        dest = "verbose",
        default = False,
        type = boolean_type,
        help = "Verbose mode for showing for debug information in the console. Options are: true|false. Default is: False")

    return parser.parse_args()
