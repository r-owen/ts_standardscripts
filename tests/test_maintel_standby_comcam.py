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

import logging
import random
import unittest
import asynctest

from lsst.ts import salobj
from lsst.ts import standardscripts
from lsst.ts.standardscripts.maintel import StandbyComCam
from lsst.ts.observatory.control.mock import ComCamMock

random.seed(47)  # for set_random_lsst_dds_domain

logging.basicConfig()


class TestStandbyComCam(standardscripts.BaseScriptTestCase, asynctest.TestCase):
    async def basic_make_script(self, index):
        self.script = StandbyComCam(index=index)
        self.comcam_mock = ComCamMock()

        return (self.script, self.comcam_mock)

    async def test_components(self):
        async with self.make_script():
            for component in self.script.group.components_attr:
                with self.subTest(f"Check {component}", component=component):
                    if getattr(self.script.group.check, component):
                        self.assertIn(component, self.script.components())

    async def test_run(self):
        async with self.make_script():
            await self.configure_script()

            await self.run_script()

            for comp in self.script.group.components_attr:

                if getattr(self.script.group.check, comp):

                    current_state = salobj.State(
                        getattr(
                            self.comcam_mock.controllers, comp
                        ).evt_summaryState.data.summaryState
                    )

                    with self.subTest(f"{comp} summary state", comp=comp):
                        self.assertEqual(
                            current_state,
                            salobj.State.STANDBY,
                            f"{comp}:  {current_state!r} != {salobj.State.STANDBY!r}",
                        )

    async def test_executable(self):
        scripts_dir = standardscripts.get_scripts_dir()
        script_path = scripts_dir / "maintel" / "standby_comcam.py"
        await self.check_executable(script_path)


if __name__ == "__main__":
    unittest.main()