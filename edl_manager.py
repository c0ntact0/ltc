from datetime import datetime
import os
import json
from pprint import pprint

output_formats = {
            'file_16':{
                'reel_size':16,
                'id_formatter':'{:06}',
                'type':'avid'
            },
            'file_32':{
                'reel_size':32,
                'id_formatter':'{:06}',
                'type':'avid'
            },
            'file_129':{
                'reel_size':129,
                'id_formatter':'{:06}',
                'type':'avid'
            },
            'CMX_3600':{
                'reel_size':8,
                'id_formatter':'{:03}',
                'type':'default'
                
            }
        }

class Edl():

    def __init__(self,title=None,output_format:str='file_32') -> None:
        self._date_string = datetime.strftime(datetime.now(),"%Y%m%d_%H%M%S")
        self._edl = {
            "title":self._date_string if not title else title,
            "cuts":{}
        }

        self._cut_counter = 0
        self._output_format = output_format

    @property
    def edl(self):
        return self._edl
    
    @property
    def date_string(self):
        return self._date_string
    
    @property
    def cut_counter(self):
        return self._cut_counter

    
    @property
    def output_format(self):
        
        return output_formats.get(self._output_format,output_formats.get('default'))

    def current_cut(self):
        return self.get_cut_by_number(self._cut_counter)

    
    def set_edl_from_file(self,filename:str):
        with open(filename) as file:
            json_str = file.read()
            self._edl = json.load(json_str)
            pprint(self._edl)

        

    def create_cut_id(self,cut_number:int):

        return self.output_format['id_formatter'].format(cut_number)
    
    def add_cut_in(self,reel:str,clipname:str,tc_in:str,timeline_in:str,reel_extension:None):
        if not reel_extension:
            reel_extension=self._cut_counter
        self._cut_counter+=1
        cut_id = self.create_cut_id(self._cut_counter)
        cut = {
            "id":cut_id,
            "reel":f"{reel}.{reel_extension}",
            "clipname":clipname,
            "tc_in":tc_in,
            "tc_out":"",
            "timeline_in":timeline_in,
            "timeline_out":""
        }
        #pprint(cut)
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
    
    def save_avid_edl(self,
                      dir:str,
                      fps:int,
                      filename:str=None,
                      title:str=None):

        if title:
            self._edl['title'] = title
        
        if not filename:
            filename = self._edl['title'] + '.edl'

        path = os.path.join(dir,filename)
        with open(path,'w',encoding='utf-8') as f:
            f.write(f"TITLE:{' ' * 3}{self._edl['title']}\n")
            f.write("FCM: NON-DROP FRAME\n")
            cuts = self._edl['cuts']
            for k in range(1,len(cuts)+1):
                cut = cuts[k]
                formatted_reel = ""
                f_diff = ' ' * (self.output_format['reel_size'] - len(cut['reel']))
                formatted_reel = cut['reel'] + f_diff
                formatted_reel = formatted_reel[0:self.output_format['reel_size']]
                #if self._output_format == 'file_32':
                #    f_diff = ' ' * (32 - len(cut['reel']))
                #    formatted_reel = cut['reel'] + f_diff
                #    formatted_reel = formatted_reel[0:32]
                #else:
                #    f_diff = ' ' * (8 - len(cut['reel']))
                #    formatted_reel = cut['reel'] + f_diff
                #    formatted_reel = formatted_reel[0:8]
            
                f.write(f"{cut['id']}  {formatted_reel} V{' ' * 5}C{' ' * 8}{cut['tc_in']} {cut['tc_out']} {cut['timeline_in']} {cut['timeline_out']}\n")
                # if self._output_format == 'file_32':
                fps_str = "{:03}".format(fps)
                f.write(f"M2      {formatted_reel}{' ' * 10}{fps_str}.0 {cut['tc_in']}\n")
                f.write(f"* FROM CLIP NAME:  {cut['clipname']}\n")
                #f.write("* SOURCE FILE: " + cut['clipname'] + "\n")

    def load_avid_edl(self,filename:str):

        #TODO: edl types        
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


if __name__ == '__main__':
    edl = Edl('Some title','file_32')
    print(edl.output_format)
    print(edl.create_cut_id(1))