#!/usr/bin/python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
from matplotlib.pyplot import text
import matplotlib.ticker as ticker

from datetime import datetime
import pandas as pd
import os, glob

class Stats():

    def __init__(self, headers = None):

        self.experiment_directory = "../experiments/*"
        self.statistics_filename = "statistics.csv"
        self.get_experiment_stat_files()

        if headers is None:
            self.headers = (
                "Time",
                "Elapsed",
                "A",
                "B",
                "TotA",
                "TotB",
                "RateA",
                "RateB",
                "Cnc",
                "TotCnc",
                "ElapsedCncRate",
                "SampleCncRate",
                "TimeDifference",
                "APulseHeight",
                "BPulseHeight",
                "RateCount",
                "SampleSize",
                "Chn"
            )
        else:
            self.headers = headers

        self.adc_kev_ratio = 0

    def get_experiment_stat_files(self, directory = None):
        for experiment_directory in glob.glob(self.experiment_directory if directory is None else directory):
            statistics_file = os.path.join(experiment_directory, self.statistics_filename)
            if os.path.isfile(statistics_file):
                yield statistics_file

    def print_experiment_stat_files(self, directory = None):
        return list(map(print, self.get_experiment_stat_files(directory)))

    def read_stats_dataframe(self, csv_filename):
        self.csv_filename = csv_filename
        df = pd.read_csv(self.csv_filename, sep = ";", names = self.headers)
        self.desc = df.describe()
        df['Time'] = pd.to_datetime(df['Time'], unit = 's')
        pd.options.display.float_format = '{:,.3f}'.format
        self.last_index = len(df) - 1
        self.stats = df
        return self.stats

    def get_desc_value(self, col, row):
        return self.desc[col][row]

    def adc_calibrate(self, adc, kev):
        self.adc = adc
        self.kev = kev
        self.adc_kev_ratio = self.kev / self.adc

    def to_kev(self, adc):
        return self.adc_kev_ratio * (adc if self.adc_kev_ratio != 0 else adc)

    def sample_size(self):
        return self.get_desc_value("SampleSize", "max")

    def max_pulse_height_a(self):
        return self.get_desc_value("APulseHeight", "max")
    def min_pulse_height_a(self):
        return self.get_desc_value("APulseHeight", "min")
    def std_pulse_height_a(self):
        return self.get_desc_value("APulseHeight", "std")
    def mean_pulse_height_a(self):
        return self.get_desc_value("APulseHeight", "mean")

    def max_pulse_height_b(self):
        return self.get_desc_value("BPulseHeight", "max")
    def min_pulse_height_b(self):
        return self.get_desc_value("BPulseHeight", "min")
    def std_pulse_height_b(self):
        return self.get_desc_value("BPulseHeight", "std")
    def mean_pulse_height_b(self):
        return self.get_desc_value("BPulseHeight", "mean")

    def pulse_heights_a(self, coincidences = True):
        return self.stats[self.stats["Cnc"] == 1]["APulseHeight"].to_numpy() if coincidences else self.stats["APulseHeight"].to_numpy()

    def pulse_heights_b(self, coincidences = True):
        return self.stats[self.stats["Cnc"] == 1]["BPulseHeight"].to_numpy() if coincidences else self.stats["BPulseHeight"].to_numpy()

    def time_differences(self, coincidences = True):
        return self.stats[self.stats["Cnc"] == 1]["TimeDifference"].to_numpy() if coincidences else self.stats["TimeDifference"].to_numpy()

    def rows_count(self):
        return self.last_index + 1

    def rate_a(self):
        return self.get_desc_value("RateA", "max")

    def rate_b(self):
        return self.get_desc_value("RateB", "max")

    def total_count_a(self):
        return int(self.get_desc_value("TotA", "max"))

    def total_count_b(self):
        return int(self.get_desc_value("TotB", "max"))

    def total_coincidences(self):
        return int(self.get_desc_value("TotCnc", "max"))

    def single_coincidences(self):
        return len(self.stats[self.stats["Cnc"] == 1])

    def time_elapsed(self):
        return self.get_desc_value("Elapsed", "max")

    def start_time(self):
        return self.stats["Time"][0]

    def end_time(self):
        return self.stats["Time"][self.last_index]

    def coincidence_elapsed_rate(self):
        return self.get_desc_value("ElapsedCncRate", "max")

    def coincidence_sample_rate(self):
        return self.get_desc_value("SampleCncRate", "max")

    def info(self):
        return self.stats.info()

    def plot(self, cols, *args, **kwargs):
        self.stats.set_index("Elapsed")[cols].plot(*args, **kwargs)

    def scatter(self, *args, **kwargs):
        df = self.stats[self.stats["Cnc"] == 1].copy()
        df['APulseHeight'] = df.loc[:, ('APulseHeight')].apply(self.to_kev)
        df['BPulseHeight'] = df.loc[:, ('BPulseHeight')].apply(self.to_kev)
        return df.plot(
            kind = "scatter",
            x = "APulseHeight",
            y = "BPulseHeight",
            c = "Chn",
            colormap = "bwr",
            colorbar = False,
            *args, **kwargs
        )

    def time_difference_histogram(self, *args, **kwargs):
        self.histogram(self.stats[self.stats["Cnc"] == 1]["TimeDifference"], kind = "hist", bins = 128, *args, **kwargs)

    def histogram(self, df, *args, **kwargs):
        return df.plot(*args, **kwargs)

    def spectrum_histogram_a(self, coincidences = True, *args, **kwargs):
        df = (self.stats[self.stats["Cnc"] == 1] if coincidences else self.stats).copy()
        df['APulseHeight'] = df['APulseHeight'].apply(self.to_kev)
        return self.histogram(df["APulseHeight"], kind="hist", bins = 128, *args, **kwargs)

    def spectrum_histogram_b(self, coincidences = True, *args, **kwargs):
        df = (self.stats[self.stats["Cnc"] == 1] if coincidences else self.stats).copy()
        df['BPulseHeight'] = df['BPulseHeight'].apply(self.to_kev)
        return self.histogram(df["BPulseHeight"], kind = "hist", bins = 128, *args, **kwargs)

    def plot_channel_counts(self, sec = 1, *args, **kwargs):
        fig, ax = plt.subplots()
        for axis in [ax.xaxis, ax.yaxis]:
            axis.set_major_locator(ticker.MaxNLocator(integer=True))
        df = self.stats
        a = df.groupby(df['Elapsed'].apply(lambda x: round(x/sec))).count()
        a[["A", "B"]].plot(kind = "line", figsize = (16,4), ax = ax, *args, **kwargs)
        ax.set_xlabel("Elapsed time (%ss)" % sec)

    def plot_channel_totals_and_rates(self):
        fig, axes = plt.subplots(nrows=2, ncols=1)
        self.plot(["TotA", "TotB"], figsize = (16,8), ax = axes[0])
        self.plot(["RateA", "RateB"], figsize = (16,8), ax = axes[1])
        axes[0].set_xlabel("")
        axes[1].set_xlabel("Elapsed time (s)")

    def plot_coincidences_and_sample_rate(self):
        fig, axes = plt.subplots(nrows = 1, ncols = 2)
        self.plot(["Cnc", "TotCnc"], figsize = (18, 4), ax = axes[0])
        self.plot(["SampleCncRate", "ElapsedCncRate"], figsize = (18, 4), ax = axes[1])
        #self.plot(["SampleSize", "Chn"], figsize = (18, 4), ax = axes[2])
        axes[0].set_xlabel("Elapsed time (s)")
        axes[1].set_xlabel("Elapsed time (s)")
        #axes[2].set_xlabel("Elapsed time (s)")

    def plot_time_histogram_and_scatter(self):
        fig, axes = plt.subplots(nrows = 1, ncols = 2)
        for axis in [axes[0].xaxis, axes[0].yaxis]:
            axis.set_major_locator(ticker.MaxNLocator(integer = True))

        self.time_difference_histogram(title = "Coincidence time difference", figsize = (16, 4), ax = axes[0])
        axes[0].set_xlabel("Time (ns)")
        axes[0].set_ylabel("Count (%s)" % self.total_coincidences())

        a = self.scatter(title = "Coincidence ADC scatter", figsize = (16, 4), ax = axes[1])
        axes[1].set_xlabel("Channel A (%s)" % ("ADC" if self.adc_kev_ratio == 0 else "keV"))
        axes[1].set_ylabel("Channel B (%s)" % ("ADC" if self.adc_kev_ratio == 0 else "keV"))

        if self.adc_kev_ratio != 0:
            axes[1].axhline(y=self.kev, xmin=-1, color="g", linestyle="--", lw=1)
            axes[1].axvline(x=self.kev, ymin=-1, color="g", linestyle="--", lw=1)
            axes[1].text(self.kev + 2, a.get_ylim()[1], "%skeV" % self.kev, rotation = 90, verticalalignment = 'top', horizontalalignment = 'left')

    def plot_spectra(self, *args, **kwargs):
        fig, axes = plt.subplots(nrows = 1, ncols = 2)
        for ax in axes:
            for axis in [ax.xaxis, ax.yaxis]:
                axis.set_major_locator(ticker.MaxNLocator(integer = True))

        a = self.spectrum_histogram_a(title = "Channel A", figsize = (16, 4), ax = axes[0], color = "red", *args, **kwargs);
        b = self.spectrum_histogram_b(title = "Channel B", figsize = (16, 4), ax = axes[1], *args, **kwargs);

        axes[0].set_xlabel("ADC" if self.adc_kev_ratio == 0 else "keV")
        axes[0].set_ylabel("Count (%s)" % (self.total_coincidences() if "coincidences" in kwargs and kwargs["coincidences"] else self.total_count_a()))
        axes[1].set_xlabel("ADC" if self.adc_kev_ratio == 0 else "keV")
        axes[1].set_ylabel("Count (%s)" % (self.total_coincidences() if "coincidences" in kwargs and kwargs["coincidences"] else self.total_count_b()))

        if self.adc_kev_ratio != 0:
            axes[0].axvline(x=self.kev, ymin=-1, color="g", linestyle="--", lw=1)
            axes[1].axvline(x=self.kev, ymin=-1, color="g", linestyle="--", lw=1)
            axes[0].text(self.kev+2, a.get_ylim()[1], "%skeV" % self.kev, rotation = 90, verticalalignment = 'top')
            axes[1].text(self.kev+2, b.get_ylim()[1], "%skeV" % self.kev, rotation = 90, verticalalignment = 'top')
