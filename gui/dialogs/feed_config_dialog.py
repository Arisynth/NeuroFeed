from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                           QSpinBox, QPushButton, QGroupBox, QSizePolicy)
from PyQt6.QtCore import Qt
from gui.tag_editor import TagEditor
from core.localization import get_text

class FeedConfigDialog(QDialog):
    def __init__(self, parent=None, feed_url="", items_count=10, labels=None, negative_labels=None):
        super().__init__(parent)
        
        self.setWindowTitle(get_text("rss_feed_config"))
        self.resize(500, 580)  # 稍微调整对话框高度
        
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
        tags_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        # 使用标准边距，但增加顶部边距避免内容与标题重叠
        tags_layout = QVBoxLayout(tags_group)
        tags_layout.setContentsMargins(9, 15, 9, 9)  # 左、上、右、下边距，增加上边距
        
        # 标签说明
        tag_description = QLabel(get_text("feed_labels_desc"))
        tag_description.setWordWrap(True)
        # 为标签描述增加一点底部间距
        tag_description.setContentsMargins(0, 0, 0, 5)
        tags_layout.addWidget(tag_description)
        
        # 创建标签编辑器
        self.tag_editor = TagEditor(rows=3)
        self.tag_editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        if labels:
            self.tag_editor.set_tags(labels)
        tags_layout.addWidget(self.tag_editor, 1)
        
        # 反向标签组
        neg_tags_group = QGroupBox(get_text("negative_interests_title"))
        neg_tags_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        # 同样调整反向标签组的边距，增加顶部边距
        neg_tags_layout = QVBoxLayout(neg_tags_group)
        neg_tags_layout.setContentsMargins(9, 15, 9, 9)  # 左、上、右、下边距，增加上边距
        
        # 反向标签说明
        neg_tag_description = QLabel(get_text("feed_negative_labels_desc"))
        neg_tag_description.setWordWrap(True)
        # 为反向标签描述增加一点底部间距
        neg_tag_description.setContentsMargins(0, 0, 0, 5)
        neg_tags_layout.addWidget(neg_tag_description)
        
        # 创建反向标签编辑器
        self.negative_tag_editor = TagEditor(rows=1)
        if negative_labels:
            self.negative_tag_editor.set_tags(negative_labels)
        neg_tags_layout.addWidget(self.negative_tag_editor, 1)
        
        # 添加组之间的间隔
        layout.setSpacing(10)  # 控制整体垂直布局的间距
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton(get_text("ok"))
        self.cancel_button = QPushButton(get_text("cancel"))
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # 组装布局 - 分配适当空间比例
        layout.addLayout(url_layout)
        layout.addLayout(count_layout)
        layout.addWidget(tags_group, 2) 
        layout.addWidget(neg_tags_group, 1) 
        layout.addLayout(button_layout)
    
    def get_feed_url(self):
        return self.url_input.text().strip()
    
    def get_items_count(self):
        return self.count_input.value()
    
    def get_labels(self):
        return self.tag_editor.get_tags()

    def get_negative_labels(self):
        return self.negative_tag_editor.get_tags()
