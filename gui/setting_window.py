from PyQt6.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QCheckBox, QComboBox, QPushButton, QFormLayout, 
                            QGroupBox, QWidget, QMessageBox, QSpinBox, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer
from core.config_manager import load_config, save_config
import requests
import json
from gui.tag_editor import TagEditor  # 导入标签编辑器
from core.email_sender import EmailSender
from core.encryption import encrypt_password, decrypt_password

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        
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
        
        self.test_email_btn = QPushButton("Test Email Settings")
        self.save_btn = QPushButton("Save")
        self.close_btn = QPushButton("Close")
        
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
        
        # 通用设置
        self.start_on_boot.stateChanged.connect(self.mark_as_changed)
        self.minimize_to_tray.stateChanged.connect(self.mark_as_changed)
        self.show_notifications.stateChanged.connect(self.mark_as_changed)
    
    def mark_as_changed(self):
        """标记有未保存的更改"""
        self.has_unsaved_changes = True
    
    def create_email_tab(self):
        """Create the email settings tab"""
        email_tab = QWidget()
        email_layout = QVBoxLayout(email_tab)
        
        # SMTP Server Group
        smtp_group = QGroupBox("SMTP Server Settings")
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
        
        smtp_form.addRow("SMTP Server:", self.smtp_server)
        smtp_form.addRow("Port:", self.smtp_port)
        smtp_form.addRow("Security:", self.smtp_security)
        
        # Authentication Group
        auth_group = QGroupBox("Authentication Settings")
        auth_form = QFormLayout(auth_group)
        
        # 如果密码已加密，解密显示
        email_password = self.global_settings.get("email_settings", {}).get("email_password", "")
        decrypted_password = decrypt_password(email_password)
        
        self.sender_email = QLineEdit(email_settings.get("sender_email", ""))
        self.email_password = QLineEdit(decrypted_password)
        self.email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember_password = QCheckBox("Remember password")
        self.remember_password.setChecked(email_settings.get("remember_password", False))
        
        auth_form.addRow("Sender Email:", self.sender_email)
        auth_form.addRow("Password:", self.email_password)
        auth_form.addRow("", self.remember_password)
        
        email_layout.addWidget(smtp_group)
        email_layout.addWidget(auth_group)
        email_layout.addStretch()
        
        self.tabs.addTab(email_tab, "Email")

    def on_smtp_server_changed(self, server):
        """Handle SMTP server text change to auto-detect OAuth requirements"""
        server = server.lower()
        
        # Auto-select OAuth for Microsoft servers
        if "office365" in server or "outlook" in server:
            self.auth_method.setCurrentText("OAuth 2.0")
            # 更新为更强硬的警告，表明没有其他选择
            QMessageBox.warning(self, "Microsoft Authentication", 
                "Microsoft已完全禁用密码认证！\n\n"
                "对于Office 365或Outlook邮箱，唯一可用的选项是OAuth 2.0认证。\n\n"
                "请按照'How to get OAuth credentials'按钮的指引完成配置。")

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
        msg.setWindowTitle("OAuth Setup Instructions")
        msg.setIcon(QMessageBox.Icon.Information)
        
        help_text = """
<h3>How to set up OAuth 2.0 for Microsoft Email</h3>

<ol>
<li><b>Register an application in Azure Portal:</b>
    <ul>
    <li>Go to <a href="https://portal.azure.com/">Azure Portal</a></li>
    <li>Navigate to "Azure Active Directory" > "App registrations" > "New registration"</li>
    <li>Name your application (e.g., "NewsDigest Email")</li>
    <li>For "Supported account types" select "Accounts in any organizational directory and personal Microsoft accounts"</li>
    <li>Leave Redirect URI empty and click "Register"</li>
    </ul>
</li>

<li><b>Get the Application (client) ID:</b>
    <ul>
    <li>After registration, copy the "Application (client) ID" from the overview page</li>
    <li>This is your <b>Client ID</b></li>
    </ul>
</li>

<li><b>Create a client secret:</b>
    <ul>
    <li>Go to "Certificates & secrets" > "Client secrets" > "New client secret"</li>
    <li>Add a description and select expiration period</li>
    <li>Click "Add" and immediately copy the secret value</li>
    <li>This is your <b>Client Secret</b></li>
    </ul>
</li>

<li><b>Configure API permissions:</b>
    <ul>
    <li>Go to "API permissions" > "Add a permission"</li>
    <li>Select "Microsoft Graph" > "Application permissions"</li>
    <li>Search for and add: "SMTP.Send"</li>
    <li>Click "Grant admin consent"</li>
    </ul>
</li>

<li><b>Get Tenant ID (optional):</b>
    <ul>
    <li>For organizational accounts, copy the "Directory (tenant) ID" from the overview page</li>
    <li>For personal accounts, use "common" as the Tenant ID</li>
    </ul>
</li>
</ol>

<p>After completing these steps, enter the values in the corresponding fields.</p>
"""
        
        msg.setText("Setting up OAuth 2.0 for Microsoft Email")
        msg.setInformativeText(help_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def show_app_password_help(self):
        """显示密码认证已被禁用的帮助对话框"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Microsoft Authentication")
        msg.setIcon(QMessageBox.Icon.Warning)
        
        help_text = """
<h3>Microsoft已禁用密码认证</h3>

<p>Microsoft已禁用所有形式的密码认证(包括常规密码和应用密码)。</p>

<p>对于Microsoft账户(Office 365或Outlook)，<b>唯一可用的选项是OAuth 2.0认证</b>。</p>

<p>请切换到OAuth 2.0认证方式并配置以下必要信息：</p>
<ul>
<li>Client ID (从Azure应用注册获取)</li>
<li>Client Secret (从Azure应用注册获取)</li>
<li>租户ID (通常使用您的实际租户ID)</li>
</ul>

<p>点击"How to get OAuth credentials"按钮获取详细设置步骤。</p>
"""
        
        msg.setText("Microsoft已禁用密码认证")
        msg.setInformativeText(help_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def create_ai_tab(self):
        """Create the AI settings tab"""
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # AI Provider Group
        provider_group = QGroupBox("AI Provider")
        provider_layout = QVBoxLayout(provider_group)
        
        # Get AI settings from config
        ai_settings = self.global_settings.get("ai_settings", {})
        ai_provider = ai_settings.get("provider", "ollama")
        
        # Provider selection
        self.ai_provider = QComboBox()
        self.ai_provider.addItems(["Ollama", "OpenAI"])
        self.ai_provider.setCurrentIndex(0 if ai_provider == "ollama" else 1)
        self.ai_provider.currentIndexChanged.connect(self.on_ai_provider_changed)
        
        provider_layout.addWidget(self.ai_provider)
        
        # Ollama settings
        self.ollama_group = QGroupBox("Ollama Settings")
        ollama_form = QFormLayout(self.ollama_group)
        
        self.ollama_host = QLineEdit(ai_settings.get("ollama_host", "http://localhost:11434"))
        
        # Ollama model with refresh button
        model_layout = QHBoxLayout()
        self.ollama_model = QComboBox()
        self.refresh_models_btn = QPushButton("Refresh")
        self.refresh_models_btn.clicked.connect(self.fetch_ollama_models)
        
        model_layout.addWidget(self.ollama_model, 1)
        model_layout.addWidget(self.refresh_models_btn)
        
        # Get current model from settings
        self.current_ollama_model = ai_settings.get("ollama_model", "")
        
        # Try to get the models from Ollama
        self.fetch_ollama_models()
        
        ollama_form.addRow("Ollama Host:", self.ollama_host)
        ollama_form.addRow("Model:", model_layout)
        
        # Connect host change to model refresh
        self.ollama_host.editingFinished.connect(self.fetch_ollama_models)
        
        # OpenAI settings
        self.openai_group = QGroupBox("OpenAI Settings")
        openai_form = QFormLayout(self.openai_group)
        
        self.openai_key = QLineEdit(ai_settings.get("openai_key", ""))
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.openai_model = QComboBox()
        openai_models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        self.openai_model.addItems(openai_models)
        
        current_openai_model = ai_settings.get("openai_model", "gpt-3.5-turbo")
        openai_model_index = openai_models.index(current_openai_model) if current_openai_model in openai_models else 2
        self.openai_model.setCurrentIndex(openai_model_index)
        
        openai_form.addRow("API Key:", self.openai_key)
        openai_form.addRow("Model:", self.openai_model)
        
        ai_layout.addWidget(provider_group)
        ai_layout.addWidget(self.ollama_group)
        ai_layout.addWidget(self.openai_group)
        ai_layout.addStretch()
        
        # Set initial visibility based on selected provider
        self.on_ai_provider_changed(self.ai_provider.currentIndex())
        
        self.tabs.addTab(ai_tab, "AI")

    def fetch_ollama_models(self):
        """Fetch available models from Ollama API"""
        host_url = self.ollama_host.text().rstrip('/')
        
        # Clear and add a loading indicator
        self.ollama_model.clear()
        self.ollama_model.addItem("Loading models...")
        
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
                    self.ollama_model.addItem("No models found")
            else:
                self.ollama_model.clear()
                self.ollama_model.addItem("Error fetching models")
                QMessageBox.warning(self, "API Error", f"Failed to fetch models: {response.status_code}")
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
                
            QMessageBox.warning(self, "Connection Error", 
                             f"Could not connect to Ollama at {host_url}.\nUsing default model list.\nError: {str(e)}")

    def create_general_tab(self):
        """Create the general settings tab"""
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Application behavior group
        behavior_group = QGroupBox("Application Behavior")
        behavior_form = QFormLayout(behavior_group)
        
        # Get general settings from config
        general_settings = self.global_settings.get("general_settings", {})
        
        self.start_on_boot = QCheckBox("Start application on system startup")
        self.start_on_boot.setChecked(general_settings.get("start_on_boot", False))
        
        self.minimize_to_tray = QCheckBox("Minimize to system tray when closed")
        self.minimize_to_tray.setChecked(general_settings.get("minimize_to_tray", True))
        
        self.show_notifications = QCheckBox("Show notifications")
        self.show_notifications.setChecked(general_settings.get("show_notifications", True))
        
        behavior_form.addRow("", self.start_on_boot)
        behavior_form.addRow("", self.minimize_to_tray)
        behavior_form.addRow("", self.show_notifications)
        
        general_layout.addWidget(behavior_group)
        general_layout.addStretch()
        
        self.tabs.addTab(general_tab, "General")

    def on_ai_provider_changed(self, index):
        """Show/hide relevant AI provider settings"""
        if index == 0:  # Ollama
            self.ollama_group.setVisible(True)
            self.openai_group.setVisible(False)
        else:  # OpenAI
            self.ollama_group.setVisible(False)
            self.openai_group.setVisible(True)

    def create_interests_tab(self):
        """Create user interest tags settings tab"""
        interests_tab = QWidget()
        layout = QVBoxLayout(interests_tab)
        
        # Description label - 移除加粗，左对齐
        description = QLabel("Set your interest tags that will be automatically applied when adding new RSS feeds:")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(description)
        
        # 获取当前用户兴趣标签
        user_interests = self.global_settings.get("user_interests", [])
        
        # 创建标签编辑器 - 4行高
        self.tag_editor = TagEditor(rows=4)
        if user_interests:
            self.tag_editor.set_tags(user_interests)
        
        layout.addWidget(self.tag_editor)
        layout.addStretch()
        
        self.tabs.addTab(interests_tab, "Interest Tags")

    def save_settings(self):
        """保存所有设置但不关闭窗口"""
        # Email settings
        email_settings = {
            "smtp_server": self.smtp_server.text(),
            "smtp_port": self.smtp_port.value(),
            "smtp_security": self.smtp_security.currentText(),
            "sender_email": self.sender_email.text(),
        }
        
        # 加密密码后再存储
        if self.remember_password.isChecked():
            email_settings["email_password"] = encrypt_password(self.email_password.text())
            email_settings["remember_password"] = True
        else:
            email_settings["remember_password"] = False
        
        # AI settings
        ai_provider = "ollama" if self.ai_provider.currentIndex() == 0 else "openai"
        ai_settings = {
            "provider": ai_provider,
            "ollama_host": self.ollama_host.text(),
            "ollama_model": self.ollama_model.currentText(),
            "openai_model": self.openai_model.currentText(),
        }
        
        # Only save OpenAI key if it's not empty
        if self.openai_key.text():
            ai_settings["openai_key"] = self.openai_key.text()
        
        # General settings
        general_settings = {
            "start_on_boot": self.start_on_boot.isChecked(),
            "minimize_to_tray": self.minimize_to_tray.isChecked(),
            "show_notifications": self.show_notifications.isChecked(),
        }
        
        # 保存用户兴趣标签
        user_interests = self.tag_editor.get_tags()
        
        # 更新全局设置
        self.global_settings.update({
            "email_settings": email_settings,
            "ai_settings": ai_settings,
            "general_settings": general_settings,
            "user_interests": user_interests  # 添加用户兴趣标签
        })
        
        self.config["global_settings"] = self.global_settings
        save_config(self.config)
        
        # 保存后更新比较基准
        self.original_config = self._get_serializable_config(self.config)
        self.has_unsaved_changes = False
        
        # 显示临时保存成功提示
        self.status_label.setText("Settings saved successfully!")
        self.status_label.setStyleSheet("color: green")
        
        # 3秒后清除提示
        QTimer.singleShot(3000, self.clear_status)
    
    def clear_status(self):
        """清除状态消息"""
        self.status_label.setText("")
        self.status_label.setStyleSheet("")
    
    def close_window(self):
        """关闭窗口，如有未保存更改则提示"""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, 
                "Unsaved Changes", 
                "You have unsaved changes. Do you want to save before closing?",
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
            QMessageBox.warning(self, "Incomplete Information", 
                             "Please fill in all email settings (server, email, and password).")
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
        QMessageBox.information(self, "Sending Test", 
                             f"Sending test email to: {email}\nPlease wait...")
        
        # 发送测试邮件
        success, message = email_sender.send_test_email(email)
        
        if success:
            QMessageBox.information(self, "Success", "Test email sent successfully!")
        else:
            QMessageBox.critical(self, "Failed", f"Failed to send test email.\nError: {message}")