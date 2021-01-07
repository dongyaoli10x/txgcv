from typing import Tuple, Union, Any, Type


num = Union[float, int]


def type_check(val: Any, val_type: Union[Type, str]) -> bool:
    # TODO: implement generic type checking
    return True


def range_check(val: Any, val_type: Any, val_range: Tuple[num, num]) -> bool:
    if val is None or val_range is None:
        return True
    if isinstance(val_type, str) and "LIST" in val_type:
        for i in val:
            if i < val_range[0] or i > val_range[1]:
                return False
            else:
                return True
    elif val >= val_range[0] and val <= val_range[1]:
        return True
    else:
        return False


class Parameter(object):
    def __init__(
        self,
        value: Any = None,
        val_type: Union[Type, str] = None,
        val_range: Tuple[num, num] = None,
        info: str = None,
        **kwargs,
    ):
        base_dict = {
            "value": value,
            "type": val_type,
            "range": val_range,
            "info": info,
        }
        object.__setattr__(self, "_attr_dict", base_dict)

        for key, val in kwargs.items():
            self._attr_dict[key] = val

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        elif name in self._attr_dict:
            return self._attr_dict[name]
        else:
            e = AttributeError(
                "'{}' object has no attribute '{}'".format(
                    self.__class__.__name__, name
                )
            )
            raise e

    def __setattr__(self, name, value):
        if name is "value":
            if not type_check(value, self._attr_dict["type"]):
                raise TypeError(f"{value} is not of the proper parameter type")
            if not range_check(
                value, self._attr_dict["type"], self._attr_dict["range"]
            ):
                raise ValueError(f"{value} is out of the parameter range")
            self._attr_dict["value"] = value

        elif name in self._attr_dict.keys():
            # TODO: check if type or range are valid
            self._attr_dict[name] = value
        else:
            raise KeyError(f"{name} is not a valid attribute of the parameter")

