from PyQt6.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QCheckBox, QComboBox, QPushButton, QFormLayout, 
                            QGroupBox, QWidget, QMessageBox, QSpinBox, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer
from core.config_manager import load_config, save_config, get_general_settings, update_general_settings, CONFIG_PATH  # Import CONFIG_PATH
import requests
import json
from gui.tag_editor import TagEditor  # 导入标签编辑器
from core.email_sender import EmailSender
from core.encryption import encrypt_password, decrypt_password
from core.localization import get_text, get_current_language, set_language

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text("settings"))
        self.setMinimumSize(500, 400)
        
        # 添加样式表确保下拉列表字体一致，添加复选框样式修正
        self.setStyleSheet("""
            QComboBox {
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                font-size: 12px;
            }
            QCheckBox {
                background: transparent;
                border: none;
            }
            QCheckBox:focus {
                background: transparent;
                border: none;
            }
        """)
        
        # 记录原始配置用于检测更改
        self.config = load_config()
        self.original_config = self._get_serializable_config(self.config)
        self.global_settings = self.config.get("global_settings", {})
        
        # 标记是否有未保存的更改
        self.has_unsaved_changes = False
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Email settings tab
        self.create_email_tab()
        
        # AI settings tab
        self.create_ai_tab()
        
        # 添加用户兴趣标签设置页
        self.create_interests_tab()
        
        # General settings tab
        self.create_general_tab()
        
        main_layout.addWidget(self.tabs)
        
        # Status message (轻提示)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_email_btn = QPushButton(get_text("test_email"))
        self.save_btn = QPushButton(get_text("save"))
        self.close_btn = QPushButton(get_text("close"))
        
        self.test_email_btn.clicked.connect(self.test_email_settings)
        self.save_btn.clicked.connect(self.save_settings)
        self.close_btn.clicked.connect(self.close_window)
        
        button_layout.addWidget(self.test_email_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        
        # 连接信号槽来检测更改
        self.connect_change_signals()
    
    def _get_serializable_config(self, config):
        """创建配置的可序列化副本以进行比较"""
        return json.dumps(config, sort_keys=True)
    
    def connect_change_signals(self):
        """连接所有可能导致更改的控件信号"""
        # Email设置
        self.smtp_server.textChanged.connect(self.mark_as_changed)
        self.smtp_port.valueChanged.connect(self.mark_as_changed)
        self.smtp_security.currentIndexChanged.connect(self.mark_as_changed)
        self.sender_email.textChanged.connect(self.mark_as_changed)
        self.email_password.textChanged.connect(self.mark_as_changed)
        self.remember_password.stateChanged.connect(self.mark_as_changed)
        
        # AI设置
        self.ai_provider.currentIndexChanged.connect(self.mark_as_changed)
        self.ollama_host.textChanged.connect(self.mark_as_changed)
        self.ollama_model.currentIndexChanged.connect(self.mark_as_changed)
        self.openai_key.textChanged.connect(self.mark_as_changed)
        self.openai_model.currentIndexChanged.connect(self.mark_as_changed)
        self.siliconflow_key.textChanged.connect(self.mark_as_changed)
        self.siliconflow_model.currentIndexChanged.connect(self.mark_as_changed)
        
        # 通用设置
        self.start_on_boot.stateChanged.connect(self.mark_as_changed)
        self.minimize_to_tray.stateChanged.connect(self.mark_as_changed)
        self.show_notifications.stateChanged.connect(self.mark_as_changed)
        self.skip_processed_checkbox.stateChanged.connect(self.mark_as_changed)
        self.language_combo.currentIndexChanged.connect(self.mark_as_changed)
        self.retention_days.valueChanged.connect(self.mark_as_changed)
    
    def mark_as_changed(self):
        """标记有未保存的更改"""
        self.has_unsaved_changes = True
    
    def create_email_tab(self):
        """Create the email settings tab"""
        email_tab = QWidget()
        email_layout = QVBoxLayout(email_tab)
        
        # SMTP Server Group
        smtp_group = QGroupBox(get_text("smtp_server_settings"))
        smtp_form = QFormLayout(smtp_group)
        
        # Get email settings from config
        email_settings = self.global_settings.get("email_settings", {})
        
        # Create widgets for email settings
        self.smtp_server = QLineEdit(email_settings.get("smtp_server", ""))
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(email_settings.get("smtp_port", 587))
        
        self.smtp_security = QComboBox()
        self.smtp_security.addItems(["SSL/TLS", "STARTTLS", "None"])
        security_index = {"SSL/TLS": 0, "STARTTLS": 1, "None": 2}.get(
            email_settings.get("smtp_security", "STARTTLS"), 1)
        self.smtp_security.setCurrentIndex(security_index)
        
        smtp_form.addRow(f"{get_text('smtp_server')}:", self.smtp_server)
        smtp_form.addRow(f"{get_text('port')}:", self.smtp_port)
        smtp_form.addRow(f"{get_text('security')}:", self.smtp_security)
        
        # Authentication Group
        auth_group = QGroupBox(get_text("authentication_settings"))
        auth_form = QFormLayout(auth_group)
        
        # 如果密码已加密，解密显示
        email_password = self.global_settings.get("email_settings", {}).get("email_password", "")
        decrypted_password = decrypt_password(email_password)
        
        self.sender_email = QLineEdit(email_settings.get("sender_email", ""))
        self.email_password = QLineEdit(decrypted_password)
        self.email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember_password = QCheckBox(get_text("remember_password"))
        self.remember_password.setChecked(email_settings.get("remember_password", False))
        
        auth_form.addRow(f"{get_text('sender_email')}:", self.sender_email)
        auth_form.addRow(f"{get_text('password')}:", self.email_password)
        auth_form.addRow("", self.remember_password)
        
        email_layout.addWidget(smtp_group)
        email_layout.addWidget(auth_group)
        email_layout.addStretch()
        
        self.tabs.addTab(email_tab, get_text("email"))

    def on_smtp_server_changed(self, server):
        """Handle SMTP server text change to auto-detect OAuth requirements"""
        server = server.lower()
        
        # Auto-select OAuth for Microsoft servers
        if "office365" in server or "outlook" in server:
            self.auth_method.setCurrentText("OAuth 2.0")
            # 更新为更强硬的警告，表明没有其他选择
            QMessageBox.warning(self, get_text("microsoft_auth"), 
                get_text("microsoft_auth_warning"))

    def on_auth_method_changed(self, index):
        """Switch between authentication methods"""
        self.auth_stack.setCurrentIndex(index)
        
        # Sync email addresses between the two input fields
        if index == 0:  # Basic -> OAuth
            self.oauth_sender_email.setText(self.sender_email.text())
        else:  # OAuth -> Basic
            self.sender_email.setText(self.oauth_sender_email.text())
    
    def show_oauth_help(self):
        """Show help dialog for obtaining OAuth credentials"""
        msg = QMessageBox(self)
        msg.setWindowTitle(get_text("oauth_setup"))
        msg.setIcon(QMessageBox.Icon.Information)
        
        help_text = get_text("oauth_help_text")
        
        msg.setText(get_text("oauth_setup_title"))
        msg.setInformativeText(help_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def show_app_password_help(self):
        """显示密码认证已被禁用的帮助对话框"""
        msg = QMessageBox(self)
        msg.setWindowTitle(get_text("microsoft_auth"))
        msg.setIcon(QMessageBox.Icon.Warning)
        
        help_text = get_text("microsoft_auth_disabled")
        
        msg.setText(get_text("microsoft_auth_disabled_title"))
        msg.setInformativeText(help_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def create_ai_tab(self):
        """Create the AI settings tab"""
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # AI Provider Group
        provider_group = QGroupBox(get_text("ai_provider"))
        provider_layout = QVBoxLayout(provider_group)
        
        # Get AI settings from config
        ai_settings = self.global_settings.get("ai_settings", {})
        ai_provider = ai_settings.get("provider", "ollama")
        
        # Provider selection
        self.ai_provider = QComboBox()
        self.ai_provider.addItems(["Ollama", "OpenAI", "Silicon Flow"])  # 添加硅基流动选项
        
        # 设置当前选择的提供商
        if ai_provider == "ollama":
            self.ai_provider.setCurrentIndex(0)
        elif ai_provider == "siliconflow":
            self.ai_provider.setCurrentIndex(2)
        else:
            self.ai_provider.setCurrentIndex(1)  # OpenAI
            
        self.ai_provider.currentIndexChanged.connect(self.on_ai_provider_changed)
        
        provider_layout.addWidget(self.ai_provider)
        
        # Ollama settings
        self.ollama_group = QGroupBox(get_text("ollama_settings"))
        ollama_form = QFormLayout(self.ollama_group)
        
        self.ollama_host = QLineEdit(ai_settings.get("ollama_host", "http://localhost:11434"))
        
        # Ollama model with refresh button
        model_layout = QHBoxLayout()
        self.ollama_model = QComboBox()
        self.refresh_models_btn = QPushButton(get_text("refresh"))
        self.refresh_models_btn.clicked.connect(self.fetch_ollama_models)
        
        model_layout.addWidget(self.ollama_model, 1)
        model_layout.addWidget(self.refresh_models_btn)
        
        # Get current model from settings
        self.current_ollama_model = ai_settings.get("ollama_model", "")
        
        # Try to get the models from Ollama
        self.fetch_ollama_models()
        
        ollama_form.addRow(f"{get_text('ollama_host')}:", self.ollama_host)
        ollama_form.addRow(f"{get_text('model')}:", model_layout)
        
        # Connect host change to model refresh
        self.ollama_host.editingFinished.connect(self.fetch_ollama_models)
        
        # OpenAI settings
        self.openai_group = QGroupBox(get_text("openai_settings"))
        openai_form = QFormLayout(self.openai_group)
        
        self.openai_key = QLineEdit(ai_settings.get("openai_key", ""))
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.openai_model = QComboBox()
        openai_models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        self.openai_model.addItems(openai_models)
        
        current_openai_model = ai_settings.get("openai_model", "gpt-3.5-turbo")
        openai_model_index = openai_models.index(current_openai_model) if current_openai_model in openai_models else 2
        self.openai_model.setCurrentIndex(openai_model_index)
        
        openai_form.addRow(f"{get_text('api_key')}:", self.openai_key)
        openai_form.addRow(f"{get_text('model')}:", self.openai_model)
        
        # 硅基流动设置
        self.siliconflow_group = QGroupBox(get_text("siliconflow_settings"))
        siliconflow_form = QFormLayout(self.siliconflow_group)
        
        self.siliconflow_key = QLineEdit(ai_settings.get("siliconflow_key", ""))
        self.siliconflow_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.siliconflow_key.setPlaceholderText(get_text("siliconflow_key_placeholder"))
        
        self.siliconflow_model = QComboBox()
        siliconflow_models = [
            "Qwen/QwQ-32B",
            "Qwen/Qwen2.5-72B-Instruct", 
            "Qwen/Qwen2.5-32B-Instruct", 
            "Qwen/Qwen2.5-14B-Instruct", 
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2-7B-Instruct",
            "Qwen/Qwen2-1.5B-Instruct",
            "THUDM/glm-4-9b-chat",
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "internlm/internlm2_5-7b-chat",
            "internlm/internlm2_5-20b-chat"
        ]
        self.siliconflow_model.addItems(siliconflow_models)
        
        current_siliconflow_model = ai_settings.get("siliconflow_model", "Qwen/Qwen2-7B-Instruct")
        try:
            siliconflow_model_index = siliconflow_models.index(current_siliconflow_model)
        except ValueError:
            siliconflow_model_index = 5  # 默认为Qwen/Qwen2-7B-Instruct
        self.siliconflow_model.setCurrentIndex(siliconflow_model_index)
        
        siliconflow_form.addRow("API Key:", self.siliconflow_key)
        siliconflow_form.addRow(f"{get_text('model')}:", self.siliconflow_model)
        
        # 添加硅基流动链接
        siliconflow_link = QLabel(f"<a href='https://siliconflow.cn'>{get_text('visit_siliconflow')}</a>")
        siliconflow_link.setOpenExternalLinks(True)
        siliconflow_form.addRow("", siliconflow_link)
        
        ai_layout.addWidget(provider_group)
        ai_layout.addWidget(self.ollama_group)
        ai_layout.addWidget(self.openai_group)
        ai_layout.addWidget(self.siliconflow_group)  # 添加硅基流动设置组
        ai_layout.addStretch()
        
        # Set initial visibility based on selected provider
        self.on_ai_provider_changed(self.ai_provider.currentIndex())
        
        self.tabs.addTab(ai_tab, get_text("ai"))

    def fetch_ollama_models(self):
        """Fetch available models from Ollama API"""
        host_url = self.ollama_host.text().rstrip('/')
        
        # Clear and add a loading indicator
        self.ollama_model.clear()
        self.ollama_model.addItem(get_text("loading_models"))
        
        try:
            # Make API request to Ollama
            response = requests.get(f"{host_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                # Parse the response
                models_data = response.json()
                models = [model['name'] for model in models_data.get('models', [])]
                
                # Update the model dropdown
                self.ollama_model.clear()
                if models:
                    self.ollama_model.addItems(models)
                    
                    # Try to select the previously selected model
                    if self.current_ollama_model in models:
                        self.ollama_model.setCurrentText(self.current_ollama_model)
                else:
                    self.ollama_model.addItem(get_text("no_models_found"))
            else:
                self.ollama_model.clear()
                self.ollama_model.addItem(get_text("error_fetching_models"))
                QMessageBox.warning(self, get_text("api_error"), f"{get_text('failed_fetch_models')}: {response.status_code}")
        except Exception as e:
            self.ollama_model.clear()
            fallback_models = ["llama3", "llama2", "mistral", "phi", "gemma"]
            self.ollama_model.addItems(fallback_models)
            
            if self.current_ollama_model in fallback_models:
                self.ollama_model.setCurrentText(self.current_ollama_model)
            elif self.current_ollama_model:
                # Add the current model even if it's not in the fallback list
                self.ollama_model.addItem(self.current_ollama_model)
                self.ollama_model.setCurrentText(self.current_ollama_model)
                
            QMessageBox.warning(self, get_text("connection_error"), 
                             f"{get_text('could_not_connect')} {host_url}.\n{get_text('using_default_list')}.\n{get_text('error')}: {str(e)}")

    def on_ai_provider_changed(self, index):
        """Show/hide relevant AI provider settings based on the selected provider"""
        if index == 0:  # Ollama
            self.ollama_group.setVisible(True)
            self.openai_group.setVisible(False)
            self.siliconflow_group.setVisible(False)
        elif index == 1:  # OpenAI
            self.ollama_group.setVisible(False)
            self.openai_group.setVisible(True)
            self.siliconflow_group.setVisible(False)
        else:  # Silicon Flow
            self.ollama_group.setVisible(False)
            self.openai_group.setVisible(False)
            self.siliconflow_group.setVisible(True)

    def create_general_tab(self):
        """Create the general settings tab"""
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Application behavior group
        behavior_group = QGroupBox(get_text("app_behavior"))
        behavior_form = QFormLayout(behavior_group)
        
        # Get general settings from config
        general_settings = self.global_settings.get("general_settings", {})
        
        self.start_on_boot = QCheckBox(get_text("start_on_boot"))
        self.start_on_boot.setChecked(general_settings.get("start_on_boot", False))
        # 确保复选框不自动获取焦点
        self.start_on_boot.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.minimize_to_tray = QCheckBox(get_text("minimize_to_tray"))
        self.minimize_to_tray.setChecked(general_settings.get("minimize_to_tray", True))
        self.minimize_to_tray.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.show_notifications = QCheckBox(get_text("show_notifications"))
        self.show_notifications.setChecked(general_settings.get("show_notifications", True))
        self.show_notifications.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        behavior_form.addRow("", self.start_on_boot)
        behavior_form.addRow("", self.minimize_to_tray)
        behavior_form.addRow("", self.show_notifications)
        
        # 创建跳过已处理文章选项 - 移除测试功能标记
        self.skip_processed_checkbox = QCheckBox(get_text("skip_processed"))
        self.skip_processed_checkbox.setChecked(general_settings.get("skip_processed_articles", False))
        self.skip_processed_checkbox.setToolTip(get_text("skip_processed_tooltip"))
        self.skip_processed_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 添加选项到布局中 - 不再标识为测试功能
        behavior_form.addRow("", self.skip_processed_checkbox)
        
        # 添加语言选择下拉菜单
        language_layout = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "中文 (Chinese)"])
        
        # 设置当前语言
        current_language = general_settings.get("language", "en")
        self.language_combo.setCurrentIndex(0 if current_language == "en" else 1)
        
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        
        behavior_form.addRow(f"{get_text('language')}:", language_layout)
        
        general_layout.addWidget(behavior_group)
        
        # 添加数据管理组
        data_group = QGroupBox(get_text("data_management"))
        data_layout = QVBoxLayout(data_group)
        
        # 添加数据库保留天数设置
        retention_layout = QHBoxLayout()
        retention_label = QLabel(get_text("db_retention_days"))
        self.retention_days = QSpinBox()
        self.retention_days.setRange(7, 365)  # 允许7天到1年的范围
        self.retention_days.setValue(general_settings.get("db_retention_days", 30))  # 默认30天
        self.retention_days.setSuffix(" " + get_text("days"))
        self.retention_days.valueChanged.connect(self.mark_as_changed)
        
        retention_layout.addWidget(retention_label)
        retention_layout.addWidget(self.retention_days)
        retention_layout.addStretch()
        
        data_layout.addLayout(retention_layout)
        
        # 添加保留天数说明
        retention_description = QLabel(get_text("db_retention_desc"))
        retention_description.setWordWrap(True)
        retention_description.setStyleSheet("color: #666; font-size: 11px;")
        data_layout.addWidget(retention_description)
        
        # 添加清除缓存按钮
        clear_cache_btn = QPushButton(get_text("clear_cache"))
        clear_cache_btn.setToolTip(get_text("clear_cache_tooltip"))
        clear_cache_btn.clicked.connect(self.clear_rss_cache)
        
        # 添加说明标签
        cache_description = QLabel(get_text("clear_cache_desc"))
        cache_description.setWordWrap(True)
        cache_description.setStyleSheet("color: #666; font-size: 11px;")
        
        data_layout.addWidget(clear_cache_btn)
        data_layout.addWidget(cache_description)
        
        general_layout.addWidget(data_group)
        general_layout.addStretch()
        
        self.tabs.addTab(general_tab, get_text("general"))

    def clear_rss_cache(self):
        """清除RSS新闻缓存数据库"""
        reply = QMessageBox.question(
            self, 
            get_text("confirm_clear_cache"), 
            get_text("clear_cache_prompt"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import sqlite3
                import os
                
                # 数据库文件路径
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'rss_news.db')
                
                if os.path.exists(db_path):
                    # 连接数据库
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 获取当前表的列表
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    
                    # 清空所有相关表，但保留表结构
                    for table in tables:
                        table_name = table[0]
                        if table_name != 'sqlite_sequence':  # 跳过SQLite内部表
                            cursor.execute(f"DELETE FROM {table_name}")
                    
                    # 提交更改
                    conn.commit()
                    conn.close()
                    
                    QMessageBox.information(self, get_text("cache_cleared"), get_text("rss_cache_cleared"))
                    self.status_label.setText(get_text("rss_cache_cleared"))
                    self.status_label.setStyleSheet("color: green;")
                    
                    # 5秒后清除状态消息
                    QTimer.singleShot(5000, self.clear_status)
                else:
                    QMessageBox.information(self, get_text("operation_complete"), get_text("db_file_not_exist"))
                    
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"{get_text('error_clearing_cache')}: {error_details}")
                QMessageBox.critical(self, get_text("error"), f"{get_text('error_clearing_cache')}: {str(e)}")

    def create_interests_tab(self):
        """Create user interest tags settings tab"""
        interests_tab = QWidget()
        layout = QVBoxLayout(interests_tab)
        
        # === 正向标签区域 ===
        positive_group = QGroupBox(get_text("positive_interests_title"))
        positive_layout = QVBoxLayout(positive_group)
        
        # 正向标签描述
        description = QLabel(get_text("set_interests"))
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignLeft)
        positive_layout.addWidget(description)
        
        # 获取当前用户兴趣标签
        user_interests = self.global_settings.get("user_interests", [])
        
        # 创建标签编辑器 - 4行高
        self.tag_editor = TagEditor(rows=4)
        if user_interests:
            self.tag_editor.set_tags(user_interests)
        
        positive_layout.addWidget(self.tag_editor)
        positive_layout.addStretch()
        
        # === 反向标签区域 ===
        negative_group = QGroupBox(get_text("negative_interests_title"))
        negative_layout = QVBoxLayout(negative_group)
        
        # 反向标签描述
        neg_description = QLabel(get_text("set_negative_interests"))
        neg_description.setWordWrap(True)
        neg_description.setAlignment(Qt.AlignmentFlag.AlignLeft)
        negative_layout.addWidget(neg_description)
        
        # 获取当前用户反向兴趣标签
        user_negative_interests = self.global_settings.get("user_negative_interests", [])
        
        # 创建反向标签编辑器 - 优化为只有1行高
        self.negative_tag_editor = TagEditor(rows=1)
        if user_negative_interests:
            self.negative_tag_editor.set_tags(user_negative_interests)
        
        negative_layout.addWidget(self.negative_tag_editor)
        negative_layout.addStretch()
        
        # 添加两个区域到主布局
        layout.addWidget(positive_group)
        layout.addWidget(negative_group)
        
        self.tabs.addTab(interests_tab, get_text("interest_tags"))

    def save_settings(self):
        """保存所有设置但不关闭窗口"""
        # 确保获取最新的语言设置
        current_general_settings = get_general_settings()
        prev_language = current_general_settings.get("language", "en")
        current_language = "en" if self.language_combo.currentIndex() == 0 else "zh"
        language_changed = prev_language != current_language

        # 打印调试信息
        print(f"[DEBUG] Previous language: {prev_language}")
        print(f"[DEBUG] Current language selection: {current_language}")
        
        # General settings
        general_settings = {
            "start_on_boot": self.start_on_boot.isChecked(),
            "minimize_to_tray": self.minimize_to_tray.isChecked(),
            "show_notifications": self.show_notifications.isChecked(),
            "skip_processed_articles": self.skip_processed_checkbox.isChecked(),
            "language": current_language,  # 确保这里设置了语言
            "db_retention_days": self.retention_days.value()  # 保存数据库保留天数设置
        }
        
        # 首先更新通用设置
        update_success = update_general_settings(general_settings)
        
        # Email settings
        email_settings = {
            "smtp_server": self.smtp_server.text(),
            "smtp_port": self.smtp_port.value(),
            "smtp_security": self.smtp_security.currentText(),
            "sender_email": self.sender_email.text(),
        }
        
        if self.remember_password.isChecked():
            email_settings["email_password"] = encrypt_password(self.email_password.text())
            email_settings["remember_password"] = True
        else:
            email_settings["remember_password"] = False
        
        # AI settings
        ai_provider_index = self.ai_provider.currentIndex()
        if ai_provider_index == 0:
            ai_provider = "ollama"
        elif ai_provider_index == 1:
            ai_provider = "openai"
        else:
            ai_provider = "siliconflow"
            
        ai_settings = {
            "provider": ai_provider,
            "ollama_host": self.ollama_host.text(),
            "ollama_model": self.ollama_model.currentText(),
            "openai_model": self.openai_model.currentText(),
            "siliconflow_model": self.siliconflow_model.currentText(),
        }
        
        # 只有当OpenAI密钥不为空时才保存
        if self.openai_key.text():
            ai_settings["openai_key"] = self.openai_key.text()
            
        # 只有当硅基流动密钥不为空时才保存
        if self.siliconflow_key.text():
            ai_settings["siliconflow_key"] = self.siliconflow_key.text()
        
        # 获取用户兴趣标签
        user_interests = self.tag_editor.get_tags()
        
        # 获取用户反向兴趣标签
        user_negative_interests = self.negative_tag_editor.get_tags()
        
        # 重要：确保在更新全局设置时不会覆盖通用设置
        self.global_settings["general_settings"] = general_settings
        self.global_settings["email_settings"] = email_settings
        self.global_settings["ai_settings"] = ai_settings
        self.global_settings["user_interests"] = user_interests
        self.global_settings["user_negative_interests"] = user_negative_interests
        
        # 保存整个配置
        self.config["global_settings"] = self.global_settings
        save_config(self.config)
        
        # 强制等待一小段时间确保文件被完全写入
        import time
        time.sleep(0.5)
        
        # 直接从文件中读取进行验证，避免缓存问题
        try:
            import json
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                direct_config = json.load(f)
                saved_language = direct_config.get("global_settings", {}).get("general_settings", {}).get("language")
                print(f"[DEBUG] Direct file verification - Language: {saved_language}")
        except Exception as e:
            print(f"[DEBUG] Error reading config directly: {str(e)}")
            saved_language = None
        
        # 正常验证流程
        verification_config = load_config()
        saved_language_from_load = verification_config.get("global_settings", {}).get("general_settings", {}).get("language")
        print(f"[DEBUG] Verification - Current config language: {current_language}")
        print(f"[DEBUG] Verification - Saved language (load_config): {saved_language_from_load}")
        print(f"[DEBUG] Verification - Saved language (direct): {saved_language}")
        
        # 结合两种读取方式进行验证
        if saved_language != current_language and saved_language_from_load != current_language:
            print("[ERROR] Language setting was not saved correctly!")
            
            # 尝试直接修复问题
            try:
                if direct_config:
                    if "global_settings" not in direct_config:
                        direct_config["global_settings"] = {}
                    if "general_settings" not in direct_config["global_settings"]:
                        direct_config["global_settings"]["general_settings"] = {}
                    
                    direct_config["global_settings"]["general_settings"]["language"] = current_language
                    
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(direct_config, f, indent=4, ensure_ascii=False)
                    print("[DEBUG] Attempted direct fix of language setting")
                    
                    # 验证修复
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        fixed_config = json.load(f)
                        fixed_language = fixed_config.get("global_settings", {}).get("general_settings", {}).get("language")
                        print(f"[DEBUG] After fix - Language: {fixed_language}")
                        
                    if fixed_language == current_language:
                        print("[DEBUG] Language setting fixed successfully!")
                    else:
                        QMessageBox.warning(self, "Save Error", "Language setting may not have been saved correctly.")
                else:
                    QMessageBox.warning(self, "Save Error", "Language setting may not have been saved correctly.")
            except Exception as e:
                print(f"[DEBUG] Error trying to fix language: {str(e)}")
                QMessageBox.warning(self, "Save Error", "Language setting may not have been saved correctly.")
        else:
            print("[DEBUG] Language setting saved successfully!")
        
        # 保存后更新比较基准
        self.original_config = self._get_serializable_config(self.config)
        self.has_unsaved_changes = False
        
        # 如果语言设置发生变化，应用新语言并显示通知
        if language_changed:
            print(f"[DEBUG] Language changed from {prev_language} to {current_language}")
            set_language(current_language)
            
            QMessageBox.information(
                self,
                "Language Changed / 语言已更改",
                get_text("restart_required")
            )
        
        self.status_label.setText(get_text("settings_saved"))
        self.status_label.setStyleSheet("color: green;")
        
        # 3秒后清除提示
        QTimer.singleShot(5000, self.clear_status)
    
    def clear_status(self):
        """清除状态消息"""
        self.status_label.setText("")
        self.status_label.setStyleSheet("")
    
    def close_window(self):
        """关闭窗口，如有未保存更改则提示"""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, 
                get_text("unsaved_changes"), 
                get_text("save_changes_prompt"),
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_settings()
                self.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                self.reject()
            # 取消则不做任何事
        else:
            self.accept()

    def test_email_settings(self):
        """测试邮件设置"""
        # Collect email settings
        server = self.smtp_server.text()
        port = self.smtp_port.value()
        security = self.smtp_security.currentText()
        email = self.sender_email.text()
        password = self.email_password.text()  # 直接使用输入框中的明文密码进行测试
        
        if not server or not email or not password:
            QMessageBox.warning(self, get_text("incomplete_info"), 
                             get_text("fill_email_settings"))
            return
        
        # Create temp config
        temp_config = {
            "global_settings": {
                "email_settings": {
                    "smtp_server": server,
                    "smtp_port": port,
                    "smtp_security": security,
                    "sender_email": email,
                    "email_password": password
                }
            }
        }
        
        # 实例化邮件发送器
        email_sender = EmailSender(temp_config)
        
        # 显示正在发送的提示
        QMessageBox.information(self, get_text("sending_test"), 
                             f"{get_text('sending_test_to')}: {email}\n{get_text('please_wait')}")
        
        # 发送测试邮件
        success, message = email_sender.send_test_email(email)
        
        if success:
            QMessageBox.information(self, get_text("success"), get_text("test_email_sent"))
        else:
            QMessageBox.critical(self, get_text("failed"), f"{get_text('test_email_failed')}\n{get_text('error')}: {message}")