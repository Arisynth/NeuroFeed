from PyQt6.QtWidgets import QMainWindow, QLabel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NewsDigest")
        self.setFixedSize(400, 300)
        self.label = QLabel("Hello, NewsDigest!", self)
        self.label.move(100, 130)