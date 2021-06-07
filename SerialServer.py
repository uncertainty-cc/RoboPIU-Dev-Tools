import time
import struct
import threading
import asyncio
import json
import logging
import socket

import serial
import serial.tools.list_ports

# import msgpack

logger = logging.getLogger("PaleBlueServer")

class EscapeCodes:
    END = b"\x0A"
    ESC = b"\x1B"
    ESC_END = b"\x1C"
    ESC_ESC = b"\x1D"

class Interval(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class PaleBlueServer:
    def __init__(self, nt, port=None):
        logger.info("Started.")
        self._nt = nt
        self._port = port

        self._ser = None
        self._kill_signal = threading.Event()
        self._kill_signal.clear()
        self._is_connected = False
        self.connect()

        self._last_tx_data = b""
        self._last_rx_data = b""
        
        self._prev_nt = {}

        self._prev_heartbeat = time.time()

    def connect(self):
        self._prev_nt = {}
        if self._ser:
            self._ser.close()
        connected = False
        while not self._is_connected:
            if self._port:
                logger.info("assigned COM port at {}".format(self._port))
            else:
                logger.info("enumerating COM ports...")
                ports = serial.tools.list_ports.comports()
                if len(ports) == 0:
                    logger.error("no COM Port detected.")
                    time.sleep(5)
                    continue
                self._port = ports[0].name
            try:      
                self._ser = serial.Serial(port=self._port, baudrate=115200, timeout=0)
                self._is_connected = True
                logger.info("COM port connected at {}".format(self._port))
            except serial.serialutil.SerialException:
                logger.error("COM port connection fail. Restarting...")
            time.sleep(2)

    def write(self, byte):
        try:
            self._ser.write(byte)
        except Exception as e:
            self._is_connected = False
            return

    def read(self):
        try:
            recv = self._ser.read(1)
        except Exception as e:
            self._is_connected = False
            return
        return recv

    def transmit(self, buffer):
        index = 0
        while index < len(buffer):
            c = struct.pack("B", buffer[index])
            if c == EscapeCodes.END:
                self.write(EscapeCodes.ESC)
                self.write(EscapeCodes.ESC_END)
            elif c == EscapeCodes.ESC:
                self.write(EscapeCodes.ESC)
                self.write(EscapeCodes.ESC_ESC)
            else:
                self.write(c)
            index += 1
        self.write(EscapeCodes.END)

    def receive(self):
        c = self.read()
        buffer = b""
        if not c:
            return buffer
        
        while c != EscapeCodes.END:
            if c == EscapeCodes.ESC:
                c = self.read()
                if c == EscapeCodes.ESC_END:
                    buffer += EscapeCodes.END
                elif c == EscapeCodes.ESC_ESC:
                    buffer += EscapeCodes.ESC
                else:
                    buffer += c
            else:
                buffer += c
            c = self.read()
        return buffer

    def heartbeat(self):
        # sync all data table to serial every 500 ms
        self._prev_nt = {}
        if not self._is_connected:
            self.connect()
        
    def handleTX(self):
        send_list = []
        
        tmp_nt = self._nt.copy()
        for key in tmp_nt:
            if self._prev_nt.get(key) != tmp_nt[key]:
                send_list.append({key: tmp_nt[key]})
                self._prev_nt[key] = tmp_nt[key]
        
        for msg in send_list:
            buffer = list(msg.items())[0][0].encode() + b":" + str(list(msg.items())[0][1]).encode()
            self.transmit(buffer)
            self._last_tx_data = buffer

    def handleRX(self):
        recv = self.receive()
        self._last_rx_data = recv
            
    def stop(self):
        self._kill_signal.set()
        logger.info("Stopped.")

    def update(self):
        if time.time() - self._prev_heartbeat > 0.5:
            self.heartbeat()
            self._prev_heartbeat = time.time()
        self.handleTX()
        self.handleRX()

    def getLastRX(self):
        return self._last_rx_data

    def isConnected(self):
        return self._is_connected
                

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    nt = {}

    server = PaleBlueServer(nt)

    dir_ = 0
    value = 0


    nt["/driverstation/enabled"] = "1"
    while True:
        try:
            if dir_:
                value -= 0.1
            else:
                value += 0.1
            if value >= 0.95 or value <= -0.95:
                dir_ = 1 - dir_
            nt["/pwm/0/value"] = value

            server.update()
            time.sleep(0.01)

        except KeyboardInterrupt as e:
            server.stop()
            break
        
