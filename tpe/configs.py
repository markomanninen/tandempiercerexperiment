#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from time import strftime
import json

config_name = "config.json"

block_mode_simple_trigger_settings = {
    # Enable to set this trigger on. Otherwise use advanced trigger.
    "enabled": 1,
    "alternate_channel": True,
    "channel": 0, # 0=A, 1=B, 2=C, 3=D
    "threshold": 1024*16, #adc value
    "direction": 2, # raising
    "delay": 0,
    # With 600ms auto trigger setting we can get equal amount of triggers and data coming from both channels.
    # Value lessr than this my favor other channel.
    "auto_trigger": 1000
}

# Special trigger for block mode. Triggers if either channel has a raising voltage over given threshold. By hysteresis it is possible to wait for lowering edge under given percentage until the next trigger is used. Set enabled 1, if you want to use this.
block_mode_advanced_trigger_settings = {
    # If simple trigger is enabled, it will override this setting.
    "enabled": 1,
    # Which one of the two channels should have OR trigger activated?
    "channels": ("A", "B"),
    # For raising edge, what is the threshold for the trigger?
    "upper_threshold": 20, # mV
    # How much should the falling edge drop below the raising edge threshold to restart a new trigger? In percents.
    "upper_hysteresis": 2.5,
    # How long should Picoscope wait until reinit data retrieval?
    # Zero means unlimited time of waiting for the trigger. In milliseconds.
    # 1000 = one second.
    "auto_trigger_ms": 1000
}

# SCA (single channel analyzer) NIM (nuclear instrumentation module) default_settings. These must be manually set according to values in the knobs.
sca_module_default_settings = {
    # High voltage value. Tested values from 700 to 1250. Negative voltage is required for the detectors used in my experiment. Same voltage is used for both SCA NIM modules.
    "high_voltage": -1100,
    # What channel is treated as front detector? 0 is channel A, 1 is channel B. This should be on e of the SCA channels!
    "front_detector": "channel_a",
    # Channel A settings.
    "channel_a": {
        # SCA device model.
        "sca_model": "Ortec 490B",
        # Channel index.
        "sca_square_pulse_index": 0,
        # Channel index.
        "raw_pulse_index": 2,
        "coarse_gain": 4,
        "fine_gain": 3.0,
        # High level discriminator.
        "window": 10.0,
        # Low level discriminator.
        "lower_level": 0.10,
        # Mode options are: diff|int.
        "mode": "diff"
    },
    # Channel B settings.
    "channel_b": {
        "sca_model": "Ortec 490B",
        "sca_square_pulse_index": 1,
        "raw_pulse_index": 3,
        "coarse_gain": 4,
        "fine_gain": 3.0,
        "window": 10.0,
        "lower_level": 0.10,
        "mode": "diff"
    }
}

# Picoscope was tested with streaming mode first, but its resolution is not suitable for the project. Thus these settings are not used but legacy and testing purposes.
streaming_mode_settings = {
    "buffer_size": 250,
    "buffer_count": 2,
    "units": "NS",
    "interval": 128
}

def create_config():
    global config_name

    # General configurations.

    data = {}
    # Where all experiment result files are stored.
    data["measurement_step"] = 1
    # Where all experiment result files are stored.
    data["experiments_dir"] = "experiments"
    # Experiment sub directory name.
    data["experiment_dir"] = "default"
    # Default experiment name.
    data["experiment_name"] = "Tandem Piercer Experiment"
    # Pulse source.
    data["pulse_source"] = "Background"
    # Picoscope voltage range for each channel from 0 to 3.
    # SCA square pulse max heights are a bit over 5, so for SCA channels range is 10V.
    # Raw pulse channels are from -12 to 10V so 20V setting is used for them.
    data["voltage_range"] = ["10V", "10V", "20V", "20V"]
    # Channel identifiers.
    data["channels"] = ["A", "B", "C", "D"]
    # Channel names.
    data["channel_names"] = ["A (SCA)", "B (SCA)", "C", "D"]
    # Default bin count for histograms.
    data["bin_count"] = 256
    # Verbose console debug.
    data["verbose"] = 0
    # Histogram queue size. After this value the first values will be dropped from the list to maintain a reasonable max size for the graphics data.
    data["histogram_queue_size"] = 30000
    # If pulse voltage range is 20, use 19660 for max adc value since 12V is the maximmum that Ortec SCA module will give.

    adc_max_0, adc_max_1, adc_max_2, adc_max_3 = (32767, 32767, 32767, 32767)

    adc_min_0, adc_min_1, adc_min_2, adc_min_3 = (4096, 4096, 500, 500)

    if data["voltage_range"][2] == "20V":
        adc_max_2 = 19660 # 19660 for 12V (20V)
    if data["voltage_range"][3] == "20V":
        adc_max_3 = 19660 # 19660 for 12V (20V)

    # In large timebases it is possible to use this value as max buffer size, but it will cause "arbitrary" time value, so 6000 is rather used. Also, with smaller timebases the maximum is 5000.
    trigger_sample_max = 6132

    # ADC max value.
    data["adc_max"] = 19660

    # Sleep time in streaming_loop.
    data["sleep_time"] = 0.01

    # Sleep time in the process of retrieving data from the picoscope.
    data["sleep_interval"] = (.00001, .00001)

    # Experiment step configurations.

    steps = {}
    steps[1] = {
        "name": "Find Gamma Spectrum",

        "description": "Use isotope source to collect spectrum and identify gamma photo peak from the spectrum. First make the high and low limits to exptreme positions both in SCA NIM module and region selector. Save full spectrum image after retrieving enough data to the spectrum plot. Store SCA NIM module and region ADC settings in the control panel as a full limit region. Then use region tool in GUI to select the gamma peak from the spectrum. From the control panel store gamma limit settings.",

        # In this step we want to use GUI to graphically select the correct regions from the spectrum.
        "headless_mode": False,

        # This is the most precise setting in Picoscope 2000 with four channels.
        # It means two nanosecond resolution for the buffer.
        # Total buffer size is pre_trigger_samples + post_trigger_samples.
        # Total sample size in nanoseconds is buffer size times timebase.
        # # 10000 * (n – 2) / 125,000,000 -> n=127 -> 0.01, n=15 -> 0.00104
        "timebase_n": 2,
        # Buffer pre trigger size.
        "pre_trigger_samples": 250,
        # Buffer post trigger size.
        "post_trigger_samples": 250,

        "spectrum_low_limits": [adc_min_0, adc_min_1, adc_min_2, adc_min_3],
        "spectrum_high_limits": [adc_max_0, adc_max_1, adc_max_2, adc_max_3],

        "simple_trigger_settings": block_mode_simple_trigger_settings,
        "advanced_trigger_settings": block_mode_advanced_trigger_settings,
        "sca_module_settings": sca_module_default_settings,
        "streaming_mode_settings": streaming_mode_settings

    }
    steps[1.2] = {

    }
    steps[1.3] = {

    }
    steps[2] = {
        "name": "Measure chance rate",

        "description": "",
        # In this step we want to disable GUI and use the maximum resoures to gather measurement data in files.
        "headless_mode": True,
        "timebase_n": 52,
        "pre_trigger_samples": 6000,
        "post_trigger_samples": 6000,
        "simple_trigger_settings": block_mode_simple_trigger_settings,
        "advanced_trigger_settings": block_mode_advanced_trigger_settings,
        "sca_module_settings": sca_module_default_settings,
        "streaming_mode_settings": streaming_mode_settings
    }
    steps[3] = {
        "name": "Measure background coincidence rate",

        "Description": "",
        # In this step we want to disable GUI and use the maximum resoures to gather measurement data in files.
        "headless_mode": True,
        "timebase_n": 2,
        "pre_trigger_samples": 125,
        "post_trigger_samples": 125,
        "simple_trigger_settings": block_mode_simple_trigger_settings,
        "advanced_trigger_settings": block_mode_advanced_trigger_settings,
        "sca_module_settings": sca_module_default_settings,
        "streaming_mode_settings": streaming_mode_settings
    }
    steps[4] = {
        "name": "Measure experiment coincidence rate",

        "description": "",
        # In this step we want to disable GUI and use the maximum resoures to gather measurement data in files.
        "headless_mode": True,
        "timebase_n": 2,
        "pre_trigger_samples": 125,
        "post_trigger_samples": 125,
        "simple_trigger_settings": block_mode_simple_trigger_settings,
        "advanced_trigger_settings": block_mode_advanced_trigger_settings,
        "sca_module_settings": sca_module_default_settings,
        "streaming_mode_settings": streaming_mode_settings
    }

    data["steps"] = steps

    # Write the above sections to config file.
    with open(config_name, "w") as json_file:
        json.dump(data, json_file, sort_keys = True, indent = 4)

def load_config():
    global config_name
    # If config file does not exists, create it.
    if not os.path.exists(config_name):
        create_config()
    with open(config_name) as json_file:
        data = json.load(json_file)
    return data
