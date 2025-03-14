# LTC in OBS

<div align="justify">
This is a plugin script written in python to use in the Open Broadcast Software (OBS). The main objective was to add the capture of an LTC signal through an audio input. However, other features were added which are summarized in the features section.

## Features
- Capture LTC through an audio input. Any analog input will do the work.

- Internal video switcher.
> Dynamically created OBS Hotkeys can be mapped to keyboard keys to act as a source switcher.

> Arduino serial I/O for switcher control. Arduino code and schematics included. Designed to use push buttons but can be adapted to GPIO interfaces.

- Start and stop recording controlled by the script.
- LTC can be displayed in a OBS Text source.
- Creates a EDL file with the cuts from the switcher.

## Installation

Read [INSTALL.md](/INSTALL.md).

## Configuration

Download or clone the repository to a location of your choice. We will refer to that location as **LTC-OBS** from now on.

### Import the OBS profile

1. In OBS menu goto **Profile** -> **Import**.  
1. Navigate to **LTC-OBS\obs_profile_scene** and select the folder **OBSLTC_Profile**.
1. Activate the profile in **Profile**.
1. Goto **File** -> **Settings** -> **Output** -> **Recording** and confirm the configuration. We use a **XDCAM MPEG2** like encoder encapsulated with a **MXF OP1A**.  
<img src="images/obs_output_settings.png" width="600">

You can change the **File path or URL** folder destination at your taste.
Take in attention that the mxf file will be re-encapsulated using FFMpeg to add the correct start time code. 

### Import the OBS Scene

1. In OBS menu goto **Scene Collection** -> **Import**.
1. In a empty row press the **...** button of the **Collection Path** field.  
<img src="images/obs_scene_collection_importer.png" width="500">
1. Navigate to **LTC-OBS**\obs_profile_scene\Scene** and select the **OBS-LTC_scene.json** file.
1. Confirm that the row is checked (left side check box) and press **Import**.
1. Activate the scene in **Scene Collection**.

A **Missing Files** alert dialog may appear, you can press **Cancel**.   

The scene have the following aspect:  
<div align="center">
<img src="images/obs_ltc_scene.png" width="500">
</div>

### Import the script into OBS 

1. In OBS goto **Tools** -> **Scripts**.  
1. In the **Scripts** tab press the plus (**+**) sign button.   
1. Navigate to the **ltc-obs.py** script location and choose the file.   

</div>