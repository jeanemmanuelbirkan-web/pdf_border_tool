"""
PDF Processor - Main engine for PDF manipulation and border addition
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
    """Main PDF processing class"""
    
    def __init__(self, settings):
        self.settings = settings
        self.image_processor = ImageProcessor(settings)
        self.cut_mark_detector = CutMarkDetector(settings)
        
    def process_pdf(self, input_path):
        """
        Main method to process a PDF file and add borders
        
        Args:
            input_path (str): Path to input PDF file
            
        Returns:
            str: Path to output PDF file
        """
        print(f"Starting processing: {Path(input_path).name}")
        
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
                    
                    # Process the image
                    processed_image = self._process_page_image(page, center_image, cut_marks)
                    
                    # Replace image in PDF with cut mark preservation
                    self._replace_image_in_page(page, center_image, processed_image, cut_marks)
                    
                else:
                    print(f"Page {page_num + 1}: No center image found, skipping")
            
            # Save processed PDF
            doc.save(output_path, garbage=4, deflate=True)
            print(f"Saved processed PDF: {Path(output_path).name}")
            
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
                
                # Process with border
                border_width_mm = self.settings.get('border_width_mm', 3)
                dpi = self.settings.get('output_dpi', 300)
                
                processed_image = self.image_processor.add_border(
                    original_image, border_width_mm, dpi)
                
                return processed_image
            
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
        Extract image data from PDF page
        
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
    
    def _process_page_image(self, page, image_info, cut_marks):
        """
        Process image with border addition
        
        Args:
            page: PyMuPDF page object
            image_info: Image information dict
            cut_marks: Cut mark detection results
            
        Returns:
            PIL.Image: Processed image with border
        """
        # Extract original image
        original_image = self._extract_image_from_page(page, image_info)
        
        # Add border using image processor
        border_width_mm = self.settings.get('border_width_mm', 3)
        dpi = self.settings.get('output_dpi', 300)
        
        print(f"Creating border: {border_width_mm}mm at {dpi} DPI")
        processed_image = self.image_processor.add_border(
            original_image, border_width_mm, dpi)
        
        # Apply any additional processing based on cut marks
        if cut_marks and cut_marks.get('detected', False):
            processed_image = self._adjust_for_cut_marks(processed_image, cut_marks)
        
        return processed_image
    
    def _replace_image_in_page(self, page, image_info, new_image, cut_marks=None):
        """
        DEBUG VERSION: Shows detailed positioning information
        """
        try:
            # Get original image rectangle and center
            old_rect = image_info['rect']
            old_center_x = (old_rect.x0 + old_rect.x1) / 2
            old_center_y = (old_rect.y0 + old_rect.y1) / 2
            old_width = old_rect.x1 - old_rect.x0
            old_height = old_rect.y1 - old_rect.y0
            
            # Get page info
            page_rect = page.rect
            
            print("="*50)
            print("DEBUG: Image Replacement Information")
            print("="*50)
            print(f"Page size: {page_rect.width:.1f} x {page_rect.height:.1f}")
            print(f"Original image position: ({old_rect.x0:.1f}, {old_rect.y0:.1f}) to ({old_rect.x1:.1f}, {old_rect.y1:.1f})")
            print(f"Original image size: {old_width:.1f} x {old_height:.1f}")
            print(f"Original image center: ({old_center_x:.1f}, {old_center_y:.1f})")
            
            # Calculate border
            border_width_mm = self.settings.get('border_width_mm', 3)
            border_points = self._mm_to_points(border_width_mm)
            print(f"Border: {border_width_mm}mm = {border_points:.1f} points")
            
            # For now, just replace at EXACT same position to test
            # Convert image
            if new_image.mode != 'RGB':
                new_image = new_image.convert('RGB')
            
            # Save to buffer
            img_buffer = io.BytesIO()
            new_image.save(img_buffer, format='JPEG', quality=90)
            img_buffer.seek(0)
            
            # Cover original image
            page.draw_rect(old_rect, color=(1, 1, 1), fill=(1, 1, 1))
            print(f"Covered original area: {old_rect}")
            
            # Insert new image at EXACT same position first
            page.insert_image(old_rect, stream=img_buffer.getvalue())
            print(f"Inserted new image at SAME position: {old_rect}")
            
            print("="*50)
            
        except Exception as e:
            print(f"Error in debug replacement: {e}")
    
    def _fallback_image_replacement(self, page, image_info, new_image):
        """
        Fallback method for image replacement
        
        Args:
            page: PyMuPDF page object
            image_info: Original image information  
            new_image: PIL.Image - New image to insert
        """
        try:
            print("Using fallback image replacement method")
            
            old_rect = image_info['rect']
            
            # Convert image
            if new_image.mode != 'RGB':
                new_image = new_image.convert('RGB')
            
            # Save to buffer
            img_buffer = io.BytesIO()
            new_image.save(img_buffer, format='JPEG', quality=90)
            img_buffer.seek(0)
            
            # Cover original image
            page.draw_rect(old_rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Insert at original location with slight expansion
            border_points = self._mm_to_points(3)
            expanded_rect = fitz.Rect(
                old_rect.x0 - border_points/2,
                old_rect.y0 - border_points/2,
                old_rect.x1 + border_points/2,
                old_rect.y1 + border_points/2
            )
            
            page.insert_image(expanded_rect, stream=img_buffer.getvalue())
            
            print("Fallback replacement completed")
            
        except Exception as e:
            print(f"Fallback replacement also failed: {e}")
    
    def _adjust_for_cut_marks(self, image, cut_marks):
        """
        Adjust processed image to preserve cut mark positioning
        
        Args:
            image: PIL.Image - Processed image
            cut_marks: Cut mark detection results
            
        Returns:
            PIL.Image: Adjusted image
        """
        if not cut_marks.get('detected', False):
            return image
        
        print(f"Adjusting image for {len(cut_marks.get('marks', []))} detected cut marks")
        
        # For now, return image as-is since positioning is handled in replacement
        # Future: Could implement image cropping/adjustment if needed
        return image
    
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
            processing_info += f" - Added {self.settings.get('border_width_mm', 3)}mm border"
            
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

