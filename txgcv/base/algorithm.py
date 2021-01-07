from typing import Dict
from txgcv.base.parameter import Parameter


class Algorithm(object):
    
    _param_dict: Dict[str, Parameter] = {}

    def __init__(self) -> None:
        pass

    def set_parameter(self, param_dict: dict):
        for key, value in param_dict.items():
            if key in self._param_dict:
                self._param_dict[key].value = value
            else:
                raise KeyError(f"{key} is not a valide parameter of {self.__class__.__name__}")

    @property
    def parameter(self) -> Dict[str, Parameter]:
        return self._param_dict