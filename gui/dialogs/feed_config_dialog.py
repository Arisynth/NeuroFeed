from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                            QLabel, QLineEdit, QSpinBox, QDialogButtonBox)
from PyQt6.QtCore import Qt
from gui.tag_editor import TagEditor
from core.localization import get_text

class FeedConfigDialog(QDialog):
    """Dialog to configure RSS feed settings"""
    def __init__(self, parent=None, feed_url="", items_count=10, labels=None):
        super().__init__(parent)
        self.setWindowTitle(get_text("rss_feed_config"))
        self.resize(550, 280)  # 稍微减小窗口宽度
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        # 设置标签左对齐，但字段不对齐，直接跟在标签后面
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        self.url_input = QLineEdit(feed_url)
        self.url_input.setMinimumWidth(400)  # 确保URL输入框足够宽
        
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 100)
        self.count_input.setValue(items_count)
        self.count_input.setFixedWidth(80)
        self.count_input.setSuffix(get_text("items"))
        
        form_layout.addRow(get_text("rss_feed_url"), self.url_input)
        form_layout.addRow(get_text("items_to_fetch"), self.count_input)
        
        # 标签区域标题，移除加粗
        labels_label = QLabel(get_text("interest_tags"))
        
        # 使用2行高的标签编辑器
        self.tag_editor = TagEditor(rows=2)
        if labels:
            self.tag_editor.set_tags(labels)
        
        layout.addLayout(form_layout)
        layout.addWidget(labels_label)
        layout.addWidget(self.tag_editor)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if (ok_button):
            ok_button.setAutoDefault(False)
            ok_button.setDefault(False)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(buttons)
    
    def keyPressEvent(self, event):
        """处理按键事件，阻止回车键关闭对话框"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # 如果焦点在输入框上，添加新标签而不关闭对话框
            if self.tag_editor.tag_input.hasFocus():
                self.tag_editor.add_current_tag()
                event.accept()
                return
        # 其他情况，调用父类处理
        super().keyPressEvent(event)
    
    def get_feed_url(self):
        return self.url_input.text()
    
    def get_items_count(self):
        return self.count_input.value()
    
    def get_labels(self):
        return self.tag_editor.get_tags()
