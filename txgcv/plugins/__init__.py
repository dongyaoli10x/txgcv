try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

# replace the asterisk with named imports
# from .txgcv import napari_experimental_provide_dock_widget
# from .test_plugin1 import test_plugin_one
# from .test_plugin2 import test_plugin_two


# __all__ = ["test_plugin_one", "test_plugin_two"]
