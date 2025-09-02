"""
Main Window - Primary application interface
"""

import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLabel, QFrame, QPushButton, 
                            QProgressBar, QTextEdit, QGroupBox,
                            QSpinBox, QComboBox, QCheckBox, QSlider,
                            QLineEdit, QFileDialog, QMessageBox,
                            QSplitter, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent, QPalette

from core.pdf_processor import PDFProcessor
from gui.preview_dialog import PreviewDialog
from gui.settings_dialog import SettingsDialog
from utils.validators import PDFValidator

class DropZone(QFrame):
    """Drag and drop zone for PDF files"""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the drop zone UI"""
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #cccccc;
                border-radius: 10px;
                background-color: #f9f9f9;
                min-height: 200px;
            }
            QFrame:hover {
                border-color: #007acc;
                background-color: #f0f8ff;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Drop zone label
        self.label = QLabel("📁 Drag & Drop PDF Files Here\n\nOr click to browse...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 14))
        self.label.setStyleSheet("color: #666666; margin: 20px;")
        
        layout.addWidget(self.label)
        self.setLayout(layout)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            pdf_files = [url.toLocalFile() for url in urls 
                        if url.toLocalFile().lower().endswith('.pdf')]
            if pdf_files:
                event.acceptProposedAction()
                self.setStyleSheet("""
                    QFrame {
                        border: 2px solid #007acc;
                        border-radius: 10px;
                        background-color: #e6f3ff;
                    }
                """)
        
    def dragLeaveEvent(self, event):
        """Handle drag leave events"""
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #cccccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
        """)
        
    def dropEvent(self, event: QDropEvent):
        """Handle file drop events"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                files.append(file_path)
        
        if files:
            self.files_dropped.emit(files)
        
        # Reset style
        self.dragLeaveEvent(event)
        event.acceptProposedAction()
        
    def mousePressEvent(self, event):
        """Handle click to browse"""
        if event.button() == Qt.LeftButton:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select PDF Files", "", 
                "PDF Files (*.pdf);;All Files (*)"
            )
            if files:
                self.files_dropped.emit(files)

class ProcessingThread(QThread):
    """Background thread for PDF processing"""
    
    progress_updated = pyqtSignal(int, str)
    file_completed = pyqtSignal(str, bool, str)
    all_completed = pyqtSignal()
    
    def __init__(self, files, config):
        super().__init__()
        self.files = files
        self.config = config
        self.processor = PDFProcessor(config)
        
    def run(self):
        """Process files in background"""
        total_files = len(self.files)
        
        for i, file_path in enumerate(self.files):
            try:
                # Update progress
                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress, f"Processing: {Path(file_path).name}")
                
                # Process file
                output_path = self.processor.process_pdf(file_path)
                self.file_completed.emit(file_path, True, output_path)
                
            except Exception as e:
                self.file_completed.emit(file_path, False, str(e))
        
        self.progress_updated.emit(100, "Processing complete!")
        self.all_completed.emit()

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.validator = PDFValidator()
        self.processing_thread = None
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("PDF Border Tool - L'Oréal")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Drop zone and file list
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Settings and controls
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready - Drag PDF files to begin")
        
    def create_left_panel(self):
        """Create the left panel with drop zone and file list"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.add_files)
        layout.addWidget(self.drop_zone)
        
        # File list
        file_group = QGroupBox("Files to Process")
        file_layout = QVBoxLayout(file_group)
        
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(150)
        file_layout.addWidget(self.file_list)
        
        # File list buttons
        file_button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_files)
        file_button_layout.addWidget(self.clear_btn)
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        file_button_layout.addWidget(self.remove_btn)
        
        file_button_layout.addStretch()
        file_layout.addLayout(file_button_layout)
        
        layout.addWidget(file_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready")
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_group)
        
        return panel
        
    def create_right_panel(self):
        """Create the right panel with settings and controls"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Border settings
        border_group = QGroupBox("Border Settings")
        border_layout = QVBoxLayout(border_group)
        
        # Border width
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Border Width (mm):"))
        self.border_width = QSpinBox()
        self.border_width.setRange(1, 10)
        self.border_width.setValue(3)
        self.border_width.setSuffix(" mm")
        width_layout.addWidget(self.border_width)
        width_layout.addStretch()
        border_layout.addLayout(width_layout)
        
        # Stretch method
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Stretch Method:"))
        self.stretch_method = QComboBox()
        self.stretch_method.addItems([
            "Edge Repeat", "Smart Fill", "Gradient Fade"
        ])
        method_layout.addWidget(self.stretch_method)
        border_layout.addLayout(method_layout)
        
        layout.addWidget(border_group)
        
        # Quality settings
        quality_group = QGroupBox("Quality Settings")
        quality_layout = QVBoxLayout(quality_group)
        
        # Output DPI
        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel("Output DPI:"))
        self.dpi_slider = QSlider(Qt.Horizontal)
        self.dpi_slider.setRange(72, 300)
        self.dpi_slider.setValue(300)
        self.dpi_slider.valueChanged.connect(self.update_dpi_label)
        self.dpi_label = QLabel("300 DPI")
        dpi_layout.addWidget(self.dpi_slider)
        dpi_layout.addWidget(self.dpi_label)
        quality_layout.addLayout(dpi_layout)
        
        layout.addWidget(quality_group)
        
        # Processing options
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        
        self.auto_detect_cuts = QCheckBox("Auto-detect cut marks")
        self.auto_detect_cuts.setChecked(True)
        options_layout.addWidget(self.auto_detect_cuts)
        
        self.show_preview = QCheckBox("Show preview before processing")
        options_layout.addWidget(self.show_preview)
        
        self.backup_original = QCheckBox("Backup original files")
        self.backup_original.setChecked(True)
        options_layout.addWidget(self.backup_original)
        
        layout.addWidget(options_group)
        
        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout(output_group)
        
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("Filename suffix:"))
        self.filename_suffix = QLineEdit("_bordered")
        suffix_layout.addWidget(self.filename_suffix)
        output_layout.addLayout(suffix_layout)
        
        layout.addWidget(output_group)
        
        # Action buttons
        layout.addStretch()
        
        button_layout = QVBoxLayout()
        
        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self.preview_changes)
        self.preview_btn.setEnabled(False)
        button_layout.addWidget(self.preview_btn)
        
        self.process_btn = QPushButton("Process Files")
        self.process_btn.clicked.connect(self.process_files)
        self.process_btn.setEnabled(False)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #005c99;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.process_btn)
        
        self.settings_btn = QPushButton("Advanced Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        button_layout.addWidget(self.settings_btn)
        
        layout.addLayout(button_layout)
        
        return panel
        
    def add_files(self, files):
        """Add files to the processing list"""
        added_count = 0
        
        for file_path in files:
            # Validate file
            is_valid, message = self.validator.validate_pdf(file_path)
            
            if is_valid:
                # Check if already in list
                existing_items = [self.file_list.item(i).text() 
                                for i in range(self.file_list.count())]
                if file_path not in existing_items:
                    item = QListWidgetItem(file_path)
                    self.file_list.addItem(item)
                    added_count += 1
            else:
                QMessageBox.warning(self, "Invalid File", 
                                  f"Cannot add {Path(file_path).name}:\n{message}")
        
        if added_count > 0:
            self.update_ui_state()
            self.statusBar().showMessage(f"Added {added_count} file(s)")
        
    def clear_files(self):
        """Clear all files from the list"""
        self.file_list.clear()
        self.update_ui_state()
        self.statusBar().showMessage("File list cleared")
        
    def remove_selected(self):
        """Remove selected files from the list"""
        current_row = self.file_list.currentRow()
        if current_row >= 0:
            self.file_list.takeItem(current_row)
            self.update_ui_state()
            self.statusBar().showMessage("File removed")
            
    def update_ui_state(self):
        """Update UI button states based on file list"""
        has_files = self.file_list.count() > 0
        self.preview_btn.setEnabled(has_files)
        self.process_btn.setEnabled(has_files)
        
    def update_dpi_label(self, value):
        """Update DPI label when slider changes"""
        self.dpi_label.setText(f"{value} DPI")
        
    def preview_changes(self):
        """Show preview of changes"""
        if self.file_list.count() > 0:
            first_file = self.file_list.item(0).text()
            dialog = PreviewDialog(first_file, self.get_current_settings(), self)
            dialog.exec_()
            
    def process_files(self):
        """Start processing files"""
        if self.file_list.count() == 0:
            return
            
        files = [self.file_list.item(i).text() 
                for i in range(self.file_list.count())]
        
        # Disable controls during processing
        self.process_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        
        # Start processing thread
        self.processing_thread = ProcessingThread(files, self.get_current_settings())
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.file_completed.connect(self.file_completed)
        self.processing_thread.all_completed.connect(self.processing_finished)
        self.processing_thread.start()
        
    def update_progress(self, value, message):
        """Update progress bar and label"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        self.statusBar().showMessage(message)
        
    def file_completed(self, file_path, success, result):
        """Handle completion of individual file"""
        file_name = Path(file_path).name
        if success:
            print(f"✓ Completed: {file_name}")
        else:
            print(f"✗ Failed: {file_name} - {result}")
            QMessageBox.warning(self, "Processing Error", 
                              f"Failed to process {file_name}:\n{result}")
            
    def processing_finished(self):
        """Handle completion of all processing"""
        self.process_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.statusBar().showMessage("Processing completed!")
        
        QMessageBox.information(self, "Complete", 
                              "All files have been processed successfully!")
        
    def show_settings(self):
        """Show advanced settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == dialog.Accepted:
            self.load_settings()
            
    def get_current_settings(self):
        """Get current settings from UI"""
        return {
            'border_width_mm': self.border_width.value(),
            'stretch_method': self.stretch_method.currentText().lower().replace(' ', '_'),
            'output_dpi': self.dpi_slider.value(),
            'auto_detect_cut_marks': self.auto_detect_cuts.isChecked(),
            'show_preview': self.show_preview.isChecked(),
            'backup_original': self.backup_original.isChecked(),
            'filename_suffix': self.filename_suffix.text(),
        }
        
    def load_settings(self):
        """Load settings from config"""
        settings = self.config.get_all_settings()
        
        self.border_width.setValue(settings.get('border_width_mm', 3))
        
        method_text = settings.get('stretch_method', 'edge_repeat').replace('_', ' ').title()
        index = self.stretch_method.findText(method_text)
        if index >= 0:
            self.stretch_method.setCurrentIndex(index)
            
        self.dpi_slider.setValue(settings.get('output_dpi', 300))
        self.auto_detect_cuts.setChecked(settings.get('auto_detect_cut_marks', True))
        self.show_preview.setChecked(settings.get('show_preview', False))
        self.backup_original.setChecked(settings.get('backup_original', True))
        self.filename_suffix.setText(settings.get('filename_suffix', '_bordered'))
        
    def closeEvent(self, event):
        """Handle application close"""
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(self, 'Close Application',
                                       'Processing is still running. Are you sure you want to quit?',
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.processing_thread.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            # Save current settings
            current_settings = self.get_current_settings()
            for key, value in current_settings.items():
                self.config.set_setting(key, value)
            self.config.save_settings()
            event.accept()