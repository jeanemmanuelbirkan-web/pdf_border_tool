"""
Settings Dialog - Advanced configuration options
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QWidget, QGroupBox,
                            QLabel, QSpinBox, QComboBox, QCheckBox,
                            QSlider, QLineEdit, QPushButton,
                            QFormLayout, QDialogButtonBox,
                            QColorDialog, QFontDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

class AdvancedTab(QWidget):
    """Advanced processing options tab"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
        
    def init_ui(self):
        """Initialize advanced settings UI"""
        layout = QVBoxLayout(self)
        
        # Processing options
        processing_group = QGroupBox("Processing Options")
        processing_layout = QFormLayout(processing_group)
        
        # Memory usage
        self.memory_limit = QSpinBox()
        self.memory_limit.setRange(256, 8192)
        self.memory_limit.setValue(self.config.get_setting('memory_limit_mb', 1024))
        self.memory_limit.setSuffix(" MB")
        processing_layout.addRow("Memory Limit:", self.memory_limit)
        
        # Threading
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 8)
        self.thread_count.setValue(self.config.get_setting('thread_count', 2))
        processing_layout.addRow("Thread Count:", self.thread_count)
        
        # Compression
        self.compression_level = QSlider(Qt.Horizontal)
        self.compression_level.setRange(1, 100)
        self.compression_level.setValue(self.config.get_setting('compression_level', 85))
        self.compression_label = QLabel(f"{self.compression_level.value()}%")
        self.compression_level.valueChanged.connect(
            lambda v: self.compression_label.setText(f"{v}%"))
        
        compression_layout = QHBoxLayout()
        compression_layout.addWidget(self.compression_level)
        compression_layout.addWidget(self.compression_label)
        
        processing_layout.addRow("JPEG Compression:", compression_layout)
        
        layout.addWidget(processing_group)
        
        # Color options
        color_group = QGroupBox("Color Options")
        color_layout = QFormLayout(color_group)
        
        # Color space preservation
        self.preserve_color_space = QCheckBox("Preserve original color space")
        self.preserve_color_space.setChecked(
            self.config.get_setting('preserve_color_space', True))
        color_layout.addRow(self.preserve_color_space)
        
        # Border color
        self.border_color_btn = QPushButton("Choose Border Color")
        self.border_color_btn.clicked.connect(self.choose_border_color)
        self.border_color = QColor(self.config.get_setting('border_color', '#FFFFFF'))
        self.update_color_button()
        color_layout.addRow("Default Border Color:", self.border_color_btn)
        
        layout.addWidget(color_group)
        
        layout.addStretch()
        
    def choose_border_color(self):
        """Open color chooser dialog"""
        color = QColorDialog.getColor(self.border_color, self)
        if color.isValid():
            self.border_color = color
            self.update_color_button()
            
    def update_color_button(self):
        """Update color button appearance"""
        self.border_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.border_color.name()};
                border: 1px solid #999999;
                padding: 8px;
                border-radius: 4px;
            }}
        """)
        
    def get_settings(self):
        """Get settings from this tab"""
        return {
            'memory_limit_mb': self.memory_limit.value(),
            'thread_count': self.thread_count.value(),
            'compression_level': self.compression_level.value(),
            'preserve_color_space': self.preserve_color_space.isChecked(),
            'border_color': self.border_color.name(),
        }

class OutputTab(QWidget):
    """Output options tab"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
        
    def init_ui(self):
        """Initialize output settings UI"""
        layout = QVBoxLayout(self)
        
        # File naming
        naming_group = QGroupBox("File Naming")
        naming_layout = QFormLayout(naming_group)
        
        # Output directory option
        self.use_output_dir = QCheckBox("Use custom output directory")
        self.use_output_dir.setChecked(
            self.config.get_setting('use_output_directory', False))
        naming_layout.addRow(self.use_output_dir)
        
        # Custom suffix patterns
        self.suffix_pattern = QLineEdit()
        self.suffix_pattern.setText(
            self.config.get_setting('suffix_pattern', '_bordered'))
        self.suffix_pattern.setPlaceholderText("_bordered, _modified, etc.")
        naming_layout.addRow("Suffix Pattern:", self.suffix_pattern)
        
        # Include timestamp
        self.include_timestamp = QCheckBox("Include timestamp in filename")
        self.include_timestamp.setChecked(
            self.config.get_setting('include_timestamp', False))
        naming_layout.addRow(self.include_timestamp)
        
        layout.addWidget(naming_group)
        
        # Metadata options
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        # Preserve metadata
        self.preserve_metadata = QCheckBox("Preserve original PDF metadata")
        self.preserve_metadata.setChecked(
            self.config.get_setting('preserve_metadata', True))
        metadata_layout.addRow(self.preserve_metadata)
        
        # Add processing info
        self.add_processing_info = QCheckBox("Add processing information to metadata")
        self.add_processing_info.setChecked(
            self.config.get_setting('add_processing_info', False))
        metadata_layout.addRow(self.add_processing_info)
        
        layout.addWidget(metadata_group)
        
        layout.addStretch()
        
    def get_settings(self):
        """Get settings from this tab"""
        return {
            'use_output_directory': self.use_output_dir.isChecked(),
            'suffix_pattern': self.suffix_pattern.text(),
            'include_timestamp': self.include_timestamp.isChecked(),
            'preserve_metadata': self.preserve_metadata.isChecked(),
            'add_processing_info': self.add_processing_info.isChecked(),
        }

class SettingsDialog(QDialog):
    """Advanced settings dialog"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
        
    def init_ui(self):
        """Initialize the settings dialog"""
        self.setWindowTitle("Advanced Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.advanced_tab = AdvancedTab(self.config)
        self.tab_widget.addTab(self.advanced_tab, "Processing")
        
        self.output_tab = OutputTab(self.config)
        self.tab_widget.addTab(self.output_tab, "Output")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        
        layout.addWidget(button_box)
        
    def save_settings(self):
        """Save all settings and close"""
        # Collect settings from all tabs
        all_settings = {}
        all_settings.update(self.advanced_tab.get_settings())
        all_settings.update(self.output_tab.get_settings())
        
        # Save to config
        for key, value in all_settings.items():
            self.config.set_setting(key, value)
        
        self.config.save_settings()
        self.accept()
        
    def restore_defaults(self):
        """Restore default settings"""
        self.config.restore_defaults()
        
        # Refresh UI with default values
        self.advanced_tab = AdvancedTab(self.config)
        self.output_tab = OutputTab(self.config)
        
        self.tab_widget.clear()
        self.tab_widget.addTab(self.advanced_tab, "Processing")
        self.tab_widget.addTab(self.output_tab, "Output")