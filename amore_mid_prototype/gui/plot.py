from PyQt6 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import (
    FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure


class Canvas(QtWidgets.QDialog):
    def __init__(self, parent=None, xlabel="", ylabel=""):
        super().__init__()
        self.autoscale = True

        self.setStyleSheet("background-color: white")

        layout = QtWidgets.QVBoxLayout(self)

        self.figure = Figure(figsize=(5, 3))
        self._canvas = FigureCanvas(self.figure)
        self._axis = self._canvas.figure.subplots()
        self._axis.set_xlabel(xlabel)
        self._axis.set_ylabel(ylabel)
        self._axis.set_position([0.15, 0.15, 0.85, 0.85])
        self._axis.grid()

        (self._line,) = self._axis.plot([], [], "o")

        self._navigation_toolbar = NavigationToolbar(self._canvas, self)
        self._navigation_toolbar.setIconSize(QtCore.QSize(20, 20))
        self._navigation_toolbar.layout().setSpacing(1)

        self._autoscale_checkbox = QtWidgets.QCheckBox("Autoscale", self)
        self._autoscale_checkbox.setCheckState(QtCore.Qt.CheckState.Checked)
        self._autoscale_checkbox.setLayoutDirection(
            QtCore.Qt.LayoutDirection.RightToLeft
        )
        self._autoscale_checkbox.stateChanged.connect(self._set_autoscale)

        layout.addWidget(self._canvas)
        layout.addWidget(self._autoscale_checkbox)
        layout.addWidget(self._navigation_toolbar)

    def _set_autoscale(self):
        if self._autoscale_checkbox.isChecked():
            self.autoscale = True
        else:
            self.autoscale = False

    def update_canvas(self, x, y):
        self._line.set_data(x, y)
        self._line.figure.canvas.draw()

        if self.autoscale:
            self._axis.set_xlim((x.min(), x.max()))
            self._axis.set_ylim((y.min(), y.max()))


class Plot:
    def __init__(self, data) -> None:
        self._data = data
        keys = list(data.columns)
        keys.remove("Comment")

        self._button_plot = QtWidgets.QPushButton()
        self._button_plot.setEnabled(True)
        self._button_plot.setText("Plot")
        self._button_plot.clicked.connect(self._button_plot_clicked)

        self.create_combo_box()
        self.update_combo_box(keys)

        self._canvas = {"key.x": [], "key.y": [], "canvas": []}

    def create_combo_box(self):
        self._combo_box_x_axis = QtWidgets.QComboBox()
        self._combo_box_y_axis = QtWidgets.QComboBox()

    def update_combo_box(self, keys):
        for ki in keys:
            self._combo_box_x_axis.addItem(ki)

        for ki in keys:
            self._combo_box_y_axis.addItem(ki)

    def _button_plot_clicked(self):
        xlabel = self._combo_box_x_axis.currentText()
        ylabel = self._combo_box_y_axis.currentText()

        canvas = Canvas(self, xlabel=xlabel, ylabel=ylabel)

        self._canvas["key.x"].append(xlabel)
        self._canvas["key.y"].append(ylabel)
        self._canvas["canvas"].append(canvas)

        self.update()

        canvas.show()

    def update(self):
        for xi, yi, ci in zip(
            self._canvas["key.x"], self._canvas["key.y"], self._canvas["canvas"]
        ):
            ci.update_canvas(self.data[xi], self.data[yi])