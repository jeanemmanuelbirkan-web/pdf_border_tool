"""
Preview Dialog - Shows before/after comparison
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QScrollArea,
                            QFrame, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter

from core.pdf_processor import PDFProcessor

class PreviewGeneratorThread(QThread):
    """Thread for generating preview images"""
    
    preview_ready = pyqtSignal(object, object)  # original, processed
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path, settings):
        super().__init__()
        self.file_path = file_path
        self.settings = settings
        
    def run(self):
        """Generate preview images"""
        try:
            processor = PDFProcessor(self.settings)
            
            # Get original and preview images
            original_image = processor.extract_first_page_image(self.file_path)
            processed_image = processor.create_preview(self.file_path)
            
            self.preview_ready.emit(original_image, processed_image)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class ImageLabel(QLabel):
    """Custom label for displaying images with scaling"""
    
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.original_pixmap = None
        self.setMinimumSize(300, 400)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setAlignment(Qt.AlignCenter)
        self.setText(f"{title}\n\nLoading...")
        
    def set_image(self, pixmap):
        """Set image with proper scaling"""
        self.original_pixmap = pixmap
        self.scale_image()
        
    def scale_image(self):
        """Scale image to fit label"""
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled_pixmap)
        
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.scale_image()

class PreviewDialog(QDialog):
    """Dialog for previewing changes before processing"""
    
    def __init__(self, file_path, settings, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.settings = settings
        self.preview_thread = None
        
        self.init_ui()
        self.generate_preview()
        
    def init_ui(self):
        """Initialize the preview dialog UI"""
        self.setWindowTitle("Preview Changes")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Preview: Before and After")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Image comparison area
        splitter = QSplitter(Qt.Horizontal)
        
        # Original image
        original_scroll = QScrollArea()
        self.original_label = ImageLabel("Original")
        original_scroll.setWidget(self.original_label)
        original_scroll.setWidgetResizable(True)
        splitter.addWidget(original_scroll)
        
        # Processed image
        processed_scroll = QScrollArea()
        self.processed_label = ImageLabel("With 3mm Border")
        processed_scroll.setWidget(self.processed_label)
        processed_scroll.setWidgetResizable(True)
        splitter.addWidget(processed_scroll)
        
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)
        
        button_layout.addStretch()
        
        self.accept_btn = QPushButton("Looks Good - Proceed")
        self.accept_btn.clicked.connect(self.accept)
        self.accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005c99;
            }
        """)
        button_layout.addWidget(self.accept_btn)
        
        layout.addLayout(button_layout)
        
    def generate_preview(self):
        """Generate preview images in background thread"""
        self.preview_thread = PreviewGeneratorThread(self.file_path, self.settings)
        self.preview_thread.preview_ready.connect(self.display_preview)
        self.preview_thread.error_occurred.connect(self.handle_error)
        self.preview_thread.start()
        
    def display_preview(self, original_image, processed_image):
        """Display the generated preview images"""
        try:
            # Convert images to QPixmap
            original_pixmap = self.image_to_pixmap(original_image)
            processed_pixmap = self.image_to_pixmap(processed_image)
            
            # Set images
            self.original_label.set_image(original_pixmap)
            self.processed_label.set_image(processed_pixmap)
            
        except Exception as e:
            self.handle_error(f"Error displaying preview: {str(e)}")
            
    def image_to_pixmap(self, image):
        """Convert PIL image to QPixmap"""
        if hasattr(image, 'save'):  # PIL Image
            import io
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            return pixmap
        else:
            # Assume it's already a QPixmap or similar
            return QPixmap(image)
            
    def handle_error(self, error_message):
        """Handle preview generation errors"""
        self.original_label.setText(f"Original\n\nError: {error_message}")
        self.processed_label.setText(f"With 3mm Border\n\nError: {error_message}")
        
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.terminate()
        event.accept()