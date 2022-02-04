#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np
from scipy.signal import find_peaks
from IPython.display import display
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
    #bca[(bca > high_limit)] = high_limit
    #bca[(bca < -high_limit)] = -high_limit
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
def show_image(file, width=640, height=480):
    image  = Image.open(file)
    aspect = width / float(height)
    display(image.resize((int(aspect * height), int(width / aspect)), Image.ANTIALIAS))

def get_channels_parameters(file = 'regions.json', region = 'gammas'):

    with open(file) as json_file:
        data = json.load(json_file)

    def format_channel_data(data, channel_name):
        limit_index = 0 if channel_name == 'channel_a' else 1
        channel = {
            'Spectrum_ADC_low_limit': data['spectrum_low_limits'][limit_index],
            'Spectrum_ADC_high_limit': data['spectrum_high_limits'][limit_index]
        }
        channel.update(data['sca_module_settings'][channel_name])
        return {key.title().replace('_', ' '): value for key, value in channel.items()}

    return pd.DataFrame({
        'Channel A': format_channel_data(data[region], 'channel_a'),
        'Channel B': format_channel_data(data[region], 'channel_b')
    })
