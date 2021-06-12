import os
import logging
import time
import json
import sys

import keyboard
import colorama

#from CameraServer import RTSPCamera, CameraServer
from SerialServer import PaleBlueServer
from HALSimWebsocketServer import HALSimWebsocketServer


CONFIG_FILE_PATH = "config.json"

config = {}

if os.path.isfile(CONFIG_FILE_PATH):
    config = json.load(open("config.json", encoding="utf-8"))
else:
    json.dump(config, open("config.json", "w", encoding="utf-8"))
    

# nt is required as a global variable
nt = {}


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")


frc_server = HALSimWebsocketServer(nt)

serial_server = PaleBlueServer(nt, port=config.get("connection").get("port"))

frc_server.run()


dir_ = 0
value = 0

colorama.init()

while True:
    try:
        end_char = "\r\n"

        serial_server.update()

        sim_connected = 1 if frc_server.isConnected() else 0
        serial_connected = 1 if serial_server.isConnected() else 0
        
        if "idlelib" not in sys.modules:
            end_char = "\r"
            if sim_connected:
                sim_connected = colorama.Fore.GREEN + str(sim_connected) + colorama.Style.RESET_ALL
            else:
                sim_connected = colorama.Fore.RED + str(sim_connected) + colorama.Style.RESET_ALL
            if serial_connected:
                serial_connected = colorama.Fore.GREEN + str(serial_connected) + colorama.Style.RESET_ALL
            else:
                serial_connected = colorama.Fore.RED + str(serial_connected) + colorama.Style.RESET_ALL
        
        print("== {green}running{clear} ==  {bright}Simulation{clear}<Connected: {sim_connected}>\t{bright}Serial{clear}<Connected: {serial_connected} RX: {serial_rx}>".format(
            green=colorama.Fore.GREEN,
            bright=colorama.Style.BRIGHT,
            clear=colorama.Style.RESET_ALL,
            sim_connected=sim_connected,
            serial_connected=serial_connected,
            serial_rx=serial_server.getLastRX()
            ), end=end_char)
        time.sleep(0.01)
    except KeyboardInterrupt as e:
        try:
            cmd = input("\r\ninput command:\n").upper()
        except KeyboardInterrupt as e:
            break
        if cmd == "Q":
            break
        if cmd == "T":
            print(nt)

print("exit.")
serial_server.stop()
frc_server.stop()
'''
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

cam = RTSPCamera("rtsp://admin:admin@192.168.1.37:554/h264/ch1/main/av_stream")
cam.setScaleFactor(0.5)
#cam.show()

cam_server = CameraServer(cam)
cam_server.run()
'''
