#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Pico Technology Ltd. See LICENSE file for terms.
# Copyright (C) 2021-2022 Marko Manninen
#
# PS2000A BLOCK MODE to retrieve data from four channels with a trigger.

from ctypes import c_int16, c_int32, c_float, byref, POINTER
from picosdk.ps2000a import ps2000a as ps, \
     PS2000A_TRIGGER_CONDITIONS, \
     PS2000A_TRIGGER_CHANNEL_PROPERTIES, \
     PS2000A_PWQ_CONDITIONS
from picosdk.functions import adc2mV

# Create chandle and status ready for use
chandle = c_int16()

# Define channels
channels = (
    'PS2000A_CHANNEL_A',
    'PS2000A_CHANNEL_B',
    'PS2000A_CHANNEL_C',
    'PS2000A_CHANNEL_D'
)

# Voltage ranges labels and millivolt values.
# Values are from the ps.PS2000A_RANGE['PS2000A_1V'] etc.
VOLTAGE_RANGES = {
    '10MV' : 0,
    '20MV' : 1,
    '50MV' : 2,
    '100MV': 3,
    '200MV': 4,
    '500MV': 5,
    '1V'   : 6,
    '2V'   : 7,
    '5V'   : 8,
    '10V'  : 9,
    '20V'  : 10,
    '50V'  : 11
}

# Four channel voltage list, for example: (10V, 10V, 20V, 20V)
channel_voltage_ranges = None

# Set number of pre and post trigger samples to be collected
preTriggerSamples = 0
postTriggerSamples = 0
totalSamples = 0
cTotalSamples = None

# timebase = 8 = 80 ns = timebase (see Programmer's guide for mre information on timebases)
timebase = 0
timeIntervalns = c_float()
oversample = c_int16(0)

maxADC = c_int16()

segment = 0

ratio_mode_none = ps.PS2000A_RATIO_MODE['PS2000A_RATIO_MODE_NONE']

buffer_max = {}
buffer_min = {}

"""
# Start picoscope.
open_picoscope()

# If application has changed picoscope parameters, use
# these functions to reinitialize the device.
set_channels()
set_buffers(
    # Trigger settings.
    {
        'enabled': 1,
        'channel': 0,
        'threshold': 1024,
        'direction': 2,
        'delay': 0,
        'auto_trigger': 1000
    },
    # Timebase settings. These are used to calculate the buffer size.
    {
        'timebase_n': 8,
        'pre_trigger_samples': 2500,
        'post_trigger_samples': 2500
    }
)

# Repeat these functions in a loop for DAQ (data acquisition).
start_capture()
get_buffers() OR get_buffers_adc2mv()
init_capture()

# Finally, when everything is done, gracefully stop the device.
stop_picoscope()
"""

def open_picoscope():
    global chandle
    try:
        return ps.ps2000aOpenUnit(byref(chandle), None) == 0
    except Exception as e:
        print(e)
        return False

# Set voltage range for each channel individually.
def set_channels(voltage_range = ('10V', '10V', '10V', '10V'),
                 analogue_offset = 0.0,
                 coupling = 'DC'):
    global chandle, channels, channel_voltage_ranges

    channel_voltage_ranges = voltage_range
    enabled = 1
    #disabled = 0

    for i, channel in enumerate(channels):
        ps.ps2000aSetChannel(
            chandle,
            ps.PS2000A_CHANNEL[channel],
            enabled,
            ps.PS2000A_COUPLING['PS2000A_%s' % coupling],
            ps.PS2000A_RANGE['PS2000A_%s' % voltage_range[i]],
            analogue_offset
        )

def set_buffers(trigger_settings, timebase_settings, advanced_trigger_settings):

    if trigger_settings['enabled'] == 1:
        set_trigger(**trigger_settings)
    elif advanced_trigger_settings['enabled'] == 1:
        set_advanced_trigger(**advanced_trigger_settings)
    ret = set_timebase(**timebase_settings)
    init_capture()
    return ret == 0

def set_trigger(enabled = 1, channel = 0, threshold = 1024, direction = 2, delay = 0, auto_trigger = 1000, alternate_channel = False):
    global chandle
    # Channel source, ps2000a_CHANNEL_A = 0
    # Threshold ADC counts
    # Direction = PS2000A_RISING = 2
    return ps.ps2000aSetSimpleTrigger(chandle, enabled, channel, threshold, direction, delay, auto_trigger)

def set_advanced_trigger(enabled = 1, channels = ('A', 'B'), upper_threshold = 20, upper_hysteresis = 2.5, auto_trigger_ms = 1000):
    global chandle

    """
    ("channelA", c_int32),
    ("channelB", c_int32),
    ("channelC", c_int32),
    ("channelD", c_int32),
    ("external", c_int32),
    ("aux", c_int32),
    ("pulseWidthQualifier", c_int32),
    ("digital", c_int32)
    """

    trigger_conditions_n = 2

    Condition = PS2000A_TRIGGER_CONDITIONS * trigger_conditions_n

    trigger_conditions = Condition(
        PS2000A_TRIGGER_CONDITIONS(
            (1 if channels[0] == 'A' else 0),
            (1 if channels[0] == 'B' else 0),
            (1 if channels[0] == 'C' else 0),
            (1 if channels[0] == 'D' else 0), 0, 0, 0, 0),
        PS2000A_TRIGGER_CONDITIONS(
            (1 if channels[1] == 'A' else 0),
            (1 if channels[1] == 'B' else 0),
            (1 if channels[1] == 'C' else 0),
            (1 if channels[1] == 'D' else 0), 0, 0, 0, 0)
    )

    """
    int16_t                     handle,
    PS2000A_TRIGGER_CONDITIONS *conditions,
    int16_t                     nConditions
    """
    # If multiple conditions are given, they are regarded as AND.
    ps.ps2000aSetTriggerChannelConditions(chandle, byref(trigger_conditions), trigger_conditions_n)
    # But if conditions function is called multiple times, they are regarded as OR.
    # ... and channel n.
    #ps.ps2000aSetTriggerChannelConditions(chandle, byref(triggerConditionsN), number_of_conditions)

    # Pulse height trigger (mV to ACD)
    upper_threshold_bits = int(2**16 * upper_threshold / 100)
    hysteresis = int(upper_hysteresis / 100 * upper_threshold_bits)
    threshold_mode = ps.PS2000A_THRESHOLD_MODE["PS2000A_LEVEL"]

    # Set advanced trigger channel properties.

    """

    ps2000a_above = 0
    ps2000a_below = 1
    ps2000a_rising = 2
    ps2000a_falling = 3
    ps2000a_rising_or_falling = 4
    ps2000a_above_lower = 5
    ps2000a_below_lower = 6
    ps2000a_rising_lower = 7
    ps2000a_falling_lower = 8

    ps2000a_inside = ps2000a_above
    ps2000a_outside = ps2000a_below
    ps2000a_enter = ps2000a_rising
    ps2000a_exit = ps2000a_falling
    ps2000a_enter_or_exit = ps2000a_rising_or_falling
    ps2000a_positive_runt = 9
    ps2000a_negative_runt = 10

    ps2000a_none = ps2000a_rising

    ("thresholdUpper", c_int16),
    ("thresholdHysteresis", c_uint16),
    ("thresholdLower", c_int16),
    ("thresholdLowerHysteresis", c_uint16),
    ("channel", c_int32),
    ("thresholdMode", c_int32)]
    """

    trigger_properties_n = 2

    Property = PS2000A_TRIGGER_CHANNEL_PROPERTIES * trigger_properties_n

    trigger_properties = Property(
        PS2000A_TRIGGER_CHANNEL_PROPERTIES(
            upper_threshold_bits, hysteresis, 0, 0, ps.PS2000A_CHANNEL["PS2000A_CHANNEL_%s" % channels[0]], threshold_mode
        ),
        PS2000A_TRIGGER_CHANNEL_PROPERTIES(
            upper_threshold_bits, hysteresis, 0, 0, ps.PS2000A_CHANNEL["PS2000A_CHANNEL_%s" % channels[1]], threshold_mode
        )
    )

    #triggerProperties1 = PS2000A_TRIGGER_CHANNEL_PROPERTIES(
    #    upper_threshold_bits, hysteresis, 0, 0, ps.PS2000A_CHANNEL["PS2000A_CHANNEL_C"], threshold_mode
    #)

    """
        int16_t                             handle,
        PS2000A_TRIGGER_CHANNEL_PROPERTIES *channelProperties,
        int16_t                             nChannelProperties,
        int16_t                             auxOutputEnable,
        int32_t                             autoTriggerMilliseconds
    """
    #ps.ps2000aSetTriggerChannelProperties(chandle, byref(triggerProperties1), 1, 0, 1000)
    ps.ps2000aSetTriggerChannelProperties(chandle, byref(trigger_properties), trigger_properties_n, 0, auto_trigger_ms)

    # Set advanced trigger channel direction.
    triggerDirection = ps.PS2000A_THRESHOLD_DIRECTION["PS2000A_RISING"]

    """
    int16_t                      handle,
        PS2000A_THRESHOLD_DIRECTION  channelA,
        PS2000A_THRESHOLD_DIRECTION  channelB,
        PS2000A_THRESHOLD_DIRECTION  channelC,
        PS2000A_THRESHOLD_DIRECTION  channelD,
        PS2000A_THRESHOLD_DIRECTION  ext,
        PS2000A_THRESHOLD_DIRECTION  aux
    """

    ps.ps2000aSetTriggerChannelDirections(chandle,
        (triggerDirection if channels[0] == 'A' else 0),
        (triggerDirection if channels[0] == 'B' else 0),
        (triggerDirection if channels[0] == 'C' else 0),
        (triggerDirection if channels[0] == 'D' else 0), 0, 0)
    ps.ps2000aSetTriggerChannelDirections(chandle,
        (triggerDirection if channels[1] == 'A' else 0),
        (triggerDirection if channels[1] == 'B' else 0),
        (triggerDirection if channels[1] == 'C' else 0),
        (triggerDirection if channels[1] == 'D' else 0), 0, 0)

    #ps.ps2000aSetTriggerChannelDirections(chandle, 0, 0, triggerDirection1, triggerDirection2, 0, 0)

    # Set pulse width qualifier with ps2000aSetTriggerDelay
    """
    pwqConditions = ps.PS2000aPwqConditions(1, 0, 0, 0, 0)
    pwqDirections = ps.PS2000_THRESHOLD_DIRECTION["PS2000_THRESHOLD_DIRECTION_RISING"]
    pwqProperties = ps.PS2000_PULSE_WIDTH_TYPE["PS2000_PW_TYPE_GREATER_THAN"]
    PW_lowerlim = ctypes.c_uint32(20000)
    PW_upperlim = ctypes.c_uint32(0)
    ps.ps2000aSetPulseWidthQualifier(chandle, byref(pwqConditions), 1, pwqDirections, PW_lowerlim, PW_upperlim, pwqProperties)
    """

def _get_trigger_direction_from_name(direction_name):
    if direction_name in ['ABOVE', 'BELOW', 'RISING', 'FALLING', 'RISING_OR_FALLING']:
        def_name = f"PS2000A_{direction_name}"
    else:
        raise InvalidParameterError(f"Trigger direction {direction_name} is not supported")
    return ps.PS2000A_THRESHOLD_DIRECTION[def_name]

def set_timebase(timebase_n = 8, pre_trigger_samples = 2500, post_trigger_samples = 2500):
    global chandle, channels, segment, buffer_max, buffer_min, timebase, totalSamples, cTotalSamples, totalSamples, timeIntervalns, oversample, preTriggerSamples, postTriggerSamples

    for channel in channels:
        #buffer_max[channel] = zeros(shape=totalSamples, dtype=int16)
        buffer_max[channel] = (c_int16 * totalSamples)()
        buffer_min[channel] = (c_int16 * totalSamples)()

    timebase = timebase_n
    preTriggerSamples = pre_trigger_samples
    postTriggerSamples = post_trigger_samples
    totalSamples = preTriggerSamples + postTriggerSamples

    # create converted type totalSamples
    cTotalSamples = c_int32(totalSamples)
    returnedMaxSamples = c_int32()

    return ps.ps2000aGetTimebase2(
        chandle,
        timebase,
        totalSamples,
        byref(timeIntervalns),
        oversample,
        byref(returnedMaxSamples),
        segment
    )

def init_capture():
    global channels, buffer_max, buffer_min

    for channel in channels:
        #buffer_max[channel] = zeros(shape=totalSamples, dtype=int16)
        buffer_max[channel] = (c_int16 * totalSamples)()
        buffer_min[channel] = (c_int16 * totalSamples)()

def run_block(time_indisposed_ms = None, lp_ready = None, p_parameter = None):
    global chandle, segment, preTriggerSamples, postTriggerSamples, timebase, oversample

    ps.ps2000aRunBlock(
        chandle,
        preTriggerSamples,
        postTriggerSamples,
        timebase,
        oversample,
        time_indisposed_ms,
        segment,
        lp_ready,
        p_parameter
    )

def start_capture(sleep_time = 0.01):
    global chandle, segment, totalSamples, cTotalSamples, overflow, ratio_mode_none, buffer_max, buffer_min

    run_block()

    # Check for data collection.
    ready = c_int16(0)
    check = c_int16(0)
    while ready.value == check.value:
        ps.ps2000aIsReady(chandle, byref(ready))

    # Set data buffer locations for data collection.
    for channel in channels:
        ps.ps2000aSetDataBuffers(
            chandle,
            ps.PS2000A_CHANNEL[channel],
            byref(buffer_max[channel]),
            byref(buffer_min[channel]),
            totalSamples,
            segment,
            ratio_mode_none
        )

    start_index = 0
    downsample_ratio = 0
    # Note, this is a global variable.
    overflow = c_int16()
    # Retried data from scope to buffers assigned above.
    ps.ps2000aGetValues(chandle, start_index, byref(cTotalSamples), downsample_ratio, ratio_mode_none, segment, byref(overflow))

def get_buffers():
    global channels, buffer_max
    for channel in channels:
        # Return copy of the buffers.
        yield buffer_max[channel][:]

def get_buffers_adc2mv():
    global chandle, maxADC, channels, buffer_max, channel_voltage_ranges, VOLTAGE_RANGES

    ps.ps2000aMaximumValue(chandle, byref(maxADC))

    # Convert ADC counts data to mV
    for i, channel in enumerate(channels):
        yield adc2mV(
            buffer_max[channel],
            VOLTAGE_RANGES[channel_voltage_ranges[i]],
            maxADC
        )[:]
    #time = np.linspace(0, (cTotalSamples.value) * timeIntervalns.value, cTotalSamples.value)

"""
def adctomv(buffer):
    global chandle, maxADC
    ps.ps2000aMaximumValue(chandle, byref(maxADC))
    return (
        adc2mV(buffer[2],VOLTAGE_RANGES[channel_voltage_ranges[2]], maxADC)
        adc2mV(buffer[3],VOLTAGE_RANGES[channel_voltage_ranges[3]], maxADC)
    )
"""

def stop_picoscope():
    global chandle
    ps.ps2000aStop(chandle)
    ps.ps2000aCloseUnit(chandle)
