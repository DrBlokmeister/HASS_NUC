from __future__ import annotations
import asyncio
import random
import websocket
import socket
import aiohttp
import async_timeout
import backoff
import time
import json
import logging
from threading import Thread
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN
_LOGGER: Final = logging.getLogger(__name__)
#Hub class for handeling communication
class Hub:
    #the init function starts the thread for all other communication
    def __init__(self, hass: HomeAssistant, host: str,cfgenty: str) -> None:
        self._host = host
        self._cfgenty = cfgenty
        self._hass = hass
        self._name = host
        self._id = host.lower()
        self.esls = []
        self.data = dict()
        self.data["ap"] = dict()
        self.data["ap"]["ip"] =  self._host;
        self.data["ap"]["systime"] = None;
        self.data["ap"]["heap"] = None;
        self.data["ap"]["recordcount"] = None;
        self.data["ap"]["dbsize"] = None;
        self.data["ap"]["littlefsfree"] = None;
        self.eventloop = asyncio.get_event_loop()
        thread = Thread(target=self.establish_connection)
        thread.start()
        self.online = True
    #parses websocket messages
    def on_message(self,ws, message) -> None:
        data =  json.loads('{' + message.split("{", 1)[-1])
        if 'sys' in data:
            sys = data.get('sys')
            systime = sys.get('currtime')
            heap = sys.get('heap')
            recordcount = sys.get('recordcount')
            dbsize = sys.get('dbsize')
            littlefsfree = sys.get('littlefsfree')
            apstate = sys.get('apstate')
            runstate = sys.get('runstate')
            temp = sys.get('temp')
            rssi = sys.get('rssi')
            wifistatus = sys.get('wifistatus')
            wifissid = sys.get('wifissid')
            self._hass.states.set(DOMAIN + ".ip", self._host,{"icon": "mdi:ip","friendly_name": "AP IP","should_poll": False})
            self.data["ap"] = dict()
            self.data["ap"]["ip"] =  self._host;
            self.data["ap"]["systime"] = systime;
            self.data["ap"]["heap"] = heap;
            self.data["ap"]["recordcount"] = recordcount;
            self.data["ap"]["dbsize"] = dbsize;
            self.data["ap"]["littlefsfree"] = littlefsfree;
            self.data["ap"]["rssi"] = rssi;
            self.data["ap"]["apstate"] = apstate;
            self.data["ap"]["runstate"] = runstate;
            self.data["ap"]["temp"] = temp;
            self.data["ap"]["wifistatus"] = wifistatus;
            self.data["ap"]["wifissid"] = wifissid;
        elif 'tags' in data:
            tag = data.get('tags')[0]
            tagmac = tag.get('mac')
            lastseen = tag.get('lastseen')
            nextupdate = tag.get('nextupdate')
            nextcheckin = tag.get('nextcheckin')
            LQI = tag.get('LQI')
            RSSI = tag.get('RSSI')
            temperature = tag.get('temperature')
            batteryMv = tag.get('batteryMv')
            pending = tag.get('pending')
            hwType = tag.get('hwType')
            contentMode = tag.get('contentMode')
            alias = tag.get('alias')
            wakeupReason = tag.get('wakeupReason')
            capabilities = tag.get('capabilities')
            hashv = tag.get('hash')
            modecfgjson = tag.get('modecfgjson')
            isexternal = tag.get('isexternal')
            rotate = tag.get('rotate')
            lut = tag.get('lut')
            ch = tag.get('ch')
            ver = tag.get('ver')
            #required for automations
           
            hwmap = {
                0: ["ST‐GR16000 1.54\"", 152, 152],
                1: ["ST‐GR29000 2.9\"",  296, 128],
                2: ["ST‐GR420B3N2 4.2\"",  400, 300],
                5: ["ST‐GR750BN 7.4\"",  640, 384],
                17: ["ST-GR2900L 2.9\" (UC8151)", 296, 128],
                51: ["EL029GSWRN 2.9\"",  384, 168],
                224: ["TFT 320x170",  320, 170],
                240: ["SLT‐EM007 Segmented",  0, 0]
            }

            self._hass.states.set(DOMAIN + "." + tagmac, hwType,{
                "icon": "mdi:fullscreen",
                "friendly_name": tagmac,
                "should_poll": False,
                "hwtype": hwType,
                "hwstring": hwmap[hwType][0],
                "width": hwmap[hwType][1],
                "height": hwmap[hwType][2],
                })
            self.data[tagmac] = dict()
            self.data[tagmac]["temperature"] = temperature
            self.data[tagmac]["rssi"] = RSSI
            self.data[tagmac]["battery"] = batteryMv
            self.data[tagmac]["lqi"] = LQI
            self.data[tagmac]["hwtype"] = hwType
            self.data[tagmac]["hwstring"] = hwmap[hwType][0]
            self.data[tagmac]["contentmode"] = contentMode
            self.data[tagmac]["lastseen"] = lastseen
            self.data[tagmac]["nextupdate"] = nextupdate
            self.data[tagmac]["nextcheckin"] = nextcheckin
            self.data[tagmac]["pending"] = pending
            self.data[tagmac]["wakeupReason"] = wakeupReason
            self.data[tagmac]["capabilities"] = capabilities
            self.data[tagmac]["external"] = isexternal
            self.data[tagmac]["alias"] = alias
            self.data[tagmac]["hashv"] = hashv
            self.data[tagmac]["modecfgjson"] = modecfgjson
            self.data[tagmac]["rotate"] = rotate
            self.data[tagmac]["lut"] = lut
            self.data[tagmac]["ch"] = ch
            self.data[tagmac]["ver"] = ver
            #maintains a list of all tags, new entities should be generated here
            if tagmac not in self.esls:
                self.esls.append(tagmac)
                loop = self.eventloop
                asyncio.run_coroutine_threadsafe(self.reloadcfgett(),loop)            
            #fire event with the wakeup reason
            lut = {0: "TIMED",1: "BOOT",2: "GPIO",3: "NFC",4: "BUTTON1",5: "BUTTON2",252: "FIRSTBOOT",253: "NETWORK_SCAN",254: "WDT_RESET"}
            event_data = {
                "device_id": tagmac,
                "type": lut[wakeupReason],
            }
            self._hass.bus.async_fire(DOMAIN + "_event", event_data)
        elif 'errMsg' in data:
            ermsg = data.get('errMsg');
        elif 'logMsg' in data:
            logmsg = data.get('logMsg');
        elif 'apitem' in data:
            logmsg = data.get('apitem');
        else:
            _LOGGER.warning("Unknown msg")
            _LOGGER.warning(data)
    #log websocket errors
    def on_error(self,ws, error) -> None:
        _LOGGER.warning("Websocket error, most likely on_message crashed")
        _LOGGER.warning(error)
    #try to reconnect after 5 munutes
    def on_close(self,ws, error, a) -> None:
        _LOGGER.warning("Websocket connection lost")
        print("Connection lost")
        print("Waiting 300 seconds")
        time.sleep(300)
        self.establish_connection()
    #we could do something here
    def on_open(self,ws) -> None:
        time.sleep(1)
    #starts the websocket
    def establish_connection(self) -> None:
        ws_url = "ws://" + self._host + "/ws"
        ws = websocket.WebSocketApp(ws_url,on_message=self.on_message,on_error=self.on_error,on_close=self.on_close,on_open=self.on_open)
        ws.run_forever()
        _LOGGER.warning("This should not happen")
    #we should do more here
    async def test_connection(self) -> bool:
        return True
    #reload is reqired to add new entities
    async def reloadcfgett(self) -> bool:
        await self._hass.config_entries.async_unload_platforms(self._cfgenty, ["sensor"])
        await self._hass.config_entries.async_forward_entry_setups(self._cfgenty, ["sensor"])
        return True
