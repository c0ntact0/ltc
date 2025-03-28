LINE_UP = '\033[1A'

class Tc:
    def __init__(self,sample_rate:int,fps:int, start=0,n_samples=None) -> None:
        self._currentTc = (0,0,0,0)
        
        self._frame = ''
        self._s_count = 0
        self._sample_rate = sample_rate
        self._fps = fps
        self._first_sampler = True
        self._start=start
        self._n_samples=n_samples
        self._is_pair=False
        self._old_sign=0
        self._period=int(sample_rate/fps/80)
        self._half_period=int(self._period/2)
        self._period_drift=2
        # bits sequencies are little endian
        self.SYNC_WORD = '0011111111111101'
        self._number_0_9 = {
            '0000':0,
            '1000':1,
            '0100':2,
            '1100':3,
            '0010':4,
            '1010':5,
            '0110':6,
            '1110':7,
            '0001':8,
            '1001':9        }

        self._number_0_2 = {
            '00':0,
            '10':1,
            '01':2,
        }

        self._number_0_5 = {

            '000':0,
            '100':1,
            '010':2,
            '110':3,
            '001':4,
            '101':5
        }
        
        self._frames = [] # GPT
    
    def frame2dic(self,data_frame:str) -> dict:
        """Gets a LTC data frame and returns a dict with all the LTC data frame components.
        
        Parameters
        ----------
        data_frame: str
            a string with the binary data frame

        Returns
        -------
        A dict with the LTC components binary strings.
        """
        return {
            # TC
            'frames_units':data_frame[0:4],
            'frames_tens':data_frame[8:10],
            'seconds_units':data_frame[16:20],
            'seconds_tens':data_frame[24:27],
            'minutes_units':data_frame[32:36],
            'minutes_tens':data_frame[40:43],
            'hours_units':data_frame[48:52],
            'hours_tens':data_frame[56:58],
            # Flags
            'flag_drop_frame':data_frame[10],
            'flag_color_frame':data_frame[11],
            'flag_polarity_correction':data_frame[27],
            'flag_BGF0':data_frame[43],
            'flag_BGF1':data_frame[58],
            'flag_BGF3':data_frame[59],
            # User
            'user1':data_frame[4:8],
            'user2':data_frame[12:16],
            'user3':data_frame[20:24],
            'user4':data_frame[28:32],
            'user5':data_frame[36:40],
            'user6':data_frame[44:48],
            'user7':data_frame[52:56],
            'user8':data_frame[60:64],
        }
    
    @property
    def currentTc(self):
        return self._currentTc

    @property
    def currentTcString(self):
        return tc2String(self._currentTc)

    def bytes2ints(self,data:bytes,bits:int=24)-> list:
        """Get signed integers from a bytes array.

            Parameters
            ----------
            data: bytes
                list of bytes
            bits: int
                number of bits of the integers

            Returns
            -------
            A list with the signed integers.
        """
        int_values=[]
        n_bytes=int(bits/8)
        for i in range(0,len(data),n_bytes):
          int_values.append(int.from_bytes(data[i:i+n_bytes],'little',signed=True))

        return int_values
    
    def getTc(self,data_frame:str):
        """Get a data frame and convert to a tuple with the time code.

        Parameters
        ----------   
        data_frame: str
            The data frame.
        
        Returns
        -------
        A tuple (hour,minutes,seconds,frames)
        """
        frame_dic = self.frame2dic(data_frame)
        #hour = self._number_0_2.get(frame_dic['hours_tens'],self.wrong_key_callback())*10+self._number_0_9.get(frame_dic['hours_units'],self.wrong_key_callback())
        #minutes = self._number_0_5.get(frame_dic['minutes_tens'],self.wrong_key_callback())*10+self._number_0_9.get(frame_dic['minutes_units'],self.wrong_key_callback())
        #seconds = self._number_0_5.get(frame_dic['seconds_tens'],self.wrong_key_callback())*10+self._number_0_9.get(frame_dic['seconds_units'],self.wrong_key_callback())
        #frames = self._number_0_2.get(frame_dic['frames_tens'],self.wrong_key_callback())*10+self._number_0_9.get(frame_dic['frames_units'],self.wrong_key_callback())
        try:
            hour = self._number_0_2.get(frame_dic['hours_tens'])*10+self._number_0_9.get(frame_dic['hours_units'])
            minutes = self._number_0_5.get(frame_dic['minutes_tens'])*10+self._number_0_9.get(frame_dic['minutes_units'])
            seconds = self._number_0_5.get(frame_dic['seconds_tens'])*10+self._number_0_9.get(frame_dic['seconds_units'])
            frames = self._number_0_2.get(frame_dic['frames_tens'])*10+self._number_0_9.get(frame_dic['frames_units'])
        except Exception as e:
            #print(e)
            print("Something went wrong while reading time code from audio stream. Please try other channel.")
            return

        return (hour,minutes,seconds,frames)
    
    def process_line_code(self,data,to_console=False,to_console_fixed=False):
        """Process a data from the audio input.

        Parameters
        ----------
        to_console: bool, optional
            send the TC to the console (tests).
        fixed: bool, optional
            print to console without line linefeed (tests).
        """
        if not self._n_samples:
            self._n_samples = len(data)
        for sample in data[self._start:self._n_samples]:
            sign = number_sign(sample)
            if self._first_sampler:
                self._old_sign = sign
                self._first_sampler = False
            self._s_count+=1
            if sign != self._old_sign and sign != 0:
                if self._is_pair:
                    self._is_pair = False
                elif self._half_period-self._period_drift < self._s_count < self._half_period+self._period_drift:
                    self._frame+='1'
                    self._is_pair=True
                elif self._period-self._period_drift < self._s_count < self._period+self._period_drift:
                    self._frame+='0'
                self._s_count=0
            
            if self._frame.endswith(self.SYNC_WORD):
                
                if len(self._frame) == 80:
                    #previousTcFrame = tc2frames(self._currentTc,self._fps)
                    self._currentTc=self.getTc(self._frame)
                    #currentTcFrames = tc2frames(self._currentTc,self._fps)
                    #deltaFrames = currentTcFrames - previousTcFrame
                    #print(deltaFrames)
                    
                    if to_console or to_console_fixed: print(tc2String(self.getTc(self._frame)),(LINE_UP if to_console_fixed else ""))
                    
                    
                self._frame=''
            self._old_sign = sign

    def wrong_key_callback(self):
        
        print("WARNING: Invalid key error in LTC audio stream. This can compromise the LTC accuracy.")
        return 0

def number_sign(number):
    if number < 0: return -1
    elif number > 0:return 1

    return number 

def tc2String(tc:tuple):
    try:
        return str("{:02}".format(tc[0]) + ":" + "{:02}".format(tc[1]) + ":" + "{:02}".format(tc[2]) + ":" +"{:02}".format(tc[3]))
    except:
        return ""

def string2tc(tc:str,fps:int):

    """Converts a TC string in format hh:mm:ss:ff to a tuple of integers like (h,m,s,f)

    Parameters
    ----------
    tc: str
        string in format "hh:mm:ss:ff"
    fps: int
        frame rate
        
    Returns
    -------
    A tuple or None if tc is in the wrong format.
    """
    ret = None
    tc_list = tc.split(':')
    if len(tc_list) == 4 and len(tc_list[0]) == 2 and len(tc_list[1]) == 2 and len(tc_list[2]) == 2 and len(tc_list[3]) == 2:
        try:
            hours_tmp = int(tc_list[0])
            minutes_tmp = int(tc_list[1])
            seconds_tmp = int(tc_list[2])
            frames_tmp = int(tc_list[3])
            if 0 <= hours_tmp <= 24 and 0 <= minutes_tmp < 60 and 0 <= seconds_tmp < 60 and 0 <= frames_tmp < fps:
                ret = (hours_tmp,minutes_tmp,seconds_tmp,frames_tmp)
        except:
            pass

    return ret

def frames2tc(total_frames:int,fps:int):
    """Converts frames to TC.
    
    Parameters
    ----------
    total_frames: int
        total frames to convert.
    fps: int
        frame rate.

    Returns
    -------
    A tuple as (hours,minutes,seconds,frames).
    """
    try:
        hours = int(total_frames / (3600 * fps))
        minutes = int(total_frames / (60 * fps) % 60)
        seconds = int(total_frames / fps % 60)
        frames = int(total_frames % fps)
    except:
        return (0,0,0,0)
    
    return (hours,minutes,seconds,frames)

def tc2frames(tc:tuple,fps:int) -> int:
    """Converts TC to frames.
    
    Parameters
    ----------
    tc: tuple
        A tuple as (hours,minutes,seconds,frames).
    fps: int
        frame rate.

    Returns
    -------
    Total number o frames.
    """
    try:
        frames_seconds = tc[2] * fps
        frames_minutes = tc[1] * 60 * fps
        frames_hours = tc[0] * 60 * 60 * fps
    except:
        return 0
    
    return frames_hours + frames_minutes + frames_seconds + tc[3]

#print(frames2tc(1000021,25))
#print(tc2frames((11,6,40,21),25))