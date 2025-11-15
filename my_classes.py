from PyQt6.QtWidgets import QLabel


class MyLabel(QLabel):
    def __init__(self, parent=None):
        super(MyLabel, self).__init__(parent)

    def mousePressEvent(self, event):
        print(f"x={event.pos().x()}, y={event.pos().y()}")
