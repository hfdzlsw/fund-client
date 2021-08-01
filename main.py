import sys
import json
import requests
import datetime
from PyQt5.QtCore import QTimer, QDateTime, QSettings
from PyQt5.QtGui import QPainter, QColor, QBrush
from PyQt5 import uic, QtChart, QtCore
from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout

settings = QSettings("sven", "fund-client")
SETTINGS_KEYS = {
    "win_transparency_key": "winTransparencyValue"
}


def reload_chart(instance, code):
    try:
        if len(str(code)) == 6:  # 基金编号只有6位
            instance.series.clear()
            res = requests.get("http://www.jjmmw.com/fund/ajax/jjgz_timechart/?fund_id={}&detail=1".format(code))
            res = json.loads(res.text)
            if res:
                time_chart = res["timechart"]
                y_max = 0
                y_min = 0
                for i in range(len(time_chart)):
                        one = time_chart[i]
                        y_value = round(float(one["estchngpct"]), 2)
                        if i == 0:
                            y_min, y_max = y_value, y_value
                        else:
                            if y_value > y_max:
                                y_max = y_value
                            if y_value < y_min:
                                y_min = y_value
                        x_time = QDateTime.fromString(one["time"].split(" ")[1], "hh:mm:ss").toMSecsSinceEpoch()
                        instance.series.append(x_time, y_value)
                instance.axis_y.setMax(y_max)
                instance.axis_y.setMin(y_min)
                instance.axis_x.setTitleText(res["fundname"])
    except Exception as e:
        raise e


class AdjustTransparencyWin(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("adjust_transparency.ui", self)

    def open(self, main_win_instance):
        self.main_win_instance = main_win_instance
        self.setWindowFlags(self.windowFlags() & QtCore.Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMinMaxButtonsHint)
        self.horizontalSlider.valueChanged.connect(self.slider_value_change)
        self.horizontalSlider.setValue(float(settings.value(SETTINGS_KEYS["win_transparency_key"], 0.99)) * 100)
        self.show()

    def slider_value_change(self):
        slider_value = self.horizontalSlider.value() / 100
        self.main_win_instance.setWindowOpacity(slider_value)
        settings.setValue(SETTINGS_KEYS["win_transparency_key"], slider_value)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)

        # Create chart
        self.chart_view = self.create_chart()
        self.series = self.create_linechart()

        self.chart_view.chart().addSeries(self.series)

        # x 轴设置
        self.axis_x = QtChart.QDateTimeAxis()
        self.axis_x.setFormat("hh:mm")
        min_time = datetime.datetime.strptime('09:30:00', '%H:%M:%S')
        max_time = datetime.datetime.strptime('15:00:00', '%H:%M:%S')
        self.axis_x.setRange(min_time, max_time)
        self.axis_x.setTickCount(12)  # 设置刻度个数
        self.chart_view.chart().addAxis(self.axis_x, QtCore.Qt.AlignBottom)
        self.series.attachAxis(self.axis_x)

        # y 轴设置
        self.axis_y = QtChart.QValueAxis()
        self.axis_y.setLabelFormat("%.2f")
        self.chart_view.chart().addAxis(self.axis_y, QtCore.Qt.AlignLeft)
        self.series.attachAxis(self.axis_y)

        # Create PyQt widget for painting
        my_layout = QVBoxLayout(self.chart)
        my_layout.addWidget(self.chart_view)

        # 每10s更新一次
        self.timer_update_events = QTimer()
        self.timer_update_events.timeout.connect(self.update_data)
        self.timer_update_events.start(60000)
        QTimer.singleShot(0, self.update_data)

        self.lineEdit.textChanged.connect(self.input_change)

        # 透明度
        self.setWindowOpacity(float(settings.value(SETTINGS_KEYS["win_transparency_key"], 0.99)))

        # 菜单栏
        self.adjust_transparency_win = AdjustTransparencyWin()
        self.adjust_transparency.triggered.connect(self.open_adjust_transparency_win)  # 调节透明度

    def update_data(self):
        input_text = self.lineEdit.text()
        if input_text:
            reload_chart(self, input_text)

    def create_chart(self):
        chart = QChart()
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        chart.setBackgroundBrush(QBrush(QColor("#fce5cd")))  # 改变图背景色
        return chart_view

    def create_linechart(self):
        series = QtChart.QLineSeries()
        return series

    def input_change(self, text):
        reload_chart(self, text)

    def open_adjust_transparency_win(self):
        self.adjust_transparency_win.open(self)


if __name__ == "__main__":
    App = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(App.exec_())
