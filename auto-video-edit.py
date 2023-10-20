"""
    -*- coding: utf-8 -*-
    Time    : 2023-10-15 11:06 a.m.
    Author  : Kevin Dunphy
    E-mail  : kevin.dunphy1989@gmail.com
    FileName: auto-video-edit.py
    
    {Description}
    -------------
    
"""
try:
    from support import *
except ImportError as e:
    import logging
    logging.log(logging.ERROR, "Please run 'pip install -r requirements.txt'")
    raise e

if __name__ == "__main__":

    args = parser.parse_args()
    handle_defaults(args)

    if not os.path.exists(args.input_file):
        raise FileNotFoundError(f"{args.input_file} does not exist!")

    filename, ext = os.path.splitext(args.input_file)
    audio_file = f"{filename}TEMP.mp3"

    # Use ffmpeg to extract the audio channel to a file
    process(convert_video_to_audio_ffmpeg, "Extracting Audio...", args=(args.input_file, audio_file))

    # Read in audio into numpy array
    fs_orig, data_orig = process(read_mp3, "Reading Audio...", args=(audio_file,))

    # Decimate audio to reduce sample rate (This assumes 44.1 kHz input audio)
    data, fs = process(decimate_data, "Decimating Signal...", args=(data_orig[:, 0], fs_orig, args))

    # Create a spectrogram of the first channel of data and generate the energy in the band
    energy_in_band, resolution = process(compute_spectrogram, "Computing Spectrogram...", args=(data, fs, args))

    # Normalize Data
    energy_in_band = process(normalize, "Normalizing Energy Data...", args=(energy_in_band, resolution, args))

    # Find interesting segments
    segments = process(find_segments, "Finding Interesting Segments...", args=(energy_in_band, resolution))

    # Extract video segments from primary video file and stitch them together into output product
    clips = process(extract_clips, "Extracting clips...", args=(args.input_file, segments, resolution))
    output_video = concatenate_videoclips(clips)
    output_video.write_videofile(args.output_file, verbose=False)

    # Clean up temporary audio file
    os.remove(audio_file)
