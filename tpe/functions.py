#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np

# Normalize signal to zero line.
def baseline_correct(data):
    return np.abs((lambda x: x - x.mean())(data))

# Remove noise from the signal.
def filter_spectrum(data, counter_str, limit, self):
    # Select only data that is greater than limit.
    a = data[data > limit]
    # Add length of the array with value greater than limit
    self.__dict__[counter_str] = len(a)
    # Return filtered values.
    return a
