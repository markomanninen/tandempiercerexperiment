#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np
from scipy.signal import find_peaks

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
