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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["SyncDOF"]

import numpy as np
import yaml
from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient

from .apply_dof import ApplyDOF

STD_TIMEOUT = 30


class SyncDOF(ApplyDOF):
    """Set absolute positions DOF to the main telescope, either bending
    mode or hexapod position.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**
    "Setting DOF..." - The DOF absolute position is being applied.

    """

    @classmethod
    def get_schema(cls):
        schema_yaml = """
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/maintel/SyncDOF.yaml
            title: SyncDOF v1
            description: Configuration for SyncDOF.
            type: object
            properties:
              day:
                description: Day obs to be used for synchronizing the state.
                type: number
                default: null
              seq:
                description: Sequence number to be used for synchronizing the state.
                type: number
                default: null
            required:
                - day
                - seq
            additionalProperties: false
        """
        schema_dict = yaml.safe_load(schema_yaml)

        base_schema_dict = super(ApplyDOF, cls).get_schema()

        for prop in base_schema_dict["properties"]:
            schema_dict["properties"][prop] = base_schema_dict["properties"][prop]

        return schema_dict

    async def configure(self, config) -> None:
        """Configure script.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Script configuration, as defined by `schema`.
        """

        # Configure tcs and camera
        await self.configure_tcs()

        self.day = config.day
        self.seq = config.seq

        for comp in getattr(config, "ignore", []):
            if comp not in self.mtcs.components_attr:
                self.log.warning(
                    f"Component {comp} not in CSC Group. "
                    f"Must be one of {self.mtcs.components_attr}. Ignoring."
                )
            else:
                self.log.debug(f"Ignoring component {comp}.")
                setattr(self.mtcs.check, comp, False)

    async def get_image_time(self, day, seq):
        """Get the image time from the given day and sequence number.

        Parameters
        ----------
        day : `int`
            Day obs to be used for synchronizing the state.
        seq : `int`
            Sequence number to be used for synchronizing the state.

        Returns
        -------
        image_time : `datetime.datetime`
            Image time.
        """

        query = f"""
            SELECT  "imageDate", "imageNumber"
            FROM "efd"."autogen"."lsst.sal.CCCamera.logevent_endReadout"
            WHERE imageDate =~ /{day}/ AND imageNumber = {seq}
        """

        time = await self.client.influx_client.query(query)
        return Time(time.iloc[0].name)

    async def get_last_issued_state(self, time):
        """Get the state from the given day and sequence number.

        Parameters
        ----------
        time : `datetime.datetime`
            Initial time to query.

        Returns
        -------
        state : `dict`
            State of the system.
        """

        topics = [f"aggregatedDoF{i}" for i in range(50)]

        current_end = time
        lookback_interval = TimeDelta(1, format="jd")
        max_lookback_days = 7

        while True:
            current_start = current_end - lookback_interval

            state = await self.client.select_time_series(
                "lsst.sal.MTAOS.logevent_degreeOfFreedom",
                topics,
                current_start,
                current_end,
            )

            if not state.empty:
                state = state.iloc[[-1]]
                return state.values.squeeze()

            current_end = current_start
            if (time - current_end).jd > max_lookback_days:
                self.log.info(
                    "No data found within the specified range and maximum lookback period."
                )
                return np.zeros(50)
        return state.values.squeeze()

    async def run(self) -> None:
        """Run script."""
        # Assert feasibility
        await self.assert_feasibility()

        self.client = EfdClient("summit_efd")
        image_end_time = self.get_image_time(self.day, self.seq)
        last_state = self.get_last_issued_state(image_end_time)

        await self.checkpoint("Setting DOF...")
        current_dof = await self.mtcs.rem.mtaos.evt_degreeOfFreedom.aget(
            timeout=STD_TIMEOUT
        )
        dof_data = self.mtcs.rem.mtaos.cmd_offsetDOF.DataType()
        for i, dof_absolute in enumerate(last_state):
            dof_data.value[i] = dof_absolute - current_dof.aggregatedDoF[i]
        await self.mtcs.rem.mtaos.cmd_offsetDOF.start(data=dof_data)
