# Python



https://obsinfo.readthedocs.io/en/master/installation.html

## Windows

Windows was the development environment, it's strongly recommended for operation.
I'm using python 3.10.13 at development time, but you can try other version, depending on your OBS version.  

I'm using OBS version 30.1.2 (64 bits) for development:
https://github.com/obsproject/obs-studio/releases/download/30.1.2/OBS-Studio-30.1.2.zip

1. ### Install Miniforge
    https://github.com/conda-forge/miniforge

    All the following python installs must be done using the Miniforge Prompt.

1. ### Install obs-ltc dependencies

    ```
    python -m pip install ffmpeg-python scipy matplotlib pyserial numpy
    ```

1. ### Install OBS dependencies
    ```
    python -m pip install jsonschema jsonref python-gitlab obspy pyyaml
    ```

1. ### Activate python in OBS
    Open OBS and goto Tools->Scripts->Python Settings and put the following path:
    ![](/images/obs_python_settings_windows.png)
<br>

The module matplotlib is only needed for development, while plotting WAV files, in order to "see" the line code.  

## MacOS arm64

Not working in MacOS.

<br>

# Usefull links
Unofficial reference:  
https://github.com/upgradeQ/Streaming-Software-Scripting-Reference