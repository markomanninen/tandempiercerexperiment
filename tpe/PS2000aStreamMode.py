#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Pico Technology Ltd. See LICENSE file for terms.
# Copyright (C) 2021-2022 Marko Manninen
#
# PS2000A STREAM MODE to retrieve data from four channels with a trigger.

from ctypes import c_int16, c_int32, byref, POINTER
from picosdk.ps2000a import ps2000a as ps
from picosdk.functions import adc2mV
from numpy import zeros, int16
from time import sleep

# Create chandle
chandle = c_int16()

maxADC = c_int16()

# Define channels
channels = (
    "PS2000A_CHANNEL_A",
    "PS2000A_CHANNEL_B",
    "PS2000A_CHANNEL_C",
    "PS2000A_CHANNEL_D"
)

channel_voltage_ranges = None

# Open picoscope
def open_picoscope():
    global chandle
    try:
        return ps.ps2000aOpenUnit(byref(chandle), None) == 0
    except Exception as e:
        print(e)
        return False


# Set channels
def set_channels(voltage_range = ("10V", "10V", "10V", "10V"),
                 analogue_offset = 0.0,
                 coupling = "DC"):
    global chandle, channels, channel_voltage_ranges

    channel_voltage_ranges = voltage_range

    enabled = 1
    #disabled = 0

    for i, channel in enumerate(channels):
        ps.ps2000aSetChannel(
            chandle,
            ps.PS2000A_CHANNEL[channel],
            enabled,
            ps.PS2000A_COUPLING["PS2000A_%s" % coupling],
            ps.PS2000A_RANGE["PS2000A_%s" % voltage_range[i]],
            analogue_offset
        )

# Size of capture
sizeOfOneBuffer = None
totalSamples = None
buffer_max = {}
buffer_complete = {}

ratio_mode_none = ps.PS2000A_RATIO_MODE["PS2000A_RATIO_MODE_NONE"]

# Set buffers
def set_buffers(buffer_size = 500, buffer_count = 2, interval = 128, units = "NS", memory_segment = 0):
    global chandle, sizeOfOneBuffer, totalSamples, buffer_max, buffer_complete, ratio_mode_none
    sizeOfOneBuffer = buffer_size
    totalSamples = buffer_size * buffer_count
    for channel in channels:
        # Reserve buffers ready for assigning pointers for data collection
        # (c_int16 * sizeOfOneBuffer)()
        buffer_max[channel] = zeros(shape=sizeOfOneBuffer, dtype=int16)
        # We need a big buffer, not registered with the driver, to keep our complete capture in
        # (c_int16 * totalSamples)()
        buffer_complete[channel] = zeros(shape=totalSamples, dtype=int16)
        ps.ps2000aSetDataBuffers(
            chandle,
            ps.PS2000A_CHANNEL[channel],
            buffer_max[channel].ctypes.data_as(POINTER(c_int16)),
            None,
            sizeOfOneBuffer,
            memory_segment,
            ratio_mode_none
        )

    return start_streaming(interval, units) == 0

# Start streaming
# units: = NS (nanoseconds), US (microseconds)
# maxPreTriggerSamples: We are not triggering in streaming mode
def start_streaming(interval = 128, units = "NS", maxPreTriggerSamples = 0, autoStopOn = 0, downsampleRatio = 1):
    global chandle, totalSamples, sizeOfOneBuffer, ratio_mode_none
    # Begin streaming mode
    return ps.ps2000aRunStreaming(
        chandle,
        byref(c_int32(interval)),
        ps.PS2000A_TIME_UNITS["PS2000A_%s" % units],
        maxPreTriggerSamples,
        totalSamples,
        autoStopOn,
        downsampleRatio,
        ratio_mode_none,
        sizeOfOneBuffer
    )

nextSample = 0
wasCalledBack = False
autoStopOuter = False

# Define streaming callback
def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
    global nextSample, autoStopOuter, wasCalledBack, buffer_max, buffer_complete, channels
    wasCalledBack = True
    destEnd = nextSample + noOfSamples
    sourceEnd = startIndex + noOfSamples
    for channel in channels:
        buffer_complete[channel][nextSample:destEnd] = buffer_max[channel][startIndex:sourceEnd]
    nextSample += noOfSamples
    if autoStop:
        autoStopOuter = True

# Convert the python function into a C function pointer
cFuncPtr = ps.StreamingReadyType(streaming_callback)

def start_capture(sleep_time = 0.01):
    streaming_loop(sleep_time)

# Define streaming loop to get latest values to the buffer
def streaming_loop(sleep_time = 0.01):
    global nextSample, autoStopOuter, wasCalledBack, totalSamples, chandle, cFuncPtr
    while nextSample < totalSamples and not autoStopOuter:
        wasCalledBack = False
        ps.ps2000aGetStreamingLatestValues(chandle, cFuncPtr, None)
        if not wasCalledBack:
            # If we weren"t called back by the driver, this means no data is ready
            # Sleep for a short while before trying again
            sleep(sleep_time)

def get_buffers():
    global channels, buffer_complete
    for channel in channels:
        yield buffer_complete[channel][:]

def get_buffers_adc2mv():
    global chandle, maxADC, channels, buffer_complete, channel_voltage_ranges

    ps.ps2000aMaximumValue(chandle, byref(maxADC))

    # Convert ADC counts data to mV
    for i, channel in enumerate(channels):
        # Return copy of the converted buffers.
        yield adc2mV(buffer_complete[channel], ps.PS2000A_RANGE["PS2000A_%s" % channel_voltage_ranges[i]], maxADC)[:]
    #time = np.linspace(0, (cTotalSamples.value) * timeIntervalns.value, cTotalSamples.value)

# Define streaming init to be used after getting new values to the buffers
def init_capture():
    global nextSample, autoStopOuter, wasCalledBack, totalSamples, buffer_complete, channels
    for channel in channels:
        # (c_int16 * totalSamples)()
        buffer_complete[channel] = zeros(shape=totalSamples, dtype=int16)
    nextSample = 0
    autoStopOuter = False
    wasCalledBack = False

# Define stop picoscope procedure
def stop_picoscope():
    global chandle
    ps.ps2000aStop(chandle)
    ps.ps2000aCloseUnit(chandle)
