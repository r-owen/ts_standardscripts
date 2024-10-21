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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = ["OpenMirrorCovers"]

from lsst.ts import salobj
from lsst.ts.observatory.control.maintel.mtcs import MTCS, MTCSUsages


class OpenMirrorCovers(salobj.BaseScript):
    """Run open mirror covers on MTCS.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    Notes
    -----
    **Checkpoints**

    * Opening mirror covers: before issuing open mirror covers command.
    """

    def __init__(self, index):
        super().__init__(index=index, descr="Open the MT mirror covers.")

        self.mtcs = None

    @classmethod
    def get_schema(cls):
        # This script does not require any configuration
        return None

    async def configure(self, config):
        if self.mtcs is None:
            self.mtcs = MTCS(
                domain=self.domain, intended_usage=MTCSUsages.All, log=self.log
            )
            await self.mtcs.start_task

    def set_metadata(self, metadata):
        metadata.duration = self.mtcs.mirror_covers_timeout

    async def run(self):
        await self.mtcs.assert_all_enabled()
        await self.checkpoint("Opening mirror covers.")
        await self.mtcs.open_m1_cover()