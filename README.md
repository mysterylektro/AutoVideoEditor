# About This Tool

This tool was inspired by watching Catan gameplay on YouTube. Most content creators spend lots of time editing their videos,
however smaller or newer creators often just upload the raw footage, leaving in all the downtime of essentially 
watching the clock tick down.

The Auto Video Editor tool extracts audio from an input video file and sets up an audio detection mechanism to highlight
areas where there's vocal activity. The following image shows an example of automatically detected audio events 
(note each event is padded by 0.25 seconds):

![The areas highlighted in pink are automatically detected audio events. The areas not highlighted will be removed](https://github.com/mysterylektro/AutoVideoEditor/blob/master/resources/example_audio_detection.png?raw=true)

After identifying these segments, the tool provides a configurable padding buffer to
each segment in order to retain some continuity of context between cuts. By splicing these segments together, 
the tool automatically removes areas without any audible activity.

The following video shows an example of the tool's capabilities, using a [video](https://www.youtube.com/watch?v=DpuKO_rsptI
) taken from [BuddyCatan's channel](https://www.youtube.com/@buddycatan):

https://youtu.be/BV_W_9zwCmw

The original video duration was approximately 49 minutes, and the tool condensed this to a more concise 36 minutes. 
In essence, this eliminated around 13 minutes of inactive content, roughly a quarter of the original video! 


# Prerequisites

This tool relies on ffmpeg (https://www.ffmpeg.org/), and has only been tested on Windows 10.

This website provides step-by-step instructions on how to install ffmpeg on windows: https://www.geeksforgeeks.org/how-to-install-ffmpeg-on-windows/

# Installation

To install this tool, you will need to do the following:

- Create a Python 3.10 (or greater) environment (typically using Conda)
- Download the content into a project folder
- Activate your python environment and install the required dependencies with the following command:
> pip install -r requirements.txt

# Usage

This tool has some fairly basic functionality, however I have plans to make additonal features.

To use the tool with all of the default options, run the following command from your python project directory:

> python auto-video-edit /path/to/input_video.mp4 /path/to/output_video.mp4
 
The output file does not have to exist; the tool will generate the video. To modify how the tool operates, 
use the following options:

| Option                 | Description                                                                                                                                                                             |
|:-----------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| -p, --padding          | Amount of time of a detected audio event (on both sides) to pad for context. (default = 0.25 s)                                                                                         |
| -sf, --start-freq      | The start frequency of audio events of interest. This is typically the narrator's vocal range (default = 200 Hz)                                                                        |
| -ef, --end-freq        | The end frequency of audio events of interest. This is typically the narrator's vocal range (default = 3000 Hz)                                                                         |
| -r, --resolution       | The minimum audio event length. (default = 0.05 seconds)                                                                                                                                |
| -o, --overlap          | Must be 0 <= overlap < 1. A higher value is needed when identifying very short audio events (default=0.5)                                                                               |
| -z, --zero-pad-percent | Must be 0 <= zero-pad-percent. Note this value is in percentage (i.e. 100 = 100 %). This value helps to reduce scalloping loss when identifying narrow frequency content. (default=100) |
| -c, --config           | Unused parameter in V0.0.1. This will be used in the future to define configuration parameters for additional features                                                                  |


