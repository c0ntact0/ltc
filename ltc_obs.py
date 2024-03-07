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

log_level = obs.LOG_DEBUG
audio = pyaudio.PyAudio()
tcObj = None
edlObj = None
tc_stream = None
tc_running = False
current_tc = (0,0,0,0)
clip_tc="00:00:00:00"
timeline_start = 0
current_timeline_frame = 0
audio_device = {}
fps=24
source_display=None
sources_cams = []
previous_cam = None
current_cam = None
edl_path = os.path.expanduser("~")
display_timeline_tc=False
format=".mxf"

sources_handlers = []

lock = threading.Lock()

# OBS CALLBACKS
def audio_device_changed(props,p,settings):
    #global audio_device
    audio_device = get_audio_device_from_properties(settings)
    p = obs.obs_properties_get(props,'info')
    if len(audio_device):
        info = "Sample Rate: " + str(int(audio_device.get('defaultSampleRate')))
    else:
        info = "No info available"
    #obs.obs_property_set_description(p,info)
    obs.obs_data_set_string(settings,'info',info)
    return True

def timeline_start_changed(props,p,settings):
    p = obs.obs_properties_get(props,'timeline_start_info')
    timeline_start = tc.string2tc(obs.obs_data_get_string(settings,'timeline_start'),fps)
    if timeline_start:
        print("OK")
        obs.obs_property_text_set_info_type(p,obs.OBS_TEXT_INFO_NORMAL)
    else:
        print("Error")
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
    global edl_path
    print("script_properties")
    props = obs.obs_properties_create()
    obs.obs_properties_add_button(props,'button_record_control',"Start Recording",lambda props,prop: True if record_control(props,prop) else True)
    obs.obs_properties_add_button(props,"button_run_tc","Start LTC capture",lambda props,prop: True if run_tc(props,prop) else True)

    list_devices = obs.obs_properties_add_list(props,"audio_device","Device name",obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_devices_names(list_devices)
    
    obs.obs_properties_add_button(props, "button_refresh_devices", "Refresh list of devices",
    lambda props,prop: True if populate_list_property_with_devices_names(list_devices) else True)

    obs.obs_properties_add_text(props, "info", "", obs.OBS_TEXT_INFO)

    list_fps = obs.obs_properties_add_list(props,'fps',"FPS", obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_INT)
    populate_list_property_with_fps(list_fps)

    list_sources_display = obs.obs_properties_add_list(props,'source_display',"TC display source", obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
    populate_list_property_with_display_sources(list_sources_display)
    obs.obs_properties_add_bool(props,'display_tmeline_tc',"Use Timeline TC")
    
    obs.obs_properties_add_editable_list(props,'sources_cams',"Cut Sources",obs.OBS_EDITABLE_LIST_TYPE_STRINGS,"","")

    timeline_start = obs.obs_properties_add_text(props,'timeline_start',"Timeline Start Hour",obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props,'timeline_start_info',"",obs.OBS_TEXT_INFO)

    obs.obs_properties_add_path(props,'edl_path','EDL export folder',obs.OBS_PATH_DIRECTORY,"",edl_path)


    # CALLBACKS
    obs.obs_property_set_modified_callback(list_devices, audio_device_changed)
    obs.obs_property_set_modified_callback(timeline_start, timeline_start_changed)
   
    return props

def script_defaults(settings):

    obs.obs_data_set_default_string(settings, "audio_device", "")
    obs.obs_data_set_default_string(settings, "info", "")
    sources = obs.obs_enum_sources()
    sources_names = [obs.obs_source_get_name(source) for source in sources]
    sources_t = list_to_array_t(sources_names)
    obs.source_list_release(sources)
    obs.obs_data_set_default_array(settings, "sources_cams", sources_t)
    obs.obs_data_set_default_int(settings,'fps',24)
    obs.obs_data_set_default_string(settings, "source_display", "")
    obs.obs_data_set_default_bool(settings,'display_tmeline_tc',False)
    obs.obs_data_set_default_string(settings,'timeline_start',"00:00:00:00")
    obs.obs_data_set_default_string(settings,'timeline_start_info',"TC format: hh:mm:ss:ff")
    obs.obs_data_set_default_string(settings,'edl_path',os.path.expanduser("~"))


def script_update(settings):
    global audio_device,fps,source_display,sources_cams,timeline_start,edl_path,current_cam,display_timeline_tc
    audio_device = get_audio_device_from_properties(settings)
    fps = obs.obs_data_get_int(settings,'fps')
    source_display = obs.obs_data_get_string(settings,'source_display')
    display_timeline_tc = obs.obs_data_get_bool(settings,'display_tmeline_tc')
    sources_cams = array_t_to_list(obs.obs_data_get_array(settings,"sources_cams"))
    add_souces_handlers()

    timeline_start = tc.string2tc(obs.obs_data_get_string(settings,'timeline_start'),fps)
    if timeline_start:
        timeline_start = tc.tc2frames(timeline_start,fps)
        obs.obs_data_set_string(settings,'timeline_start_info',"TC format: hh:mm:ss:ff")
    else:
        timeline_start = 0
        obs.obs_data_set_string(settings,'timeline_start_info',"Format error, must be: hh:mm:ss:ff")
    edl_path = obs.obs_data_get_string(settings,'edl_path')
    current_cam = get_current_cam_name()
    print(obs.obs_frontend_get_current_profile())


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
    #global edlObj,tc_running,tcObj,timeline_start,current_timeline_frame,edl_path,fps
    global current_cam
    source = obs.calldata_source(calldata,"source")
    current_cam = obs.obs_source_get_name(source)

def script_tick(seconds):
    process_tc(lock)

def script_load(settings):
    obs.obs_frontend_add_event_callback(on_frontend_event)


def script_unload():
    global tc_running,tc_stream,tcObj,audio
    if tc_running:
        tc_stream.close()
        tcObj = None
    if audio:
        audio.terminate()

def on_frontend_event(e):
    global edlObj,current_timeline_frame,timeline_start, fps,tcObj

    if e == obs.OBS_FRONTEND_EVENT_RECORDING_STARTING:
        print("Recording Starting...")
        edlObj = Edl()
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
    obs.source_list_release(audio_devices)

def populate_list_property_with_fps(list_property):
    fps_list = [24,25,30]
    obs.obs_property_list_clear(list_property)
    for rate in fps_list:
        obs.obs_property_list_add_int(list_property,str(rate),rate)
    obs.source_list_release(fps_list)

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

def populate_list_property_with_sources(list_property):
    sources = obs.obs_enum_sources()
    obs.obs_property_list_clear(list_property)
    obs.obs_property_list_add_string(list_property, "", "")
    for source in sources:
        name = obs.obs_source_get_name(source)
        obs.obs_property_list_add_string(list_property, name, to_data_t(name))
    obs.source_list_release(sources)

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
    global sources_cams
           
    for cam in sources_cams:
        source = obs.obs_get_source_by_name(cam)
        if obs.obs_source_active(source):
            obs.obs_source_release(source)
            return cam
        obs.obs_source_release(source)


    return None

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

def apply_ffmpeg_rewrap(reel:str):
    config = obs.obs_frontend_get_profile_config()
    #print(obs.config_get_string(config, "Output", "FilenameFormatting") or "")
    video_path = obs.config_get_string(config, "AdvOut", "RecFilePath") or None
    video_filename = os.path.join(video_path,reel + format)
    video_filename_renamed = os.path.join(video_path,reel + "_old" + format)
    os.rename(video_filename,video_filename_renamed)
    time.sleep(0.5)
    (
        ffmpeg.input(video_filename_renamed)
        .output(video_filename,c='copy',timecode=clip_tc,
                movflags='use_metadata_flags',map_metadata=0,metadata='"Reel='+reel+'"'
                ).run()
    )
    os.remove(video_filename_renamed)
    pprint(ffmpeg.probe(video_filename))
    
    print("Rewrap applied")
    
def process_tc(lock):
    global current_tc,previous_cam,current_cam,timeline_start, current_timeline_frame,fps,edlObj,edl_path,display_timeline_tc,clip_tc
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
                    current_cam = get_current_cam_name()
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
                    if recording and edlObj.cut_counter == 0: #not edlObj:
                    #    #current_timeline_frame = timeline_start
                    #    edlObj = Edl()
                    #    config = obs.obs_frontend_get_profile_config()
                    #    obs.config_set_string(config, "Output","FilenameFormatting", "teste" + edlObj.date_string)
                         clip_tc = current_tc_string
                         #edlObj.add_cut_in(current_cam,current_cam,current_tc_string,timeline_tc_string)
                         edlObj.add_cut_in(current_cam,current_cam,current_tc_string,current_tc_string)
                    #    #pprint(edlObj.edl)
                    elif new_cam and recording and edlObj.cut_counter > 0:
                        #edlObj.add_cut_out(mark_tc_string,mark_timeline_tc_string)
                        #edlObj.add_cut_in(current_cam,current_cam,mark_tc_string,mark_timeline_tc_string)
                        edlObj.add_cut_out(mark_tc_string,mark_tc_string)
                        edlObj.add_cut_in(current_cam,current_cam,mark_tc_string,mark_tc_string)
                        #pprint(edlObj.edl)
                    elif not new_cam and not recording and edlObj.cut_counter > 0:
                        reel = edlObj.date_string
                        #edlObj.add_cut_out(mark_tc_string,mark_timeline_tc_string)
                        edlObj.add_cut_out(mark_tc_string,mark_tc_string)
                        edlObj.save_avid_edl(edl_path)
                        edlObj = None
                        t = threading.Thread(target=apply_ffmpeg_rewrap,args=(reel,))
                        t.start()
                        print("Last cut")
                        #pprint(edlObj.edl)
                    else:
                        pass
                

            if recording:
                current_timeline_frame+=1

def tc_stream_callback(in_data, frame_count, time_info, status):
    int_values = tcObj.bytes2ints(in_data)
    tcObj.process_line_code(int_values)
    
    #process_tc(lock)
    
    return (in_data, pyaudio.paContinue)

