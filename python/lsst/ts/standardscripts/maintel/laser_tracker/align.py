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

__all__ = ["Align", "AlignComponent"]

import enum

import numpy as np
import yaml
from lsst.ts.idl.enums.LaserTracker import LaserStatus
from lsst.ts.observatory.control import RemoteGroup
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages
from lsst.ts.observatory.control.remote_group import Usages

from lsst.ts import salobj


# TODO (DM-38880) - Subsitute by class in idl.enum when available
class AlignComponent(enum.IntEnum):
    M2 = enum.auto()
    Camera = enum.auto()


class Align(salobj.BaseScript):
    """Align component using laser tracker.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**
    - "Starting alignment procedure.": Starting alignment with laser tracker.
    - "M2 Hexapod aligned with laser tracker.": M2 aligned.
    - "Camera Hexapod aligned with laser tracker.": M2 aligned.
    """

    def __init__(self, index: int, add_remotes: bool = True):
        super().__init__(index, descr="Align MTCS components with laser tracker.")

        self.laser_tracker = RemoteGroup(
            domain=self.domain,
            components=["LaserTracker:1"],
            intended_usage=None if add_remotes else Usages.DryTest,
            log=self.log,
        )

        self.mtcs = MTCS(
            domain=self.domain,
            intended_usage=None if add_remotes else MTCSUsages.DryTest,
            log=self.log,
        )

        self.timeout_align = 120
        self.timeout_std = 60

        self.max_iter = 10
        self.tolerance_linear = 1.0e-7  # meter
        self.tolerance_angular = 5.0 / 3600.0  # degrees
        self.target = None

    @classmethod
    def get_schema(cls):
        url = "https://github.com/lsst-ts/"
        path = (
            "ts_externalscripts/blob/main/python/lsst/ts/standardscripts/"
            "maintel/laser_tracker/align.py"
        )
        schema_yaml = f"""
        $schema: http://json-schema.org/draft-07/schema#
        $id: {url}{path}
        title: MaintelLaserTrackerAlign v1
        description: Configuration for Maintel laser tracker alignment SAL Script.
        type: object
        properties:
            max_iter:
                description: maximum number of iterations to align components.
                type: integer
                default: 10
                minimum: 1
            tolerance_linear:
                description: tolerance for rigid body degrees of freedom corrections (meters).
                type: number
                default: 1.0e-7
                minimum: 0.0
            tolerance_angular:
                description: tolerance for tip/tilt degrees of freedom corrections (deg).
                type: number
                default: 0.00138
                minimum: 0.0
            target:
                description: >-
                    Target to align. Options are:
                    M2: Secondary mirror.
                    Camera: LSST Camera.
                type: string
                enum: ["Camera", "M2"]
        additionalProperties: false
        required:
            - target
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.max_iter = config.max_iter
        self.target = getattr(AlignComponent, config.target)
        self.tolerance_linear = config.tolerance_linear
        self.tolerance_angular = config.tolerance_angular

    def set_metadata(self, metadata):
        """Set estimated duration of the script."""

        metadata.duration = (self.timeout_align + self.timeout_std) * self.max_iter

    def get_align_func(self):
        """Get function to align target."""

        if self.target == AlignComponent.M2:
            return self.mtcs.offset_m2_hexapod
        elif self.target == AlignComponent.Camera:
            return self.mtcs.offset_camera_hexapod
        else:
            raise RuntimeError(f"Invalid target {self.target!r}.")

    async def align_target(self):
        """Align target with laser tracker.

        Notes
        -----
        **Checkpoints**
        - "Starting alignment procedure.": Starting alignment.
        - "{...} aligned with laser tracker.": Component aligned.

        Raises
        ------
        RuntimeError
            If not aligned after max_iter iterations.
        """

        # Set function to align target.
        align_func = self.get_align_func()

        for n_iter in range(self.max_iter):
            self.laser_tracker.rem.lasertracker_1.evt_offsetsPublish.flush()
            await self.laser_tracker.rem.lasertracker_1.cmd_align.set_start(
                target=self.target,
                timeout=self.timeout_align,
            )
            offset = (
                await self.laser_tracker.rem.lasertracker_1.evt_offsetsPublish.next(
                    flush=False, timeout=self.timeout_std
                )
            )

            corrections = np.array(
                [
                    offset.dX * 1e6 if abs(offset.dX) > self.tolerance_linear else 0.0,
                    offset.dY * 1e6 if abs(offset.dY) > self.tolerance_linear else 0.0,
                    offset.dZ * 1e6 if abs(offset.dZ) > self.tolerance_linear else 0.0,
                    offset.dRX if abs(offset.dRX) > self.tolerance_angular else 0.0,
                    offset.dRY if abs(offset.dRX) > self.tolerance_angular else 0.0,
                ]
            )

            if any(corrections):
                self.log.info(
                    f"[{n_iter+1:02d}:{self.max_iter:02d}]: Applying corrections: {corrections}"
                )
                await align_func(*-corrections)

            else:
                self.log.info(
                    f"[{n_iter+1:02d}:{self.max_iter:02d}]: Corrections completed."
                )
                return

        raise RuntimeError(
            f"Failed to align {self.target} after {self.max_iter} iterations."
        )

    async def check_laser_status_ok(self):
        """Check that laser status is ON."""
        laser_status = await self.laser_tracker.rem.lasertracker_1.evt_laserStatus.aget(
            timeout=self.timeout_std,
        )

        if laser_status.status != LaserStatus.ON:
            raise RuntimeError(
                f"Laser status is {LaserStatus(laser_status.status)!r}, expected {LaserStatus.ON!r}."
            )

    async def run(self):
        """Run the script."""

        await self.check_laser_status_ok()

        await self.checkpoint("Starting alignment procedure.")

        # Align component
        await self.align_target()
        await self.checkpoint(f"{self.target} aligned with laser tracker.")