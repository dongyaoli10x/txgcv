import numpy as np
import time
import random
import SimpleITK as sitk
from typing import List, Tuple, Callable, Dict
from txgcv.base import Algorithm, Parameter


class ImageRegister(Algorithm):

    _param_dict = {
        "sampling_rate": Parameter(
            value=0.01,
            val_type=float,
            val_range=[0, 1],
            info="pixel sampling rate when calculating metric",
        ),
        "num_hist_bin": Parameter(
            value=60,
            val_type=int,
            val_range=[0, 256],
            info="number of histogram bin used in mutual information computation",
        ),
        "learning_rate": Parameter(
            value=1.0,
            val_type=float,
            val_range=[0, np.inf],
            info="learning rate of gradient descent",
        ),
        "min_step": Parameter(
            value=0.01,
            val_type=float,
            val_range=[0, np.inf],
            info="minimum step of step gradient descent",
        ),
        "num_iter": Parameter(
            value=100,
            val_type=int,
            val_range=[1, np.inf],
            info="maximum iteration of gradient descent",
        ),
        "grad_tol": Parameter(
            value=1e-8,
            val_type=float,
            val_range=[0, np.inf],
            info="gradient tolerance to determine convergence",
        ),
        "relax_factor": Parameter(
            value=0.5,
            val_type=float,
            val_range=[0, 1],
            info="relaxation factor of learning rate of gradient descent",
        ),
        "shrink_factor": Parameter(
            value=[4, 2, 1],
            val_type="LIST_OF_INT",
            val_range=[0, np.inf],
            info="shrink factor for multi resolution iteration",
        ),
        "smooth_sigma": Parameter(
            value=[2, 1, 0],
            val_type="LIST_OF_INT",
            val_range=[0, np.inf],
            info="sigma of smoothing Gaussian kernal used at each resolution",
        ),
    }

    def __init__(
        self, moving_img: np.ndarray = None, fixed_img: np.ndarray = None
    ) -> None:
        super().__init__()
        self.set_moving_img(moving_img)
        self.set_fixed_img(fixed_img)

    def set_moving_img(self, img: np.ndarray) -> None:
        if img is None:
            self._moving_img = None
        else:
            self._moving_img = sitk.GetImageFromArray(img)

    def set_fixed_img(self, img: np.ndarray) -> None:
        if img is None:
            self._fixed_img = None
        else:
            self._fixed_img = sitk.GetImageFromArray(img[1, :, :])

    def keypoint_initialize(
        self, moving_kp: List[Tuple[float, float]], fixed_kp: List[Tuple[float, float]]
    ) -> np.ndarray:

        fix_data = fixed_kp.flatten()
        n = len(fix_data)
        mv_data = np.zeros((n, 6))
        mv_data[0::2, 2] = 1
        mv_data[1::2, 5] = 1
        mv_data[0::2, 0] = moving_kp[:, 0]
        mv_data[0::2, 1] = moving_kp[:, 1]
        mv_data[1::2, 3] = moving_kp[:, 0]
        mv_data[1::2, 4] = moving_kp[:, 1]
        transform = np.linalg.lstsq(mv_data, fix_data)[0]
        scale = np.sqrt(
            np.abs(transform[0] * transform[4] - transform[1] * transform[3])
        )
        if transform[0] * transform[4] < 0:
            mirror = -1
        else:
            mirror = 1
        cos_theta = 0.5 * (transform[0] / mirror + transform[4]) / scale
        sin_theta = 0.5 * (transform[3] - transform[1]) / scale
        theta = np.arctan2(sin_theta, cos_theta)
        trans_x = transform[2]
        trans_y = transform[5]

        init_transform = sitk.Similarity2DTransform()
        init_transform.SetScale(scale)
        init_transform.SetAngle(theta)
        init_transform.SetTranslation([trans_x, trans_y])

        # if mirror == -1:
        #     print("flipping")
        #     self._moving_img = self._moving_img[:, ::-1]

        self.moving_resampled = sitk.Resample(
            self._moving_img,
            # self.fix_resampled,
            self._fixed_img,
            init_transform,
            sitk.sitkLinear,
            0.0,
            self._moving_img.GetPixelID(),
        )

        checker_img = sitk.CheckerBoard(
            self._fixed_img, self.moving_resampled, [20, 20]
        )
        checker_img = sitk.GetArrayFromImage(checker_img)
        self._init_transform = init_transform
        return checker_img

    def regist(self, live_optimize_plot_handle: Callable = None) -> np.ndarray:
        registration_method = sitk.ImageRegistrationMethod()
        registration_method.SetMetricAsMattesMutualInformation(
            numberOfHistogramBins=self._param_dict["num_hist_bin"].value
        )
        registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
        registration_method.SetMetricSamplingPercentage(
            self._param_dict["sampling_rate"].value
        )
        registration_method.SetInterpolator(sitk.sitkLinear)

        registration_method.SetOptimizerAsRegularStepGradientDescent(
            learningRate=self._param_dict["learning_rate"].value,
            minStep=self._param_dict["min_step"].value,
            numberOfIterations=self._param_dict["num_iter"].value,
            gradientMagnitudeTolerance=self._param_dict["grad_tol"].value,
            relaxationFactor=self._param_dict["relax_factor"].value,
        )
        registration_method.SetOptimizerScalesFromPhysicalShift()

        registration_method.SetInitialTransform(self._init_transform, inPlace=False)
        registration_method.SetShrinkFactorsPerLevel(
            shrinkFactors=self._param_dict["shrink_factor"].value
        )
        registration_method.SetSmoothingSigmasPerLevel(
            smoothingSigmas=self._param_dict["smooth_sigma"].value
        )
        registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

        def start():
            global metric_values, multires_iterations
            metric_values = []
            multires_iterations = []

        def end():
            global metric_values, multires_iterations
            del metric_values
            del multires_iterations

        def res():
            pass

        def record_metric(registration_method):
            global metric_values, multires_iterations
            multires_iterations.append(len(metric_values))
            metric_values.append(registration_method.GetMetricValue())
            if live_optimize_plot_handle is not None:
                live_optimize_plot_handle((multires_iterations, metric_values))

        registration_method.AddCommand(sitk.sitkStartEvent, start)
        registration_method.AddCommand(sitk.sitkEndEvent, end)
        registration_method.AddCommand(sitk.sitkMultiResolutionIterationEvent, res)
        registration_method.AddCommand(
            sitk.sitkIterationEvent, lambda: record_metric(registration_method)
        )

        final_transform = registration_method.Execute(
            sitk.Cast(self._fixed_img, sitk.sitkFloat32),
            sitk.Cast(self._moving_img, sitk.sitkFloat32),
        )
        moving_resampled = sitk.Resample(
            self._moving_img,
            self._fixed_img,
            final_transform,
            sitk.sitkLinear,
            0.0,
            self._moving_img.GetPixelID(),
        )

        checker_img = sitk.CheckerBoard(self._fixed_img, moving_resampled, [20, 20])
        checker_img = sitk.GetArrayFromImage(checker_img)
        return checker_img
