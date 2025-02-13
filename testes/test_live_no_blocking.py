import pyaudio  
import wave
from pprint import pprint
from tc import Tc

def callback(in_data, frame_count, time_info, status):
    int_values = tcObj.bytes2ints(in_data)
    tcObj.process_line_code(int_values)
    print(tcObj.currentTcString)

    return (in_data, pyaudio.paContinue) 

p = pyaudio.PyAudio()
devices = p.get_device_count()

print('Devices:',devices)

input_devices = 0
for i in range(devices):
    device_info = p.get_device_info_by_index(i)
    if device_info.get('maxInputChannels') > 0:
      pprint(device_info)
      input_devices+=1

print('Input Devices:',input_devices)


device_info = p.get_device_info_by_index(1)


pprint(device_info)
RATE = int(device_info.get('defaultSampleRate'))
CHUNK=32*24

RECORD_SECONDS=5
WAVE_OUTPUT_FILE='D:\LTC_PROJECT\input_test_8bits.wav'
FORMAT=pyaudio.paInt24
CHANNELS=1
tcObj = Tc(RATE,25) #TODO: ver como lidar com os samples
stream = p.open(format=FORMAT,input=True,input_device_index=1,rate=RATE,channels=CHANNELS,frames_per_buffer=CHUNK,stream_callback=callback)
print ("recording...")

sair = input()
print ("finished recording")
  
  
# stop Recording
stream.close()
p.terminate()

exit()
waveFile = wave.open(WAVE_OUTPUT_FILE, 'wb')
waveFile.setnchannels(CHANNELS)
waveFile.setsampwidth(p.get_sample_size(FORMAT))
waveFile.setframerate(RATE)
waveFile.writeframes(b''.join(frames))
waveFile.close()