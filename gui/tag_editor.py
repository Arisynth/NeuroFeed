from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QLineEdit, QLabel, QScrollArea, QSizePolicy, 
                            QCompleter, QFrame, QLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QPoint
from PyQt6.QtGui import QColor
from core.localization import get_text  # 添加本地化导入

# Custom FlowLayout for tag wrapping
class QFlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.itemList = []
        self.m_hSpace = spacing
        self.m_vSpace = spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def horizontalSpacing(self):
        if self.m_hSpace >= 0:
            return self.m_hSpace
        else:
            return 0

    def verticalSpacing(self):
        if self.m_vSpace >= 0:
            return self.m_vSpace
        else:
            return 0

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().left(), 2 * self.contentsMargins().top())
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(+left, +top, -right, -bottom)
        x = effective.x()
        y = effective.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.horizontalSpacing()
            spaceY = self.verticalSpacing()

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effective.right() and lineHeight > 0:
                x = effective.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom

class TagWidget(QFrame):
    """Widget representing a single tag with delete button"""
    delete_clicked = pyqtSignal(str)
    
    def __init__(self, tag_text, parent=None):
        super().__init__(parent)
        self.tag_text = tag_text
        
        # 更新样式 - 调整透明度为80%
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 0.6);  /* 修改透明度为60% */
                color: white;
                border-radius: 4px;
                padding: 2px;
                margin: 2px;
                font-weight: bold;
            }
            QFrame:hover {
                background-color: rgba(45, 45, 45, 0.9);  /* 修改透明度为90% */
            }
            QPushButton {
                border: none;
                color: rgba(255, 255, 255, 0.6);  /* 保持60%透明度 */
                background: transparent;
                padding: 0px 2px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: rgba(255, 0, 0, 0.9);  /* 修改为90%透明度 */
            }
            QLabel {
                color: white;
            }
        """)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 2, 2)
        layout.setSpacing(2)
        
        # Label for tag text
        label = QLabel(tag_text)
        label.setStyleSheet("background: transparent;")
        
        # Delete button
        delete_btn = QPushButton("✕")
        delete_btn.setFixedSize(16, 16)
        delete_btn.clicked.connect(self.on_delete)
        
        layout.addWidget(label)
        layout.addWidget(delete_btn)
        
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    
    def on_delete(self):
        """Emit signal when delete button is clicked"""
        self.delete_clicked.emit(self.tag_text)

class TagEditor(QWidget):
    """Widget for editing a list of tags"""
    tags_changed = pyqtSignal(list)
    
    def __init__(self, parent=None, rows=3):
        super().__init__(parent)
        
        # 将标签建议翻译为当前语言
        self.common_tags = [
            get_text("tag_news"), get_text("tag_politics"), 
            get_text("tag_finance"), get_text("tag_sports"),
            get_text("tag_technology"), get_text("tag_entertainment"),
            get_text("tag_education"), get_text("tag_health"),
            get_text("tag_culture"), get_text("tag_travel"),
            get_text("tag_automotive"), get_text("tag_real_estate"),
            get_text("tag_electronics"), get_text("tag_fashion")
        ]
        
        # Current tags
        self.tags = []
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Input area
        input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText(get_text("add_tag_placeholder"))
        self.tag_input.returnPressed.connect(self.add_current_tag)
        
        # Add autocomplete for common tags
        completer = QCompleter(self.common_tags)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.tag_input.setCompleter(completer)
        
        add_btn = QPushButton(get_text("add"))
        add_btn.clicked.connect(self.add_current_tag)
        
        input_layout.addWidget(self.tag_input)
        input_layout.addWidget(add_btn)
        
        # Tags area with flow layout for wrapping
        self.tags_container = QWidget()
        # 确保标签容器可以自由扩展高度，但首选按宽度约束
        self.tags_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        self.tags_layout = QFlowLayout(self.tags_container)
        self.tags_layout.setSpacing(4)
        
        # Add a scroll area to contain tags - 改进滚动区域配置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 设置滚动区域Frame样式为无边框，更美观
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # 设置高度基于rows参数，但允许在必要时滚动
        scroll_area.setMinimumHeight(40 * rows)
        scroll_area.setWidget(self.tags_container)
        
        main_layout.addLayout(input_layout)
        main_layout.addWidget(scroll_area)
    
    def add_current_tag(self):
        """Add the current tag from input field"""
        tag = self.tag_input.text().strip()
        if tag and tag not in self.tags:
            self.add_tag(tag)
            self.tag_input.clear()
    
    def add_tag(self, tag):
        """Add a tag to the editor"""
        if tag in self.tags:
            return
        
        self.tags.append(tag)
        
        tag_widget = TagWidget(tag)
        tag_widget.delete_clicked.connect(self.remove_tag)
        
        self.tags_layout.addWidget(tag_widget)
        
        # 强制更新标签容器的布局，确保滚动条正确响应
        self.tags_container.updateGeometry()
        
        self.tags_changed.emit(self.tags)
    
    def remove_tag(self, tag):
        """Remove a tag from the editor"""
        if tag in self.tags:
            self.tags.remove(tag)
            
            # Remove the tag widget
            for i in range(self.tags_layout.count()):
                widget = self.tags_layout.itemAt(i).widget()
                if isinstance(widget, TagWidget) and widget.tag_text == tag:
                    widget.setParent(None)
                    break
            
            # 强制更新标签容器的布局，确保滚动条正确响应
            self.tags_container.updateGeometry()
            
            self.tags_changed.emit(self.tags)
    
    def set_tags(self, tags):
        """Set the current tags"""
        # Clear existing tags
        self.clear()
        
        # Add new tags
        for tag in tags:
            self.add_tag(tag)
    
    def get_tags(self):
        """Get the current list of tags"""
        return self.tags
    
    def clear(self):
        """Remove all tags"""
        self.tags = []
        
        # Remove all tag widgets
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        # 强制更新标签容器的布局，确保滚动条正确响应
        self.tags_container.updateGeometry()
        
        self.tags_changed.emit(self.tags)
