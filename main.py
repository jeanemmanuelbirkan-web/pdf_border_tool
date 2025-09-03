#!/usr/bin/env python3
"""
PDF Border Tool - Main Application Entry Point
Adds 3mm borders to center images in PDF files.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from utils.config import Config

class PDFBorderApp(QApplication):
    """Main application class"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("PDF Border Tool")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("L'Oréal")
        
        # Set application properties
        self.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # Initialize configuration
        self.config = Config()
        
        # Create main window
        self.main_window = None
        
    def run(self):
        """Initialize and show the main window"""
        try:
            self.main_window = MainWindow(self.config)
            self.main_window.show()
            return self.exec_()
        except Exception as e:
            QMessageBox.critical(None, "Startup Error", 
                               f"Failed to start application:\n{str(e)}")
            return 1

def main():
    """Main entry point"""
    # Enable high DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = PDFBorderApp(sys.argv)
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
