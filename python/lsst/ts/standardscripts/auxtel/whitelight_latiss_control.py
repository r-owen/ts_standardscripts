# This file is part of ts_standardscripts
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License

from lsst.ts import salobj
from abc import abstractmethod
from yaml import safe_load
from types import SimpleNamespace
import asyncio

_ATWhiteLightSchema = """
$schema: http://json-schema.org/draft-07/schema#
$id: TODOTODOTODO
title: AuxtelWhiteLightControl{script_suffix} v1
description: Control the auxtel white light system
type: object
properties:
    event_timeout:
        description: Timeout (seconds) to wait for SAL events
        type: number
        default: 30
    lamp_power:
        description: Desired lamp power in Watts
        type: number
        default: 1200
    chiller_turnon_wait:
        description: Time to wait if we need to turn the chiller on in seconds
        type: number
        default: 120
"""


class WhiteLightControlScriptBase(salobj.BaseScript):
    """White Light Control script base class for Auxtel

    This is a SAL script to control the functions of the auxtel
    white light calibration system.

    Until that is installed, in the meantime it will be able to control
    the red LED dome flat projector on and off in auxtel"""

    @property
    @abstractmethod
    def script_descr_name(self) -> str:
        pass

    def __init__(self, index: int):
        descr = f"Turn the auxtel White Light {self.script_descr_name}"
        super().__init__(index=index, descr=descr)

        self._whitelight = salobj.Remote(self.domain, "ATWhiteLight")

    @classmethod
    def get_schema(cls) -> dict:
        ourschema = _ATWhiteLightSchema.format(
            script_suffix=cls.SCRIPT_DESCR_NAME.capitalize()
        )
        return safe_load(ourschema)

    async def configure(self, config: SimpleNamespace):
        self.event_timeout: int = config.event_timeout
        self.lamp_power: float = config.lamp_power
        self.chiller_turnon_wait: float = config.chiller_turnon_wait

    def set_metadata(self, metadata):
        pass

    async def run(self) -> None:
        # First check if ATWhiteLight is enabled.
        ss = await self._whitelight.evt_summaryState.aget(timeout=self._eventt_timeout)
        state = salobj.State(ss)

        if state != salobj.State.ENABLED:
            raise AssertionError(
                f"{self._whitelight.name} needs to be enabled to run this script"
            )

        # Now turn on (or off, depending on instantiation) the lamp
        await self._exec_whitelight_onoff_action()

    @abstractmethod
    async def _exec_whitelight_onoff_action(self) -> None:
        ...


class WhiteLightControlScriptTurnOn(WhiteLightControlScriptBase):
    @property
    def script_descr_name(self) -> str:
        return "on"

    async def _exec_whitelight_onoff_action(self) -> None:
        # If we are turning on the lamp, first need to verify
        # that the chiller is turned on. If not, turn it on
        chillerState = await self._whitelight.evt_chillerWatchdog(
            timeout=self._event_timeout
        )
        # Note: 2 is chillerState.RUN
        if chillerState != 2:
            await self._whitelight.cmd_startChiller()
            await asyncio.sleep(self.chiller_turnon_wait)
        chillerState = await self._whitelight.evt_chillerWatchdog(
            timeout=self._event_timeout
        )
        if chillerState != 2:
            raise RuntimeError("chiller failed to turn on in the specified time")
        await self._whitelight.cmd_turnLampOn(self._lamp_power)


class WhiteLightControlScriptTurnOff(WhiteLightControlScriptBase):
    @property
    def script_descr_name(self) -> str:
        return "off"

    async def _exec_whitelight_onoff_action(self) -> None:
        await self._whitelight.cmd_turnLampOff()
