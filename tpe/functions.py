#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np

def baseline_correct(data):
    return np.abs((lambda x: x - x.mean())(data))

def filter_spectrum(data, counter_str, limit, self):
    a = data[data > limit]
    self.__dict__[counter_str] += len(a)
    return a
