#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import numpy as np
from scipy.signal import find_peaks
from IPython.display import display, Markdown as md
from IPython.core.display import HTML
from PIL import Image
import json, pandas as pd

# Normalize signal to zero line.
def baseline_correct(data):
    return (lambda x: x - x.mean())(np.array(data))

# Remove noise from the signal.
def filter_spectrum(data, counter_str, limit, self):
    # Select only data that is greater than limit.
    a = data[data > limit]
    # Add length of the array with value greater than limit
    self.__dict__[counter_str] = len(a)
    # Return filtered values.
    return a

def baseline_correction_and_limit(data, low_limit, high_limit):
    if len(data) == 0:
        return data
    bca = baseline_correct(data)
    bca[(bca < low_limit) & (bca > -low_limit)] = 0
    return bca

def raising_edges_for_raw_pulses(data, width = 50, distance = 50, threshold = 128):
    return find_peaks(
            data,
            width = width,
            distance = distance,
            threshold = threshold)[0]

def raising_edges_for_square_pulses(data, low_limit = 4096):
    pos = data > low_limit
    return (pos[:-1] & ~pos[1:]).nonzero()[0]

# Use the show_image helper function as a shortcut to display images.
def show_image(file, width=None, height=None):
    image  = Image.open(file)
    original_aspect = image.width / float(image.height)
    if width is None and height is not None:
        width = int(height * original_aspect)
    elif height is None and width is not None:
        height = int(width / original_aspect)
    elif width is None and height is None:
        width = image.width
        height = image.height
    display(image.resize((width, height), Image.ANTIALIAS))

def get_channels_parameters(file = "regions.json", region = "gammas"):

    with open(file) as json_file:
        data = json.load(json_file)

    def format_channel_data(data, channel_name, keys = False):
        limit_index = 0 if channel_name == "channel_a" else 1
        channel = {
            "Spectrum_ADC_low_limit": data["spectrum_low_limits"][limit_index],
            "Spectrum_ADC_high_limit": data["spectrum_high_limits"][limit_index]
        }
        channel.update(data["sca_module_settings"][channel_name])
        return [(key.title().replace("_", " ") if keys else value) for key, value in channel.items()]

    return pd.DataFrame({
        "": format_channel_data(data[region], "channel_a", True),
        "Channel A": format_channel_data(data[region], "channel_a"),
        "Channel B": format_channel_data(data[region], "channel_b")
    }).set_index([""]).rename(columns={"": "", "Channel A": "", "Channel B": ""})

def load_styles(file):
    with open(file) as f:
        css = f.read()
    return HTML("<style>%s</style>" % css)

measurement_1_headers = [
    "Measurement Start Time",
    "Elapsed Time (hh:mm:ss)",
    "Time Window (ns)",
    "Clicks in Detector A",
    "Clicks in Detector B",
    "Rate of Detector A (1/s)",
    "Rate of Detector B (1/s)",
    "Coincidence Count",
    "Coincidence Rate (1/s)"
]

measurement_1_keys = [
    "start_time",
    "elapsed_time",
    "time_window",
    "channel_a_count",
    "channel_b_count",
    "channel_a_rate",
    "channel_b_rate",
    "coincidence_count",
    "coincidence_rate"
]

measurement_2_headers = measurement_1_headers[:-2]
measurement_2_headers.append("Chance Rate (1/s)")

measurement_2_keys = measurement_1_keys[:-2]
measurement_2_keys.append("chance_rate")

measurement_3_headers = measurement_1_headers[:]
measurement_3_keys = measurement_1_keys[:]

measurement_4_headers = measurement_1_headers[:]
measurement_4_keys = measurement_1_headers[:]

uqe_headers = [
    "Measurement Start Time",
    "Elapsed Time (hh:mm:ss)",
    "Chance Rate (1/s)",
    "Background Coincidence Rate (1/s)",
    "Experiment Rate (1/s)",
    "Corrected Experiment Rate (1/s)",
    "Unquantum Effect Ratio"
]

# Not used...
uqe_keys = [
    "start_time",
    "elapsed_time",
    "chance_rate",
    "background_coincidence_rate",
    "experiment_rate",
    "corrected_rate",
    "unquantum_effect_ratio"
]

measurement_key_types = {
    "start_time": str,
    "elapsed_time": str,
    "time_window": int,
    "channel_a_count": int,
    "channel_b_count": int,
    "channel_a_rate": float,
    "channel_b_rate": float,
    "coincidence_count": int,
    "coincidence_rate": float,
    "chance_rate": float,
    "background_coincidence_rate": float,
    "experiment_rate": float,
    "corrected_rate": float,
    "unquantum_effect_ratio": float
}

step1_json_file = "step1_results.json"
step1_csv_file = "step1_results.csv"
step1_2_json_file = "step1_2_results.json"
step1_2_csv_file = "step1_2_results.csv"
step1_3_json_file = "step1_3_results.json"
step1_3_csv_file = "step1_3_results.csv"
step1_4_json_file = "step1_4_results.json"
step1_4_csv_file = "step1_4_results.csv"
step2_json_file = "step2_results.json"
step2_csv_file = "step2_results.csv"
step3_json_file = "step3_results.json"
step3_csv_file = "step3_results.csv"
step4_json_file = "step4_results.json"
step4_csv_file = "step4_results.csv"

# save_results("dir", step1_json_file, data)
def save_results(experiment_dir, measurement_file, data):
    save_json_results(os.path.join(experiment_dir, measurement_file), data)

def save_json_results(file_json, data):
    with open(file_json, "w") as file:
        json.dump(data, file, sort_keys = True, indent = 4)

# CSV: timestamp, channel_a_count, channel_b_count, channel_a_rate, channel_b_rate, coincidence_count, coincidence_rate

def append_to_csv_file(experiment_dir, measurement_file, data):
    f = open(os.path.join(experiment_dir, measurement_file), "a")
    print(*data, sep = ";", file = f)
    f.close()

def write_buffers(buffers, file):
    f = open(file, "a")
    for i, b in enumerate(buffers):
        print(*([i]+list(b)), sep = ";", file = f)
    f.close()

def load_buffers(file, buffers = [], b = [], first_line = True):
    with open(file, "r") as f:
        for line in f:
            items = line.strip().split(";")
            # All data is string in a csv file.
            if items[0] == "0":
                # If the first line of the file is parsed,
                # b list should not be appended to the final result.
                if not first_line:
                    buffers.append(b)
                    b = []
                first_line = False
            # Must convert to str to int.
            b.append(list(map(int, items[1:])))
        # If all four channels are retrieved from the file for
        # the tail of the buffer append b to the final result.
        if len(b) == 4:
            buffers.append(b)
    return buffers

def load_measurement_values(experiment_dir, measurement_file, measurement_headers, measurement_keys,  default_values):
    measurement_values = default_values

    if experiment_dir is not None:
        results_json = os.path.join(
            experiment_dir,
            measurement_file
        )
        if os.path.exists(results_json):
            print(results_json)
            try:
                with open(results_json) as file:
                    results = json.load(file)
                measurement_values = [measurement_key_types[key](results[key]) for key in measurement_keys]
            except Exception as e:
                print(e)

    return pd.DataFrame({
        "": measurement_headers,
        "Value": measurement_values
    }).set_index([""]).rename(columns={"":"","Value":""})

# Detectors apart from each other.
def show_step1_2_results(experiment_dir = None):
    return load_measurement_values(experiment_dir, step1_2_json_file, measurement_1_headers, measurement_1_keys,
    # Default values.
    [
        "2022-01-25 20:22:59",
        "4:00:00",
        2000,
        50473,
        38896,
        3.39,
        2.94,
        6,
        1.85e-4
    ])

# Detectors horizontally next to each other.
def show_step1_3_results(experiment_dir = None):
    return load_measurement_values(experiment_dir, step1_3_json_file, measurement_1_headers, measurement_1_keys,
    # Default values.
    [
        "2022-01-26 10:00:00",
        "18:50:30",
        2000,
        153636,
        139304,
        2.25,
        2.04,
        924,
        1.35e-2
    ])

# Detectors vertically next to (on top of) each other.
def show_step1_4_results(experiment_dir = None):
    return load_measurement_values(experiment_dir, step1_4_json_file, measurement_1_headers, measurement_1_keys,
    # Default values.
    [
        "2022-01-26 10:00:00",
        "18:50:30",
        2000,
        153636,
        139304,
        2.25,
        2.04,
        924,
        1.35e-2
    ])

# Chance rate.
def show_step2_results(experiment_dir = None):
    return load_measurement_values(experiment_dir, step2_json_file, measurement_2_headers, measurement_2_keys,
    # Default values.
    [
        "2022-01-25 20:22:59",
        "2:56:11",
        2000,
        47736,
        48,
        4.5,
        4.52e-3,
        4.5 * 4.52e-3 * 2.0e-3
    ])

# Background rate.
def show_step3_results(experiment_dir = None):
    return load_measurement_values(experiment_dir, step3_json_file, measurement_3_headers, measurement_3_keys,
    # Default values.
    [
        "2022-01-25 20:22:59",
        "2:56:11 ",
        2000,
        47736,
        48,
        4.5,
        4.52e-3,
        35,
        7.44e-3
    ])

# Tandem rate.
def show_step4_results(experiment_dir = None):
    return load_measurement_values(experiment_dir, step4_json_file, measurement_4_headers, measurement_4_keys,
    # Default values.
    [
        "2022-01-10 22:56:48",
        "10:01:49",
        2000,
        67463,
        87,
        1.9,
        2.45e-3,
        69,
        1.94e-2
    ])

def show_uqe(step2, step3, step4):
    T_s = step2[""]["Measurement Start Time"]
    # Total time added from chance, background and experiment elapsed times.
    T_t = "24:56:11"
    R_c = step2[""]["Chance Rate (1/s)"]
    R_b = step3[""]["Coincidence Rate (1/s)"]
    R_e = step4[""]["Coincidence Rate (1/s)"]
    R_r = R_e - R_b
    uqe = R_r / float(R_c)
    return pd.DataFrame({
        "": uqe_headers,
        "Value": [
            T_s,
            T_t,
            R_c,
            R_b,
            R_e,
            R_r,
            uqe
        ]
    }).set_index([""]).rename(columns={"":"","Value":""})

def get_result(key, data):
    return data[""][key]

def background_rate_detectors_apart(value):
    return md(mathjax_equation("R_{bfa} = %s/s" % value))

def background_rate_detectors_close(value):
    return md(mathjax_equation("R_{bfn} = %s/s" % value))

def background_rate_detectors_final(value):
    return md(mathjax_equation("R_{bff} = R_{bfn} - R_{bfa} = %s/s" % value))

def mathjax_equation(clause):
    return "<br/><br/>\\begin{equation}\n%s\n\\end{equation}" % clause
