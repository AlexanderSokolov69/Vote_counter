import sys

from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow
from test import Ui_MainWindow

class MyWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        WIDTH = self.screen().size().width()
        HEIGHT = self.screen().size().height()
        screen_w, screen_h = self.width(), self.height()
        self.setGeometry(WIDTH // 2 - screen_w // 2,
                         HEIGHT // 2 - screen_h // 2,
                         screen_w, screen_h)
        self.setWindowTitle('Название программы')


def except_hook(exc_type, exc_value, exc_tb):
    sys.__excepthook__(exc_type, exc_value, exc_tb)


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    win = MyWindow()
    win.show()
    sys.exit(app.exec())
