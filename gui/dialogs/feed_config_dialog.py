from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                           QSpinBox, QPushButton, QGroupBox)
from PyQt6.QtCore import Qt
from gui.tag_editor import TagEditor
from core.localization import get_text

class FeedConfigDialog(QDialog):
    def __init__(self, parent=None, feed_url="", items_count=10, labels=None, negative_labels=None):
        super().__init__(parent)
        
        self.setWindowTitle(get_text("rss_feed_config"))
        self.resize(500, 500)  # 增加对话框高度，以容纳更大的反向标签区域
        
        layout = QVBoxLayout(self)
        
        # Feed URL
        url_layout = QHBoxLayout()
        url_label = QLabel(get_text("rss_feed_url"))
        self.url_input = QLineEdit(feed_url)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input, 1)
        
        # Items count
        count_layout = QHBoxLayout()
        count_label = QLabel(get_text("items_to_fetch"))
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 50)
        self.count_input.setValue(items_count)
        self.count_input.setSuffix(get_text("items"))
        count_layout.addWidget(count_label)
        count_layout.addWidget(self.count_input)
        count_layout.addStretch()
        
        # 标签组
        tags_group = QGroupBox(get_text("positive_interests_title"))
        tags_layout = QVBoxLayout(tags_group)
        
        # 标签说明
        tag_description = QLabel(get_text("feed_labels_desc"))
        tag_description.setWordWrap(True)
        tags_layout.addWidget(tag_description)
        
        # 创建标签编辑器
        self.tag_editor = TagEditor(rows=3)
        if labels:
            self.tag_editor.set_tags(labels)
        tags_layout.addWidget(self.tag_editor)
        
        # 反向标签组 - 调整布局，不再使用紧凑设计
        neg_tags_group = QGroupBox(get_text("negative_interests_title"))
        neg_tags_layout = QVBoxLayout(neg_tags_group)
        # 使用标准边距，不再特别减小
        neg_tags_layout.setContentsMargins(9, 9, 9, 9)  
        neg_tags_layout.setSpacing(6)  # 使用标准间距
        
        # 反向标签说明
        neg_tag_description = QLabel(get_text("feed_negative_labels_desc"))
        neg_tag_description.setWordWrap(True)
        neg_tags_layout.addWidget(neg_tag_description)
        
        # 创建反向标签编辑器 - 增加高度
        self.negative_tag_editor = TagEditor(rows=1)
        self.negative_tag_editor.setMinimumHeight(60)  # 设置最小高度而不是最大高度
        if negative_labels:
            self.negative_tag_editor.set_tags(negative_labels)
        neg_tags_layout.addWidget(self.negative_tag_editor)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton(get_text("ok"))
        self.cancel_button = QPushButton(get_text("cancel"))
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # 组装布局 - 不使用分割线，直接组织各部分
        layout.addLayout(url_layout)
        layout.addLayout(count_layout)
        layout.addWidget(tags_group)
        layout.addWidget(neg_tags_group)
        layout.addLayout(button_layout)
    
    def get_feed_url(self):
        return self.url_input.text().strip()
    
    def get_items_count(self):
        return self.count_input.value()
    
    def get_labels(self):
        return self.tag_editor.get_tags()

    def get_negative_labels(self):
        return self.negative_tag_editor.get_tags()
