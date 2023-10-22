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

    # Decimate audio in first channel to reduce sample rate (This assumes 44.1 kHz stereo input audio)
    data, fs = process(decimate_data, "Decimating Signal...", args=(data_orig[:, 0], fs_orig, args))

    # Filter and rectify data
    processed_data = process(process_audio, "Processing audio...", args=(data, fs, args))

    # Find interesting segments
    segments = process(find_segments, "Finding Interesting Segments...", args=(processed_data, fs, args))

    # Generate an example image if requested
    if args.example_image:
        process(export_example_image, "Generating Example Image... ", args=(data_orig[:, 0],
                                                                            fs_orig,
                                                                            fs,
                                                                            segments,
                                                                            args,))

    # Extract video segments from primary video file and stitch them together into output product
    clips = process(extract_clips, "Extracting clips...", args=(args.input_file, segments, 1/fs))
    output_video = concatenate_videoclips(clips)

    # Write audio file
    output_video.audio.write_audiofile(audio_file, fps=44100)

    # If specified, filter audio file to remove rumbling and high frequency noise.
    if args.nice_audio:
        process(nice_audio, "Making audio nice...", args=(audio_file,))

    # Write to video file
    output_video.write_videofile(args.output_file, audio=audio_file, verbose=False)

    # Clean up temporary audio file
    os.remove(audio_file)
