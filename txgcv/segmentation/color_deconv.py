import numpy as np
from typing import Dict, Tuple
from txgcv.base import Algorithm, Parameter


class ColorDeconvSvd(Algorithm):
    """Color deconvolution based on SVD

    based on paper: A method for normalizing histology slides for quantitative analysis
    https://ieeexplore.ieee.org/document/5193250

    """

    _param_dict: Dict[str, Parameter] = {
        "od_threshold": Parameter(
            value=0.1,
            val_type=float,
            val_range=[0, 1],
            info="lower limit of optical density to paticipate single value decomposition for stability reason",
        ),
        "angle_threshold": Parameter(
            value=1,
            val_type=float,
            val_range=[0, 100],
            info="percentail of angle of color vector to decide two base color vector",
        ),
        "sampling": Parameter(
            value=3,
            val_type=int,
            val_range=[1, np.inf],
            info="pixel sampling rate for single value decomposition",
        ),
    }

    def __init__(self, img: np.ndarray = None) -> None:
        super().__init__()
        self._img = img

    def set_image(self, img: np.ndarray) -> None:
        h, w, c = img.shape
        if h == 3:
            img = np.swapaxes(img, 0, 1)
            img = np.swapaxes(img, 1, 2)
        elif c != 3:
            raise ValueError(f"image must have RGB channels but get {c} channels")
        self._img = (img + 1) / 256

    def color_deconv(self) -> Tuple[np.ndarray, np.ndarray]:
        h, w, c = self._img.shape
        od = -np.log(self._img)
        od_flat = od.reshape((-1, 3))
        mask = np.any(od_flat > self._param_dict["od_threshold"].value, axis=1)
        od_flat = od_flat[mask]

        u, s, vh = np.linalg.svd(od_flat[::3], full_matrices=False,)

        project = np.dot(od_flat, vh[:2, :].T)
        angle = np.arctan(project[:, 1] / project[:, 0])
        angle_min = np.percentile(angle, self._param_dict["angle_threshold"].value)
        angle_max = np.percentile(
            angle, 100 - self._param_dict["angle_threshold"].value
        )
        v1 = np.cos(angle_min) * vh[0, :] + np.sin(angle_min) * vh[1, :]
        v2 = np.cos(angle_max) * vh[0, :] + np.sin(angle_max) * vh[1, :]
        base = np.array([v1, v2]).T
        stain_deconv = np.linalg.lstsq(base, od.reshape(-1, 3).T, rcond=None)[0]
        if v1[0] < v2[0]:
            hemo_idx = 0
            eosin_idx = 1
            hemo_vec = v1
            eosin_vec = v2
        else:
            hemo_idx = 1
            eosin_idx = 0
            hemo_vec = v2
            eosin_vec = v1
        
        hemo_od = hemo_vec[None, :] * stain_deconv[hemo_idx, :][..., None]
        eosin_od = eosin_vec[None, :] * stain_deconv[eosin_idx, :][..., None]
        hemo_rgb = np.exp(-hemo_od).reshape(h, w, c)
        eosin_rgb = np.exp(-eosin_od).reshape(h, w, c)
        return (hemo_rgb, eosin_rgb)
