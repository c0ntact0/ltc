"""
    Can be used to list the devices and test the input.
    Blocking flavor
"""
import pyaudio  
import wave
from pprint import pprint
from tc import Tc

p = pyaudio.PyAudio()
devices = p.get_device_count()

print('Devices:',devices)

for i in range(devices):
    device_info = p.get_device_info_by_index(i)
    if device_info.get('maxInputChannels') > 0:
      pprint(device_info)

try:
    input_device_index = int(input("Please choose a index: "))
except Exception:
    print("Some error occurred.")
    exit()
    
device_info = p.get_device_info_by_index(1)
pprint(device_info)
RATE = int(device_info.get('defaultSampleRate'))
CHUNK=1024
RECORD_SECONDS=5
WAVE_OUTPUT_FILE='D:\LTC_PROJECT\input_test_8bits.wav'
FORMAT=pyaudio.paInt24
CHANNELS=1
tcObj = Tc(RATE,25) #TODO: ver como lidar com os samples
stream = p.open(format=FORMAT,input=True,input_device_index=input_device_index,rate=RATE,channels=CHANNELS,frames_per_buffer=CHUNK)
print ("recording...")
frames = []
  
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    int_values = tcObj.bytes2ints(data)
    #print(int_values)
    tcObj.process_line_code(int_values)
    frames.append(data)
print ("finished recording")
  
  
# stop Recording
stream.stop_stream()
stream.close()
p.terminate()

# comment this exit to write the wav to a file
exit()
waveFile = wave.open(WAVE_OUTPUT_FILE, 'wb')
waveFile.setnchannels(CHANNELS)
waveFile.setsampwidth(p.get_sample_size(FORMAT))
waveFile.setframerate(RATE)
waveFile.writeframes(b''.join(frames))
waveFile.close()