from qtpy.QtWidgets import QWidget, QLineEdit, QHBoxLayout, QLabel, QMessageBox
from txgcv.base import Parameter


class ParameterEditBox(QWidget):

    def __init__(self, name: str, para: Parameter, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if para.type not in ["LIST_OF_INT", "LIST_OF_FLOAT", int, float]:
            raise ValueError(f"{self.__class__.__name__} does not support parameter of type {para.type}")
        self._parameter = para
        self._name = name
        self.value_input = QLineEdit(self)
        self._set_text()
        self.value_input.editingFinished.connect(self._update_value)

        layout = QHBoxLayout(self)
        self.value_input.setMaximumWidth(70)
        self.value_input.setFixedWidth(70)
        layout.addWidget(QLabel(self._name))
        layout.addWidget(self.value_input)
        layout.setContentsMargins(0,0,0,0)
    
    def _set_text(self):
        if isinstance(self._parameter.type, str) and "LIST" in self._parameter.type:
            self.value_input.setText(", ".join(list(map(str, self._parameter.value))))
        else:
            self.value_input.setText(str(self._parameter.value))
    
    def _update_value(self):
        text = self.value_input.text()
        try:
            if self._parameter.type == "LIST_OF_INT":
                self._parameter.value = list(map(int, text.split(",")))
            elif self._parameter.type == "LIST_OF_FLOAT":
                self._parameter.value = list(map(float, text.split(",")))
            elif self._parameter.type is float:
                self._parameter.value = float(text)
            elif self._parameter.type is int:
                self._parameter.value = int(text)
        except Exception as e:
            self._set_text()
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle('Setting Error')
            msg.setText('Illegal Parameter Setting')
            msg.setInformativeText(f"{text} is illegal for the parameter.<br>" + str(e))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.show()
