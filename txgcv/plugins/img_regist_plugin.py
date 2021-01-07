import numpy as np
from skimage import io

from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QFileDialog,
)

from napari_plugin_engine import napari_hook_implementation
from napari._qt.qt_liveplot import QtLivePlotWidget
from napari.qt.threading import thread_worker
from txgcv.registration.img_regist import ImageRegister
from txgcv.plugins.base import ParameterEditBox


@napari_hook_implementation(specname="napari_experimental_provide_dock_widget")
def img_register_plugin(viewer):
    return [(RegistWidget(viewer), {"area": "right", "name": "ImageRegister"})]


class RegistWidget(QWidget):
    """Plugin UI for image registration with manual initialization
    """

    def __init__(self, viewer) -> None:
        super().__init__()
        self._register = ImageRegister()
        self._viewer = viewer
        layout = QVBoxLayout()

        self._parameter_button = QPushButton("Parameters", self)
        self._parameter_button.clicked.connect(self._show_parameter)
        self._load_mv_button = QPushButton("Load Moving Image", self)
        self._load_mv_button.clicked.connect(self.load_mv_image)
        self._load_fix_button = QPushButton("Load Fixed Image", self)
        self._load_fix_button.clicked.connect(self.load_fix_image)
        self._init_button = QPushButton("Init", self)
        self._init_button.clicked.connect(self.init_registration)
        self._regist_button = QPushButton("Register", self)
        self._regist_button.clicked.connect(self.run_registration)
        line_style = dict(marker_size=8, color="w", edge_color="w", face_color="w",)
        self._loss_plot = QtLivePlotWidget(
            vertical=False, line_style=line_style, axis_kwargs={'tick_font_size': 4}
        )

        control_panel = QWidget()
        control_layout = QHBoxLayout()
        control_layout.addWidget(self._parameter_button)
        control_layout.addWidget(self._load_mv_button)
        control_layout.addWidget(self._load_fix_button)
        control_layout.addWidget(self._init_button)
        control_layout.addWidget(self._regist_button)
        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)
        layout.addWidget(self._loss_plot)

        self.setLayout(layout)

    def load_mv_image(self) -> None:
        path = QFileDialog.getOpenFileName(
            self, "Select Moving Image", filter="Image files (*.tif *.tiff *.png *.jpg)"
        )
        if path[0]:
            filename = path[0]
        else:
            return
        moving_img = self._load_img(filename)

        self._register.set_moving_img(moving_img)
        estimate_pt_size = np.max(moving_img.shape) * 0.005
        self._viewer.add_image(moving_img, name="Moving Image")
        self._viewer.add_points(face_color="red", name="Moving Points", size=estimate_pt_size)
        
    def load_fix_image(self) -> None:
        path = QFileDialog.getOpenFileName(
            self, "Select Fixed Image", filter="Image files (*.tif *.tiff *.png *.jpg)"
        )
        if path[0]:
            filename = path[0]
        else:
            return
        fixed_img = self._load_img(filename)
        self._register.set_fixed_img(fixed_img)

        estimate_pt_size = np.max(fixed_img.shape) * 0.005
        self._viewer.add_image(fixed_img, name="Fixed Image")
        self._viewer.add_points(face_color="blue", name="Fixed Points", size=estimate_pt_size)

    def _load_img(self, filename: str) -> np.array:
        img = io.imread(filename).astype(np.float32)
        img = 255 * img / np.max(img)
        shape = img.shape
        if len(shape) == 3:
            if shape[2] <= 3:
                img = np.swapaxes(img, 1, 2)
                img = np.swapaxes(img, 0, 1)
        return img

    def _show_parameter(self):
        self._para_container = QWidget()
        self._para_container.setWindowTitle('Parameters')
        self._para_container.setLayout(QVBoxLayout())
        info = QLabel('Please set the parameters properly')
        self._para_container.layout().addWidget(info)

        for param_name, param_obj in self._register.parameter.items():
            widget = ParameterEditBox(param_name, param_obj)
            self._para_container.layout().addWidget(widget)

        self._para_container.resize(self._para_container.sizeHint().width()*1.5,
                               self._para_container.sizeHint().height()*1.5)
        self._para_container.show()

    def init_registration(self) -> None:
        def show_init(img):
            self._viewer.add_image(img, name="Initialization")

        @thread_worker(connect={"returned": show_init})
        def init():
            fixed_kp = self._viewer.layers["Moving Points"].data
            moving_kp = self._viewer.layers["Fixed Points"].data
            
            fixed_kp = fixed_kp[:, ::-1]
            moving_kp = moving_kp[:, ::-1]
            init_img = self._register.keypoint_initialize(moving_kp, fixed_kp)
            return init_img
    
        init()

    def run_registration(self) -> None:
        def final_registration(img):
            self._viewer.add_image(img, name="Registered Image")

        @thread_worker(connect={"returned": final_registration})
        def run():
            result = self._register.regist(live_optimize_plot_handle=self._loss_plot.set_data)
            return result
        try:
            run()
        except Exception as e:
            print(str(e))