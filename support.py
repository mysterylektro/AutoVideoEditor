"""
    -*- coding: utf-8 -*-
    Time    : 2023-10-19 4:28 p.m.
    Author  : Kevin Dunphy
    E-mail  : kevin.dunphy1989@gmail.com
    FileName: support.py
    
    {Description}
    -------------
    
"""
import os.path
import pydub
import subprocess
import time
from alive_progress import alive_bar
from threading import Thread
from scipy.signal import decimate, fftconvolve, hilbert, butter, lfilter
import numpy as np
from moviepy.editor import *
import argparse
from functools import reduce

__major_version__ = 0
__minor_version__ = 0
__revision__ = 3
__VERSION__ = f'Auto Video Editor {__major_version__}.{__minor_version__}.{__revision__}'

parser = argparse.ArgumentParser(description="Automatically remove silence from a video.")
parser.add_argument('input_file')
parser.add_argument('output_file')
parser.add_argument('-p', '--padding', type=float)
parser.add_argument('-sf', '--start-freq', type=float)
parser.add_argument('-ef', '--end-freq', type=float)
parser.add_argument('-d', '--decimate', type=int)
parser.add_argument('-t', '--threshold', type=float)
parser.add_argument('-bg', '--band-gap', type=float)
parser.add_argument('-li', '--lead-in', type=float)
parser.add_argument('-lo', '--lead-out', type=float)
parser.add_argument('-c', '--config')
parser.add_argument('-n', '--nice-audio', action='store_true')
parser.add_argument('-v', '--version', action='version', version=__VERSION__)


def combine_overlaps(ranges):
    return reduce(
        lambda acc, el: acc[:-1:] + [(min(*acc[-1], *el), max(*acc[-1], *el))]
        if acc[-1][1] >= el[0]
        else acc + [el],
        ranges[1::],
        ranges[0:1],
    )


def handle_defaults(args: argparse.ArgumentParser):
    if args.padding is None:
        args.padding = 0.60

    if args.start_freq is None:
        args.start_freq = 200.

    if args.end_freq is None:
        args.end_freq = 3000.

    if args.threshold is None:
        args.threshold = 5.0

    if args.band_gap is None:
        args.band_gap = 50.0


class ThreadWithReturnValue(Thread):

    def __init__(self, group=None, target=None, name=None, verbose=None,
                 args=(), kwargs=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self.verbose = verbose
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                        **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return


def process(func, title, args=None, kwargs=None):
    with alive_bar(title_length=30, title=title, bar='classic', spinner='waves') as bar:
        x = ThreadWithReturnValue(target=func, args=args, kwargs=kwargs)
        x.start()
        while x.is_alive():
            bar()
            time.sleep(0.1)

        return x.join()


def decimate_data(data, fs, args):
    interval = args.decimate

    if interval is None:
        """
        No decimation interval is defined. Check the desired end frequency, and determine what the maximum
        decimation factor can be. Note this may not be desirable for future analysis 
        (i.e. there may be other sounds that are in a higher frequency range that are important that will get 
        filtered out)
        """
        # Multiply the sample rate by 10 % to ensure the end frequency lies well outside the Nyquist criterion
        interval = int(np.floor(fs / (1.1*(2 * (args.end_freq + args.band_gap)))))

    output_data = decimate(data, interval)
    return output_data, fs / interval


def find_segments(processed_data, fs, args):
    # Find signals above threshold
    indices = np.argwhere(processed_data >= args.threshold).flatten()
    start_indices = indices - int(args.padding * fs)
    start_indices[start_indices < 0] = 0
    start_indices = list(start_indices)
    end_indices = indices + int(args.padding * fs)
    end_indices[end_indices > len(processed_data)] = len(processed_data)
    end_indices = list(end_indices)

    # Add lead in and lead out values
    if args.lead_in is not None:
        start_indices.insert(0, 0)
        end_indices.insert(0, int(args.lead_in * fs))

    if args.lead_out is not None:
        start_indices.append(len(processed_data) - int(args.lead_out * fs))
        end_indices.append(len(processed_data))

    return combine_overlaps(list(zip(start_indices, end_indices)))


def next_power_of_2(x: int):
    return 1 if x == 0 else 2 ** (x - 1).bit_length()


def convert_video_to_audio_ffmpeg(video_file, audio_file_out):
    """Converts video to audio directly using `ffmpeg` command
    with the help of subprocess module"""
    if not os.path.exists(audio_file_out):
        subprocess.call(["ffmpeg", "-y", "-i", video_file, audio_file_out],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT)


def process_audio(data, fs, args):
    b, a = butter(5, [args.start_freq, args.end_freq], fs=fs, btype='bandpass')
    band_pass_data = lfilter(b, a, data)

    b, a = butter(5, [args.start_freq - args.band_gap, args.end_freq + args.band_gap], fs=fs, btype='bandstop')
    band_stop_data = lfilter(b, a, data)

    band_pass_data = np.abs(hilbert(band_pass_data))
    band_stop_data = np.abs(hilbert(band_stop_data))

    # Normalize the in-band using the out-of-band data
    # Use a 1-second mean for now.
    window = np.ones(int(fs), dtype=float)
    mean_data = fftconvolve(band_stop_data, window, 'same') / np.sum(window)
    band_pass_data /= mean_data

    # Put in log space
    band_pass_data = 10*np.log10(band_pass_data)

    return band_pass_data


def extract_clips(video_file, segments, resolution):
    main_clip = VideoFileClip(video_file)
    video_segments = [main_clip.subclip(s[0]*resolution, s[1]*resolution) for s in segments]

    return video_segments


# MP3 Read
def read_mp3(f, normalized=False):
    """MP3 to numpy array"""
    a = pydub.AudioSegment.from_mp3(f)
    y = np.array(a.get_array_of_samples())
    if a.channels == 2:
        y = y.reshape((-1, 2))
    if normalized:
        return a.frame_rate, np.float32(y) / 2 ** 15
    else:
        return a.frame_rate, y


# MP3 write
def write_mp3(f, sr, x, normalized=False):
    """numpy array to MP3"""
    channels = 2 if (x.ndim == 2 and x.shape[1] == 2) else 1
    if normalized:  # normalized array - each item should be a float in [-1, 1)
        y = np.int16(x * 2 ** 15)
    else:
        y = np.int16(x)
    song = pydub.AudioSegment(y.tobytes(), frame_rate=sr, sample_width=2, channels=channels)
    song.export(f, format="mp3", bitrate="320k")


def nice_audio(audio_file):
    fs, data = read_mp3(audio_file)
    b, a = butter(5, [150, 10000], fs=fs, btype='bandpass')
    data_out = lfilter(b, a, data[:, 0])
    data_out /= np.max(np.abs(data_out))
    write_mp3(audio_file, fs, data_out, normalized=True)
