import os
import sys
import json
import requests
import datetime
from PyQt5.QtCore import QTimer, QDateTime, QSettings, QSize
from PyQt5.QtGui import QPainter, QColor, QBrush, QFont, QTextDocument
from PyQt5 import uic, QtChart, QtCore
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QCategoryAxis
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem, QListWidget, QTextEdit

current_path = os.path.abspath(__file__)
parent_path = os.path.dirname(current_path)

settings = QSettings("sven", "fund-client")
SETTINGS_KEYS = {
    "win_transparency_key": "winTransparencyValue",
    "concern_funds_key": "concernFunds"
}
# 初始化
if not settings.value(SETTINGS_KEYS["concern_funds_key"]):
    settings.setValue(SETTINGS_KEYS["concern_funds_key"], {})


class ChartView(QChartView):
    mouseMoved = QtCore.pyqtSignal(QtCore.QPoint)

    def mouseMoveEvent(self, event):
        self.mouseMoved.emit(event.pos())
        return QChartView.mouseMoveEvent(self, event)


class Chart(QChart):
    # ...

    def mouseMoved(self, pos):
        print("Chart.mouseMoved parent coord domain: ", pos)
        print("Chart.mouseMoved own coord domain:", self.mapFromParent(pos))
        print("chart.mouseMoved line series coord domain:", self.mapToValue(self.mapFromParent(pos), self.series()[0]))


def create_chart():
    chart = QChart()
    chart_view = QChartView(chart)
    # chart_view.mouseMoved.connect(chart_view.chart().mouseMoved)
    chart_view.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
    chart.setAnimationOptions(QChart.AllAnimations)  # 动态展示
    chart.legend().setVisible(False)
    chart.setBackgroundBrush(QBrush(QColor("#fce5cd")))  # 改变图背景色
    title_font = QFont('Sergoe UI', 12)
    title_font.setWeight(QFont.Bold)
    chart.setTitleFont(title_font)
    return chart, chart_view


def create_linechart(chart):
    series = QtChart.QLineSeries(chart)
    return series


class ItemWidget(QWidget):
    def __init__(self, chart_frame, item, list_widget, fund_code, timer, *args, **kwargs):
        super(ItemWidget, self).__init__(*args, **kwargs)
        self.list_widget = list_widget
        self._item = item
        self.fund_code = fund_code
        self.timer = timer
        self.setMaximumSize(520, 300)
        layout = QVBoxLayout(self)  # 总体是垂直布局
        # 趋势图
        layout.addWidget(chart_frame)

        # 操作按钮
        flayout = QHBoxLayout()  # 水平布局
        # flayout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        flayout.addStretch(1)  # 伸缩量设置为1
        delete_button = QPushButton("删除", self, clicked=self.delete_item)
        delete_button.setMaximumWidth(50)
        flayout.addWidget(delete_button)
        layout.addLayout(flayout)

    def delete_item(self):
        # 根据item得到它对应的行数
        row = self.list_widget.indexFromItem(self._item).row()
        # 删除item
        item = self.list_widget.takeItem(row)
        # 删除widget
        self.list_widget.removeItemWidget(item)
        del item
        # 删除定时任务
        self.timer.stop()
        # 删除保存的数据
        concern_funds = settings.value(SETTINGS_KEYS["concern_funds_key"])
        del concern_funds[self.fund_code]
        settings.setValue(SETTINGS_KEYS["concern_funds_key"], concern_funds)

    def sizeHint(self):
        # 每个item控件的大小
        return QSize(520, 300)


def add_chart_to_frame(code="", update_data_func=None, frame=None):
    # Create chart
    chart, chart_view = create_chart()

    if frame:
        # Create PyQt widget for painting
        my_layout = QVBoxLayout(frame)
        my_layout.addWidget(chart_view)

    if update_data_func:
        # 每60s更新一次
        timer_update_events = QTimer()
        from functools import partial
        timerCallback = partial(update_data_func, chart, chart_view, code)
        timer_update_events.timeout.connect(timerCallback)
        timer_update_events.start(60000)
        QTimer.singleShot(0, timerCallback)
    else:
        timer_update_events = None

    return chart, chart_view, timer_update_events


def reload_chart(code, chart, chart_view):
    try:
        if len(str(code)) == 6:  # 基金编号只有6位  161725
            series = create_linechart(chart)
            res = requests.get("http://www.jjmmw.com/fund/ajax/jjgz_timechart/?fund_id={}&detail=1".format(code))
            res = json.loads(res.text)
            if res:
                time_chart = res["timechart"]
                y_max = 0
                y_min = 0
                first_x_custom_value = ""
                for i in range(len(time_chart)):
                    one = time_chart[i]
                    # y轴
                    y_value = round(float(one["estchngpct"]), 2)
                    if i == 0:
                        y_min, y_max = y_value, y_value
                    else:
                        if y_value > y_max:
                            y_max = y_value
                        if y_value < y_min:
                            y_min = y_value
                    # x轴
                    # x_time = QDateTime.fromString(one["time"].split(" ")[1], "hh:mm:ss").toMSecsSinceEpoch()
                    x_time = i
                    series.append(x_time, y_value)
                chart.addSeries(series)
                chart.createDefaultAxes()  # 创建默认的轴
                # 自定义x轴
                category = ["09:30", "10:00", "10:30", "11:00", "11:30", "13:00", "13:30", "14:00", "14:30", "15:00"]
                x_len = len(category)
                x_min = chart.axisX().min()
                x_max = chart.axisX().max()
                axis_x = QCategoryAxis(chart, labelsPosition=QCategoryAxis.AxisLabelsPositionOnValue)
                if x_len < 2:
                    axis_x.append(first_x_custom_value, x_min)
                else:
                    step = (x_max - x_min) / (x_len - 1)
                    for i in range(len(category)):
                        axis_x.append(category[i], x_min + i * step)
                axis_x.setTickCount(x_len)  # 设置刻度个数
                axis_x.setGridLineVisible(False)  # 隐藏网格线条
                chart.setAxisX(axis_x, series)
                axis_y = chart.axisY()
                axis_y.setMax(y_max)
                axis_y.setMin(y_min)
                chart.setTitle(res["fundname"])
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


class SearchWin(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("search.ui", self)

        # 栅格布局设置间隔
        self.centralwidget.setContentsMargins(5, 5, 5, 5)

        # 添加图表至qFrame上
        self.chart, self.chart_view, no_timer = add_chart_to_frame(frame=self.searchResult)

        # 输入框设置事件
        self.lineEdit.textChanged.connect(self.input_change)

        # 保存按钮
        self.saveButton.clicked.connect(self.save)

    def closeEvent(self, event):
        self.chart.removeAllSeries()
        self.lineEdit.clear()

    def input_change(self, text):
        reload_chart(text, self.chart, self.chart_view)

    def save(self):
        concern_funds = settings.value(SETTINGS_KEYS["concern_funds_key"])
        search_text = self.lineEdit.text()
        if search_text in concern_funds:
            QMessageBox.information(self, "", "该基金已经保存", QMessageBox.Yes, QMessageBox.Yes)
        else:
            concern_funds[search_text] = ""
            settings.setValue(SETTINGS_KEYS["concern_funds_key"], concern_funds)
            self.main_win_instance.reload_concern_funds()  # 重新加载
            self.lineEdit.clear()
            self.close()

    def open(self, main_win_instance):
        self.main_win_instance = main_win_instance
        self.setWindowFlags(self.windowFlags() & QtCore.Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowMinMaxButtonsHint)
        self.show()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main_dev.ui", self)

        # 栅格布局设置间隔
        # self.centralwidget.setContentsMargins(5, 5, 5, 5)

        # 透明度
        self.setWindowOpacity(float(settings.value(SETTINGS_KEYS["win_transparency_key"], 0.99)))

        # 菜单栏
        self.adjust_transparency_win = AdjustTransparencyWin()
        self.adjust_transparency.triggered.connect(self.open_adjust_transparency_win)  # 调节透明度

        # 搜索
        self.search_win = SearchWin()
        self.search.triggered.connect(self.open_search_win)  # 调节透明度

        # 自己关注的基金
        self.reload_concern_funds()

    def reload_concern_funds(self):
        concern_funds = settings.value(SETTINGS_KEYS["concern_funds_key"])
        grid = self.centralwidget.layout()
        if not concern_funds:
            text_edit = QTextEdit()
            content = "当前没有收藏的基金，请在“开始->搜索”中搜索自己关注的基金并保存"
            text_edit.setText(content)
            text_edit.setAlignment(QtCore.Qt.AlignCenter)
            width = text_edit.fontMetrics().width(content)
            text_edit.setMinimumWidth(width)
            text_edit.setReadOnly(True)
            grid.addWidget(text_edit)
        else:
            # concern_funds = ["161725", "161726"]
            names = self.__dict__
            list_widget = QListWidget()
            list_widget.setFrameShape(list_widget.NoFrame)  # 无边框
            list_widget.setFlow(list_widget.LeftToRight)  # 从左到右
            list_widget.setWrapping(True)  # 这三个组合可以达到和FlowLayout一样的效果
            list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            list_widget.setResizeMode(list_widget.Adjust)
            # list_widget.resize(800, 600)
            grid.addWidget(list_widget, 0, 0)
            for fund_code in concern_funds:
                chart, chart_view, timer = add_chart_to_frame(fund_code, self.update_data)
                names['own_timer_events_' + fund_code] = timer
                item = QListWidgetItem(list_widget)
                iwidget = ItemWidget(chart_view, item, list_widget, fund_code, timer)
                item.setSizeHint(iwidget.sizeHint())
                list_widget.setItemWidget(item, iwidget)

    def update_data(self, chart, chart_view, code=""):
        """
        更新图表数据

        :param chart:
        :param chart_view:
        :param code:
        :return:
        """
        if code:
            reload_chart(code, chart, chart_view)
        else:
            input_text = self.lineEdit.text()
            if input_text:
                reload_chart(input_text, chart, chart_view)

    def open_adjust_transparency_win(self):
        self.adjust_transparency_win.open(self)

    def open_search_win(self):
        self.search_win.open(self)


if __name__ == "__main__":
    App = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(App.exec_())
