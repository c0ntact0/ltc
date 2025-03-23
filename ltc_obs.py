import obspython as obs
import time,os,sys
from pprint import pprint
import pyaudio
import tc
from tc import Tc
import json
from edl_manager import Edl, output_formats
import threading
import ffmpeg
from serial_com import SerialPort
from pprint import pformat
#import debugpy

#debugpy.configure(python=r"C:\Users\rui.loureiro\AppData\Local\miniforge3\envs\obs\python.exe")
#debugpy.listen(5678)
#print("Waiting for debugger attach")
#debugpy.wait_for_client()
#debugpy.breakpoint()

# TODO: continua a dar problemas com cortes no modo timeline
# TODO: choose if we want the current_cam as reel extension or the cut number



G = lambda: ...
G.settings = None

G.ffmpeg_path = 'ffmpeg'

G.log_level = [obs.LOG_DEBUG,obs.LOG_INFO,obs.LOG_WARNING,obs.LOG_ERROR]
"""Types of logs to show"""

G.audio = None
"""PyAudio object instance"""
G.tcObj = None
"""Tc object instance"""
G.t_tc = None
"""Thread to process the tc stream"""
G.edlObj = None
G.serialPort = SerialPort()
G.tc_stream = None
G.tc_running = False
G.current_tc = (0,0,0,0)
G.clip_tc=(0,0,0,0) # clip (file) start TC.
G.timeline_start = 0 # timeline TC start frame
G.current_timeline_frame = 0
G.current_tc_frame = 0
G.audio_device = {} # current pyaudio device dict
G.tc_audio_chunk=24
G.tc_max_channels=1
G.tc_channel=0
G.fps=25 # TC frame rate
G.tick_count=0
"""Counts the ticks (frames)"""
G.start_tick_count=0
"""Stores the first tick"""
G.source_display=None
"""OBS source to display the TC"""
G.sources_cams = []
"""OBS sources used as cam channels (Cut Sources)"""
G.source_playout= None
"""OBS source used for playout"""
G.previous_cam = None
"""previous visible (selected) camera"""
G.current_cam = None
"""Currently selected camera"""
G.edl_path = os.path.expanduser("~")
"""Path to write the EDL files. Defaults to the user home path"""
G.display_timeline_tc=False # Use the timeline TC insted of LTC 
"""Use the timeline TC instead of LTC """
G.current_video_file=None
"""Last video file recorded to be played out"""
G.clipname = None
"""The clipname used in the edl"""
G.edl_format = 'file_32'
"""The EDL format used. See what formats can be used in the output_formats dict from the edl_manager.py module"""
# TODO: this may be added to the hotkeys callbacks
G.sources_handlers = []
"""Handlers to signal the cam sources visibility"""
G.lock = threading.Lock()
"""Lock for the LTC process thread"""
G.hotkey_ids = {}
"""This is a dict that have the cam name as key and a tuple (hotkey_id,hotkey_callback) as value"""
G.kill_all = False
"""If true kill all threads"""
G.source_change_tc = (0,0,0,0)
"""Store the TC at when the source is changed"""
G.source_change_timeline_tc = (0,0,0,0)
"""Store the timeline TC at when the source is changed"""
G.invert_reel = False
"""Invert the EDL reel, e.g. instead of filename.cam_name, cam_name.filename."""

# print functions
def print_debug(*values:object, 
             sep: str | None = " ",
             end: str | None = "\n"):
    
    if obs.LOG_DEBUG in G.log_level: print("DEBUG:",*values,sep=sep,end=end)

def print_error(*values:object, 
             sep: str | None = " ",
             end: str | None = "\n"):
    
    if obs.LOG_ERROR in G.log_level: print("ERROR:",*values,sep=sep,end=end)
    
def print_warning(*values:object, 
             sep: str | None = " ",
             end: str | None = "\n"):
    
    if obs.LOG_WARNING in G.log_level: print("WARNING:",*values,sep=sep,end=end)
    
def print_info(*values:object, 
             sep: str | None = " ",
             end: str | None = "\n"):
    
    if obs.LOG_INFO in G.log_level: print("INFO:",*values,sep=sep,end=end)


def get_version():
    """
        Get the script version from the VERSIONS.md file
        
        Returns
        -------
        A string with the version
    """
    versions_file = os.path.join(script_path(),'VERSIONS.md')
    if not os.path.exists(versions_file):
        return "Versions file does not exist."
    
    with open(versions_file,'r') as f:
        return f.readline().strip("- ").strip("\n")

# OBS PROPS CALLBACKS

   
def button_pressed(props,p,*args):
    print_debug("Button pressed")
    list_property = obs.obs_properties_get(props,'audio_device')
    populate_list_property_with_devices_names(list_property)
    process_audio_devices_ui(props,p,G.settings)

    return True

def audio_device_changed(props,p,settings):
    """
        Called when the list_devices property change. Populates the tc_audio_channel property
        with the channels from the selected device. Update the sample_rate_info property text.
    """

    process_audio_devices_ui(props,p,settings)
    
    return True

def timeline_start_changed(props,p,settings):
    """
        Called when the timeline_start property change. Update the timeline_start_info property text.
    """
    p = obs.obs_properties_get(props,'timeline_start_info')
    timeline_start = tc.string2tc(obs.obs_data_get_string(settings,'timeline_start'),G.fps)
    if timeline_start:
        #print("OK")
        obs.obs_property_text_set_info_type(p,obs.OBS_TEXT_INFO_NORMAL)
    else:
        #print("Error")
        obs.obs_property_text_set_info_type(p,obs.OBS_TEXT_INFO_ERROR)

    return True

def cut_sources_changed(props,p,settings):
    """
        Called when the sources_cams change. Validates the entry.
    """
    print_debug(f"cut_sources_changed: {G.sources_cams}")
    to_remove = False
    info = ""

    for cam in G.sources_cams:
        if not get_source_by_name(cam):
            to_remove = True
            info += f"OBS source {cam} does not exist."
            break
        elif G.sources_cams.count(cam) > 1:
            to_remove = True
            info += f"Cut source {cam} already exist."
            break
    
    if to_remove:
        #info = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {info}"
        print_error(info)
        G.sources_cams.pop(-1)
        sources_cams_t = list_to_array_t(G.sources_cams)
        obs.obs_data_set_array(settings,'sources_cams',sources_cams_t)
        if len(G.sources_cams) > 0:
            add_souces_handlers()
            register_hot_keys(settings)
            print_debug(f"hotkeys\n {pformat(G.hotkey_ids)}")
        
    obs.obs_data_set_string(settings,'sources_info',info)

    return True

def invert_reel_changed(props,p,settings):
    """
        Called when the invert_reel property change. Update the invert_reel_info property text.
    """
    if G.invert_reel:
        obs.obs_data_set_string(settings,'invert_reel_info',f"{G.current_cam}.{Edl('').date_string}")
    else:
        obs.obs_data_set_string(settings,'invert_reel_info',f"{Edl('').date_string}.{G.current_cam}")
        
    return True

# TODO: Start/Stop record using the OBS controls dock
#def recording_changed(props,p,*args, **kwargs):
#    print("recording_changed")
##    recording = obs.obs_frontend_recording_active()
#    button_run_tc = obs.obs_properties_get(props,'button_run_tc')
#    #obs.obs_property_set_description(rec_bt,("Stop Recording" if recording else "Start Recording"))
#    obs.obs_property_set_description(button_run_tc,"Changed")
#
#    return True



# OBS FUNCTIONS
def script_description():
    return f"""LTC-OBS ({get_version()})
- Configure all settings
- Press "Start LTC capture" to capture the external LTC
- Press "Start Recording" to start the recorder and external LTC capture.
    """
def script_properties():
    print_debug("script_properties")
    
    props = obs.obs_properties_create()
    operation_group = obs.obs_properties_create()
    config_tc_group = obs.obs_properties_create()
    config_sources_group = obs.obs_properties_create()
    config_edl_group = obs.obs_properties_create()
    config_serial_group = obs.obs_properties_create()
    miscellaneous_group = obs.obs_properties_create()
    logging_group = obs.obs_properties_create()

    obs.obs_properties_add_group(props,'operation_group',"Operation",obs.OBS_GROUP_NORMAL,operation_group)
    obs.obs_properties_add_group(props,'config_tc_group',"LTC Configuration",obs.OBS_GROUP_NORMAL,config_tc_group)
    obs.obs_properties_add_group(props,'config_sources_group',"Sources Configuration",obs.OBS_GROUP_NORMAL,config_sources_group)
    obs.obs_properties_add_group(props,'config_edl_group',"EDL Configuration",obs.OBS_GROUP_NORMAL,config_edl_group)
    obs.obs_properties_add_group(props,'config_serial_group',"Serial Port Configuration",obs.OBS_GROUP_NORMAL,config_serial_group)
    obs.obs_properties_add_group(props,'miscellaneous_group',"Miscellaneous Configuration",obs.OBS_GROUP_NORMAL,miscellaneous_group)
    obs.obs_properties_add_group(props,'logging_group',"Logging Configuration",obs.OBS_GROUP_NORMAL,logging_group)


    # ======== Operation =========
    obs.obs_properties_add_button(operation_group,'button_record_control',"Start Recording",lambda props,p: record_control(props))
    #clipname = 
    obs.obs_properties_add_text(operation_group,'clipname',"Clipname",obs.OBS_TEXT_DEFAULT)

    # ======== TC =========
    obs.obs_properties_add_button(config_tc_group,"button_run_tc","Start LTC capture",lambda props,p: run_tc(props))

    list_devices = obs.obs_properties_add_list(config_tc_group,"audio_device","Audio device",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_devices_names(list_devices)
        
    channels_list = obs.obs_properties_add_list(config_tc_group,"tc_audio_channel","Channel",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_INT)
    populate_list_property_with_integers(channels_list,G.tc_max_channels)
    
    button_refresh_devices = obs.obs_properties_add_button(config_tc_group, "button_refresh_devices", "Refresh list of devices",button_pressed)

    sample_rate_info = obs.obs_properties_add_text(config_tc_group, "sample_rate_info", "", obs.OBS_TEXT_INFO)
    obs.obs_property_set_description(sample_rate_info,"Sample Rate")

    list_fps = obs.obs_properties_add_list(config_tc_group,'fps',"FPS", obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_INT)
    populate_list_property_with_fps(list_fps)
    
    obs.obs_properties_add_int_slider(config_tc_group,'slider_chunk',"Buffer Size",1,1024,1)

    list_sources_display = obs.obs_properties_add_list(config_tc_group,'source_display',"TC display source", obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_display_sources(list_sources_display)

    display_timeline_tc = obs.obs_properties_add_bool(config_tc_group,'display_timeline_tc',"Use Timeline TC (Experimental)")
    obs.obs_property_set_long_description(display_timeline_tc,"Use timeline TC when recording. Display the TC when recording only.")
    timeline_start = obs.obs_properties_add_text(config_tc_group,'timeline_start',"Timeline Start TC",obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(config_tc_group,'timeline_start_info',"",obs.OBS_TEXT_INFO)
    
    # ======== Sources =========
    sources_info = obs.obs_properties_add_text(config_sources_group,'sources_info',"",obs.OBS_TEXT_INFO)
    obs.obs_property_text_set_info_type(sources_info,obs.OBS_TEXT_INFO_ERROR)
    sources_prop = obs.obs_properties_add_editable_list(config_sources_group,'sources_cams',"Cut Sources",obs.OBS_EDITABLE_LIST_TYPE_STRINGS,"","")
    obs.obs_property_set_long_description(
        sources_prop,
        "To assign a keyboard key to a new Cut Source go to the OBS menu File->Settings->Hotkeys.")

    
    list_source_playout = obs.obs_properties_add_list(config_sources_group,'source_playout',"Source for Playout",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_sources(list_source_playout,'ffmpeg_source')

    # ======== Edl =========
    edl_format_lis = obs.obs_properties_add_list(config_edl_group,'edl_format',"Edl Format",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_edl_types(edl_format_lis)
    
    invert_reel = obs.obs_properties_add_bool(config_edl_group,'invert_reel',"Invert Reel Name and Reel Extension")
    obs.obs_properties_add_text(config_edl_group,'invert_reel_info',"Reel Preview",obs.OBS_TEXT_INFO)
    
    obs.obs_properties_add_path(config_edl_group,'edl_path','EDL export folder',obs.OBS_PATH_DIRECTORY,"",G.edl_path)

    # ======== Serial =========
    list_serial_port = obs.obs_properties_add_list(config_serial_group,'serial_port',"Serial Ports",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_serial_ports(list_serial_port)


    # ======== Miscellaneous =========
    dock_state = obs.obs_properties_add_bool(miscellaneous_group,'dock_state',"Apply Dock State")
    obs.obs_property_set_long_description(dock_state,'Only "Scenes","Sources" and "Audio Mixer" docks are loaded at startup.')
    
    obs.obs_properties_add_text(miscellaneous_group,'ffmpeg_path',"FFmpeg Path",obs.OBS_TEXT_DEFAULT)
    
    # ======== Logging =========
    obs.obs_properties_add_bool(logging_group,'log_info',"Log Info Messages")
    obs.obs_properties_add_bool(logging_group,'log_warning',"Log Warning Messages")
    obs.obs_properties_add_bool(logging_group,'log_error',"Log Error Messages")
    obs.obs_properties_add_bool(logging_group,'log_debug',"Log Debug Messages")
    
    # CALLBACKS
    obs.obs_property_set_modified_callback(list_devices, audio_device_changed)
    obs.obs_property_set_modified_callback(timeline_start, timeline_start_changed)
    obs.obs_property_set_modified_callback(sources_prop,cut_sources_changed)
    obs.obs_property_set_modified_callback(invert_reel,invert_reel_changed)
    
    obs.obs_property_set_modified_callback(button_refresh_devices,button_pressed)
    
    
   
   # This must be here because we need the Cut Sources values to get the current cam number
    if G.serialPort.is_open:
        _,cam_number = get_current_cam_name()
        write_to_serial(cam_number)
        write_to_serial(len(G.sources_cams),'N')

    obs.obs_properties_apply_settings(props, G.settings)
    return props

def script_defaults(settings):
    print_debug("script_defaults")

    obs.obs_data_set_default_string(settings, "audio_device", "")
    obs.obs_data_set_default_string(settings, "sample_rate_info", "NA")
    obs.obs_data_set_default_string(settings, "clipname", "")
    
    # TODO: error when reloading the script or getting defaults
    #sources = obs.obs_enum_sources()
    #sources_names = [obs.obs_source_get_name(source) for source in sources]
    #sources_names_str = []
    #for s in sources_names:
    #    if s.startswith("CAM"):
    #        sources_names_str.append(s)
    #        
    #print(sources_names_str)

    #sources_t = list_to_array_t(sources_names_str)
    #obs.obs_data_set_default_array(settings, "sources_cams", sources_t)
    #obs.source_list_release(sources)
    #obs.obs_data_array_release(sources_t)

    obs.obs_data_set_default_int(settings,'fps',25)
    obs.obs_data_set_default_int(settings,'slider_chunk',24)
    obs.obs_data_set_default_string(settings, "source_display", "")
    obs.obs_data_set_default_string(settings, "source_playout", "")
    obs.obs_data_set_default_bool(settings,'display_timeline_tc',False)
    obs.obs_data_set_default_string(settings,'timeline_start',"00:00:00:00")
    obs.obs_data_set_default_string(settings,'timeline_start_info',"TC format: hh:mm:ss:ff")
    obs.obs_data_set_default_string(settings,'sources_info',"")
    obs.obs_data_set_default_string(settings,'edl_format',"file_32")
    obs.obs_data_set_default_string(settings,'invert_sources_info',f"{Edl('').date_string}.{G.current_cam}")
    obs.obs_data_set_default_string(settings,'edl_path',os.path.expanduser("~"))
    obs.obs_data_set_default_bool(settings,'dock_state',True)
    obs.obs_data_set_default_string(settings,'serial_port',"")
    obs.obs_data_set_default_string(settings,'ffmpeg_path',"ffmpeg")

    obs.obs_data_set_default_bool(settings,'log_info',True)
    obs.obs_data_set_default_bool(settings,'log_warning',True)
    obs.obs_data_set_default_bool(settings,'log_error',True)
    obs.obs_data_set_default_bool(settings,'log_debug',True)

def script_update(settings):
   
    print_debug("script_update")

    G.ffmpeg_path = obs.obs_data_get_string(settings,'ffmpeg_path')
    G.clipname = obs.obs_data_get_string(settings,'clipname')
    G.audio_device = get_audio_device_from_properties(settings)
    try:
        G.tc_max_channels = int(G.audio_device.get('maxInputChannels',1))
    except TypeError:
        print_warning("No audio device for LTC.")
        
    G.tc_channel = obs.obs_data_get_int(settings,'tc_audio_channel')
    G.fps = obs.obs_data_get_int(settings,'fps')
    G.tc_audio_chunk = obs.obs_data_get_int(settings,'slider_chunk')
    G.source_display = obs.obs_data_get_string(settings,'source_display')
    G.source_playout = obs.obs_data_get_string(settings,'source_playout')
    G.display_timeline_tc = obs.obs_data_get_bool(settings,'display_timeline_tc')
    try:
        sources_cams_array = obs.obs_data_get_array(settings,"sources_cams")
        G.sources_cams = array_t_to_list(sources_cams_array)
        print_debug(f"Cut sources {G.sources_cams}")
        obs.obs_data_array_release(sources_cams_array)
    except:
        print_error("Please choose cut sources")
    
    # this is needed for the script reload from OBS GUI
    if len(G.sources_cams) > 0:
        add_souces_handlers()
        register_hot_keys(settings)
        print_debug(f"hotkeys\n {pformat(G.hotkey_ids)}")

    
    # just for testing
    G.timeline_start = tc.string2tc(obs.obs_data_get_string(settings,'timeline_start'),G.fps)
    if G.timeline_start:
        G.timeline_start = tc.tc2frames(G.timeline_start,G.fps)
        obs.obs_data_set_string(settings,'timeline_start_info',"TC format: hh:mm:ss:ff")
    else:
        G.timeline_start = 0
        obs.obs_data_set_string(settings,'timeline_start_info',"Format error, must be: hh:mm:ss:ff")
        
    G.edl_format = obs.obs_data_get_string(settings,'edl_format')
    G.invert_reel = obs.obs_data_get_bool(settings,'invert_reel')
    G.edl_path = obs.obs_data_get_string(settings,'edl_path')
    G.current_cam,_ = get_current_cam_name()
    
    if not G.serialPort.is_open:
        try:
            G.serialPort.inicialize_port(obs.obs_data_get_string(settings,'serial_port'))

            if G.serialPort.is_open:
                #TODO: replace with timer, or not :-)
                t = threading.Thread(target=read_from_serial)
                t.start()
        except Exception as e:
            print_error(e)
            
            
    if not G.t_tc: 
        G.t_tc = threading.Thread(target=process_tc_thread)
        G.t_tc.start()

    # Logging
    G.log_level.clear()
    if obs.obs_data_get_bool(settings,'log_info'): G.log_level.append(obs.LOG_INFO)
    if obs.obs_data_get_bool(settings,'log_warning'): G.log_level.append(obs.LOG_WARNING)
    if obs.obs_data_get_bool(settings,'log_error'): G.log_level.append(obs.LOG_ERROR)
    if obs.obs_data_get_bool(settings,'log_debug'): G.log_level.append(obs.LOG_DEBUG)
        
    print_info("Current Profile:",obs.obs_frontend_get_current_profile())
    
    G.settings = settings

def script_tick(seconds):
    G.tick_count+=1    
    
def script_load(settings):
    
    G.settings = settings
    print_debug("script_load")
    G.audio = pyaudio.PyAudio()
    if obs.obs_data_get_bool(settings,'dock_state'):
        obs_main_version = int(obs.obs_get_version_string().split('.')[0])
        print_info("OBS Version:",obs.obs_get_version_string())
        if obs_main_version >= 31:
            config = obs.obs_frontend_get_user_config()
        else:
            config = obs.obs_frontend_get_global_config()
        #config = obs.obs_frontend_get_global_config()
        obs.config_set_string(config,"BasicWindow","DockState","AAAA/wAAAAD9AAAAAQAAAAMAAAQAAAABAfwBAAAABvsAAAAUAHMAYwBlAG4AZQBzAEQAbwBjAGsBAAAAAAAAASwAAACgAP////sAAAAWAHMAbwB1AHIAYwBlAHMARABvAGMAawEAAAEwAAABLAAAAKAA////+wAAABIAbQBpAHgAZQByAEQAbwBjAGsBAAACYAAAAaAAAADeAP////sAAAAeAHQAcgBhAG4AcwBpAHQAaQBvAG4AcwBEAG8AYwBrAAAAAx4AAADiAAAAnAD////7AAAAGABjAG8AbgB0AHIAbwBsAHMARABvAGMAawAAAALKAAABNgAAAJ4A////+wAAABIAcwB0AGEAdABzAEQAbwBjAGsCAAACYgAAAdcAAAK8AAAAyAAABAAAAAFLAAAABAAAAAQAAAAIAAAACPwAAAAA")

    obs.obs_frontend_add_event_callback(on_frontend_event)



def script_unload():
   
    print_debug("script_unload")
    G.kill_all = True
    time.sleep(0.5)
    #obs.timer_remove(process_tc_thread)
    if G.tc_running:
        G.tc_stream.close()

    if G.audio:
        G.audio.terminate()

    if G.serialPort.running:
        G.serialPort.stop()
        G.serialPort.close_port()
    
    if G.tcObj: del G.tcObj
    if G.edlObj: del G.edlObj
        
def script_save(settings):
    save_hotkeys(settings)
    G.settings = settings
    

# HOT_KEYS
def register_hot_keys(settings):
    """
        Register and removes hotkeys.
        
        Parameters
        ----------
        settings: obs_data_t
            OBS settings object
    """

    # Removes callbacks and hotkeys for removed source cams
    removed_cams = []
    for cam,hotkey_id in G.hotkey_ids.items():
        if cam not in G.sources_cams:
            f_name = f"hotkey_id_{cam.lower()}_callback"
            obs.obs_hotkey_unregister(hotkey_id[1])
            removed_cams.append(cam)
            print_debug(f"hotkey_id {cam} and {f_name} callback removed")
    for cam in removed_cams:
        G.hotkey_ids.pop(cam)
    
    # Register hotkeys for new source cam
    for cam in G.sources_cams:
        if cam not in G.hotkey_ids.keys():
            description = f"Select {cam}"

            current_hotkey_id = len(G.hotkey_ids)+1        
            f_name = f"hotkey_id_{current_hotkey_id}_callback"
            code = f"def {f_name}(pressed):\n    if pressed:\n        set_current_cam({current_hotkey_id})\n        write_to_serial({current_hotkey_id})"
            x = compile(code,'callback','single')
            exec(x)

            G.hotkey_ids[cam] = (obs.obs_hotkey_register_frontend(cam,description, eval(f_name)),eval(f_name))
            hotkey_save_array = obs.obs_data_get_array(settings, f"hotkey_{cam}")
            obs.obs_hotkey_load(G.hotkey_ids[cam][0], hotkey_save_array)
            obs.obs_data_array_release(hotkey_save_array)

    save_hotkeys(settings)

def save_hotkeys(settings):
    """
        Save the hotkeys to settings
        
        Parameters
        ----------
        settings: obs_data_t
            OBS settings object
    """
    print_debug("Saving hotkeys")
    for k,v in G.hotkey_ids.items():
        hotkey_save_array = obs.obs_hotkey_save(v[0])
        obs.obs_data_set_array(settings, f"hotkey_{k}", hotkey_save_array)
        obs.obs_data_array_release(hotkey_save_array)

# SOURCES HANDLERS AND CALLBACKS
def add_souces_handlers():
    """
        Connect the signal handlers for the show signal to the sources_callback callback function.  
    """
    print_debug("Configuring source handlers")

    for h in G.sources_handlers:
        obs.signal_handler_disconnect(h,"show",sources_callback)
    
    G.sources_handlers.clear()

    for cam in G.sources_cams:
        print_debug(f"Configuring handler for {cam}")
        source = obs.obs_get_source_by_name(cam)
        sh = obs.obs_source_get_signal_handler(source)
        obs.signal_handler_connect(sh,"show",sources_callback)
        G.sources_handlers.append(sh)
        obs.obs_source_release(source)

def remove_source_handlers():
    """
        Disconnect the signal handlers for the show signal from the sources_callback callback function.  
    """
    print_debug("Removing source handlers.")
    for h in G.sources_handlers:
        obs.signal_handler_disconnect(h,"show",sources_callback)    

def sources_callback(calldata):
    """
        Called when the show signal is emitted from a OBS source that is connected to this callback.
        
        Parameters
        ----------
        calldata: calldata_t
            Data from the connected object
    """
    source = obs.calldata_source(calldata,"source")
    G.current_cam = obs.obs_source_get_name(source)
    print_debug(f"Current cam is {G.current_cam}")
    G.source_change_tc = G.current_tc
    G.source_change_timeline_tc = tc.frames2tc(G.timeline_start + tc.tc2frames(G.current_tc,G.fps) - tc.tc2frames(G.clip_tc,G.fps),G.fps)
    if G.tc_running:  print_debug(f"Current TC:{tc.tc2String(G.current_tc)} {tc.tc2String(G.source_change_timeline_tc) if G.display_timeline_tc else tc.tc2String(G.current_tc)}")


def on_frontend_event(e):
    """
        Called from the obs_frontend_add_event_callback.
        
        Parameters
        ----------
        e: obs_frontend_event
            The event type.
    """
    if e == obs.OBS_FRONTEND_EVENT_RECORDING_STARTING:
        print_info("Recording Starting...")
        G.clip_tc = (0,0,0,0)
        G.edlObj = Edl(G.clipname)
        config = obs.obs_frontend_get_profile_config()
        obs.config_set_string(config, "Output","FilenameFormatting", G.edlObj.date_string)
        
        #edlObj.add_cut_in(current_cam,current_cam,mark_tc_string,mark_timeline_tc_string)
    elif e == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        print_info("Recording Started...")
        G.tick_count=0
        #obs.obs_properties_apply_settings(props,settings_g)
        
    elif e == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print_info("Recording Stopped.")
        #create_cuts()
        
    elif e == obs.OBS_FRONTEND_EVENT_FINISHED_LOADING:
        # This is needed for the first script load
        add_souces_handlers()
    elif e == obs.OBS_FRONTEND_EVENT_SCRIPTING_SHUTDOWN:
        remove_source_handlers()

def record_control(probs):
    """
        Controls the start ans stop of the OBS recorder. Called from the button_record_control button property.
        
        Parameters
        ----------
        probs: obs_properties_t
            The OBS props object
    """
    recording = obs.obs_frontend_recording_active()
    bt_rec = obs.obs_properties_get(probs,'button_record_control')
    bt_tc = obs.obs_properties_get(probs,'button_run_tc')
    if recording:
        obs.obs_property_set_description(bt_rec,'Start Recording')
        obs.obs_frontend_recording_stop()

        obs.obs_property_set_enabled(bt_tc,True)
    else:
        config = obs.obs_frontend_get_profile_config()
        rec_type = obs.config_get_string(config,"AdvOut","RecType")
        video_path = obs.config_get_string(config, "AdvOut", "FFFilePath") or None
        if rec_type == 'Standard':
            video_path = obs.config_get_string(config, "AdvOut", "RecFilePath") or None
        if not video_path or not os.path.exists(video_path):
            print_warning(f"Recording path {video_path} does not exist.")
            return True
        set_current_scene("RECORD") #TODO: escolher no script
        if not G.tc_running:
            run_tc(probs)
            time.sleep(1)
        G.current_timeline_frame = G.timeline_start
        current_tc_string = tc.tc2String(tc.frames2tc(G.timeline_start,G.fps)) if G.display_timeline_tc else G.tcObj.currentTcString
        process_tc_display(current_tc_string)
        obs.obs_property_set_description(bt_rec,'Stop Recording')
        obs.obs_property_set_enabled(bt_tc,False)
        obs.obs_frontend_recording_start()

    return True

################## OBS USER FUNCTIONS
def get_audio_device_from_properties(settings):
    """
        Get the PyAudio device info for the selected audio device.
        
        Parameters
        ----------
        settings: obs_data_t
            OBS settings object
            
        Returns
        -------
            A dict with the device info or a empty dict if the device index does not exist.
    """
    index_string = obs.obs_data_get_string(settings,"audio_device")
    index_exists = len(index_string) > 0
    #print(index_exists)
    index = -1 if not index_exists else int(index_string)
    return {} if not index_exists else G.audio.get_device_info_by_index(index)

def populate_list_property_with_devices_names(list_property):
    """
        Populate a list property with audio device names.
        
        Parameters
        ----------
        list_property: obs_property_t
            The list property to populate
            
        Returns
        -------
            True
    """
    print_debug("Listing audio devices.")
    audio_devices = get_audio_devices(G.audio)
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for device in audio_devices:
      obs.obs_property_list_add_string(list_property, f"{device.get('name')} | Channels: {device.get('maxInputChannels')}" , str(device.get('index')))
      
    #obs.source_list_release(audio_devices)
    
    return True

def populate_list_property_with_integers(list_property,maximum:int,minimum:int=0,step:int=1):
    """
        Populate a list property with integers from minimum to maximum using step distance.
        
        Parameters
        ----------
        list_property: obs_property_t
            The list property to populate
        maximum: int
            Maximum number for the list (exclusive) 
        minimum: int, optional
            Minimum number for the list (inclusive). Default is 0.
        step: int, optional
            Step distance to use between numbers. Default is 1.
            
    """
    channels = [i for i in range(minimum,maximum,step)]
    obs.obs_property_list_clear(list_property)
    for ch in channels:
        obs.obs_property_list_add_int(list_property,f"{ch}",ch)

def populate_list_property_with_fps(list_property):
    """
        Populate a list property with frame rates. 
        
        Parameters
        ----------
        list_property: obs_property_t
            The list property to populate
    """
    fps_list = [24,25,30]
    obs.obs_property_list_clear(list_property)
    for rate in fps_list:
        obs.obs_property_list_add_int(list_property,str(rate),rate)
    #obs.source_list_release(fps_list)

def populate_list_property_with_edl_types(list_property):
    """
        Populate a list property with edl format types. 
        
        Parameters
        ----------
        list_property: obs_property_t
            The list property to populate
    """
    obs.obs_property_list_clear(list_property)
    for k in output_formats.keys():
        obs.obs_property_list_add_string(list_property,k,k)

def populate_list_property_with_sources(list_property,types:list=[], show_type:bool=False,add_empty:bool=True):
    """
        Populate a list property with sources name. The sources IDs (types) can be specified to be filtered.
        By default includes a empty entry a the top of the list.
        
        Parameters
        ----------
        list_property: obs_property_t
            The list property to populate
        types: list(int), optional
            The types of sources to add to the list. Default is a empty list.
        show_type:bool, optional
            Show the source type between square brackets after the source name. Default is False. 
        add_empty: bool, optional
            If True add a empty entry to the top of the list. Default is True.
    """
    sources = obs.obs_enum_sources()
    obs.obs_property_list_clear(list_property)
    if add_empty: obs.obs_property_list_add_string(list_property, "", "")
    for source in sources:
        source_id = obs.obs_source_get_unversioned_id(source)
        if (source_id in types) or len(types) == 0:
            name = obs.obs_source_get_name(source)
            display_name = name
            #print_debug(name,source_id)
            if show_type:
                display_name+=" [" + source_id + "]"
            obs.obs_property_list_add_string(list_property, display_name, name)
    obs.source_list_release(sources)
    
def populate_list_property_with_display_sources(list_property):
    """
        Populate a list property with text display sources names (text_gdiplus and text_ft2_source). 
        
        Parameters
        ----------
        list_property: obs_property_t
            The list property to populate
    """
    populate_list_property_with_sources(list_property,["text_gdiplus","text_ft2_source"])

def populate_list_property_with_serial_ports(list_property):
    """
        Populate a list property with a serial ports list. 
        
        Parameters
        ----------
        list_property: obs_property_t
            The list property to populate
    """
    serial_ports = G.serialPort.get_serial_ports()
    obs.obs_property_list_clear(list_property)
    for port,desc,hwid in serial_ports:
        obs.obs_property_list_add_string(list_property,desc,port)

 # Not used
def get_sceneitem_from_source_name_in_current_scene(name):
    result_sceneitem = None
    current_scene_as_source = obs.obs_frontend_get_current_scene()
    if current_scene_as_source:
        current_scene = obs.obs_scene_from_source(current_scene_as_source)
        result_sceneitem = obs.obs_scene_find_source_recursive(current_scene, name)
    
        obs.obs_source_release(current_scene_as_source)
        
    return result_sceneitem

def get_source_by_name(name:str):
    """
        Get a source from the current scene using the source name.
        
        Parameters
        ----------
        name: str
            The name of the source to get.
            
        Returns
        -------
        A obs_sceneitem_t object
    """
    
    result_source = None
    current_scene_have_source = obs.obs_frontend_get_current_scene()
    if current_scene_have_source:
        current_scene = obs.obs_scene_from_source(current_scene_have_source)
        result_source = obs.obs_scene_find_source_recursive(current_scene, name)
        obs.obs_source_release(current_scene_have_source)
    
    return result_source

def get_current_cam_name():
    """
    Retuns:
        cam name, cam number
    """
           
    for i in range(len(G.sources_cams)):
        source = obs.obs_get_source_by_name(G.sources_cams[i])
        if obs.obs_source_active(source):
            obs.obs_source_release(source)
            return G.sources_cams[i],i+1
        obs.obs_source_release(source)

    return None,0

def set_current_cam(cam_number:int):
    """
        cam_number is a number from 1 to max number of cameras
    """
    idx = cam_number-1
    if idx < 0:
        return
    
    for i in range(len(G.sources_cams)):
        #print(sources_cams[i])
        current_scene_as_source = obs.obs_frontend_get_current_scene()
        if current_scene_as_source:
            current_scene = obs.obs_scene_from_source(current_scene_as_source)
            scene_item = obs.obs_scene_find_source_recursive(current_scene, G.sources_cams[i])
            if scene_item:
                obs.obs_sceneitem_set_visible(scene_item,i == idx)
            obs.obs_source_release(current_scene_as_source)

def set_current_scene(scene_name):
        scenes = obs.obs_frontend_get_scenes()
        for scene in scenes:
            name = obs.obs_source_get_name(scene)
            if name == scene_name:
                obs.obs_frontend_set_current_scene(scene)
        #obs.obs_frontend_source_list_free(scenes) 
        obs.source_list_release(scenes)

# OBS UTIL FUNCTIONS
def from_data_t(data_t):
    j = obs.obs_data_get_json(data_t)
    obs.obs_data_release(data_t)
    d = json.loads(j)
    return d["value"]

def to_data_t(value):

    dic = {
        "hidden": False,
        "selected": False,
        "value": value
        }
    j = json.dumps(dic)
    return obs.obs_data_create_from_json(j)

def array_t_to_list(array_t):
    length = obs.obs_data_array_count(array_t)
    if length == 0:
        return []
    data_t_list = [obs.obs_data_array_item(array_t, i) for i in range(length)]
    
    return [from_data_t(data_t) for data_t in data_t_list]

def list_to_array_t(values:list):
    data_t_list = [to_data_t(value) for value in values]
    array_t = obs.obs_data_array_create()
    for data_t in data_t_list:
        obs.obs_data_array_push_back(array_t, data_t)
        
    return array_t

# PYAUDIO FUNCTIONS
def process_audio_devices_ui(props,p,settings):
    
    G.audio_device = get_audio_device_from_properties(settings)
    max_channels=0
    if len(G.audio_device):
        max_channels = G.audio_device.get('maxInputChannels')
        info = f"{G.audio_device.get('defaultSampleRate')}"# str(int(audio_device.get('defaultSampleRate')))
    else:
        info = "NA"
    
    obs.obs_data_set_string(settings,'sample_rate_info',info)
    p = obs.obs_properties_get(props,'tc_audio_channel')
    populate_list_property_with_integers(p,max_channels)
        
def get_audio_devices(audio:pyaudio) -> list:
    
    # this need to be done to PortAudio reinicialize the devices 
    audio.terminate()
    audio = pyaudio.PyAudio()
    
    devices = []
    try:
        devices_num = audio.get_device_count()
        for i in range(devices_num):
            device_info = audio.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                devices.append(device_info)
                #pprint(device_info)
    except Exception as e:
        print(f"Error while trying to get audio devices:\n{e}")
    
    return devices

def get_audio_devices_names(audio:pyaudio) -> list:
    names = []
    devices = get_audio_devices(audio)
    for device in devices:
      names.append(device.get('name'))

    return names

def get_audio_device_by_name(name:str,audio:pyaudio) -> int:
    devices = get_audio_devices(audio)
    for device in devices:
       if device.get('name') == name:
          return device
       
    return None



def run_tc(props):
    p = obs.obs_properties_get(props,'button_run_tc')
    if G.tc_running:
        obs.obs_property_set_description(p,'Start LTC capture')
        if G.tc_stream:
            G.tc_stream.close()
            G.tcObj = None
        G.tc_running=False
        print_info("TC Capture Stopped...")

    else:
        print_info("=============================================")
        print_info("Selected Audio Device")
        pprint(G.audio_device)
        print_info("---------------------------------------------")
        print_info(f"Buffer Size: {G.tc_audio_chunk}")
        print_info("=============================================")
        FORMAT=pyaudio.paInt24
        G.tc_max_channels = int(G.audio_device.get('maxInputChannels'))
        try:
            SAMPLE_RATE = int(G.audio_device.get('defaultSampleRate'))
        except TypeError as e:
            print_error(f"Can't get sample rate from the audio device.")
            return True
        try:
            DEVICE_INDEX = int(G.audio_device.get('index'))
        except TypeError as e:
            print_error(f"Can't get device index from the audio device.")
            return True

        obs.obs_property_set_description(p,'Stop LTC capture')
        G.tcObj = Tc(SAMPLE_RATE,G.fps)
        
        # TODO: for MacOS we may need pyaudio.PaMacCoreStreamInfo
        # https://people.csail.mit.edu/hubert/pyaudio/docs/index.html#pyaudio.PaMacCoreStreamInfo
        G.tc_stream = G.audio.open(format=FORMAT,input=True,input_device_index=DEVICE_INDEX,rate=SAMPLE_RATE,channels=G.tc_max_channels,frames_per_buffer=G.tc_audio_chunk,stream_callback=tc_stream_callback)
        G.tc_running=True
        print_info("TC Capture Running...")
        
    return True

def process_tc_display(tc_string):
    source_tc = obs.obs_get_source_by_name(G.source_display)

    if source_tc:
        # does not process if the source is hidden
        if obs.obs_source_showing(source_tc):
            settings = obs.obs_data_create()
            obs.obs_data_set_string(settings, "text", tc_string)
            obs.obs_source_update(source_tc, settings)
            obs.obs_data_release(settings)
        obs.obs_source_release(source_tc)

def set_playout_source(filename:str):
    source = obs.obs_get_source_by_name(G.source_playout)
    if source:
        settings = obs.obs_data_create()
        #settings = obs.obs_source_get_settings(source)
        #pprint(obs.obs_data_get_json(settings))
        obs.obs_data_set_bool(settings, "is_local_file", True)
        obs.obs_data_set_string(settings, "local_file", filename
                                )
        obs.obs_source_update(source, settings)

        obs.obs_data_release(settings)
        obs.obs_source_release(source)

def apply_ffmpeg_rewrap(reel:str):
    config = obs.obs_frontend_get_profile_config()
    rec_type = obs.config_get_string(config,"AdvOut","RecType")
    ff_extension = "." +  obs.config_get_string(config,"AdvOut","FFExtension")
    video_path = obs.config_get_string(config, "AdvOut", "FFFilePath") or None
    if rec_type == 'Standard':
        ff_extension = "." + obs.config_get_string(config,"AdvOut","RecFormat2")
        video_path = obs.config_get_string(config, "AdvOut", "RecFilePath") or None

    print_debug(f"File extension is {ff_extension}")
    #print(obs.config_get_string(config, "Output", "FilenameFormatting") or "")
    video_filename = os.path.join(video_path,reel + ff_extension)
    video_filename_renamed = os.path.join(video_path,reel + "_old" + ff_extension)
    rename_tries = 0
    while True:
        try:
            rename_tries+=1
            os.rename(video_filename,video_filename_renamed)
            print_debug("File renamed")
            break
        except PermissionError:
            if rename_tries == 10:
                break
            
            print_debug("File rename failed. Retrying...")
            time.sleep(1)
        
    time.sleep(1)
    (
        ffmpeg.input(video_filename_renamed)
        .output(video_filename,c='copy',
                timecode=tc.tc2String(G.clip_tc),
                movflags='use_metadata_tags',
                map_metadata=0,
                metadata='name='+reel
                ).run(cmd=G.ffmpeg_path)
    )
    os.remove(video_filename_renamed)
    G.current_video_file=video_filename
    #pprint(ffmpeg.probe(video_filename))
    
    print_info("Rewrap applied")

    set_playout_source(video_filename)

def process_tc_thread(): # this start in script_update

    #print_debug("Using running LTC for cuts.")
    while True:
        if G.kill_all:
            break
        start = time.perf_counter()
        with G.lock:
            if G.tc_running:

                recording = obs.obs_frontend_recording_active()
                if recording and not G.edlObj:
                    print_warning("We have a problem. OBS is recording but no edl object it's created.")
                    return
                previous_tc_frames = tc.tc2frames(G.current_tc,G.fps)
                G.current_tc = G.tcObj.currentTc
                G.current_tc_frame = tc.tc2frames(G.current_tc,G.fps)
                diff_frames = G.current_tc_frame - previous_tc_frames

                if diff_frames > 1:
                    print_debug(f"Missing {diff_frames-1} frames. Try to decrease the buffer (current: {G.tc_audio_chunk} bytes")
                elif diff_frames < 0:
                    print_debug(f"Missing {diff_frames-1} frames. Try to increase the buffer (current: {G.tc_audio_chunk} bytes")

                timeline_tc_string = tc.tc2String(tc.frames2tc(G.current_timeline_frame,G.fps))
                current_tc_string = tc.tc2String(G.current_tc)
                if not G.current_cam:
                    G.current_cam,_ = get_current_cam_name()
                new_cam = G.current_cam != G.previous_cam
                if new_cam:
                    G.previous_cam = G.current_cam
                
                mark_tc_string = tc.tc2String(G.source_change_tc) #tc.tc2String(tc.frames2tc(current_tc_frame,fps))
                mark_timeline_tc_string = tc.tc2String(G.source_change_timeline_tc) if G.display_timeline_tc else mark_tc_string

                if G.edlObj:
                    file_reel = G.edlObj.date_string
                    if recording and G.edlObj.cut_counter == 0: #not edlObj:
                        #timeline_tc_string = tc.tc2String(tc.frames2tc(timeline_start,fps))
                        G.clip_tc = G.current_tc
                        G.edlObj.add_cut_in(
                            file_reel,
                            file_reel,
                            current_tc_string,
                            tc.tc2String(tc.frames2tc(G.timeline_start,G.fps)) if G.display_timeline_tc else current_tc_string,
                            G.current_cam,
                            G.invert_reel)
                        print_info("MARK:",current_tc_string,timeline_tc_string,G.current_cam)
                    elif new_cam and recording and G.edlObj.cut_counter > 0:
                        #edlObj.add_cut_out(
                        #    mark_tc_string,
                        #    mark_timeline_tc_string)
                        #edlObj.add_cut_in(
                        #    file_reel,
                        #    file_reel,
                        #    mark_tc_string,
                        #    mark_timeline_tc_string,
                        #    current_cam)
                        #print_info("MARK:",current_tc_string,timeline_tc_string,current_cam)
                        t_cut = threading.Thread(target=add_cut_callback,args=(G.edlObj,file_reel,file_reel,mark_tc_string,mark_timeline_tc_string,G.current_cam,G.invert_reel))
                        t_cut.start()
                    elif not new_cam and not recording and G.edlObj.cut_counter > 0:
                        mark_timeline_tc_string = tc.tc2String(tc.frames2tc(G.timeline_start + G.tick_count,G.fps)) if G.display_timeline_tc else tc.tc2String(tc.frames2tc(tc.tc2frames(G.clip_tc,G.fps) + G.tick_count,G.fps))
                        G.edlObj.add_cut_out(
                            current_tc_string,
                            mark_timeline_tc_string)
                        print_info("MARK:",current_tc_string,mark_timeline_tc_string,G.current_cam)
                        G.edlObj.save_avid_edl(G.edl_path,G.fps,file_reel+'.edl',G.clipname)
                        G.edlObj = None
                        # This is necessary to apply the TC to the file
                        t = threading.Thread(target=apply_ffmpeg_rewrap,args=(file_reel,))
                        t.start()
                        print_info(f"Last cut: tick count {G.tick_count}")
                    else:
                        pass
                    
                if G.display_timeline_tc and recording:
                    process_tc_display(timeline_tc_string)
                else:
                    process_tc_display(current_tc_string)  

                if recording:
                    G.current_timeline_frame = G.timeline_start + tc.tc2frames(G.current_tc,G.fps) - tc.tc2frames(G.clip_tc,G.fps)
                else:
                    G.current_timeline_frame = G.timeline_start


            delta = time.perf_counter() - start
            if delta > 1/G.fps:
                print_warning(f"Processing time excedes FPS: {delta}")          
        time.sleep(1/(G.fps*2))
    
    print_debug("process_tc_thread terminated")
    

def add_cut_callback(edlObj:Edl,
                     file_reel,
                     clipname,
                     mark_tc_string,
                     mark_timeline_tc_string,
                     current_cam,
                     invert_edl_reel,
                     cut_out=True,
                     cut_in=True
                     ):
    if cut_out: edlObj.add_cut_out(mark_tc_string,mark_timeline_tc_string)
    if cut_in: edlObj.add_cut_in(file_reel,clipname,mark_tc_string,mark_timeline_tc_string,current_cam,invert_edl_reel)
    print_info("MARK:",mark_tc_string,mark_timeline_tc_string,current_cam)
    

def tc_stream_callback(in_data, frame_count, time_info, status):
    if G.tc_running:
        int_values = G.tcObj.bytes2ints(in_data[G.tc_channel::G.tc_max_channels])
        G.tcObj.process_line_code(int_values,to_console=False)
        #process_tc_thread()
    
    return (in_data, pyaudio.paContinue)

# SERIAL
def read_from_serial():
    
    if G.serialPort.is_open:
        if not G.serialPort.running:
            G.serialPort.start()
        while G.serialPort.running:
            G.serialPort.serial_obj.timeout = None
            try:
                serial_msg = G.serialPort.serial_obj.read().decode('utf-8')
                print_debug(f"Serial Msg: {serial_msg}")
                if serial_msg.isdigit():
                    set_current_cam(int(serial_msg))
            except Exception as e:
                print_error(e)
                G.serialPort.stop()
                G.serialPort.close_port()
                break
            
            time.sleep(0.001)
    
def write_to_serial(number,msg:str='C'):
    if G.serialPort.is_open:
        bytes2write = bytearray(msg+str(number),'utf-8')
        #print(bytes2write,number)
        G.serialPort.serial_obj.write(bytes2write)
