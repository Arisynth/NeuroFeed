from PyQt6.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QCheckBox, QComboBox, QPushButton, QFormLayout, 
                            QGroupBox, QWidget, QMessageBox, QSpinBox)
from PyQt6.QtCore import Qt
from core.config_manager import load_config, save_config
import requests
import json

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        
        # Load current settings
        self.config = load_config()
        self.global_settings = self.config.get("global_settings", {})
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Email settings tab
        self.create_email_tab()
        
        # AI settings tab
        self.create_ai_tab()
        
        # General settings tab
        self.create_general_tab()
        
        main_layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.test_email_btn = QPushButton("Test Email Settings")
        
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        self.test_email_btn.clicked.connect(self.test_email_settings)
        
        button_layout.addWidget(self.test_email_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)

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
        
        # Login Group
        login_group = QGroupBox("Login Settings")
        login_form = QFormLayout(login_group)
        
        self.sender_email = QLineEdit(email_settings.get("sender_email", ""))
        self.email_password = QLineEdit(email_settings.get("email_password", ""))
        self.email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember_password = QCheckBox("Remember password")
        self.remember_password.setChecked(email_settings.get("remember_password", False))
        
        login_form.addRow("Sender Email:", self.sender_email)
        login_form.addRow("Password:", self.email_password)
        login_form.addRow("", self.remember_password)
        
        email_layout.addWidget(smtp_group)
        email_layout.addWidget(login_group)
        email_layout.addStretch()
        
        self.tabs.addTab(email_tab, "Email")

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

    def save_settings(self):
        """Save all settings to config"""
        # Email settings
        email_settings = {
            "smtp_server": self.smtp_server.text(),
            "smtp_port": self.smtp_port.value(),
            "smtp_security": self.smtp_security.currentText(),
            "sender_email": self.sender_email.text(),
            "remember_password": self.remember_password.isChecked(),
        }
        
        # Only save password if remember password is checked
        if self.remember_password.isChecked():
            email_settings["email_password"] = self.email_password.text()
        
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
        
        # Update global settings in config
        self.global_settings = {
            "email_settings": email_settings,
            "ai_settings": ai_settings,
            "general_settings": general_settings,
        }
        
        self.config["global_settings"] = self.global_settings
        save_config(self.config)
        
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
        self.accept()

    def test_email_settings(self):
        """Test the email settings by sending a test email"""
        # Collect email settings
        server = self.smtp_server.text()
        port = self.smtp_port.value()
        security = self.smtp_security.currentText()
        email = self.sender_email.text()
        password = self.email_password.text()
        
        if not server or not email or not password:
            QMessageBox.warning(self, "Incomplete Information", 
                             "Please fill in all email server details before testing.")
            return
        
        # Display a message that in a real app, this would send a test email
        QMessageBox.information(self, "Test Email", 
                             f"This would test sending an email using:\nServer: {server}:{port}\n"
                             f"Email: {email}\nSecurity: {security}")
        
        # In a real implementation, you would use something like:
        # try:
        #     # Code to actually send a test email
        #     success = send_test_email(server, port, security, email, password)
        #     if success:
        #         QMessageBox.information(self, "Success", "Test email sent successfully!")
        #     else:
        #         QMessageBox.critical(self, "Failed", "Failed to send test email.")
        # except Exception as e:
        #     QMessageBox.critical(self, "Error", f"Error sending test email: {str(e)}")