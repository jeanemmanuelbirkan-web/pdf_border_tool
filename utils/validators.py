"""
Validators - Input validation and file checking utilities
"""

import os
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import mimetypes

class PDFValidator:
    """PDF file validation utilities"""
    
    def __init__(self):
        self.max_file_size = 100 * 1024 * 1024  # 100MB default
        self.supported_versions = ['1.0', '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '2.0']
    
    def validate_pdf(self, file_path):
        """
        Comprehensive PDF validation
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                return False, "File is not readable (permission denied)"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                size_mb = file_size / (1024 * 1024)
                return False, f"File too large ({size_mb:.1f}MB). Maximum size: {self.max_file_size // (1024*1024)}MB"
            
            if file_size == 0:
                return False, "File is empty"
            
            # Check file extension
            if file_path.suffix.lower() != '.pdf':
                return False, "File does not have .pdf extension"
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type != 'application/pdf':
                return False, f"File MIME type is {mime_type}, expected application/pdf"
            
            # Try to open with PyMuPDF
            try:
                doc = fitz.open(str(file_path))
                
                # Check if password protected
                if doc.needs_pass:
                    doc.close()
                    return False, "PDF is password protected"
                
                # Check for corruption
                if doc.page_count == 0:
                    doc.close()
                    return False, "PDF has no pages"
                
                # Test first page access
                try:
                    first_page = doc[0]
                    page_rect = first_page.rect
                    if page_rect.width <= 0 or page_rect.height <= 0:
                        doc.close()
                        return False, "PDF has invalid page dimensions"
                except Exception:
                    doc.close()
                    return False, "Cannot access PDF pages (possibly corrupted)"
                
                # Check for images
                has_images = self._check_for_images(doc)
                if not has_images:
                    doc.close()
                    return False, "PDF does not contain any images to process"
                
                doc.close()
                return True, "PDF is valid and ready for processing"
                
            except Exception as e:
                return False, f"Cannot open PDF: {str(e)}"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _check_for_images(self, doc):
        """
        Check if PDF contains processable images
        
        Args:
            doc: PyMuPDF document
            
        Returns:
            bool: True if images found
        """
        try:
            for page_num in range(min(3, doc.page_count)):  # Check first 3 pages
                page = doc[page_num]
                image_list = page.get_images()
                
                if image_list:
                    # Check if any image is reasonably large
                    page_rect = page.rect
                    min_size = min(page_rect.width, page_rect.height) * 0.1
                    
                    for img in image_list:
                        img_rects = page.get_image_rects(img[0])
                        if img_rects:
                            img_rect = img_rects[0]
                            img_width = img_rect.x1 - img_rect.x0
                            img_height = img_rect.y1 - img_rect.y0
                            
                            if img_width > min_size and img_height > min_size:
                                return True
            
            return False
            
        except Exception:
            return False
    
    def validate_batch(self, file_paths):
        """
        Validate multiple PDF files
        
        Args:
            file_paths (list): List of file paths
            
        Returns:
            dict: Validation results for each file
        """
        results = {}
        
        for file_path in file_paths:
            is_valid, message = self.validate_pdf(file_path)
            results[file_path] = {
                'valid': is_valid,
                'message': message,
                'size': Path(file_path).stat().st_size if Path(file_path).exists() else 0
            }
        
        return results
    
    def get_pdf_info(self, file_path):
        """
        Get detailed PDF information
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            dict: PDF information
        """
        try:
            doc = fitz.open(file_path)
            
            # Basic info
            info = {
                'file_path': file_path,
                'file_size': Path(file_path).stat().st_size,
                'page_count': doc.page_count,
                'metadata': doc.metadata,
                'is_pdf': True,
                'needs_password': doc.needs_pass,
                'pages': []
            }
            
            # Page information
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_rect = page.rect
                
                page_info = {
                    'page_number': page_num + 1,
                    'width': page_rect.width,
                    'height': page_rect.height,
                    'rotation': page.rotation,
                    'image_count': len(page.get_images()),
                    'has_text': bool(page.get_text().strip())
                }
                
                info['pages'].append(page_info)
            
            doc.close()
            return info
            
        except Exception as e:
            return {
                'file_path': file_path,
                'error': str(e),
                'is_pdf': False
            }

class SettingsValidator:
    """Settings and input validation"""
    
    @staticmethod
    def validate_border_width(width):
        """
        Validate border width setting
        
        Args:
            width: Border width value
            
        Returns:
            tuple: (is_valid: bool, normalized_value, message: str)
        """
        try:
            width_float = float(width)
            
            if width_float <= 0:
                return False, 1.0, "Border width must be positive"
            
            if width_float > 50:
                return False, 50.0, "Border width too large (maximum 50mm)"
            
            return True, width_float, "Valid border width"
            
        except ValueError:
            return False, 3.0, "Border width must be a number"
    
    @staticmethod
    def validate_dpi(dpi):
        """
        Validate DPI setting
        
        Args:
            dpi: DPI value
            
        Returns:
            tuple: (is_valid: bool, normalized_value, message: str)
        """
        try:
            dpi_int = int(dpi)
            
            if dpi_int < 72:
                return False, 72, "DPI too low (minimum 72)"
            
            if dpi_int > 600:
                return False, 600, "DPI too high (maximum 600)"
            
            return True, dpi_int, "Valid DPI"
            
        except ValueError:
            return False, 300, "DPI must be a number"
    
    @staticmethod
    def validate_filename_suffix(suffix):
        """
        Validate filename suffix
        
        Args:
            suffix: Filename suffix
            
        Returns:
            tuple: (is_valid: bool, normalized_value, message: str)
        """
        if not suffix:
            return False, "_bordered", "Suffix cannot be empty"
        
        # Check for invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in suffix:
                return False, "_bordered", f"Suffix contains invalid character: {char}"
        
        # Ensure suffix starts with underscore or dash for clarity
        if not suffix.startswith(('_', '-')):
            suffix = '_' + suffix
        
        return True, suffix, "Valid filename suffix"
    
    @staticmethod
    def validate_output_directory(directory):
        """
        Validate output directory
        
        Args:
            directory: Directory path
            
        Returns:
            tuple: (is_valid: bool, normalized_path, message: str)
        """
        if not directory:
            return True, "", "Using default output location"
        
        try:
            dir_path = Path(directory)
            
            # Check if directory exists
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    return True, str(dir_path), "Created output directory"
                except Exception as e:
                    return False, "", f"Cannot create directory: {str(e)}"
            
            # Check if writable
            if not os.access(dir_path, os.W_OK):
                return False, "", "Directory is not writable"
            
            return True, str(dir_path), "Valid output directory"
            
        except Exception as e:
            return False, "", f"Invalid directory path: {str(e)}"

class ImageValidator:
    """Image validation utilities"""
    
    @staticmethod
    def validate_image_format(image):
        """
        Validate PIL image format
        
        Args:
            image: PIL Image object
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not hasattr(image, 'format'):
            return False, "Not a valid PIL Image"
        
        supported_formats = ['JPEG', 'PNG', 'TIFF', 'BMP', 'GIF']
        
        if image.format not in supported_formats:
            return False, f"Unsupported image format: {image.format}"
        
        if image.size[0] <= 0 or image.size[1] <= 0:
            return False, "Invalid image dimensions"
        
        return True, "Valid image format"
    
    @staticmethod
    def validate_image_size(image, max_pixels=50000000):  # 50MP default
        """
        Validate image size constraints
        
        Args:
            image: PIL Image object
            max_pixels: Maximum total pixels
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        width, height = image.size
        total_pixels = width * height
        
        if total_pixels > max_pixels:
            return False, f"Image too large ({total_pixels:,} pixels, max: {max_pixels:,})"
        
        if width < 10 or height < 10:
            return False, "Image too small (minimum 10x10 pixels)"
        
        return True, "Valid image size"
