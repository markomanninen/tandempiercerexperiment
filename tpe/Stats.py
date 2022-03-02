#!/usr/bin/python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
from matplotlib.pyplot import text
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from IPython.display import Markdown as md
from scipy.signal import find_peaks
from collections import Counter

from tpe.functions import get_measurement_resolution, get_measurement_configurations
from datetime import datetime, timedelta, date
from pandas import Series
from math import floor
import pandas as pd
import numpy as np
import os, glob

import requests
from dateutil import tz
from dateutil.parser import parse

def calibration_line(plot, x, unit = ""):
    plot.axvline(x = x, ymin = -1, color = "g", linestyle = "--", lw = 1)
    plot.text(x, plot.get_ylim()[0]+1, "%s %s" % (x, unit), rotation = 90, verticalalignment = 'bottom', backgroundcolor = "White")

def plot_peak_lines(norm, width = 2, distance = 2, threshold = 0.2):
    return find_peaks(norm, width = width, distance = distance, threshold = threshold)[0]

def add_calibration_line(plot, x, unit = ""):
    plot.axvline(x = x, ymin = -1, color = "g", linestyle = "--", lw = 2)
    plot.text(x, plot.get_ylim()[1], "%s %s" % (x, unit), rotation = 90, verticalalignment = 'top', backgroundcolor = "White")

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
        self.calibration_lines_a = []
        self.calibration_lines_b = []

    def get_experiment_stat_files(self, directory = None):
        for experiment_directory in glob.glob(self.experiment_directory if directory is None else directory):
            statistics_file = os.path.join(experiment_directory, self.statistics_filename)
            if os.path.isfile(statistics_file):
                yield statistics_file

    def print_experiment_stat_files(self, directory = None):
        return list(map(print, self.get_experiment_stat_files(directory)))

    def get_experiment_directories(self, directory = None):
        return glob.glob(self.experiment_directory if directory is None else directory)

    def read_stats_dataframe(self, directory, filter = False):
        self.csv_filename = "%s\statistics.csv" % directory
        df = pd.read_csv(self.csv_filename, sep = ";", names = self.headers)

        if filter:
            df = df[(df["APulseHeight"] > 0) | (df["BPulseHeight"] > 0)]
            df = df[(((df["APulseHeight"] == 0) & (df["Cnc"] > 0) == False) & ((df["BPulseHeight"] == 0) & (df["Cnc"] > 0) == False))]


        self.desc = df.describe()
        df['Time'] = pd.to_datetime(df['Time'], unit = 's')
        pd.options.display.float_format = '{:.3f}'.format
        self.last_index = len(df) - 1
        self.stats = df
        self.resolution = get_measurement_resolution(directory)
        self.measurement_settings = get_measurement_configurations(directory)
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

    def add_calibration_line_a(self, val):
        self.calibration_lines_a.append(val)

    def add_calibration_line_b(self, val):
        self.calibration_lines_b.append(val)

    def reset_calibration_lines(self):
        self.calibration_lines = []
        self.calibration_lines_a = []
        self.calibration_lines_b = []

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
        return self.get_desc_value("RateA", "mean")

    def rate_b(self):
        return self.get_desc_value("RateB", "mean")

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
        return self.get_desc_value("ElapsedCncRate", "mean")

    def coincidence_sample_rate(self):
        return self.get_desc_value("SampleCncRate", "mean")

    def info(self):
        return self.stats.info()

    def plot(self, cols, elapsed = None, *args, **kwargs):
        if elapsed is None:
            return self.stats.set_index("Elapsed")[cols].plot(*args, **kwargs)
        else:
            return self.stats[(self.stats["Elapsed"] > elapsed[0]) & (self.stats["Elapsed"] < elapsed[1])].set_index("Elapsed")[cols].plot(*args, **kwargs)

    def scatter(self, time_difference=None, channel=None, low=None, high=None, *args, **kwargs):

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

        if low is not None:
            df = df[df["APulseHeight"] > low[0]]
            df = df[df["BPulseHeight"] > low[1]]

        if high is not None:
            df = df[df["APulseHeight"] < high[0]]
            df = df[df["BPulseHeight"] < high[1]]

        max_time_difference = df['TimeDifference'].apply(lambda x: abs(x)).max()
        max_time_difference = 500
        size_ratio = 8

        def point_size(x):
            diff = max_time_difference - abs(x)
            size = (max_time_difference / diff) if diff > 0 else max_time_difference
            return np.log2(size * size_ratio) * size_ratio

        df['TimeDifferenceSize'] = df.loc[:, ('TimeDifference')].apply(point_size)

        return df.plot(
            kind = "scatter",
            x = "APulseHeight",
            y = "BPulseHeight",
            s = "TimeDifferenceSize",
            colorbar = None,
            alpha = 0.5,
            edgecolors = 'none',
            *args, **kwargs
        ), df

    def time_difference_histogram(self, time_difference=None, channel=None, low=None, high=None, *args, **kwargs):
        df = self.get_filtered_stats()

        if time_difference is not None:
            df = df[(df["TimeDifference"] > -time_difference-1) & (df["TimeDifference"] < time_difference+1)]

        if channel is not None:
            df = df[df["Chn"] == channel]

        if low is not None:
            df['APulseHeight'] = df['APulseHeight'].apply(self.to_kev_a)
            df['BPulseHeight'] = df['BPulseHeight'].apply(self.to_kev_b)
            df = df[df["APulseHeight"] > low[0]]
            df = df[df["BPulseHeight"] > low[1]]

        if high is not None:
            if low is None:
                df['APulseHeight'] = df['APulseHeight'].apply(self.to_kev_a)
                df['BPulseHeight'] = df['BPulseHeight'].apply(self.to_kev_b)
            df = df[df["APulseHeight"] < high[0]]
            df = df[df["BPulseHeight"] < high[1]]

        df["TimeDifference"] = df["TimeDifference"].apply(lambda x: x * self.resolution)
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

    def plot_channel_counts(self, sec=1, low=None, high=None, start_time=None, coincidences=False, sunlines=False, *args, **kwargs):
        fig, ax = plt.subplots()
        for axis in [ax.xaxis, ax.yaxis]:
            axis.set_major_locator(ticker.MaxNLocator(integer=True))

        start_hour = self.stats["Time"].dt.hour[0]
        df = self.get_filtered_stats(coincidences)

        if low is not None:
            df['APulseHeight'] = df['APulseHeight'].apply(self.to_kev_a)
            df['BPulseHeight'] = df['BPulseHeight'].apply(self.to_kev_b)
            df = df[df["APulseHeight"] > low[0]]
            df = df[df["BPulseHeight"] > low[1]]

        if high is not None:
            if low is None:
                df['APulseHeight'] = df['APulseHeight'].apply(self.to_kev_a)
                df['BPulseHeight'] = df['BPulseHeight'].apply(self.to_kev_b)
            df = df[df["APulseHeight"] < high[0]]
            df = df[df["BPulseHeight"] < high[1]]

        if start_time is not None:
            start_hour = start_time[3]
            d = pd.Timestamp(*start_time)
            e = df[(df["Time"] >= d) == False].copy()
            e["Time"] = e["Time"] + pd.Timedelta(hours=24)
            e["Elapsed"] = e["Elapsed"] + 24 * 60 * 60
            df = pd.concat([df[df["Time"] >= d], e])

        a = df.groupby(df['Elapsed'].apply(lambda x: floor(x/sec))).sum()

        if start_time is not None:
            xticks = [i % 24 for i in range(start_hour - 1, start_hour + len(a) - 1)]
            plt.xticks(range(len(a)), xticks)

            a[["A", "B"]][1:].plot(ylabel="Clicks", kind = "line", figsize = (16,4), ax = ax, *args, **kwargs)

        else:
            xticks = [i % 24 for i in range(start_hour, start_hour + len(a))]
            plt.xticks(range(len(a)), xticks)

            if not coincidences:
                a[["A", "B"]].plot(ylabel="Clicks", kind = "line", figsize = (16,4), ax = ax, *args, **kwargs)
            else:
                a[["A", "B"]].plot(ylabel="Clicks", kind = "line", figsize = (16,4), ax = ax, *args, **kwargs)

        if sunlines:
            for i, n in zip(range(len(a)), xticks):
                if n == self.sunrise_hour:
                    plt.axvline(x = i + self.sunrise_seconds / 3600, color = 'y', label = 'Sunrise', lw=50, alpha=.25)
                if n == self.sunset_hour:
                    plt.axvline(x = i + self.sunset_seconds / 3600, color = 'r', label = 'Sunset', lw=50, alpha=.25)

        ax.set_xlabel("Elapsed time (%ss)" % sec)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    def set_and_print_sunrise_and_sunset(self, longitude=25.050708, latitude=60.215023, timezone='Europe/Helsinki'):

        params = {
            "lng":longitude,
            "lat":latitude,
            "date":"%s-%s-%s" % (
                self.stats["Time"].dt.year[0],
                self.stats["Time"].dt.month[0],
                self.stats["Time"].dt.day[0]
            )
        }

        url = 'https://api.sunrise-sunset.org/json?formatted=0'

        response = requests.get(url, params=params)
        resp_json = response.json()

        fi_tz = tz.gettz(timezone)

        def date_to_time(date):
            return parse(date).astimezone(fi_tz).strftime("%H:%I:%S")

        sunrise = date_to_time(resp_json['results']['sunrise'])
        (h, m, s) = sunrise.split(':')
        self.sunrise_hour = int(h)
        self.sunrise_seconds = int(m) * 60 + int(s)

        sunset = date_to_time(resp_json['results']['sunset'])
        (h, m, s) = sunset.split(':')
        self.sunset_hour = int(h)
        self.sunset_seconds = int(m) * 60 + int(s)

        print("Sun rise: %s" % sunrise)
        print("Sun set: %s" % sunset)

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

    def plot_time_histogram_and_scatter(self, hide_calibration = False, time_difference = None, channel = None, *args, **kwargs):

        fig, axes = plt.subplots(nrows = 1, ncols = 2)
        for axis in [axes[0].xaxis, axes[0].yaxis]:
            axis.set_major_locator(ticker.MaxNLocator(integer = True))

        histogram, count = self.time_difference_histogram(time_difference=time_difference, channel=channel, title="Coincidence time difference", figsize=(16, 6), ax=axes[0], bins=self.default_bins, *args, **kwargs)
        axes[0].set_xlabel("Time (s)")
        axes[0].set_ylabel("Count (%s) - 1 / %s s" % (
            count,
            timedelta(seconds = int(1./(float(count)/self.time_elapsed())) if count > 0 else 0)))

        scatter, df = self.scatter(time_difference=time_difference, channel=channel, title="Coincidence scatter", figsize=(16, 6), ax=axes[1], grid=False, *args, **kwargs)
        axes[1].set_xlabel("Channel A (%s)" % ("ADC" if self.adc_kev_ratio_a == 0 else "keV"))
        axes[1].set_ylabel("Channel B (%s)" % ("ADC" if self.adc_kev_ratio_b == 0 else "keV"))

        if False:
            from sklearn.cluster import KMeans, DBSCAN, AffinityPropagation, Birch, MiniBatchKMeans, SpectralClustering, OPTICS, MeanShift, AgglomerativeClustering
            from sklearn.mixture import GaussianMixture
            from numpy import unique, where

            X = np.array([[i, j] for i, j in zip(df["APulseHeight"], df["BPulseHeight"])])
            #X = [df["APulseHeight"], df["BPulseHeight"]]

            model = KMeans(
                n_clusters=6,
                #init="k-means++",
                init="random",
                n_init=500,
                max_iter=1500,
                random_state=142
            )

            #model = GaussianMixture(n_components=2)
            #model = AffinityPropagation(damping=0.95)
            #model = MiniBatchKMeans(n_clusters=9)
            model = Birch(threshold=1, n_clusters=4)
            model.fit(X);yhat = model.predict(X)

            #model = SpectralClustering(n_clusters=9)
            #model = OPTICS(eps=0.3, min_samples=30)
            #model = DBSCAN(eps=0.3, min_samples=30)
            #model = MeanShift()

            #model = AgglomerativeClustering(n_clusters=9)
            #yhat = model.fit_predict(X)

            #centers = model.cluster_centers_
            clusters = unique(yhat)
            for cluster in clusters:
            	# get row indexes for samples with this cluster
            	row_ix = where(yhat == cluster);
            	# create scatter of these samples
            	plt.scatter(X[row_ix, 0], X[row_ix, 1], alpha=0.25, edgecolors="none")

            #plt.scatter(centers[:, 0], centers[:, 1], c='green', s=2000, alpha=0.25, edgecolors="black");

        line_width = 2
        if self.adc_kev_ratio_a != 0 and count > 0:
            if channel == None or channel == 0:
                if not hide_calibration:
                    axes[1].axhline(y=self.kev_a, xmin=-1, color="g", linestyle="--", lw=line_width)
                    axes[1].text(scatter.get_xlim()[1], self.kev_a + 2, "%s keV" % self.kev_a, rotation = 0, verticalalignment = 'center', horizontalalignment = 'center', backgroundcolor = "White")
                for val in self.calibration_lines_a:
                    axes[1].axhline(y=val, xmin=-1, color="g", linestyle="--", lw=line_width)
                    axes[1].text(scatter.get_xlim()[1], val + 2, "%skeV" % val, rotation = 0, verticalalignment = 'center', horizontalalignment = 'center', backgroundcolor = "White")

        if self.adc_kev_ratio_b != 0 and count > 0:
            if channel == None or channel == 1:
                if not hide_calibration:
                    axes[1].axvline(x=self.kev_b, ymin=-1, color="g", linestyle="--", lw=line_width)
                    axes[1].text(self.kev_b, scatter.get_ylim()[1], "%s keV" % self.kev_b, rotation = 90, verticalalignment = 'top', horizontalalignment = 'center', backgroundcolor = "White")
                for val in self.calibration_lines_b:
                    axes[1].axvline(x=val, ymin=-1, color="g", linestyle="--", lw=line_width)
                    axes[1].text(val, scatter.get_ylim()[1], "%s keV" % val, rotation = 90, verticalalignment = 'top', horizontalalignment = 'center', backgroundcolor = "White")

        self.remove_top_right_spines(axes)

    def plot_spectra(self, hide_calibration = False, *args, **kwargs):

        bins_a, bins_b = kwargs["bins"] if "bins" in kwargs else (self.default_bins, self.default_bins)

        fig, axes = plt.subplots(nrows = 1, ncols = 2)

        log = "log" in kwargs and kwargs["log"]

        for ax in axes:
            if log:
                ax.yaxis.set_major_locator(ticker.LogLocator(base = 10))
            for axis in [ax.xaxis, ax.yaxis]:
                axis.set_major_locator(ticker.MaxNLocator(integer = True))

        kwargs["bins"] = bins_a
        a, length_a = self.spectrum_histogram_a(title = "Channel A", figsize = (16, 4), ax = axes[0], color = "Red", *args, **kwargs);

        kwargs["bins"] = bins_b
        b, length_b = self.spectrum_histogram_b(title = "Channel B", figsize = (16, 4), ax = axes[1], color = "Blue", *args, **kwargs);

        axes[0].set_xlabel("ADC" if self.adc_kev_ratio_a == 0 else "keV")
        axes[0].set_ylabel("Count (%s)" % length_a)
        axes[1].set_xlabel("ADC" if self.adc_kev_ratio_b == 0 else "keV")
        axes[1].set_ylabel("Count (%s)" % length_b)

        self.remove_top_right_spines(axes)

        if self.adc_kev_ratio_a != 0 and length_a:
            if not hide_calibration:
                axes[0].axvline(x=self.kev_a, ymin=-1, color="g", linestyle="--", lw=2)
                axes[0].text(self.kev_a+2, a.get_ylim()[1], "%s keV" % self.kev_a, rotation = 90, verticalalignment = 'top', backgroundcolor = "White")
            for val in self.calibration_lines_a:
                axes[0].axvline(x=val, ymin=-1, color="g", linestyle="--", lw=2)
                axes[0].text(val+2, a.get_ylim()[1], "%s keV" % val, rotation = 90, verticalalignment = 'top', backgroundcolor = "White")

        if self.adc_kev_ratio_b != 0 and length_b:
            if not hide_calibration:
                axes[1].axvline(x=self.kev_b, ymin=-1, color="g", linestyle="--", lw=2)
                axes[1].text(self.kev_b+2, b.get_ylim()[1], "%s keV" % self.kev_b, rotation = 90, verticalalignment = 'top', backgroundcolor = "White")
            for val in self.calibration_lines_b:
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

        kwargs["bins"] = kwargs["bins"] if "bins" in kwargs else (self.default_bins, self.default_bins)

        a, b = self.plot_spectra(*args, **kwargs)
        log = "log" in kwargs and kwargs["log"]
        coincidences = "coincidences" in kwargs and kwargs["coincidences"]
        df = self.get_filtered_stats(coincidences)

        dfa = df[df["APulseHeight"] > 0]
        bins = kwargs["bins"][0]
        norm_y_ma_a, plot_a, centers_a = self._fit_spectra(dfa["APulseHeight"], dfa["APulseHeight"].max(), dfa["APulseHeight"].min(), a, log, bins, rolling[0], "Blue", self.to_kev_a)

        dfb = df[df["BPulseHeight"] > 0]
        bins = kwargs["bins"][1]
        norm_y_ma_b, plot_b, centers_b = self._fit_spectra(dfb["BPulseHeight"], dfb["BPulseHeight"].max(), dfb["BPulseHeight"].min(), b, log, bins, rolling[1], "Red", self.to_kev_b)

        return norm_y_ma_a, norm_y_ma_b, plot_a, plot_b, centers_a, centers_b

    def summary_plots(self):

        fig, axes = plt.subplots(nrows=1, ncols=3)
        for axis in axes:
            axis.set_axis_off()

        unit = "ADC"

        d = self.stats
        d = d[d["APulseHeight"] > 0]["APulseHeight"]
        d = Counter(d)

        v, k = [x for x in d.values()], [x for x in d.keys()]
        plot_1 = pd.DataFrame({unit: k, "Pulse Height": v}).plot(
            ax = axes[0],
            figsize = (8, 3),
            logy = True,
            kind = "scatter",
            x = unit,
            y = "Pulse Height",
            colorbar = None,
            edgecolors = 'none',
            alpha = 0.5,
            color = "red"
        );

        d = self.stats
        d = d[d["BPulseHeight"] > 0]["BPulseHeight"]
        d = Counter(d)

        v, k = [x for x in d.values()], [x for x in d.keys()]
        plot_2 = pd.DataFrame({unit: k, "Pulse Height": v}).plot(
            ax = plot_1,
            logy = True,
            kind = "scatter",
            x = unit,
            y = "Pulse Height",
            colorbar = None,
            edgecolors = 'none',
            alpha = 0.5,
            color = "blue"
        );

        self.scatter(figsize=(8, 3), ax=axes[1])

        self.time_difference_histogram(figsize=(16, 3), ax=axes[2], bins=self.default_bins)


    def plot_channel_pulse_height_spectrum(self, col, coincidences = False, bins = 64, rolling = 1, width = .1, distance = 5, threshold = 0.000001):

        fig, axes = plt.subplots(nrows = 1, ncols = 2)
        for axis in axes:
            axis.xaxis.set_major_locator(ticker.MaxNLocator(integer = True))

        d = self.stats
        if coincidences:
            d = d[d["TimeDifference"]>0]

        d = d[d["%sPulseHeight" % col] > 0]["%sPulseHeight" % col]

        color = "blue"
        if col == "A":
            color = "red"

        line_width = 2

        kevf = self.to_kev_a if col == "A" else self.to_kev_b
        d = d.apply(kevf)

        v, k = np.histogram(d, bins = np.linspace(d.min(), d.max(), bins))
        vv, kk = v, k
        plot_1 = pd.DataFrame({"": k[:-1].astype(int), "Pulse Height": v}).plot(
            ax = axes[0],
            figsize = (16, 4),
            kind = "bar",
            logy = True,
            x = "",
            y = "Pulse Height",
            alpha = 0.5,
            color = color
        );

        axes[0].legend([Line2D([0], [0], color = color, lw = line_width)], ["Pulse Height Histogram"])

        unit = "keV" if (col == "A" and self.adc_kev_ratio_a != 0) or (col == "B" and self.adc_kev_ratio_b != 0) else "ADC"

        new_ticks = np.linspace(0, d.max(), 8)
        s = pd.Series(v, index = k[:-1])
        axes[0].set_xticks(np.interp(new_ticks, s.index, np.arange(s.size)))
        axes[0].set_xticklabels(new_ticks.astype(int))

        d = Counter(d)

        print("Maximum bins: %s" % len(d))

        v, k = [x for x in d.values()], [x for x in d.keys()]
        plot_4 = pd.DataFrame({unit: k, "Pulse Height": v}).plot(
            ax = axes[1],
            figsize = (16, 4),
            logy = True,
            kind = "scatter",
            x = unit,
            y = "Pulse Height",
            colorbar = None,
            edgecolors = 'none',
            alpha = 0.5,
            color = color
        );
        axes[1].legend([Line2D([0], [0], color = color, lw = line_width)], ["Pulse Height Scatter"])

        fig, axis = plt.subplots(nrows = 1, ncols = 1)
        axis.xaxis.set_major_locator(ticker.MaxNLocator(integer = True))

        centers = kk[:-1] + np.diff(kk)[0] / 2
        ss =  vv.sum()
        norm_y = vv / ss
        norm_y_ma = pd.Series(norm_y).rolling(rolling, center = True).mean().round(8).values
        plot_3 = pd.DataFrame(norm_y_ma * ss, centers).plot(
            logy = True,
            figsize = (8, 4),
            ax = axis,
            marker = '.',
            xlabel = unit,
            color = color,
            alpha = 0.5
        );
        axis.legend([Line2D([0], [0], color = color, lw = line_width)], ["Pulse Height Fit"])

        peaks = plot_peak_lines(norm_y_ma, width = width, distance = distance, threshold = threshold)

        for peak in peaks:
            calibration_line(plot_3, int(centers[peak]), "")
            calibration_line(plot_4, int(centers[peak]), "")

        return [centers[peak] for peak in peaks]

    def summary_row(self):
        settings = self.measurement_settings["application"]
        return md(
            "<table><thead>\
                <tr>\
                    <th>Measurement</th>\
                    <th>Started</th>\
                    <th>Duration</th>\
                    <th>Source</th>\
                    <th>Geometry</th>\
                    <th>Resolution</th>\
                    <th>Rows</th>\
                    <th>Coincidences</th>\
                </tr></thead><tbody>\
                <tr>\
                <td><b>%s</b></td>\
                <td>%s</td>\
                <td>%s</td>\
                <td>%s</td>\
                <td>%s</td>\
                <td>%s</td>\
                <td>%s</td>\
                <td>%s</td>\
            </tr></tbody></table>" % (
                settings["experiment_name"],
                self.start_time_str(),
                self.time_elapsed_str(),
                settings["pulse_source"],
                settings["detector_geometry"],
                self.resolution,
                self.rows_count(),
                self.total_coincidences()
            )
        )

    def stats_github_link(self):
        return 'https://github.com/markomanninen/tandempiercerexperiment/raw/main%s' % self.csv_filename.replace("\\\\", "/").replace("..", "")

    def print_stats_link(self):
        return md("<br/><center><h3>Download csv file: <a target='_blank' href='%s'>statistics.csv</a></h3></center>" % self.stats_github_link())

    def start_time_str(self):
        return str(self.start_time()).split(".")[0]

    def end_time_str(self):
        return str(self.end_time()).split(".")[0]

    def time_elapsed_str(self):
        return timedelta(seconds = int(self.time_elapsed()))

    def print_basic_data(self):
        r = self.coincidence_elapsed_rate()
        cnc_rate = (" (1/%ss)" % timedelta(seconds = int(1./r))) if r < 1 else ""
        return list(map(print, [

            "\r\n",

            "Start time:\t%s" % self.start_time_str(),
            "End time:\t%s" % self.end_time_str(),

            "Time elapsed:\t%s" % self.time_elapsed_str(),

            "Rows count:\t%s" % self.rows_count(),

            "Total count A:\t%s" % self.total_count_a(),
            "Total count B:\t%s" % self.total_count_b(),

            "Elapsed rate A:\t%s/s" % round(self.total_count_a()/self.time_elapsed(), 3),
            "Elapsed rate B:\t%s/s" % round(self.total_count_b()/self.time_elapsed(), 3),

            "Sample rate A:\t%s/s" % round(self.rate_a(), 1),
            "Sample rate B:\t%s/s" % round(self.rate_b(), 1),

            "\r\n",

            "Total coincidences:\t\t%s" % self.total_coincidences(),
            "Single coincidences:\t\t%s" % self.single_coincidences(),

            "Coincidence elapsed rate:\t%s/s%s" % (round(self.coincidence_elapsed_rate(), 3), cnc_rate),
            "Coincidence sample rate:\t%s/s" % round(self.coincidence_sample_rate(), 2)
        ]));
