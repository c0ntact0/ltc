<h1>LTC for OBS</h1>

<div align="justify">
This is a Python plugin script for use with Open Broadcaster Software (OBS). The main objective was to enable the capture of an LTC signal through an audio input. However, additional features have been added, which are summarized in the features section.

<h2>Table of Contents</h2>

- [Features](#features)
- [Installation](#install)
- [Preparation](#preparation)
    - [Import the OBS profile](#import_profile)
    - [Import the OBS Scene](#import_scene)
    - [Import the script into OBS](#import_script)
- [Script Configuration](#script_conf)
    - [LTC Configuration](#ltc_conf)
    - [Sources Configuration](#sources_conf)
    - [EDL Configuration](#edl_conf)
    - [Serial Port Configuration](#serial_cof)
    - [Miscellaneous Configuration](#misc_conf)
    - [Logging Configuration](#logging_conf)
- [Development and Testing](#dev_test)
    - [Equipment](#equipment)
    - [Known Issues](#issues)
- [Motivation and Goals of This Project](#motivation)
- [Version History](VERSIONS.md)

<h2 id="features">Features</h2>

- Capture LTC through an audio input. Any analog input will work.
- Internal video switcher.
> Dynamically created OBS hotkeys can be mapped to keyboard keys to function as a source switcher.

> Arduino serial I/O for switcher control. Arduino code and schematics included. Designed for push-button control but can be adapted to GPIO interfaces.

- Start and stop recording controlled by the script.
- LTC can be displayed in an OBS text source.
- Generates an EDL file with cuts from the switcher.

<h2 id="install">Installation</h2>

Read [INSTALL.md](/INSTALL.md).

<h2 id="preparation">Preparation</h2>

Download or clone the repository to a location of your choice. We will refer to that location as **LTC-OBS** from now on.

<h3 id="import_profile">Import the OBS Profile</h3>

1. In the OBS menu, go to **Profile** -> **Import**.  
1. Navigate to **LTC-OBS\obs_profile_scene** and select the **OBSLTC_Profile** folder.
1. Activate the profile in **Profile**.
1. Go to **File** -> **Settings** -> **Output** -> **Recording** and confirm the configuration. We use an **XDCAM MPEG2**-like encoder encapsulated with **MXF OP1A**.  
<img src="images/obs_output_settings.png" width="600">

You can change the **File Path or URL** folder destination as needed.
Note that the MXF file will be re-encapsulated using FFMpeg to add the correct start timecode.

<h3 id="import_scene">Import the OBS Scene</h3>

1. In the OBS menu, go to **Scene Collection** -> **Import**.
1. In an empty row, click the **...** button in the **Collection Path** field.   
<img src="images/obs_scene_collection_importer.png" width="500">
1. Navigate to **LTC-OBS\obs_profile_scene\Scene** and select the **OBS-LTC_scene.json** file.
1. Ensure the row is checked (left-side checkbox) and click **Import**.
1. Activate the scene in **Scene Collection**.

A **Missing Files** alert dialog may appear; you can click **Cancel**. 

The scene appears as follows:   
<div align="center">
<img src="images/obs_ltc_scene.png" width="500">
</div>

<h3 id="import_script">Import the Script into OBS</h3>

1. In OBS, go to **Tools** -> **Scripts**. 
1. In the **Scripts** tab, click the plus (**+**) button.   
1. Navigate to the **LTC-OBS** folder and select the **ltc-obs.py** script file.   

If you get this error in the script log:
   
> OSError: [Errno -10000] PortAudio not initialized   

please reload the script.

<h2 id="script_conf">Script configuration</h2>
<h3 id="ltc_conf">LTC Configuration</h3>

This is where the LTC related configurations are made. The **LTC-OBS\testes\test_live_no_blocking.py** can be used to list de devices properties and help choosing the correct device and channel.
<div align="center">
<img src="images/ltc-obs_ltc_config.png" width="400">
</div>

- **Audio Device**: Select the audio device where the LTC signal is connected.
- **Channel**: Select the channel to use (the audio device must be selected first).
- **FPS**: Select the frame rate of the incoming LTC signal.
- **Buffer Size**: The size of the buffer (data chunk) read from the audio stream in each iteration. If the timecode display jumps, try increasing this value. A value too high may cause frame drops. The default is 24 bytes. Each LTC frame consists of 80 bits.
- **TC Display Source**: The OBS text source used to display the timecode. This source can be toggled visible using the "eye" icon.
- **Use Timeline TC**: Uses **Timeline Start TC** as the starting timecode for EDL cuts. This feature is highly experimental and under development; avoid using it if possible.

After configuration, click **Start LTC Capture** to run the LTC. Use this button to test if the audio device and channel are configured correctly.

***

<h3 id="sources_conf">Sources Configuration</h3>
<div align="center">
<img src="images/ltc-obs_sources_config.png" width="400">
</div>
<br>

- **Cut Sources**: Defines OBS sources as video input channels, which are mapped to hotkeys. Ensure the names entered here match the OBS source names exactly. For example, if you have three sources named CAM1, CAM2, and CAM3, enter them in this list. Order matters—place sources in the order you want them mapped to hotkeys (e.g., *CAM1* as *1*).  
To add sources, click the plus (**+**) button; to remove them, use the trash bin button. Click the cogwheel button to rename a source.  
After adding sources, go to **File** -> **Settings** -> **Hotkeys**, scroll down to the source hotkeys section, and assign a key to each.

<div align="center">
<img src="images/obs_hotkeys_settings.png" width="400">
</div>
<br>

- **Source for Playout**: Select the OBS source used for playout of recorded videos. If using the **OBS-LTC scene**, a **Playout** source exists in the **PLAYOUT** scene, but you may choose another one. Recorded videos are automatically opened in this source when recording stops.

***
<h3 id="edl_conf">EDL Configuration</h3>
<div align="center">
<img src="images/ltc-obs_edl_config.png" width="400">
</div>

- **EDL Format**: Here you can choose the EDL format. There are four default EDL format types (**file_16**, **file_32**, **file_129**, and **CMX_3600**). You can add more formats in the ***edl_manager.py*** module using the ***output_formats*** dictionary.  
- **Invert Reel Name and Reel Extension**: Normally, the EDL reel is formatted using the date and time in the format *YYYYMMDD_HHMMSS*, with the OBS source name as the extension. Checking this box places the OBS source name first, followed by the date and time as the extension.  
- **Reel Preview**: Displays a preview of the reel format.  
- **EDL Export Folder**: Here you can choose the folder where the EDL file will be exported. A good practice is to use the same folder where the video files are saved.

***
<h3 id="serial_cof">Serial Port Configuration</h3>
<div align="center">
<img src="images/ltc-obs_serial_config.png" width="400">
</div>

- **Serial Ports**: here you can choose the serial port for the Arduino switcher communication.

***
<h3 id="misc_conf">Miscellaneous Configuration</h3>
<div align="center">
<img src="images/ltc-obs_misc_config.png" width="400">
</div>

- **Apply Dock State**: if this box is checked, only the **Scenes**, **Sources**, and **Audio Mixer** OBS docks will be loaded at startup. The default setting for this box is checked. Keep in mind that you must not use the **Start Recording** button in the **Controls** dock to control the recorder. Instead, use the **LTC-OBS** button.

***
<h3 id="logging_conf">Logging Configuration</h3>
<div align="center">
<img src="images/ltc-obs_logging_config.png" width="400">
</div>
<br>

Each of this checkboxes activates the one log level. In production environment it's recommended to turn of at least the debug level.   

***

<h2 id="dev_test">Development and testing</h2>

Follows a brief description of the equipment used for development and the known issues.

<h3 id="equipment">Equipment</h3>

At the time I'm writing this markdown I'm using the following equipment:

- **Computer**: 
    - Dell Precision Tower 7910 with two Intel Xeon E5-2687W v3 @ 3.10GHz (10 cores each).
    - 128 GBytes of RAM
    - NVIDIA GeForce GTX 980 Ti
    - Windows 10 Professional

- **Video capturing**
    - Blackmagic Decklink Duo SDI
    - Blackmagic Decklink Studio 2

- **Signals generation and distribution**
    - Sony HVR-S270E HDV camera for SDI and LTC signals generation. 
    - The LTC signal comes from a BNC plug and is directly feeded into the Dell computer on-board audio microphone/LineIn 3.5 jack input using a splitter cable.
    - The SDI video signal is feeded into a Blackmagic SDI distributer and sended to the Decklinks inputs on the computer. To distinguish between channels in OBS, I use Color Correction filters in two of the inputs.

<h3 id="issues">Known Issues</h3>

Here’s the corrected version of your text:  

- The Timeline TC feature is not working well. Some cuts do not coincide with the video changes. More work is needed on this feature.  
- Sometimes, cuts made with LTC are delayed by 1 frame. I noticed that restarting OBS fixes the issue. Currently, there is one callback for the hotkeys and another for the camera sources. The latter is triggered when the source becomes visible and is responsible for capturing the running LTC to be used in the cut. This may need to be refactored to optimize processing time.  
- I have not tested the script without debug logging. Disabling debug logging can save processing time by reducing output to stdout. This could be crucial for preventing delays between pressing a key to change the source and capturing the current LTC frame.  

<h2 id="motivation">Motivation and aims for this project</h2>

The main goal when I started this project was to create a way to record signals from cameras like the Sony F55 and Sony Venice, while also capturing a video stream with the director's cuts from the video mixer (and generating the corresponding EDL for post-production), all while simultaneously recording on the cameras' memory cards (e.g., SxS Cards).  

By following a specific naming convention for OBS sources, it is theoretically possible to relink the media from the camera cards with the cuts stored in the EDL, provided that all equipment is using the same LTC signal. The video recorded in OBS can serve as a rough edit for the director, giving them an idea of the final cut, while the post-production team gains a better understanding of the director’s intentions.  

When cameras like the Sony Venice were introduced to the market with high-quality native codecs, recording to a video server became an undesirable workflow. Maintaining an expensive video server just to record a draft stream as an editing reference for post-production is not a cost-effective solution.  

The **LTC-OBS project** is an attempt to address this issue by integrating LTC into the OBS environment and, from there, developing a workflow that combines the advantages of video mixer cuts with the high-quality media recorded on digital camera cards.  

Unfortunately, I do not have the means to test this with multiple Sony F55 cameras using distributed LTC. However, the foundations have been laid. If anyone out there is interested in testing the script and workflow, please feel free to contact me.  

Rui Loureiro  
E-Mail: ruiloureiro70@gmail.com

</div>