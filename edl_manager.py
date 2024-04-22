from datetime import datetime
import os
import json
from pprint import pprint

class Edl():

    def __init__(self,title=None) -> None:
        self._date_string = datetime.strftime(datetime.now(),"%Y%m%d_%H%M%S")
        self._edl = {
            "title":self._date_string if not title else title,
            "cuts":{}
        }

        self._cut_counter = 0

    @property
    def edl(self):
        return self._edl
    
    @property
    def date_string(self):
        return self._date_string
    
    @property
    def cut_counter(self):
        return self._cut_counter

    def current_cut(self):
        return self.get_cut_by_number(self._cut_counter)

    
    def set_edl_from_file(self,filename:str):
        with open(filename) as file:
            json_str = file.read()
            self._edl = json.load(json_str)
            pprint(self._edl)

        

    def create_cut_id(self,cut_number:int):
        return "{:03}".format(cut_number)

    def add_cut_in(self,reel:str,clipname:str,tc_in:str,timeline_in:str):
        self._cut_counter+=1
        cut_id = self.create_cut_id(self._cut_counter)
        cut = {
            "id":cut_id,
            "reel":reel.zfill(8),
            "clipname":clipname,
            "tc_in":tc_in,
            "tc_out":"",
            "timeline_in":timeline_in,
            "timeline_out":""
        }
        #cuts = self._edl.get("cuts")#.copy()
        #cuts[self._cut_counter] = cut    
        self._edl["cuts"][self._cut_counter] = cut

    def add_cut_out(self,tc_out:str,timeline_out:str):
        cut = self.get_cut_by_number(self._cut_counter)
        cut["tc_out"] = tc_out
        cut["timeline_out"] = timeline_out
        #self._edl.update({"cuts": {self._cut_counter:cut}})
        cuts = self._edl["cuts"]
        cuts.update({self._cut_counter:cut})
        self._edl.update({"cuts":cuts})

    def get_cut_by_number(self,number:int):
        cuts = self._edl['cuts']
        return cuts[number]
    
    def save_avid_edl(self,dir:str,filename:str=None,title:str=None):

        if title:
            self._edl['title'] = title
        
        if not filename:
            filename = self._edl['title'] + '.edl'

        path = os.path.join(dir,filename)
        with open(path,'w',encoding='utf-8') as f:
            f.write("TITLE:   " + self._edl['title'] + "\n")
            f.write("FCM: NON-DROP FRAME\n")
            cuts = self._edl['cuts']
            for k in range(1,len(cuts)+1):
                cut = cuts[k]
                f.write(cut['id'] + "  " + cut['reel'] + " V     C        " + cut['tc_in'] + " " + cut['tc_out'] + " " + cut['timeline_in'] + " " + cut['timeline_out'] + "\n")
                f.write("* FROM CLIP NAME:  " + cut['clipname'] + "\n")

    def load_avid_edl(self,filename:str):
        
        self._edl = {}
        line_counter = 0
        with open(filename) as file:
            line = file.readline()
            while line:
                line_counter+=1
                
                if line_counter == 1:
                    self._edl = {
                        "title":line[10:len(line)],
                        "cuts":{}
                        }
                   
                elif line_counter == 2:
                    # read FCM, not needed for now, is a fixed value of NON-DROP FRAME
                    pass
                elif line_counter % 2 == 0:
                    # odd line
                    cut_id = line[:3]
                    if cut_id.isdigit():
                        reel = line[5:13]
                        tcs = line[30:len(line)].split(' ')
                        tc_in = tcs[0]
                        tc_out = tcs[1]
                        timeline_in = tcs[2]
                        timeline_out = tcs[3]
                        line_counter+=1
                        line = file.readline()
                        clipname = line[10:len(line)]
                        self.add_cut_in(reel,clipname,tc_in,timeline_in)
                        self.add_cut_out(tc_out,timeline_out)

                line = file.readline()

        pprint(self._edl)


            
