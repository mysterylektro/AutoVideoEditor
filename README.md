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

| Option                 | Description                                                                                                            |
|:-----------------------|:-----------------------------------------------------------------------------------------------------------------------|
| -p, --padding          | Amount of time of a detected audio event (on both sides) to pad for context. (default = 0.25 s)                        |
| -sf, --start-freq      | The start frequency of audio events of interest. This is typically the narrator's vocal range (default = 200 Hz)       |
| -ef, --end-freq        | The end frequency of audio events of interest. This is typically the narrator's vocal range (default = 3000 Hz)        |
| -r, --resolution       | The minimum audio event length. (default = 0.05 seconds)                                                               |
| -o, --overlap          | Must be >= 0 and < 1. A higher value is needed when identifying very short audio events (default=0.5)                  |
| -z, --zero-pad-percent | Must be >= 0. This value helps to reduce scalloping loss when identifying narrow frequency content. (default=100)      |
| -c, --config           | Unused parameter in V0.0.1. This will be used in the future to define configuration parameters for additional features |


