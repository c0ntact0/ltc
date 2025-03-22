# LTC for OBS installation instructions

## Table of contents

- [OBS General Python](#obs-python)
- [Windows](#windows-install)
- [MacOS arm64](#macos-install)
- [Ubuntu](#ubuntu-install)

<h2 id="obs-python">OBS General Python Instructions</h2>
You may want to read this first.   

https://obsinfo.readthedocs.io/en/master/installation.html


<h2 id="windows-install">Windows</h2>

Windows was the development environment and it's strongly recommended for operation.
I'm using python 3.10.13 at development time, but you can try other version, depending on your OBS version.  

I'm using OBS version 30.1.2 (64 bits) for development:
https://github.com/obsproject/obs-studio/releases/download/30.1.2/OBS-Studio-30.1.2.zip

1. ### Install Miniforge
    https://github.com/conda-forge/miniforge

    <mark>All the following python installs must be done using the Miniforge Prompt.</mark>

1. ### Create a conda environment for obs (optional but recommended)
    ```
    conda create -n obs python=3.10.13
    conda activate obs
    ```

1. ### Install obs-ltc dependencies

    ```
    python -m pip install ffmpeg-python scipy matplotlib pyserial numpy pyaudio debugpy
    ```

1. ### Install OBS dependencies
    ```
    python -m pip install jsonschema jsonref python-gitlab obspy pyyaml
    ```

1. ### Activate python in OBS
    Open OBS and goto Tools->Scripts->Python Settings and browse to the following path:

    > %USERPROFILE%/AppData/Local/miniforge3/env/obs


    If you are not using a conda environment point to:
    > %USERPROFILE%/AppData/Local/miniforge3

    ![](/images/obs_python_settings_windows.png)

1. ### Install FFMpeg
    FFMpeg is needed to rewrap the media files with the correct start time code.
    https://ffmpeg.org/download.html#build-windows  
    <br>
    Don't forget to add your FFMpeg binaries location to the PATH environment variable. 

<br>

The module matplotlib is only needed for development, while plotting WAV files, in order to "see" the line code.  

<h2 id="macos-install">MacOS arm64</h2>


Work in progress.
<br>

<h2 id="ubuntu-install">Ubuntu</h2>

1. ### Install OBS 
    ```
    sudo add-apt-repository ppa:obsproject/obs-studio
    sudo apt update
    sudo apt install obs-studio
    ```
1. ### Install PortAudio
    #### Install ALSA
    ```
    sudo apt-get install libasound-dev
    ```
    #### Install build dependencies
    ```
    sudo apt install gcc
    sudo apt install make0
    ```
    #### Download PortAudio
    https://files.portaudio.com/download.html  
    Go to the folder where you download the tgz and unpack (replace the filename to match yours)
    ```
    tar xvfz pa_stable_v190600_20161030.tgz
    ```
    #### Build PortAudio
    ```
    cd portaudio
    ./configure && make
    sudo make install
    ```
1. ### Install FFMpeg
    ```
    sudo apt install ffmpeg
    ```
1. ### Install PyAudio
    ```
    conda install pip
    pip install pyaudio
    ```

1. ### Install Decklink (optional)
    - Download Blackmagic Decklink software
    https://www.blackmagicdesign.com/support/download
    - Unpack the tar file
    - Read the ReadMe.txt file in the root folder

1. ### Create Python environment

    ```
    cd ~
    python3 -m venv obs-python
    source obs-python/bin/activate
    ```

1. ### Instal Python ltc-obs dependencies
    ```
    pip install ffmpeg-python scipy matplotlib pyserial numpy
    ```

1. ### Install Python OBS dependencies
    ```
    pip install jsonschema jsonref python-gitlab obspy pyyaml
    ```

1. ### Run OBS
    The obs-python environment must be activated
    ```
    obs
    ```

# Usefull links
Official reference: 
https://docs.obsproject.com/  
Unofficial reference: 
https://github.com/upgradeQ/Streaming-Software-Scripting-Reference  
OBS Forums: https://obsproject.com/forum/