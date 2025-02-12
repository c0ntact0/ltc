# Python

If you have conda please get out of any environment:
````
conda deactivate
````

https://obsinfo.readthedocs.io/en/master/installation.html

## MacOS arm64

1. ### Install this version of OBS
    https://github.com/obsproject/obs-studio/releases/download/29.1.0/obs-studio-29.1.0-macos-arm64.dmg

    With version 30.x and 31.x the numpy give an error in the include

1. ### Install python
    This is needed by the OBS  
    https://docs.python.org/3/using/mac.html

    Last time I installed the version 3.11.9  
    https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg

    The pip must be used with the correct python version  
    First update pip

    ```
    python3.11 -m pip install --upgrade pip
    ```
1. ### Activate python in OBS
    Open OBS and goto Tools->Scripts->Python Settings and put the following path:
    ![](/images/obs_python_settings.png)

1. ### pyaudio install em Mac arm64
    ```
    brew uninstall portaudio
    python3.11 -m pip uninstall pyaudio
    arch -arm64 /opt/homebrew/bin/brew install portaudio
    ```
    ```
    python3.11 -m pip install \
    --no-cache-dir --global-option='build_ext' \
    --global-option='-I/opt/homebrew/Cellar/portaudio/19.7.0/include' \
    --global-option='-L/opt/homebrew/Cellar/portaudio/19.7.0/lib' pyaudio
    ````


1. ### Install obs-ltc dependencies

    ```
    python3.11 -m pip install ffmpeg-python scipy matplotlib pyserial numpy
    ```

1. ### Install OBS dependencies
    ````
    python3.11 -m pip install jsonschema jsonref python-gitlab obspy pyyaml
    ````   
<br>



# Usefull links
Unofficial reference:  
https://github.com/upgradeQ/Streaming-Software-Scripting-Reference