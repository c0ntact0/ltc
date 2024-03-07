import scipy as sp
from scipy.io import wavfile
import matplotlib.pyplot as plt
import numpy as np
from tc import Tc
import os

if __name__ == "__main__":   
    
    print_wave=1
    if os.name == 'nt':
        #sample_rate,data = wavfile.read('D:\LTC_PROJECT\LTC_01000000_1mins_30fps_48000x24.wav')
        sample_rate,data = wavfile.read('D:\LTC_PROJECT\input_test.wav')

    else:
        #sample_rate,data = wavfile.read('/Users/rui/LTC_PROJECT/LTC_01000000_10mins_25fps_44100x24.wav')
        #sample_rate,data = wavfile.read('/Users/rui/LTC_PROJECT/LTC_01000000_1mins_25fps_48000x24.wav')
        #sample_rate,data = wavfile.read('/Users/rui/LTC_PROJECT/LTC_01000000_1mins_30fps_48000x24.wav')
        sample_rate,data = wavfile.read('/Users/rui/LTC_PROJECT/input_test_8bits.wav')
    
    fps=25
    print(f"Sample Rate = {sample_rate}")
    length = data.shape[0]/sample_rate
    print(f"length = {length}s")
    start=0
    n_samples = None
    #t = np.linspace(.0,length,data.shape[0])
    #plt.plot(t[start:start+n_samples],data[start:start+n_samples])
    #plt.show()

    if print_wave:
        s = np.arange(0,data.shape[0])
        plt.plot(s[start:n_samples],data[start:n_samples])
        plt.grid()
        plt.show()
    tcObj = Tc(sample_rate,fps,start,n_samples)
    tcObj.process_line_code(data)
    exit(0)
    CHUCK=960
    for pointer in range(0,len(data[start:n_samples]),CHUCK):
        
        tcObj.process_line_code(data[pointer:pointer+CHUCK])

