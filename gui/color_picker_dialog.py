"""
Color Picker Dialog - Pick colors from PDF images
"""

import os
import io
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QScrollArea, QWidget,
                            QMessageBox)
from PyQt5.QtCore import Qt, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QCursor, QColor, QPen

from core.pdf_processor import PDFProcessor

class ImageLoadThread(QThread):
    """Thread for loading PDF image in background"""
    
    image_loaded = pyqtSignal(object)  # PIL Image
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path, settings):
        super().__init__()
        self.file_path = file_path
        self.settings = settings
        
    def run(self):
        """Load image in background"""
        try:
            processor = PDFProcessor(self.settings)
            image = processor.extract_first_page_image(self.file_path)
            self.image_loaded.emit(image)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ClickableImageLabel(QLabel):
    """Image label that responds to clicks for color picking"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.setMinimumSize(400, 300)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """)
        
        # Crosshair cursor for color picking
        self.setCursor(QCursor(Qt.CrossCursor))
        
    def set_image(self, pixmap):
        """Set the image for color picking"""
        self.original_pixmap = pixmap
        self.update_display()
        
    def update_display(self):
        """Update the displayed image"""
        if self.original_pixmap:
            # Scale image to fit label while maintaining aspect ratio
            available_size = self.size()
            # Leave some margin
            display_size = available_size * 0.95
            
            self.scaled_pixmap = self.original_pixmap.scaled(
                int(display_size.width()), int(display_size.height()), 
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(self.scaled_pixmap)
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if self.original_pixmap:
            self.update_display()
            
    def mousePressEvent(self, event):
        """Handle mouse clicks to pick colors"""
        if event.button() == Qt.LeftButton and self.original_pixmap and self.scaled_pixmap:
            try:
                # Get click position relative to the widget
                click_pos = event.pos()
                widget_size = self.size()
                scaled_size = self.scaled_pixmap.size()
                
                # Calculate the position of the scaled image within the widget
                offset_x = (widget_size.width() - scaled_size.width()) // 2
                offset_y = (widget_size.height() - scaled_size.height()) // 2
                
                # Check if click is within the actual image area
                if (offset_x <= click_pos.x() <= offset_x + scaled_size.width() and 
                    offset_y <= click_pos.y() <= offset_y + scaled_size.height()):
                    
                    # Convert click position to scaled image coordinates
                    img_x = click_pos.x() - offset_x
                    img_y = click_pos.y() - offset_y
                    
                    # Convert to original image coordinates
                    scale_x = self.original_pixmap.width() / scaled_size.width()
                    scale_y = self.original_pixmap.height() / scaled_size.height()
                    
                    orig_x = int(img_x * scale_x)
                    orig_y = int(img_y * scale_y)
                    
                    # Ensure coordinates are within bounds
                    orig_x = max(0, min(orig_x, self.original_pixmap.width() - 1))
                    orig_y = max(0, min(orig_y, self.original_pixmap.height() - 1))
                    
                    # Get pixel color from original image
                    pixel_color = self.original_pixmap.toImage().pixelColor(orig_x, orig_y)
                    
                    if self.parent_dialog:
                        self.parent_dialog.color_picked(pixel_color, orig_x, orig_y)
                        
            except Exception as e:
                print(f"Error picking color: {e}")
                if self.parent_dialog:
                    QMessageBox.warning(self.parent_dialog, "Color Pick Error", 
                                      f"Could not pick color: {str(e)}")

class ColorPickerDialog(QDialog):
    """Dialog for picking colors from PDF images"""
    
    def __init__(self, file_path, settings, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.settings = settings
        self.selected_color = None
        self.image_load_thread = None
        
        self.init_ui()
        self.load_image()
        
    def init_ui(self):
        """Initialize the color picker dialog UI"""
        self.setWindowTitle(f"Pick Border Color - {os.path.basename(self.file_path)}")
        self.setModal(True)
        self.resize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # Title and instructions
        title_label = QLabel("Color Picker")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        instructions = QLabel("🎯 Click anywhere on the image to pick a color for the border")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Loading label
        self.loading_label = QLabel("Loading image...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #999999; font-style: italic;")
        layout.addWidget(self.loading_label)
        
        # Scroll area for image
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignCenter)
        scroll_area.setMinimumHeight(400)
        
        # Clickable image label
        self.image_label = ClickableImageLabel(self)
        scroll_area.setWidget(self.image_label)
        layout.addWidget(scroll_area)
        
        # Selected color display section
        color_section = QWidget()
        color_section.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
        """)
        color_layout = QHBoxLayout(color_section)
        
        color_layout.addWidget(QLabel("Selected Color:"))
        
        # Color preview box
        self.color_display = QLabel()
        self.color_display.setFixedSize(60, 40)
        self.color_display.setStyleSheet("""
            border: 2px solid #999; 
            background-color: white;
            border-radius: 3px;
        """)
        color_layout.addWidget(self.color_display)
        
        # Color information
        color_info_layout = QVBoxLayout()
        self.color_info = QLabel("Click on the image to select a color")
        self.color_info.setStyleSheet("font-weight: bold;")
        self.pixel_info = QLabel("")
        self.pixel_info.setStyleSheet("color: #666666; font-size: 11px;")
        
        color_info_layout.addWidget(self.color_info)
        color_info_layout.addWidget(self.pixel_info)
        color_layout.addLayout(color_info_layout)
        
        color_layout.addStretch()
        layout.addWidget(color_section)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Helper buttons
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.clicked.connect(self.reset_selection)
        self.reset_btn.setEnabled(False)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        # Main action buttons
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("✓ Use This Color")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        self.ok_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
    def load_image(self):
        """Load PDF image in background thread"""
        self.image_load_thread = ImageLoadThread(self.file_path, self.settings)
        self.image_load_thread.image_loaded.connect(self.on_image_loaded)
        self.image_load_thread.error_occurred.connect(self.on_load_error)
        self.image_load_thread.start()
        
    def on_image_loaded(self, pil_image):
        """Handle successful image loading"""
        try:
            # Convert PIL image to QPixmap
            if hasattr(pil_image, 'save'):  # PIL Image
                buffer = io.BytesIO()
                
                # Convert to RGB if necessary
                if pil_image.mode in ('RGBA', 'LA'):
                    # Create white background
                    background = pil_image.convert('RGB')
                    if pil_image.mode == 'RGBA':
                        # Composite with white background
                        white_bg = Image.new('RGB', pil_image.size, (255, 255, 255))
                        background = Image.alpha_composite(white_bg.convert('RGBA'), pil_image).convert('RGB')
                    pil_image = background
                elif pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                
                # Save to buffer
                pil_image.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Create QPixmap
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())
                
                # Hide loading label and show image
                self.loading_label.hide()
                self.image_label.set_image(pixmap)
                
        except Exception as e:
            self.on_load_error(f"Error converting image: {str(e)}")
            
    def on_load_error(self, error_message):
        """Handle image loading error"""
        self.loading_label.setText(f"Error loading image: {error_message}")
        self.loading_label.setStyleSheet("color: red; font-style: italic;")
        
        QMessageBox.warning(self, "Image Load Error", 
                          f"Could not load PDF image:\n{error_message}")
        
    def color_picked(self, color, x, y):
        """Handle color selection from image click"""
        self.selected_color = color
        
        # Update color display
        self.color_display.setStyleSheet(f"""
            border: 2px solid #999; 
            background-color: {color.name()};
            border-radius: 3px;
        """)
        
        # Update color information
        rgb_text = f"RGB({color.red()}, {color.green()}, {color.blue()})"
        hex_text = f"Hex: {color.name().upper()}"
        self.color_info.setText(f"{rgb_text} • {hex_text}")
        
        # Update pixel information
        self.pixel_info.setText(f"Picked from pixel ({x}, {y})")
        
        # Enable buttons
        self.ok_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        
        print(f"Color picked: {color.name()} from pixel ({x}, {y})")
        
    def reset_selection(self):
        """Reset color selection"""
        self.selected_color = None
        
        # Reset color display
        self.color_display.setStyleSheet("""
            border: 2px solid #999; 
            background-color: white;
            border-radius: 3px;
        """)
        
        # Reset information
        self.color_info.setText("Click on the image to select a color")
        self.pixel_info.setText("")
        
        # Disable buttons
        self.ok_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        
    def get_selected_color(self):
        """Get the selected color"""
        return self.selected_color
        
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.image_load_thread and self.image_load_thread.isRunning():
            self.image_load_thread.terminate()
            self.image_load_thread.wait()
        event.accept()
