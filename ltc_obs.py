import obspython as obs
import math,time,os,time
from pprint import pprint
import pyaudio
import tc
from tc import Tc
import json
from edl_manager import Edl
import threading
import ffmpeg
from serial_com import SerialPort

log_level = obs.LOG_DEBUG
audio = pyaudio.PyAudio()
tcObj = None

edlObj = None
serialPort = SerialPort()
tc_stream = None
tc_running = False
current_tc = (0,0,0,0)
clip_tc="00:00:00:00" # clip (file) start TC. 
timeline_start = 0 # timeline TC start frame
current_timeline_frame = 0
audio_device = {} # current pyaudio device dict
fps=24 # TC frame rate
source_display=None # OBS source to display the TC
sources_cams = [] # OBS sources used as cam channels
source_playout= None # OBS source used for playout
previous_cam = None # previous visible (selected) camera
current_cam = None
edl_path = os.path.expanduser("~") # path to write the EDL files
display_timeline_tc=False # Use the timeline TC insted of LTC 
current_video_file=None # last video file recorded
clipname = None

sources_handlers = [] # handlers to signal the cam souces visibility

lock = threading.Lock() # lock for the LTC process thread

hotkeys_num = 5
hotkey_ids = []


# OBS CALLBACKS
def audio_device_changed(props,p,settings):
    #global audio_device
    audio_device = get_audio_device_from_properties(settings)
    p = obs.obs_properties_get(props,'info')
    if len(audio_device):
        info = "Sample Rate: " + str(int(audio_device.get('defaultSampleRate')))
    else:
        info = "No info available"
    obs.obs_data_set_string(settings,'info',info)
    return True

def timeline_start_changed(props,p,settings):
    p = obs.obs_properties_get(props,'timeline_start_info')
    timeline_start = tc.string2tc(obs.obs_data_get_string(settings,'timeline_start'),fps)
    if timeline_start:
        #print("OK")
        obs.obs_property_text_set_info_type(p,obs.OBS_TEXT_INFO_NORMAL)
    else:
        #print("Error")
        obs.obs_property_text_set_info_type(p,obs.OBS_TEXT_INFO_ERROR)

    return True

def recording_changed(props,p,*args, **kwargs):
    print("recording_changed")
    recording = obs.obs_frontend_recording_active()
    button_run_tc = obs.obs_properties_get(props,'button_run_tc')
    #obs.obs_property_set_description(rec_bt,("Stop Recording" if recording else "Start Recording"))
    obs.obs_property_set_description(button_run_tc,"Changed")

    return True



# OBS FUNCTIONS
def script_description():
    return """- Configure all settings
- Press "Start LTC capture" to capture the external LTC
- Press "Start Recording" to start the recorder and external LTC capture.
    """
def script_properties():
    global edl_path,serialPort
    print("script_properties")
    props = obs.obs_properties_create()
    operation_group = obs.obs_properties_create()
    config_group = obs.obs_properties_create()
    serial_group = obs.obs_properties_create()

    obs.obs_properties_add_group(props,'operation_group',"Operation",obs.OBS_GROUP_NORMAL,operation_group)
    obs.obs_properties_add_group(props,'config_group',"Configuration",obs.OBS_GROUP_NORMAL,config_group)
    obs.obs_properties_add_group(props,'serial_group',"Serial Port",obs.OBS_GROUP_NORMAL,serial_group)

    obs.obs_properties_add_button(operation_group,'button_record_control',"Start Recording",lambda props,prop: True if record_control(props,prop) else True)
    clipname = obs.obs_properties_add_text(operation_group,'clipname',"Clipname",obs.OBS_TEXT_DEFAULT)

    obs.obs_properties_add_button(config_group,"button_run_tc","Start LTC capture",lambda props,prop: True if run_tc(props,prop) else True)

    list_devices = obs.obs_properties_add_list(config_group,"audio_device","Device name",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_devices_names(list_devices)
    
    obs.obs_properties_add_button(config_group, "button_refresh_devices", "Refresh list of devices",
    lambda props,prop: True if populate_list_property_with_devices_names(list_devices) else True)

    obs.obs_properties_add_text(config_group, "info", "", obs.OBS_TEXT_INFO)

    list_fps = obs.obs_properties_add_list(config_group,'fps',"FPS", obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_INT)
    populate_list_property_with_fps(list_fps)

    list_sources_display = obs.obs_properties_add_list(config_group,'source_display',"TC display source", obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_display_sources(list_sources_display)

    display_tmeline_tc = obs.obs_properties_add_bool(config_group,'display_tmeline_tc',"Use Timeline TC")
    obs.obs_property_set_long_description(display_tmeline_tc,"Use timeline TC when recording. Display the TC when recording only.")
    timeline_start = obs.obs_properties_add_text(config_group,'timeline_start',"Timeline Start TC",obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(config_group,'timeline_start_info',"",obs.OBS_TEXT_INFO)
    
    obs.obs_properties_add_editable_list(config_group,'sources_cams',"Cut Sources",obs.OBS_EDITABLE_LIST_TYPE_STRINGS,"","")

    list_source_playout = obs.obs_properties_add_list(config_group,'source_playout',"Source for Playout",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_sources(list_source_playout,'ffmpeg_source')


    obs.obs_properties_add_path(config_group,'edl_path','EDL export folder',obs.OBS_PATH_DIRECTORY,"",edl_path)

    dock_state = obs.obs_properties_add_bool(config_group,'dock_state',"Apply Dock State")
    obs.obs_property_set_long_description(dock_state,'Only "Scenes","Sources" and "Audio Mixer" docks are loaded at startup.')

    list_serial_port = obs.obs_properties_add_list(serial_group,'serial_port',"Serial Ports",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_serial_ports(list_serial_port)

    # CALLBACKS
    obs.obs_property_set_modified_callback(list_devices, audio_device_changed)
    obs.obs_property_set_modified_callback(timeline_start, timeline_start_changed)
   
   # This must be here because we need the Cut Sources values to get the current cam number
    if serialPort.is_open:
        _,cam_number = get_current_cam_name()
        write_to_serial(cam_number)
        write_to_serial(len(sources_cams),'N')


    return props

def script_defaults(settings):
    print("script_defaults")

    obs.obs_data_set_default_string(settings, "audio_device", "")
    obs.obs_data_set_default_string(settings, "info", "")
    obs.obs_data_set_default_string(settings, "clipname", "")
    sources = obs.obs_enum_sources()
    sources_names = [obs.obs_source_get_name(source) for source in sources]
    sources_t = list_to_array_t(sources_names)
    obs.source_list_release(sources)
    obs.obs_data_set_default_array(settings, "sources_cams", sources_t)
    obs.obs_data_set_default_int(settings,'fps',24)
    obs.obs_data_set_default_string(settings, "source_display", "")
    obs.obs_data_set_default_string(settings, "source_playout", "")
    obs.obs_data_set_default_bool(settings,'display_tmeline_tc',False)
    obs.obs_data_set_default_string(settings,'timeline_start',"00:00:00:00")
    obs.obs_data_set_default_string(settings,'timeline_start_info',"TC format: hh:mm:ss:ff")
    obs.obs_data_set_default_string(settings,'edl_path',os.path.expanduser("~"))
    obs.obs_data_set_default_bool(settings,'dock_state',True)
    obs.obs_data_set_default_string(settings,'serial_port',"")
    


def script_update(settings):
    global audio_device,fps,source_display,sources_cams,source_playout,timeline_start,edl_path,current_cam,display_timeline_tc,clipname,hotkey_ids
    print("script_update")
    clipname = obs.obs_data_get_string(settings,'clipname')
    audio_device = get_audio_device_from_properties(settings)
    fps = obs.obs_data_get_int(settings,'fps')
    source_display = obs.obs_data_get_string(settings,'source_display')
    source_playout = obs.obs_data_get_string(settings,'source_playout')
    display_timeline_tc = obs.obs_data_get_bool(settings,'display_tmeline_tc')
    sources_cams = array_t_to_list(obs.obs_data_get_array(settings,"sources_cams"))
    add_souces_handlers()
    
    
    register_hot_keys(settings)
    print(hotkey_ids)

    timeline_start = tc.string2tc(obs.obs_data_get_string(settings,'timeline_start'),fps)
    if timeline_start:
        timeline_start = tc.tc2frames(timeline_start,fps)
        obs.obs_data_set_string(settings,'timeline_start_info',"TC format: hh:mm:ss:ff")
    else:
        timeline_start = 0
        obs.obs_data_set_string(settings,'timeline_start_info',"Format error, must be: hh:mm:ss:ff")
    edl_path = obs.obs_data_get_string(settings,'edl_path')
    current_cam,cam_number = get_current_cam_name()
    if not serialPort.is_open:
        serialPort.inicialize_port(obs.obs_data_get_string(settings,'serial_port'))

        if serialPort.is_open:
            t = threading.Thread(target=read_from_serial)
            t.start()

    print("Current Profile:",obs.obs_frontend_get_current_profile())


def script_tick(seconds):
    process_tc(lock)

def script_load(settings):
    global serialPort
    print("script_load")
    if obs.obs_data_get_bool(settings,'dock_state'):
        config = obs.obs_frontend_get_global_config()
        obs.config_set_string(config,"BasicWindow","DockState","AAAA/wAAAAD9AAAAAQAAAAMAAAQAAAABAfwBAAAABvsAAAAUAHMAYwBlAG4AZQBzAEQAbwBjAGsBAAAAAAAAASwAAACgAP////sAAAAWAHMAbwB1AHIAYwBlAHMARABvAGMAawEAAAEwAAABLAAAAKAA////+wAAABIAbQBpAHgAZQByAEQAbwBjAGsBAAACYAAAAaAAAADeAP////sAAAAeAHQAcgBhAG4AcwBpAHQAaQBvAG4AcwBEAG8AYwBrAAAAAx4AAADiAAAAnAD////7AAAAGABjAG8AbgB0AHIAbwBsAHMARABvAGMAawAAAALKAAABNgAAAJ4A////+wAAABIAcwB0AGEAdABzAEQAbwBjAGsCAAACYgAAAdcAAAK8AAAAyAAABAAAAAFLAAAABAAAAAQAAAAIAAAACPwAAAAA")

    obs.obs_frontend_add_event_callback(on_frontend_event)



def script_unload():
    global tc_running,tc_stream,tcObj,edlObj,audio,serialPort
    print("script_unload")
    del tcObj
    del edlObj
    if tc_running:
        tc_stream.close()

    if audio:
        audio.terminate()

    if serialPort.is_open:
        serialPort.stop()
        serialPort.close_port()

def script_save(settings):
    save_hotkeys(settings)
    

# HOT_KEYS
def register_hot_keys(settings):
    global hotkey_ids
    for i in range(len(hotkey_ids)):
        current_hotkey_id = i+1        
        f_name = "hotkey_id_"+ str(current_hotkey_id) + "_callback"
        obs.obs_hotkey_unregister(f_name)
            
    
    hotkey_ids = [obs.OBS_INVALID_HOTKEY_ID for i in range(len(sources_cams))]
    for i in range(len(hotkey_ids)):
        description = "Select CAM" + str(i+1)
        current_hotkey_id = i+1        
        #hotkey_ids[i] = obs.obs_hotkey_register_frontend(script_path(),description,eval("hotkey_id_" + str(i+1) + "_callback"))
        f_name = "hotkey_id_"+ str(current_hotkey_id) + "_callback"
        code = "def " +  f_name +"(pressed):\n    if pressed:\n        set_current_cam("+ str(current_hotkey_id) +")\n        write_to_serial(" + str(current_hotkey_id) + ")"
        x = compile(code,'callback','exec')
        exec(x)
        hotkey_ids[i] = obs.obs_hotkey_register_frontend(script_path(),description, eval(f_name))
        hotkey_save_array = obs.obs_data_get_array(settings, "hotkey_" + str(i))
        obs.obs_hotkey_load(hotkey_ids[i], hotkey_save_array)
        obs.obs_data_array_release(hotkey_save_array)

def save_hotkeys(settings):
    for i in range(len(hotkey_ids)):
        hotkey_save_array = obs.obs_hotkey_save(hotkey_ids[i])
        obs.obs_data_set_array(settings, "hotkey_" + str(i), hotkey_save_array)
        obs.obs_data_array_release(hotkey_save_array)

# SOURCES HANDLERS AND CALLBACKS
def add_souces_handlers():
    global sources_handlers,sources_cams
    print("Configuring source handlers")

    for h in sources_handlers:
        obs.signal_handler_disconnect(h,"show",sources_callback)
    
    sources_handlers.clear()

    for cam in sources_cams:
        source = obs.obs_get_source_by_name(cam)
        sh = obs.obs_source_get_signal_handler(source)
        obs.signal_handler_connect(sh,"show",sources_callback)
        sources_handlers.append(sh)
        #obs.obs_source_release(source)

def sources_callback(calldata):
    global current_cam
    source = obs.calldata_source(calldata,"source")
    current_cam = obs.obs_source_get_name(source)


def on_frontend_event(e):
    global edlObj,current_timeline_frame,timeline_start, fps,tcObj

    if e == obs.OBS_FRONTEND_EVENT_RECORDING_STARTING:
        print("Recording Starting...")
        edlObj = Edl(clipname)
        config = obs.obs_frontend_get_profile_config()
        obs.config_set_string(config, "Output","FilenameFormatting", edlObj.date_string)
        #edlObj.add_cut_in(current_cam,current_cam,mark_tc_string,mark_timeline_tc_string)
    elif e == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        print("Recording Started...")
        #obs.obs_properties_apply_settings(props,settings_g)
        
    elif e == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("Recording Stopped.")

def record_control(probs,bt_rec):
    global current_timeline_frame,timeline_start, fps,tcObj
    recording = obs.obs_frontend_recording_active()
    bt_rec = obs.obs_properties_get(probs,'button_record_control')
    bt_tc = obs.obs_properties_get(probs,'button_run_tc')
    if recording:
        obs.obs_property_set_description(bt_rec,'Start Recording')
        obs.obs_frontend_recording_stop()
        obs.obs_property_set_enabled(bt_tc,True)

    else:
        set_current_scene("RECORD") #TODO: escolher no script
        if not tc_running:
            run_tc(probs,bt_rec)
            time.sleep(1)
        current_timeline_frame = timeline_start
        current_tc_string = tc.tc2String(tc.frames2tc(current_timeline_frame,fps)) if display_timeline_tc else tcObj.currentTcString
        process_tc_display(current_tc_string)
        obs.obs_property_set_description(bt_rec,'Stop Recording')
        obs.obs_frontend_recording_start()
        obs.obs_property_set_enabled(bt_tc,False)

################## OBS USER FUNCTIONS
def get_audio_device_from_properties(settings):
    index_string = obs.obs_data_get_string(settings,"audio_device")
    index_exists = len(index_string) > 0
    #print(index_exists)
    index = -1 if not index_exists else int(index_string)
    return {} if not index_exists else audio.get_device_info_by_index(index)

def populate_list_property_with_devices_names(list_property):
    audio_devices = get_audio_devices(audio)
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for device in audio_devices:
      obs.obs_property_list_add_string(list_property, device.get('name'), str(device.get('index')))
    #obs.source_list_release(audio_devices)

def populate_list_property_with_fps(list_property):
    fps_list = [24,25,30]
    obs.obs_property_list_clear(list_property)
    for rate in fps_list:
        obs.obs_property_list_add_int(list_property,str(rate),rate)
    #obs.source_list_release(fps_list)

def populate_list_property_with_display_sources(list_property):
    sources = obs.obs_enum_sources()
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for source in sources:
        source_id = obs.obs_source_get_unversioned_id(source)
        if source_id == "text_gdiplus" or source_id == "text_ft2_source":
            name = obs.obs_source_get_name(source)
            obs.obs_property_list_add_string(list_property, name, name)
    obs.source_list_release(sources)

def populate_list_property_with_sources(list_property,types:list=None, show_type:bool=False):
    sources = obs.obs_enum_sources()
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for source in sources:
        source_id = obs.obs_source_get_unversioned_id(source)
        if (types and source_id in types) or not types:
            name = obs.obs_source_get_name(source)
            display_name = name
            #print(name,source_id)
            if show_type:
                display_name+=" [" + source_id + "]"
            obs.obs_property_list_add_string(list_property, display_name, name)
    obs.source_list_release(sources)

def populate_list_property_with_serial_ports(list_property):
    serial_ports = serialPort.get_serial_ports()
    obs.obs_property_list_clear(list_property)
    for port,desc,hwid in serial_ports:
        obs.obs_property_list_add_string(list_property,desc,port)

def get_sceneitem_from_source_name_in_current_scene(name):
	result_sceneitem = None
	current_scene_as_source = obs.obs_frontend_get_current_scene()
	if current_scene_as_source:
		current_scene = obs.obs_scene_from_source(current_scene_as_source)
		result_sceneitem = obs.obs_scene_find_source_recursive(current_scene, name)
		obs.obs_source_release(current_scene_as_source)
	
	return result_sceneitem

def get_source_by_name(name:str):
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
    global sources_cams
           
    for i in range(len(sources_cams)):
        source = obs.obs_get_source_by_name(sources_cams[i])
        if obs.obs_source_active(source):
            obs.obs_source_release(source)
            return sources_cams[i],i+1
        obs.obs_source_release(source)

    return None,0

def set_current_cam(cam_number:int):
    """
    cam_number is a number from 1 to max number of cameras
    """
    global sources_cams

    idx = cam_number-1
    if idx < 0:
        return
    
    for i in range(len(sources_cams)):
        #print(sources_cams[i])
        current_scene_as_source = obs.obs_frontend_get_current_scene()
        if current_scene_as_source:
            current_scene = obs.obs_scene_from_source(current_scene_as_source)
            scene_item = obs.obs_scene_find_source_recursive(current_scene, sources_cams[i])
            if scene_item:
                obs.obs_sceneitem_set_visible(scene_item,i == idx)
                obs.obs_source_release(current_scene_as_source)

def set_current_scene(scene_name):
        scenes = obs.obs_frontend_get_scenes()
        for scene in scenes:
            name = obs.obs_source_get_name(scene)
            if name == scene_name:
                obs.obs_frontend_set_current_scene(scene)
        obs.source_list_release(scenes)

# OBS UTIL FUNCTIONS
def from_data_t(data_t):
    j = obs.obs_data_get_json(data_t)
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
    data_t_list = [obs.obs_data_array_item(array_t, i) for i in range(length)]
    return [from_data_t(data_t) for data_t in data_t_list]

def list_to_array_t(values:list):
    data_t_list = [to_data_t(value) for value in values]
    array_t = obs.obs_data_array_create()
    for data_t in data_t_list:
        obs.obs_data_array_push_back(array_t, data_t)
    return array_t

# PYAUDIO FUNCTIONS
        
def get_audio_devices(audio:pyaudio) -> list:
    
    devices = []
    devices_num = audio.get_device_count()
    for i in range(devices_num):
        device_info = audio.get_device_info_by_index(i)
        if device_info.get('maxInputChannels') > 0:
            devices.append(device_info)
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



def run_tc(props,p):
    global audio_device, tc_stream, tc_running,tcObj
    p = obs.obs_properties_get(props,'button_run_tc')
    if tc_running:
        obs.obs_property_set_description(p,'Start LTC capture')
        if tc_stream:
            tc_stream.close()
            tcObj = None
        tc_running=False
        print("TC Capture Stopped...")

    else:
        #pprint(audio_device)
        FORMAT=pyaudio.paInt24
        CHANNELS=1
        SAMPLE_RATE = int(audio_device.get('defaultSampleRate'))
        CHUNK=32*24
        obs.obs_property_set_description(p,'Stop LTC capture')
        tcObj = Tc(SAMPLE_RATE,fps)
        tc_stream = audio.open(format=FORMAT,input=True,input_device_index=1,rate=SAMPLE_RATE,channels=CHANNELS,frames_per_buffer=CHUNK,stream_callback=tc_stream_callback)
        tc_running=True
        print("TC Capture Running...")

def process_tc_display(tc_string):
    global source_display,current_cam
    source_txt = obs.obs_get_source_by_name(source_display)
    if source_txt:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", tc_string)
        obs.obs_source_update(source_txt, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source_txt)

def set_playout_source(filename:str):
    global source_playout
    source = obs.obs_get_source_by_name(source_playout)
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
    global current_video_file
    config = obs.obs_frontend_get_profile_config()
    ff_extension = "." +  obs.config_get_string(config,"AdvOut","FFExtension")
    #print(obs.config_get_string(config, "Output", "FilenameFormatting") or "")
    video_path = obs.config_get_string(config, "AdvOut", "RecFilePath") or None
    video_filename = os.path.join(video_path,reel + ff_extension)
    video_filename_renamed = os.path.join(video_path,reel + "_old" + ff_extension)
    os.rename(video_filename,video_filename_renamed)
    time.sleep(0.5)
    (
        ffmpeg.input(video_filename_renamed)
        .output(video_filename,c='copy',
                timecode=clip_tc,
                movflags='use_metadata_tags',
                map_metadata=0,
                metadata='name='+reel
                ).run()
    )
    os.remove(video_filename_renamed)
    current_video_file=video_filename
    #pprint(ffmpeg.probe(video_filename))
    
    print("Rewrap applied")

    set_playout_source(video_filename)

    
def process_tc(lock):
    global current_tc,previous_cam,current_cam,timeline_start, current_timeline_frame,fps,edlObj,edl_path,display_timeline_tc,clip_tc,clipname
    with lock:
        if tc_running:
            this_tc = current_tc
            current_tc = tcObj.currentTc
            recording = obs.obs_frontend_recording_active()
            if recording and not edlObj:
                print("We have a problem. OBS is recording but no edl object it's created.")
                return
            if this_tc != current_tc:
                if not current_cam:
                    current_cam,_ = get_current_cam_name()
                timeline_tc_string = tc.tc2String(tc.frames2tc(current_timeline_frame,fps)) # used in the first cut
                mark_timeline_tc_string = tc.tc2String(tc.frames2tc(current_timeline_frame - (1 if edlObj else 0),fps))
                
                current_tc_string = timeline_tc_string if display_timeline_tc else tc.tc2String(current_tc) # used in the first cut
                new_cam = current_cam != previous_cam
                if new_cam:
                    previous_cam = current_cam
                #this_cam = get_current_cam_name() if recording else None
                process_tc_display(current_tc_string)
                if display_timeline_tc:
                    mark_tc_string = mark_timeline_tc_string
                else:
                    mark_frames = tc.tc2frames(current_tc,fps)
                    mark_tc_string = tc.tc2String(tc.frames2tc(mark_frames - (1 if edlObj else 0),fps))
                if new_cam and edlObj:
                    print("MARK:",mark_tc_string,current_cam)
                #mark_tc_string = current_tc_string
                if edlObj:
                    file_reel = edlObj.date_string
                    if recording and edlObj.cut_counter == 0: #not edlObj:
                        clip_tc = current_tc_string
                        edlObj.add_cut_in(current_cam,file_reel,current_tc_string,current_tc_string)
                    elif new_cam and recording and edlObj.cut_counter > 0:
                        edlObj.add_cut_out(mark_tc_string,mark_tc_string)
                        edlObj.add_cut_in(current_cam,file_reel,mark_tc_string,mark_tc_string)
                    elif not new_cam and not recording and edlObj.cut_counter > 0:
                        edlObj.add_cut_out(mark_tc_string,mark_tc_string)
                        edlObj.save_avid_edl(edl_path,file_reel+'.edl',clipname)
                        edlObj = None
                        t = threading.Thread(target=apply_ffmpeg_rewrap,args=(file_reel,))
                        t.start()
                        print("Last cut")
                    else:
                        pass
                

            if recording:
                current_timeline_frame+=1

def tc_stream_callback(in_data, frame_count, time_info, status):
    int_values = tcObj.bytes2ints(in_data)
    tcObj.process_line_code(int_values)
    
    #process_tc(lock)
    
    return (in_data, pyaudio.paContinue)

# SERIAL
def read_from_serial():
    global serialPort
    if not serialPort.running:
        serialPort.start()
    while serialPort.running:
        serialPort.serial_obj.timeout = None
        serial_msg = serialPort.serial_obj.read().decode('utf-8')
        #print("Serial Msg:",serial_msg)
        if serial_msg.isdigit():
            set_current_cam(int(serial_msg))
    
def write_to_serial(number,msg:str='C'):
    global serialPort
    if serialPort.is_open:
        bytes2write = bytearray(msg+str(number),'utf-8')
        #print(bytes2write,number)
        serialPort.serial_obj.write(bytes2write)
