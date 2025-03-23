import serial.tools.list_ports as serial_list_ports
import serial
import time

class SerialPort():

    def __init__(self) -> None:
        self._serial_obj = None
        self._running = False

    @property
    def is_open(self):
        return True if self._serial_obj and self._serial_obj.is_open else False
    @property
    def serial_obj(self):
        return self._serial_obj
    
    @property
    def running(self):
        return self._running
    
    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def inicialize_port(self,port:str,baudrate:int = 9600,bytesize:int = 8,parity:str = 'N',stopbits:int = 1):
        try:
            self._serial_obj = serial.Serial(port,baudrate,bytesize,parity,stopbits)
            time.sleep(3) # wait for arduino init
        except serial.SerialException as e:
            print(f'ERROR: while trying to open serial port: {e}')
        else:
            print(f'INFO: Serial port {port} opened.')

    def close_port(self):
        try:
            self._serial_obj.close()
        except Exception as e:
            print(f"ERROR: while trying to close the serial port: {e}")

    def get_serial_ports(self):
        return serial_list_ports.comports()
        #for port,desc,hwid in sorted(serial_ports):
        #    print("{}: {} [{}]".format(port, desc, hwid))
    