#!/usr/bin/python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
from matplotlib.pyplot import text
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from IPython.display import Markdown as md
from scipy.signal import find_peaks

from datetime import datetime, timedelta
from pandas import Series
import pandas as pd
import numpy as np
import os, glob

def plot_peak_lines(norm, width = 2, distance = 2, threshold = 0.2):
    return find_peaks(norm, width = width, distance = distance, threshold = threshold)[0]

def add_calibration_line(plot, x, unit = ""):
    plot.axvline(x = x, ymin = -1, color = "g", linestyle = "--", lw = 2)
    plot.text(x, plot.get_ylim()[1], "%s %s" % (x, unit), rotation = 90, verticalalignment = 'top', backgroundcolor="White")

class Stats():

    def __init__(self, headers = None):

        self.experiment_directory = "../experiments/*"
        self.statistics_filename = "statistics.csv"
        self.get_experiment_stat_files()

        if headers is None:
            self.headers = (
                "RateCount",
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
                "SampleSize",
                "Chn"
            )
        else:
            self.headers = headers

        self.adc_kev_ratio_a = 0
        self.adc_kev_ratio_b = 0
        self.adc_a = 1
        self.adc_b = 1
        self.kev_a = 1
        self.kev_b = 1
        self.default_bins = 76
        self.calibration_lines = []

    def get_experiment_stat_files(self, directory = None):
        for experiment_directory in glob.glob(self.experiment_directory if directory is None else directory):
            statistics_file = os.path.join(experiment_directory, self.statistics_filename)
            if os.path.isfile(statistics_file):
                yield statistics_file

    def print_experiment_stat_files(self, directory = None):
        return list(map(print, self.get_experiment_stat_files(directory)))

    def read_stats_dataframe(self, directory, filter = False):
        self.csv_filename = "%s\statistics.csv" % directory
        df = pd.read_csv(self.csv_filename, sep = ";", names = self.headers)

        if filter:
            df = df[(df["APulseHeight"] > 0) | (df["BPulseHeight"] > 0)]
            df = df[(((df["APulseHeight"] == 0) & (df["Cnc"] > 0) == False) & ((df["BPulseHeight"] == 0) & (df["Cnc"] > 0) == False))]


        self.desc = df.describe()
        df['Time'] = pd.to_datetime(df['Time'], unit = 's')
        pd.options.display.float_format = '{:,.3f}'.format
        self.last_index = len(df) - 1
        self.stats = df
        return self.stats

    def get_desc_value(self, col, row):
        return self.desc[col][row]

    def adc_calibrate_a(self, adc, kev):
        self.adc_a = adc
        self.kev_a = kev
        self.adc_kev_ratio_a = self.kev_a / self.adc_a

    def adc_calibrate_b(self, adc, kev):
        self.adc_b = adc
        self.kev_b = kev
        self.adc_kev_ratio_b = self.kev_b / self.adc_b

    def add_calibration_line(self, val):
        self.calibration_lines.append(val)

    def reset_calibration_lines(self):
        self.calibration_lines = []

    def to_kev_a(self, adc):
        return (self.adc_kev_ratio_a * adc) if self.adc_kev_ratio_a != 0 else adc

    def to_kev_b(self, adc):
        return (self.adc_kev_ratio_b * adc) if self.adc_kev_ratio_b != 0 else adc

    def to_adc_a(self, kev):
        return (kev / self.adc_kev_ratio_a) if self.adc_kev_ratio_a != 0 else kev

    def to_adc_b(self, kev):
        return (kev / self.adc_kev_ratio_b) if self.adc_kev_ratio_b != 0 else kev

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

    def plot(self, cols, elapsed = None, *args, **kwargs):
        if elapsed is None:
            return self.stats.set_index("Elapsed")[cols].plot(*args, **kwargs)
        else:
            return self.stats[(self.stats["Elapsed"] > elapsed[0]) & (self.stats["Elapsed"] < elapsed[1])].set_index("Elapsed")[cols].plot(*args, **kwargs)

    def scatter(self, time_difference = None, channel = None, *args, **kwargs):
        df = self.stats[self.stats["Cnc"] == 1].copy()

        if time_difference is not None:
            df = df[(df["TimeDifference"] > -time_difference-1) & (df["TimeDifference"] < time_difference+1)]

        if channel is None:
            kwargs["colormap"] = kwargs["colormap"] if "colormap" in kwargs else "bwr"
            kwargs["c"] = kwargs["c"] if "c" in kwargs else "Chn"
        else:
            df = df[df["Chn"] == channel]
            kwargs["c"] = "Blue" if channel == 0 else "Red"

        df['APulseHeight'] = df.loc[:, ('APulseHeight')].apply(self.to_kev_a)
        df['BPulseHeight'] = df.loc[:, ('BPulseHeight')].apply(self.to_kev_b)

        return df.plot(
            kind = "scatter",
            x = "APulseHeight",
            y = "BPulseHeight",
            colorbar = None,
            alpha = 0.5,
            edgecolors = 'none',
            *args, **kwargs
        )

    def time_difference_histogram(self, time_difference = None, channel = None, *args, **kwargs):
        df = self.get_filtered_stats()

        if time_difference is not None:
            df = df[(df["TimeDifference"] > -time_difference-1) & (df["TimeDifference"] < time_difference+1)]

        if channel is not None:
            df = df[df["Chn"] == channel]

        return self.histogram(df["TimeDifference"], kind = "hist", *args, **kwargs)

    def histogram(self, df, *args, **kwargs):
        return df.plot(*args, **kwargs), len(df)

    def get_filtered_stats(self, coincidences = True):
        return (self.stats[self.stats["Cnc"] == 1] if coincidences else self.stats).copy()

    def spectrum_histogram_a(self, coincidences = True, *args, **kwargs):
        df = self.get_filtered_stats(coincidences)
        df = df[df["APulseHeight"] > 0]
        df['APulseHeight'] = df['APulseHeight'].apply(self.to_kev_a)
        kwargs["bins"] = kwargs["bins"] if "bins" in kwargs else self.default_bins
        return self.histogram(df["APulseHeight"], kind="hist", *args, **kwargs)

    def spectrum_histogram_b(self, coincidences = True, *args, **kwargs):
        df = self.get_filtered_stats(coincidences)
        df = df[df["BPulseHeight"] > 0]
        df['BPulseHeight'] = df['BPulseHeight'].apply(self.to_kev_b)
        kwargs["bins"] = kwargs["bins"] if "bins" in kwargs else self.default_bins
        return self.histogram(df["BPulseHeight"], kind = "hist", *args, **kwargs)

    def plot_channel_counts(self, sec = 1, *args, **kwargs):
        fig, ax = plt.subplots()
        for axis in [ax.xaxis, ax.yaxis]:
            axis.set_major_locator(ticker.MaxNLocator(integer=True))
        df = self.stats
        a = df.groupby(df['Elapsed'].apply(lambda x: round(x/sec))).count()
        a[["A", "B"]].plot(kind = "line", figsize = (16,4), ax = ax, *args, **kwargs)
        ax.set_xlabel("Elapsed time (%ss)" % sec)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    def remove_top_right_spines(self, axes):
        axes[0].spines['top'].set_visible(False)
        axes[1].spines['top'].set_visible(False)
        axes[0].spines['right'].set_visible(False)
        axes[1].spines['right'].set_visible(False)

    def plot_channel_totals_and_rates(self):
        fig, axes = plt.subplots(nrows=2, ncols=1)
        self.plot(["TotA", "TotB"], figsize = (16,8), ax = axes[0])
        self.plot(["RateA", "RateB"], figsize = (16,8), ax = axes[1])

        axes[0].set_xlabel("")
        axes[1].set_xlabel("Elapsed time (s)")

        self.remove_top_right_spines(axes)

    def plot_coincidences_and_sample_rate(self, elapsed = None):
        fig, axes = plt.subplots(nrows = 1, ncols = 2)
        self.plot(["Cnc", "TotCnc"], elapsed = elapsed, figsize = (18, 4), ax = axes[0])
        self.plot(["SampleCncRate", "ElapsedCncRate"], elapsed = elapsed, figsize = (18, 4), ax = axes[1])
        #self.plot(["SampleSize", "Chn"], figsize = (18, 4), ax = axes[2])
        axes[0].set_xlabel("Elapsed time (s)")
        axes[1].set_xlabel("Elapsed time (s)")

        self.remove_top_right_spines(axes)

    def plot_time_histogram_and_scatter(self, time_difference = None, channel = None, *args, **kwargs):

        fig, axes = plt.subplots(nrows = 1, ncols = 2)
        for axis in [axes[0].xaxis, axes[0].yaxis]:
            axis.set_major_locator(ticker.MaxNLocator(integer = True))

        histogram, count = self.time_difference_histogram(time_difference = time_difference, channel = channel, title = "Coincidence time difference", figsize = (16, 6), ax = axes[0], bins = self.default_bins)
        axes[0].set_xlabel("Time (ns)")
        axes[0].set_ylabel("Count (%s)" % count)

        scatter = self.scatter(time_difference = time_difference, channel = channel, title = "Coincidence scatter", figsize = (16, 6), ax = axes[1])
        axes[1].set_xlabel("Channel A (%s)" % ("ADC" if self.adc_kev_ratio_a == 0 else "keV"))
        axes[1].set_ylabel("Channel B (%s)" % ("ADC" if self.adc_kev_ratio_b == 0 else "keV"))

        line_width = 1
        if self.adc_kev_ratio_a != 0:
            if channel == None or channel == 0:
                axes[1].axhline(y=self.kev_a, xmin=-1, color="g", linestyle="-", lw=line_width)
                axes[1].text(scatter.get_xlim()[1], self.kev_a + 2, "%skeV" % self.kev_a, rotation = 0, verticalalignment = 'center', horizontalalignment = 'center', backgroundcolor = "White")
                for val in self.calibration_lines:
                    axes[1].axhline(y=val, xmin=-1, color="g", linestyle="-", lw=line_width)
                    axes[1].text(scatter.get_xlim()[1], val + 2, "%skeV" % val, rotation = 0, verticalalignment = 'center', horizontalalignment = 'center', backgroundcolor = "White")

        if self.adc_kev_ratio_b != 0:
            if channel == None or channel == 1:
                axes[1].axvline(x=self.kev_b, ymin=-1, color="g", linestyle="-", lw=line_width)
                axes[1].text(self.kev_b, scatter.get_ylim()[1], "%skeV" % self.kev_b, rotation = 90, verticalalignment = 'top', horizontalalignment = 'center', backgroundcolor = "White")
                for val in self.calibration_lines:
                    axes[1].axvline(x=val, ymin=-1, color="g", linestyle="-", lw=line_width)
                    axes[1].text(val, scatter.get_ylim()[1], "%skeV" % val, rotation = 90, verticalalignment = 'top', horizontalalignment = 'center', backgroundcolor = "White")

        self.remove_top_right_spines(axes)

    def plot_spectra(self, hide_calibration = False, *args, **kwargs):

        kwargs["bins"] = kwargs["bins"] if "bins" in kwargs else self.default_bins

        fig, axes = plt.subplots(nrows = 1, ncols = 2)

        log = "log" in kwargs and kwargs["log"]

        for ax in axes:
            if log:
                ax.yaxis.set_major_locator(ticker.LogLocator(base = 10))
            for axis in [ax.xaxis, ax.yaxis]:
                axis.set_major_locator(ticker.MaxNLocator(integer = True))

        a, length_a = self.spectrum_histogram_a(title = "Channel A", figsize = (16, 4), ax = axes[0], color = "Red", *args, **kwargs);

        b, length_b = self.spectrum_histogram_b(title = "Channel B", figsize = (16, 4), ax = axes[1], color = "Blue", *args, **kwargs);

        axes[0].set_xlabel("ADC" if self.adc_kev_ratio_a == 0 else "keV")
        axes[0].set_ylabel("Count (%s)" % length_a)
        axes[1].set_xlabel("ADC" if self.adc_kev_ratio_b == 0 else "keV")
        axes[1].set_ylabel("Count (%s)" % length_b)

        self.remove_top_right_spines(axes)

        if self.adc_kev_ratio_a != 0 and not hide_calibration:
            axes[0].axvline(x=self.kev_a, ymin=-1, color="g", linestyle="--", lw=2)
            axes[0].text(self.kev_a+2, a.get_ylim()[1], "%s keV" % self.kev_a, rotation = 90, verticalalignment = 'top', backgroundcolor = "White")
            for val in self.calibration_lines:
                axes[0].axvline(x=val, ymin=-1, color="g", linestyle="--", lw=2)
                axes[0].text(val+2, a.get_ylim()[1], "%s keV" % val, rotation = 90, verticalalignment = 'top', backgroundcolor = "White")

        if self.adc_kev_ratio_b != 0 and not hide_calibration:
            axes[1].axvline(x=self.kev_b, ymin=-1, color="g", linestyle="--", lw=2)
            axes[1].text(self.kev_b+2, b.get_ylim()[1], "%s keV" % self.kev_b, rotation = 90, verticalalignment = 'top', backgroundcolor = "White")
            for val in self.calibration_lines:
                axes[1].axvline(x=val, ymin=-1, color="g", linestyle="--", lw=2)
                axes[1].text(val+2, b.get_ylim()[1], "%s keV" % val, rotation = 90, verticalalignment = 'top', backgroundcolor = "White")

        return a, b

    def _fit_spectra(self, pulse_heights, max_pulse_height, min_pulse_height, parent_plot, log, bins, rolling, color, kevf):
        d = [kevf(x) for x in pulse_heights]
        y, x = np.histogram(d, bins = np.linspace(kevf(min_pulse_height), kevf(max_pulse_height), bins-1))
        centers = x[:-1] + np.diff(x)[0] / 2
        norm_y = y / y.sum()
        norm_y_ma = Series(norm_y).rolling(rolling, center = True).mean().values
        ax = pd.DataFrame(norm_y_ma * parent_plot.get_ylim()[1], centers).plot(logy = log, color = color, ax = parent_plot, marker = '.')
        #ax = pd.DataFrame(norm_y * max(y) * 2, x[:-1]).plot(logy = log, color = color, ax = parent_plot, marker = '.')
        ax.legend([Line2D([0], [0], color = color, lw = 2)], ["Fit"])
        return norm_y_ma, ax, centers

    def fit_spectra(self, rolling = (3, 3), *args, **kwargs):
        kwargs["bins"] = kwargs["bins"] if "bins" in kwargs else self.default_bins
        a, b = self.plot_spectra(*args, **kwargs)
        log = "log" in kwargs and kwargs["log"]
        coincidences = "coincidences" in kwargs and kwargs["coincidences"]
        df = self.get_filtered_stats(coincidences)
        dfa = df[df["APulseHeight"] > 0]
        norm_y_ma_a, plot_a, centers_a = self._fit_spectra(dfa["APulseHeight"], dfa["APulseHeight"].max(), dfa["APulseHeight"].min(), a, log, kwargs["bins"], rolling[0], "Blue", self.to_kev_a)
        dfb = df[df["BPulseHeight"] > 0]
        norm_y_ma_b, plot_b, centers_b = self._fit_spectra(dfb["BPulseHeight"], dfb["BPulseHeight"].max(), dfb["BPulseHeight"].min(), b, log, kwargs["bins"], rolling[1], "Red", self.to_kev_b)
        return norm_y_ma_a, norm_y_ma_b, plot_a, plot_b, centers_a, centers_b

    def print_stats_link(self):
        return md("<br/><center><h3>Download csv file: <a target='_blank' href='https://github.com/markomanninen/tandempiercerexperiment/raw/main%s'>statistics.csv</a></h3></center>" % self.csv_filename.replace("\\\\", "/").replace("..", ""))

    def print_basic_data(self):
        return list(map(print, [

            "\r\n",

            "Start time:\t%s" % str(self.start_time()).split(".")[0],
            "End time:\t%s" % str(self.end_time()).split(".")[0],

            "Time elapsed:\t%s" % timedelta(seconds = int(self.time_elapsed())),

            "Rows count:\t%s" % self.rows_count(),

            "Total count A:\t%s" % self.total_count_a(),
            "Total count B:\t%s" % self.total_count_b(),

            "Elapsed rate A:\t%s/s" % round(self.total_count_a()/self.time_elapsed(), 1),
            "Elapsed rate B:\t%s/s" % round(self.total_count_b()/self.time_elapsed(), 1),

            "Sample rate A:\t%s/s" % round(self.rate_a(), 1),
            "Sample rate B:\t%s/s" % round(self.rate_b(), 1),

            "\r\n",

            "Total coincidences:\t\t%s" % self.total_coincidences(),
            "Single coincidences:\t\t%s" % self.single_coincidences(),

            "Coincidence elapsed rate:\t%s/s" % round(self.coincidence_elapsed_rate(), 1),
            "Coincidence sample rate:\t%s/s" % round(self.coincidence_sample_rate(), 1)
        ]));
