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

__all__ = ["OfflineGroup"]

import abc
import yaml

from lsst.ts import salobj


class OfflineGroup(salobj.BaseScript, metaclass=abc.ABCMeta):
    """Put components of a group in offline.

    Parameters
    ----------
    index : `int`
        Index of Script SAL component.

    """

    __test__ = False  # stop pytest from warning that this is not a test

    def __init__(self, index, descr):

        super().__init__(index=index, descr=descr)

        self.config = None

    @property
    @abc.abstractmethod
    def group(self):
        """Return group of CSC attribute.

        Returns
        -------
        group
            This property must return a subclass of `RemoteGroup` from
            `lsst.ts.observatory.control`, e.g. `ATCS` or `MTCS`.

        """
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def components(cls):
        """Return list of components name as appeared in
        `self.group.components`.

        Returns
        -------
        components : `list` of `str`.

        """
        raise NotImplementedError()

    @classmethod
    def get_schema(cls):
        schema_yaml = f"""
            $schema: http://json-schema.org/draft-07/schema#
            $id: https://github.com/lsst-ts/ts_standardscripts/offline_group.yaml
            title: OfflineGroup v1
            description: Configuration for OfflineGroup.
            type: object
            properties:
                ignore:
                    description: >-
                        CSCs from the group to ignore. Name must match those in
                        self.group.components, e.g.; mtdometrajectory or hexapod_1
                        for the MTDomeTrajectory and Hexapod:1 components, respectively.
                        Valid options are: {cls.components}.
                    type: array
                    items:
                        type: string
            additionalProperties: false
        """
        return yaml.safe_load(schema_yaml)

    async def configure(self, config):
        self.config = config

    def set_metadata(self, metadata):
        metadata.duration = 60.0

    async def run(self):

        if hasattr(self.config, "ignore"):
            for comp in self.config.ignore:
                if comp not in self.components():
                    self.log.warning(
                        f"Component {comp} not in CSC Group. "
                        f"Must be one of {self.components()}. Ignoring."
                    )
                else:
                    self.log.debug(f"Ignoring {comp}.")
                    setattr(self.group.check, comp, False)

        await self.group.offline()