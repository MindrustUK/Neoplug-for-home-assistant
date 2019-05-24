"""
homeassistant.custom_components.heatmiserneo.switch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heatmiser NeoPlug control via Heatmiser Neo-hub
"""

import logging

import requests
import voluptuous as vol

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_RESOURCE, CONF_HOST, CONF_PORT,
                                 STATE_OFF, STATE_ON, STATE_STANDBY, STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv

import socket
import json

_LOGGER = logging.getLogger(__name__)

VERSION = '1.0.0'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.port,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up a Heatmiser Neo-Hub And Returns NeoPlugs"""
    host = config.get(CONF_HOST, None)
    port = config.get(CONF_PORT, 4242)

    switches = []

    NeoHubJson = HeatmiserNeoplug(host, port).json_request({"INFO": 0})

    _LOGGER.debug(NeoHubJson)

    for device in NeoHubJson['devices']:
        if device['DEVICE_TYPE'] == 6:
            name = device['device']
            state = STATE_ON
            _LOGGER.info("Plug Name: %s, State: %s " % (name, state))
            switches.append(HeatmiserNeoplug(host, port, name, state))
            _LOGGER.debug("Switches: %s" % switches)

        elif device['DEVICE_TYPE'] != 6:
            _LOGGER.debug("Found a non Neoplug named: %s skipping" % device['device'])

    _LOGGER.info("Adding Switches: %s " % switches)
    add_devices(switches)


class HeatmiserNeoplug(SwitchDevice):
    """ Represents a Heatmiser Neoplug. """
    def __init__(self, host, port, name="Null", state=False):
        self._name = name
        self._host = host
        self._port = port
        self._state = None
        self.update()

    @property
    def name(self):
        """ Returns the name. """
        return self._name

    @property
    def operation(self):
        """ Returns current operation. heat, cool idle """
        return self._operation

    @property
    def current_operation(self):
        """Return current operation."""
        return self._current_operation

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def turn_on(self):
        """Turn the device on."""
        self._state = True
        _LOGGER.debug("Heatmiser NeoPlug Trun on for device: %s" % self._name)
        response = self.json_request({"TIMER_ON":self._name})

    def turn_off(self):
        """Turn the device off."""
        self._state = False
        _LOGGER.debug("Heatmiser NeoPlug Trun off for device: %s" % self._name)
        response = self.json_request({"TIMER_OFF":self._name})

    def update(self):
        """ Get Updated Info. """
        _LOGGER.debug("Entered update(self)")
        response = self.json_request({"INFO": 0})
        return False

    def json_request(self, request=None, wait_for_response=False):
        """ Communicate with the json server. """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        try:
            sock.connect((self._host, self._port))
        except OSError:
            sock.close()
            return False

        if not request:
            sock.close()
            return True

        _LOGGER.debug("json_request: %s " % request)

        sock.send(bytearray(json.dumps(request) + "\0\r", "utf-8"))
        try:
            buf = sock.recv(4096)
        except socket.timeout:
            sock.close()
            return False

        # read until a newline or timeout
        buffering = True
        while buffering:
            if "\n" in str(buf, "utf-8"):
                response = str(buf, "utf-8").split("\n")[0]
                buffering = False
            else:
                try:
                    more = sock.recv(4096)
                except socket.timeout:
                    more = None
                if not more:
                    buffering = False
                    response = str(buf, "utf-8")
                else:
                    buf += more

        sock.close()

        response = response.rstrip('\0')

        _LOGGER.debug("json_response: %s " % response)

        return json.loads(response, strict=False)
