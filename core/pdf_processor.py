"""
PDF Processor - Adds background border layers without touching original content
"""

import os
import fitz  # PyMuPDF
import tempfile
import io
from pathlib import Path
from PIL import Image, ImageEnhance
import numpy as np
from datetime import datetime

from core.image_processor import ImageProcessor
from core.cut_mark_detector import CutMarkDetector

class PDFProcessor:
    """Main PDF processing class - background border approach"""
    
    def __init__(self, settings):
        self.settings = settings
        self.image_processor = ImageProcessor(settings)
        self.cut_mark_detector = CutMarkDetector(settings)
        
    def process_pdf(self, input_path):
        """
        Main method to process a PDF file and add background borders
        
        Args:
            input_path (str): Path to input PDF file
            
        Returns:
            str: Path to output PDF file
        """
        print(f"Starting BACKGROUND BORDER processing: {Path(input_path).name}")
        
        # Generate output path
        output_path = self._generate_output_path(input_path)
        
        # Create backup if requested
        if self.settings.get('backup_original', True):
            self._create_backup(input_path)
        
        # Open PDF document
        doc = fitz.open(input_path)
        
        try:
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Find center image on page
                center_image = self._find_center_image(page)
                
                if center_image:
                    print(f"Processing page {page_num + 1}: Found center image")
                    
                    # Detect cut marks BEFORE processing
                    cut_marks = self.cut_mark_detector.detect_cut_marks(page)
                    
                    # Generate border content from image
                    border_content = self._generate_border_content(page, center_image)
                    
                    # Add border as BACKGROUND layer (don't touch original or cut marks)
                    self._add_background_border_layer(page, center_image, border_content)
                    
                else:
                    print(f"Page {page_num + 1}: No center image found, skipping")
            
            # Save processed PDF
            doc.save(output_path, garbage=4, deflate=True)
            print(f"✓ Saved processed PDF: {Path(output_path).name}")
            
            # Add metadata if requested
            if self.settings.get('add_processing_info', False):
                self._add_processing_metadata(output_path)
            
            return output_path
            
        finally:
            doc.close()
    
    def extract_first_page_image(self, pdf_path):
        """
        Extract first page as image for preview
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            PIL.Image: First page as image
        """
        doc = fitz.open(pdf_path)
        try:
            page = doc[0]
            
            # Render page to image
            dpi = self.settings.get('output_dpi', 300)
            mat = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            
            return image
            
        finally:
            doc.close()
    
    def create_preview(self, pdf_path):
        """
        Create preview of processed image
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            PIL.Image: Preview image with borders
        """
        doc = fitz.open(pdf_path)
        try:
            page = doc[0]
            
            # Find center image
            center_image = self._find_center_image(page)
            
            if center_image:
                # Get original image
                original_image = self._extract_image_from_page(page, center_image)
                
                # Generate border content
                border_width_mm = self.settings.get('border_width_mm', 3)
                dpi = self.settings.get('output_dpi', 300)
                
                border_content = self.image_processor.generate_border_content(
                    original_image, border_width_mm, dpi)
                
                return border_content
            
            else:
                # Return original page if no center image
                return self.extract_first_page_image(pdf_path)
                
        finally:
            doc.close()
    
    def _find_center_image(self, page):
        """
        Find the center image on a PDF page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            dict: Image information or None
        """
        page_rect = page.rect
        page_center_x = page_rect.width / 2
        page_center_y = page_rect.height / 2
        
        # Get all images on page
        image_list = page.get_images()
        
        if not image_list:
            return None
        
        center_image = None
        min_distance = float('inf')
        
        for img_index, img in enumerate(image_list):
            # Get image rectangle
            img_rects = page.get_image_rects(img[0])
            
            if img_rects:
                img_rect = img_rects[0]  # Take first occurrence
                
                # Calculate center of image
                img_center_x = img_rect.x0 + (img_rect.x1 - img_rect.x0) / 2
                img_center_y = img_rect.y0 + (img_rect.y1 - img_rect.y0) / 2
                
                # Calculate distance from page center
                distance = ((img_center_x - page_center_x) ** 2 + 
                           (img_center_y - page_center_y) ** 2) ** 0.5
                
                # Check if image is reasonably large (not a small icon/logo)
                img_width = img_rect.x1 - img_rect.x0
                img_height = img_rect.y1 - img_rect.y0
                min_size = min(page_rect.width, page_rect.height) * 0.2  # At least 20% of page
                
                if (distance < min_distance and 
                    img_width > min_size and img_height > min_size):
                    min_distance = distance
                    center_image = {
                        'index': img_index,
                        'xref': img[0],
                        'rect': img_rect,
                        'width': img_width,
                        'height': img_height
                    }
        
        return center_image
    
    def _extract_image_from_page(self, page, image_info):
        """
        Extract image data from PDF page (for border generation only)
        
        Args:
            page: PyMuPDF page object
            image_info: Image information dict
            
        Returns:
            PIL.Image: Extracted image
        """
        # Get image data
        img_data = page.parent.extract_image(image_info['xref'])
        img_bytes = img_data["image"]
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(img_bytes))
        
        return image
    
    def _generate_border_content(self, page, image_info):
        """
        Generate border content from original image (without modifying original)
        
        Args:
            page: PyMuPDF page object
            image_info: Image information dict
            
        Returns:
            PIL.Image: Border content image
        """
        # Extract original image (read-only)
        original_image = self._extract_image_from_page(page, image_info)
        
        # Generate border content using image processor
        border_width_mm = self.settings.get('border_width_mm', 3)
        dpi = self.settings.get('output_dpi', 300)
        
        print(f"Generating border content: {border_width_mm}mm at {dpi} DPI")
        
        # Generate border content (original + stretched borders)
        border_content = self.image_processor.generate_border_content(
            original_image, border_width_mm, dpi)
        
        return border_content
    
    def _add_background_border_layer(self, page, image_info, border_content):
        """
        Add border content as BACKGROUND layer - don't touch original or cut marks
        
        Args:
            page: PyMuPDF page object
            image_info: Original image information
            border_content: PIL.Image - Generated border content
        """
        try:
            # Get original image rectangle
            original_rect = image_info['rect']
            original_center_x = (original_rect.x0 + original_rect.x1) / 2
            original_center_y = (original_rect.y0 + original_rect.y1) / 2
            
            # Calculate border expansion
            border_width_mm = self.settings.get('border_width_mm', 3)
            border_points = self._mm_to_points(border_width_mm)
            
            # Calculate background border rectangle (centered on original)
            original_width = original_rect.x1 - original_rect.x0
            original_height = original_rect.y1 - original_rect.y0
            border_width = original_width + (2 * border_points)
            border_height = original_height + (2 * border_points)
            
            # Center border content on original image position
            border_rect = fitz.Rect(
                original_center_x - border_width / 2,
                original_center_y - border_height / 2,
                original_center_x + border_width / 2,
                original_center_y + border_height / 2
            )
            
            # Ensure border doesn't go outside page boundaries
            page_rect = page.rect
            border_rect = border_rect & page_rect  # Intersection with page
            
            print(f"Background border placement:")
            print(f"  Original image: {original_rect}")
            print(f"  Border content: {border_rect}")
            print(f"  Original stays: UNCHANGED")
            print(f"  Cut marks stay: UNCHANGED")
            
            # Prepare border content for insertion
            if border_content.mode in ('RGBA', 'LA'):
                # Convert transparency to white background
                background = Image.new('RGB', border_content.size, (255, 255, 255))
                if border_content.mode == 'RGBA':
                    background.paste(border_content, mask=border_content.split()[-1])
                else:
                    background.paste(border_content)
                border_content = background
            elif border_content.mode != 'RGB':
                border_content = border_content.convert('RGB')
            
            # Save border content to buffer
            img_buffer = io.BytesIO()
            quality = max(85, 100 - self.settings.get('compression_level', 15))
            border_content.save(img_buffer, format='JPEG', quality=quality, optimize=True)
            img_buffer.seek(0)
            
            # CRITICAL: Insert border content as BACKGROUND layer
            # This goes BEHIND original image and cut marks
            page.insert_image(border_rect, stream=img_buffer.getvalue(), overlay=False)
            
            print("✓ Background border layer added successfully")
            print("✓ Original image and cut marks preserved in exact positions")
            
        except Exception as e:
            print(f"Error adding background border: {e}")
    
    def _generate_output_path(self, input_path):
        """
        Generate output file path based on settings
        
        Args:
            input_path (str): Input file path
            
        Returns:
            str: Output file path
        """
        input_path = Path(input_path)
        
        # Get suffix from settings
        suffix = self.settings.get('filename_suffix', '_bordered')
        
        # Add timestamp if requested
        if self.settings.get('include_timestamp', False):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            suffix = f"{suffix}_{timestamp}"
        
        # Generate output filename
        output_name = f"{input_path.stem}{suffix}{input_path.suffix}"
        
        # Use custom output directory if specified
        if self.settings.get('use_output_directory', False):
            output_dir = self.settings.get('output_directory', input_path.parent)
            output_path = Path(output_dir) / output_name
        else:
            output_path = input_path.parent / output_name
        
        return str(output_path)
    
    def _create_backup(self, input_path):
        """
        Create backup of original file
        
        Args:
            input_path (str): Path to original file
        """
        input_path = Path(input_path)
        backup_path = input_path.parent / f"{input_path.stem}_backup{input_path.suffix}"
        
        # Copy file
        import shutil
        shutil.copy2(input_path, backup_path)
        print(f"Created backup: {backup_path.name}")
    
    def _add_processing_metadata(self, pdf_path):
        """
        Add processing information to PDF metadata
        
        Args:
            pdf_path (str): Path to processed PDF
        """
        doc = fitz.open(pdf_path)
        try:
            # Get existing metadata
            metadata = doc.metadata
            
            # Add processing info
            processing_info = f"Processed with PDF Border Tool on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            processing_info += f" - Added {self.settings.get('border_width_mm', 3)}mm background border"
            
            metadata['subject'] = processing_info
            metadata['producer'] = 'PDF Border Tool - L\'Oréal'
            
            # Set updated metadata
            doc.set_metadata(metadata)
            doc.save(pdf_path, incremental=True)
            
        finally:
            doc.close()
    
    def _mm_to_points(self, mm):
        """
        Convert millimeters to PDF points
        
        Args:
            mm (float): Millimeters
            
        Returns:
            float: Points
        """
        return mm * 2.834645669  # 1mm = 2.834645669 points
