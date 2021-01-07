import numpy as np
from skimage import io

from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QFileDialog,
)

from napari_plugin_engine import napari_hook_implementation
from napari.qt.threading import thread_worker
from txgcv.segmentation import ColorDeconvSvd
from txgcv.plugins.base import ParameterEditBox


@napari_hook_implementation(specname="napari_experimental_provide_dock_widget")
def color_deconv_svd_plugin(viewer):
    return [(ColorDeconvSvdWidget(viewer), {"area": "right", "name": "ImageRegister"})]


class ColorDeconvSvdWidget(QWidget):
    """Plugin UI for color deconvolution of H&E image
    """

    def __init__(self, viewer) -> None:
        super().__init__()
        self._algo = ColorDeconvSvd()
        self._viewer = viewer
        layout = QVBoxLayout()

        self._parameter_button = QPushButton("Parameters", self)
        self._parameter_button.clicked.connect(self._show_parameter)
        self._load_img_button = QPushButton("Load Image", self)
        self._load_img_button.clicked.connect(self.load_image)
        self._deconv_button = QPushButton("H&E Color Deconvolution", self)
        self._deconv_button.clicked.connect(self._deconv)

        control_panel = QWidget()
        control_layout = QVBoxLayout()
        control_layout.addWidget(self._parameter_button)
        control_layout.addWidget(self._load_img_button)
        control_layout.addWidget(self._deconv_button)
        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)
        self.setLayout(layout)

    def load_image(self) -> None:
        path = QFileDialog.getOpenFileName(
            self, "Select H&E RGB Image", filter="Image files (*.tif *.tiff *.png *.jpg)"
        )
        if path[0]:
            filename = path[0]
        else:
            return
        img = self._load_img(filename)
        self._algo.set_image(img)
        self._viewer.add_image(img, name="H&E Image")
        
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

        for param_name, param_obj in self._algo.parameter.items():
            widget = ParameterEditBox(param_name, param_obj)
            self._para_container.layout().addWidget(widget)

        self._para_container.resize(self._para_container.sizeHint().width()*1.5,
                               self._para_container.sizeHint().height()*1.5)
        self._para_container.show()

    def _deconv(self) -> None:
        def show_result(image_pair):
            self._viewer.add_image(image_pair[0], name="Hematoxylin")
            self._viewer.add_image(image_pair[1], name="Eosin")

        @thread_worker(connect={"returned": show_result})
        def run():
            hemo, eosin = self._algo.color_deconv()
            return (hemo, eosin)

        run()
