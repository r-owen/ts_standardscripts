__all__ = ["ATCamTakeImage"]

import collections

import numpy as np

from lsst.ts.standardscripts.auxtel.latiss import LATISS
from lsst.ts.scriptqueue.base_script import BaseScript
from lsst.ts import salobj

import SALPY_ATCamera
import SALPY_ATSpectrograph


class ATCamTakeImage(BaseScript):
    """ Take a series of images with the ATCamera with set exposure times.

    Parameters
    ----------
    index : `int`
        SAL index of this Script

    Notes
    -----
    **Checkpoints**

    * exposure {n} of {m}: before sending the ATCamera ``takeImages`` command
    """
    def __init__(self, index):
        super().__init__(index=index, descr="Test ATCamTakeImage",
                         remotes_dict=dict(atcam=salobj.Remote(SALPY_ATCamera),
                                           atspec=salobj.Remote(SALPY_ATSpectrograph)))

        self.latiss = LATISS(atcam=self.atcam,
                             atspec=self.atspec)
        self.cmd_timeout = 60.  # command timeout (sec)
        # large because of an issue with one of the components

    async def configure(self, nimages=1, exp_times=0., shutter=False,
                        groupid='',
                        filter=None,
                        grating=None,
                        linear_stage=None):
        """Configure script.

        Parameters
        ----------
        nimages : `int`
            Number of images to be taken on the stress test, must be
            larger than zero.
            Ignored if ``exp_times`` is a sequence.
        exp_times : `float` or `List` [ `float` ]
            Exposure times (in seconds) for the image sequence.
            Either a single float (same exposure time for all images)
            or a list with the exposure times of each image.
            If exp_times is a list, nimages is ignored, must be equal to or
            larger then zero.
        shutter : `bool`
            Open the shutter?
        groupid : `str`
            A string that will be mapped to the GROUPID entry in the image
            header.
        filter : `None` or `int` or `str`
            Filter id or name. If `None` (default), do not change the filter.
        grating : `None` or `int` or `str`
            Grating id or name.  If `None` (default), do not change the grating.
        linear_stage : `None` or `float`
            Linear stage position.  If `None` (default), do not change the
            linear stage.

        Raises
        ------
        ValueError
            If input parameters outside valid ranges.
        """
        self.log.info("Configure started")

        # make exposure time a list with size = nimages, if it is not
        if isinstance(exp_times, collections.Iterable):
            if len(exp_times) == 0:
                raise ValueError(f"exp_times={exp_times}; must provide at least one value")
            self.exp_times = [float(t) for t in exp_times]
        else:
            if nimages < 1:
                raise ValueError(f"nimages={nimages} must be > 0")
            self.exp_times = [float(exp_times)]*nimages

        if np.min(self.exp_times) < 0:
            raise ValueError(f"Exposure times {exp_times} must be >= 0")

        self.shutter = bool(shutter)
        self.imageSequenceName = str(groupid)

        self.filter = filter
        self.grating = grating
        self.linear_stage = linear_stage

        self.log.info(f"exposure times={self.exp_times}, "
                      f"shutter={self.shutter}, "
                      f"image_name={self.imageSequenceName}"
                      f"filter={self.filter}"
                      f"grating={self.grating}"
                      f"linear_stage={self.linear_stage}")

    def set_metadata(self, metadata):
        nimages = len(self.exp_times)
        mean_exptime = np.mean(self.exp_times)
        metadata.duration = (mean_exptime + self.readout_time +
                             self.shutter_time*2 if self.shutter else 0) * nimages

    async def run(self):
        nimages = len(self.exp_times)
        for i, exposure in enumerate(self.exp_times):
            await self.checkpoint(f"exposure {i+1} of {nimages}")
            end_readout = await self.latiss.take_image(exptime=exposure,
                                                       shutter=self.shutter,
                                                       image_seq_name=self.imageSequenceName,
                                                       filter=self.filter,
                                                       grating=self.grating,
                                                       linear_stage=self.linear_stage)
            self.log.debug(f"Took {end_readout.imageName}")