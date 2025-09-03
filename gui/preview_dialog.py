"""
Preview Dialog - Split-view comparison with draggable divider
"""

import os  # 
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFrame, QSplitter,
                            QScrollArea, QWidget, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QPainter, QCursor, QPen, QColor
import io

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

class SplitViewWidget(QFrame):
    """Split view widget with draggable divider"""
    
    def __init__(self):
        super().__init__()
        self.original_pixmap = None
        self.bordered_pixmap = None
        self.divider_pos = 0.5  # 50% split
        self.dragging = False
        self.zoom_factor = 1.0
        self.setMinimumSize(600, 400)
        self.setFrameStyle(QFrame.StyledPanel)
        
    def set_images(self, original_pixmap, bordered_pixmap):
        """Set both images for comparison"""
        self.original_pixmap = original_pixmap
        self.bordered_pixmap = bordered_pixmap
        self.update()
        
    def paintEvent(self, event):
        """Paint the split view"""
        super().paintEvent(event)
        
        if not self.original_pixmap or not self.bordered_pixmap:
            painter = QPainter(self)
            painter.drawText(self.rect(), Qt.AlignCenter, "Loading preview...")
            return
            
        painter = QPainter(self)
        rect = self.rect()
        
        # Calculate divider position
        divider_x = int(rect.width() * self.divider_pos)
        
        # Scale images to fit height while maintaining aspect ratio
        available_height = rect.height()
        original_scaled = self.original_pixmap.scaledToHeight(
            int(available_height * self.zoom_factor), Qt.SmoothTransformation)
        bordered_scaled = self.bordered_pixmap.scaledToHeight(
            int(available_height * self.zoom_factor), Qt.SmoothTransformation)
        
        # Center images horizontally
        orig_x = (rect.width() - original_scaled.width()) // 2
        border_x = (rect.width() - bordered_scaled.width()) // 2
        
        # Draw original image (left side)
        if divider_x > 0:
            left_rect = QRect(0, 0, divider_x, rect.height())
            painter.setClipRect(left_rect)
            painter.drawPixmap(orig_x, 0, original_scaled)
        
        # Draw bordered image (right side)
        if divider_x < rect.width():
            right_rect = QRect(divider_x, 0, rect.width() - divider_x, rect.height())
            painter.setClipRect(right_rect)
            painter.drawPixmap(border_x, 0, bordered_scaled)
        
        # Draw divider line
        painter.setClipping(False)
        pen = QPen(QColor(0, 122, 204), 3)  # Blue divider
        painter.setPen(pen)
        painter.drawLine(divider_x, 0, divider_x, rect.height())
        
        # Draw drag handle
        handle_size = 20
        handle_rect = QRect(divider_x - handle_size//2, rect.height()//2 - handle_size//2, 
                           handle_size, handle_size)
        painter.fillRect(handle_rect, QColor(0, 122, 204))
        painter.setPen(QPen(Qt.white, 1))
        painter.drawText(handle_rect, Qt.AlignCenter, "⋮⋮")
        
        # Draw labels
        painter.setPen(QPen(Qt.black, 1))
        if divider_x > 100:
            painter.drawText(10, 25, "ORIGINAL")
        if rect.width() - divider_x > 100:
            painter.drawText(divider_x + 10, 25, "WITH BORDER")
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.update_divider_position(event.x())
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        rect = self.rect()
        divider_x = int(rect.width() * self.divider_pos)
        
        # Change cursor near divider
        if abs(event.x() - divider_x) < 10:
            self.setCursor(QCursor(Qt.SizeHorCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            
        if self.dragging:
            self.update_divider_position(event.x())
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.dragging = False
        self.setCursor(QCursor(Qt.ArrowCursor))
    
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel"""
        delta = event.angleDelta().y()
        zoom_in = delta > 0
        
        if zoom_in and self.zoom_factor < 3.0:
            self.zoom_factor *= 1.25
        elif not zoom_in and self.zoom_factor > 0.25:
            self.zoom_factor /= 1.25
            
        self.update()
    
    def update_divider_position(self, x):
        """Update divider position based on mouse x coordinate"""
        self.divider_pos = max(0.1, min(0.9, x / self.rect().width()))
        self.update()

class PreviewDialog(QDialog):
    """Dialog for previewing changes with split view"""
    
    proceed_requested = pyqtSignal()  # Signal for proceeding with processing
    
    def __init__(self, file_path, settings, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.settings = settings
        self.preview_thread = None
        self.parent_window = parent
        
        self.init_ui()
        self.generate_preview()
        
    def init_ui(self):
        """Initialize the preview dialog UI"""
        self.setWindowTitle("Preview Changes - Split View")
        self.setModal(True)
        self.resize(900, 700)
        
        layout = QVBoxLayout(self)
        
        # Title and file info
        title_label = QLabel(f"📁 {os.path.basename(self.file_path)}") 
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Split view widget
        self.split_view = SplitViewWidget()
        layout.addWidget(self.split_view)
        
        # Instructions
        instructions = QLabel("💡 Drag the divider left/right to compare  •  🔍 Scroll wheel to zoom")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("color: #666666; margin: 10px;")
        layout.addWidget(instructions)
        
        # Current view info
        self.info_label = QLabel("Loading preview...")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("""
            background-color: #f0f0f0; 
            padding: 8px; 
            border-radius: 4px; 
            margin: 5px;
        """)
        layout.addWidget(self.info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)
        
        button_layout.addStretch()
        
        self.proceed_btn = QPushButton("Looks Good - Proceed")
        self.proceed_btn.clicked.connect(self.accept_and_proceed)
        self.proceed_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #005c99;
            }
        """)
        button_layout.addWidget(self.proceed_btn)
        
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
            
            # Set images in split view
            self.split_view.set_images(original_pixmap, processed_pixmap)
            
            # Update info
            border_width = self.settings.get('border_width_mm', 3)
            stretch_method = self.settings.get('stretch_method', 'edge_repeat').replace('_', ' ').title()
            source_width = self.settings.get('stretch_source_width_mm', 1.0)
            
            info_text = f"📏 Border: +{border_width}mm all sides  •  🎨 Method: {stretch_method}"
            if stretch_method != "Solid Color":
                info_text += f"  •  📐 Source: {source_width}mm"
            
            self.info_label.setText(info_text)
            
        except Exception as e:
            self.handle_error(f"Error displaying preview: {str(e)}")
            
    def image_to_pixmap(self, image):
        """Convert PIL image to QPixmap"""
        if hasattr(image, 'save'):  # PIL Image
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
        self.info_label.setText(f"Error: {error_message}")
        
    def accept_and_proceed(self):
        """Accept preview and trigger processing"""
        self.accept()
        # Trigger processing in parent window
        if self.parent_window and hasattr(self.parent_window, 'process_files'):
            self.parent_window.process_files()
        
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.terminate()
        event.accept()

