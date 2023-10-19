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
from scipy.signal import spectrogram, decimate, fftconvolve, hilbert
import numpy as np
from moviepy.editor import *
import argparse

parser = argparse.ArgumentParser(description="Automatically remove silence from a video.")
parser.add_argument('input_file')
parser.add_argument('output_file')
parser.add_argument('-p', '--padding', type=float)
parser.add_argument('-sf', '--start-freq', type=float)
parser.add_argument('-ef', '--end-freq', type=float)
parser.add_argument('-c', '--config')
parser.add_argument('-r', '--resolution', type=float)
parser.add_argument('-o', '--overlap', type=float)
parser.add_argument('-z', '--zero-pad-percent', type=float)


def handle_defaults(args: argparse.ArgumentParser):

    if args.padding is None:
        args.padding = 0.25

    if args.start_freq is None:
        args.start_freq = 200.

    if args.end_freq is None:
        args.end_freq = 3000.

    if args.resolution is None:
        args.resolution = 0.05  # fft duration

    if args.overlap is None:
        args.overlap = 0.50
    else:
        if args.overlap >= 1 or args.overlap < 0:
            raise ValueError(f"Invalid overlap value {args.overlap}\nValid range [0, 1)")

    if args.zero_pad_percent is None:
        args.zero_padding_percent = 100


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


def decimate_data(data, fs, interval: int):
    output_data = decimate(data, interval)
    return output_data, fs/interval


def compute_spectrogram(data, fs, args):
    # Create a spectrogram of the first channel of data
    n_res = args.resolution * (1 + args.overlap)
    nperseg = int(n_res * fs)
    n_overlap = int(nperseg * args.overlap)
    nfft = next_power_of_2(int(nperseg) + int(args.zero_padding_percent * nperseg / 100))

    f, t, Sxx = spectrogram(data,
                            fs,
                            nperseg=nperseg,
                            nfft=nfft,
                            noverlap=n_overlap,
                            scaling='density',
                            mode='magnitude')

    resolution = t[1] - t[0]  # Todo: Fix this

    start_idx = (np.abs(f - args.start_freq)).argmin()
    end_idx = (np.abs(f - args.end_freq)).argmin()

    return np.sum(Sxx[start_idx:end_idx, :], axis=0), resolution


def find_segments(energy_in_band, resolution, threshold=3.0, padding_width=0.25):
    # Find signals above 5 dB threshold
    indices = np.argwhere(energy_in_band > 3.0).flatten()
    start_indices = indices - int(padding_width/resolution)
    start_indices[start_indices < 0] = 0
    end_indices = indices + int(padding_width / resolution)
    end_indices[end_indices > len(energy_in_band)] = len(energy_in_band)
    interesting_indices = set()
    for start_idx, end_idx in zip(start_indices, end_indices):
        interesting_indices = interesting_indices.union(set(range(int(start_idx), int(end_idx))))

    interesting_indices = np.array(list(interesting_indices))
    interesting_indices.sort()

    contiguous_segments = np.split(interesting_indices, np.where(np.diff(interesting_indices) != 1)[0] + 1)
    segments = [[segment[0]*resolution, segment[-1]*resolution] for segment in contiguous_segments]
    return segments


def next_power_of_2(x):
    return 1 if x == 0 else 2**(x - 1).bit_length()


def convert_video_to_audio_ffmpeg(video_file, audio_file_out):
    """Converts video to audio directly using `ffmpeg` command
    with the help of subprocess module"""
    if not os.path.exists(audio_file_out):
        subprocess.call(["ffmpeg", "-y", "-i", video_file, audio_file_out],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT)


def normalize(energy_in_band, resolution):

    # Split window normalizer
    window_length = 1.0
    window_gap = 0.05
    window = np.ones(int(window_length / resolution), dtype=float)
    gap_width = int(window_gap / resolution)
    if len(window) % 2 == 1:
        gap_start, gap_end = (len(window) - 1) // 2 - gap_width // 2, (len(window) - 1) // 2 + gap_width // 2
    else:
        gap_start, gap_end = len(window) // 2 - gap_width // 2, len(window) // 2 + gap_width // 2
    window[gap_start:gap_end] = 0.0

    mean_data = fftconvolve(np.abs(energy_in_band), window, 'same') / np.sum(window)
    energy_in_band /= mean_data

    energy_in_band = 10 * np.log10(np.abs(energy_in_band))

    # Hilbert transform to get the envelope of the energy
    energy_in_band = np.abs(hilbert(energy_in_band))

    return energy_in_band


def extract_clips(video_file, segments):
    main_clip = VideoFileClip(video_file)
    video_segments = [main_clip.subclip(s[0], s[1]) for s in segments]

    return video_segments


# MP3 Read
def read_mp3(f, normalized=False):
    """MP3 to numpy array"""
    a = pydub.AudioSegment.from_mp3(f)
    y = np.array(a.get_array_of_samples())
    if a.channels == 2:
        y = y.reshape((-1, 2))
    if normalized:
        return a.frame_rate, np.float32(y) / 2**15
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
