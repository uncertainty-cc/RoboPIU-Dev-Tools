import time
import logging
import threading
import asyncio
import json

import websockets

logger = logging.getLogger("HALSimWebsocketServer")


class HALSimWebsocketServer:
    _uri = "ws://localhost:3300/wpilibws"
    
    def __init__(self, nt):
        logger.info("Started.")
        self._nt = nt
        self._is_connected = False
        self._is_running = threading.Event()
        self._is_running.set()

    def run(self):
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=loop.run_until_complete, args=(self.handleHALSimWebocket(), ))
        t.start()

    def stop(self):
        self._is_running.clear()

    def isConnected(self):
        return self._is_connected

    async def handleHALSimWebocket(self):
        while self._is_running.is_set():
            try:
                logger.info("connecting to FRC websocket...")
                websocket = await websockets.connect(self._uri, ping_interval=None)
                self._is_connected = True
            except ConnectionRefusedError:
                logger.error("Connection failed, retrying...")
                continue
            logger.info("WebSocket connected.")
            while self._is_running.is_set():
                try:
                    recv = await websocket.recv()
                except Exception as e:
                    self._is_connected = False
                    logger.error("Remote connection closed. Restarting...")
                    break
                if recv:
                    recv = json.loads(recv)
                    
                    nt_key = None
                    nt_value = None

                    # message forwarding rules
                    if recv.get("type") == "DriverStation":
                        if recv.get("data").get(">new_data"):
                            continue
                        key = list(recv.get("data").keys())[0]
                        nt_key = "/driverstation/{key}".format(key=key[1:])
                        if nt_key == "/driverstation/match_time" or nt_key == "/driverstation/station":
                            nt_value = recv.get("data").get(key)
                        else:
                            nt_value = 1 if recv.get("data").get(key) else 0
                        
                        
                    if recv.get("type") == "PWM":
                        if recv.get("data").get("<init"):
                            continue
                        key = list(recv.get("data").keys())[0]
                        nt_key = "/pwm/{index}/{key}".format(key="value", index=recv.get("device"))
                        nt_value = 0
                        if recv.get("data").get("<speed"):
                            nt_value = recv.get("data").get("<speed")
                        elif recv.get("data").get("<position"):
                            nt_value = float(recv.get("data").get("<position")) * 2 - 1.
                        
                    if nt_key:
                        self._nt[nt_key] = nt_value

if __name__ == "__main__":

    # nt is required as a global variable
    nt = {}

    
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")


    server = HALSimWebsocketServer(nt)
    server.run()


    while True:
        try:
            time.sleep(1)
            print(nt)
        except KeyboardInterrupt as e:
            server.stop()
            break

    print(nt)

