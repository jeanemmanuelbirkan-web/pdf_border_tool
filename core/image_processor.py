"""
Image Processor - Generates border content without modifying original
"""

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2

class ImageProcessor:
    """Generates border content from edge pixels"""
    
    def __init__(self, settings):
        self.settings = settings
    
    def generate_border_content(self, original_image, border_width_mm, dpi):
        """
        Generate border content around original image (original stays unchanged in center)
        
        Args:
            original_image (PIL.Image): Original image (read-only)
            border_width_mm (float): Border width in millimeters
            dpi (int): Dots per inch for calculation
            
        Returns:
            PIL.Image: Border content (original + generated borders)
        """
        # Convert mm to pixels
        border_pixels = self._mm_to_pixels(border_width_mm, dpi)
        
        # Get stretch method from settings
        method = self.settings.get('stretch_method', 'edge_repeat')
        
        print(f"Generating border content: {border_width_mm}mm ({border_pixels} pixels)")
        print(f"Method: {method}")
        print(f"Original size: {original_image.size}")
        
        # Generate border content using specified method
        if method == 'edge_repeat':
            result = self._generate_edge_stretched_content(original_image, border_pixels)
        elif method == 'smart_fill':
            result = self._generate_smart_fill_content(original_image, border_pixels)
        elif method == 'gradient_fade':
            result = self._generate_gradient_content(original_image, border_pixels)
        else:
            result = self._generate_edge_stretched_content(original_image, border_pixels)
        
        print(f"Generated content size: {result.size}")
        return result
    
    def _generate_edge_stretched_content(self, original_image, border_pixels):
        """
        Generate content: original in center + stretched edge borders
        
        Args:
            original_image (PIL.Image): Original image (unchanged)
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Complete content (original + borders)
        """
        # Convert original to array (read-only)
        original_array = np.array(original_image)
        orig_height, orig_width = original_array.shape[:2]
        
        # Calculate final dimensions
        final_width = orig_width + (2 * border_pixels)
        final_height = orig_height + (2 * border_pixels)
        
        print(f"  Original: {orig_width} x {orig_height}")
        print(f"  Final content: {final_width} x {final_height}")
        
        # Create final content array
        if len(original_array.shape) == 3:
            content_array = np.zeros((final_height, final_width, original_array.shape[2]), dtype=original_array.dtype)
        else:
            content_array = np.zeros((final_height, final_width), dtype=original_array.dtype)
        
        # STEP 1: Place original image in center (EXACT copy, no modifications)
        content_array[border_pixels:border_pixels+orig_height, 
                     border_pixels:border_pixels+orig_width] = original_array.copy()
        
        print("  ✓ Original placed in center (pixel-perfect copy)")
        
        # STEP 2: Generate border content from edge pixels
        # Extract edge strips for stretching (1mm worth of pixels)
        stretch_source_pixels = max(1, min(border_pixels // 3, orig_width // 10, orig_height // 10))
        
        print(f"  ✓ Using {stretch_source_pixels} pixels from edges for stretching")
        
        # Get edge data
        top_edge = original_array[:stretch_source_pixels, :].copy()
        bottom_edge = original_array[-stretch_source_pixels:, :].copy()
        left_edge = original_array[:, :stretch_source_pixels].copy()
        right_edge = original_array[:, -stretch_source_pixels:].copy()
        
        # STEP 3: Fill border areas with stretched content
        
        # Top border
        for i in range(border_pixels):
            source_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            fade_factor = max(0.3, 1.0 - (i / border_pixels) * 0.7)
            
            source_row = top_edge[source_idx, :].astype(np.float32)
            faded_row = (source_row * fade_factor).astype(original_array.dtype)
            
            # Fill entire width (including corner extensions)
            row_start = border_pixels - 1 - i
            
            # Center part
            content_array[row_start, border_pixels:border_pixels+orig_width] = faded_row
            
            # Left extension
            left_pixel = faded_row[0]
            for j in range(border_pixels):
                corner_fade = fade_factor * max(0.2, 1.0 - j / border_pixels)
                if len(original_array.shape) == 3:
                    content_array[row_start, border_pixels-1-j] = (left_pixel * corner_fade).astype(original_array.dtype)
                else:
                    content_array[row_start, border_pixels-1-j] = (left_pixel * corner_fade).astype(original_array.dtype)
            
            # Right extension
            right_pixel = faded_row[-1]
            for j in range(border_pixels):
                corner_fade = fade_factor * max(0.2, 1.0 - j / border_pixels)
                if len(original_array.shape) == 3:
                    content_array[row_start, border_pixels+orig_width+j] = (right_pixel * corner_fade).astype(original_array.dtype)
                else:
                    content_array[row_start, border_pixels+orig_width+j] = (right_pixel * corner_fade).astype(original_array.dtype)
        
        # Bottom border
        for i in range(border_pixels):
            source_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            fade_factor = max(0.3, 1.0 - (i / border_pixels) * 0.7)
            
            source_row = bottom_edge[-(source_idx + 1), :].astype(np.float32)
            faded_row = (source_row * fade_factor).astype(original_array.dtype)
            
            row_start = border_pixels + orig_height + i
            
            # Center part
            content_array[row_start, border_pixels:border_pixels+orig_width] = faded_row
            
            # Corner extensions
            left_pixel = faded_row[0]
            right_pixel = faded_row[-1]
            for j in range(border_pixels):
                corner_fade = fade_factor * max(0.2, 1.0 - j / border_pixels)
                if len(original_array.shape) == 3:
                    content_array[row_start, border_pixels-1-j] = (left_pixel * corner_fade).astype(original_array.dtype)
                    content_array[row_start, border_pixels+orig_width+j] = (right_pixel * corner_fade).astype(original_array.dtype)
                else:
                    content_array[row_start, border_pixels-1-j] = (left_pixel * corner_fade).astype(original_array.dtype)
                    content_array[row_start, border_pixels+orig_width+j] = (right_pixel * corner_fade).astype(original_array.dtype)
        
        # Left border (center part only, corners handled above)
        for i in range(border_pixels):
            source_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            fade_factor = max(0.3, 1.0 - (i / border_pixels) * 0.7)
            
            source_col = left_edge[:, source_idx].astype(np.float32)
            faded_col = (source_col * fade_factor).astype(original_array.dtype)
            
            content_array[border_pixels:border_pixels+orig_height, border_pixels-1-i] = faded_col
        
        # Right border (center part only, corners handled above)
        for i in range(border_pixels):
            source_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            fade_factor = max(0.3, 1.0 - (i / border_pixels) * 0.7)
            
            source_col = right_edge[:, -(source_idx + 1)].astype(np.float32)
            faded_col = (source_col * fade_factor).astype(original_array.dtype)
            
            content_array[border_pixels:border_pixels+orig_height, border_pixels+orig_width+i] = faded_col
        
        print("  ✓ Border areas filled with stretched edge content")
        
        # Convert back to PIL Image
        result_image = Image.fromarray(content_array)
        return result_image
    
    def _generate_smart_fill_content(self, original_image, border_pixels):
        """
        Generate content using smart fill around original
        
        Args:
            original_image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Content with smart-filled borders
        """
        try:
            return self._opencv_smart_fill(original_image, border_pixels)
        except Exception as e:
            print(f"Smart fill failed, using edge stretch: {e}")
            return self._generate_edge_stretched_content(original_image, border_pixels)
    
    def _opencv_smart_fill(self, original_image, border_pixels):
        """Use OpenCV for smart content-aware border generation"""
        orig_array = np.array(original_image)
        orig_height, orig_width = orig_array.shape[:2]
        
        # Create larger canvas
        final_width = orig_width + (2 * border_pixels)
        final_height = orig_height + (2 * border_pixels)
        
        if len(orig_array.shape) == 3:
            extended_img = np.zeros((final_height, final_width, 3), dtype=np.uint8)
            img_cv = cv2.cvtColor(orig_array, cv2.COLOR_RGB2BGR)
        else:
            extended_img = np.zeros((final_height, final_width), dtype=np.uint8)
            img_cv = orig_array
        
        # Place original in center
        extended_img[border_pixels:border_pixels+orig_height, 
                    border_pixels:border_pixels+orig_width] = img_cv
        
        # Create mask for border areas
        mask = np.zeros((final_height, final_width), dtype=np.uint8)
        mask[:border_pixels, :] = 255  # Top
        mask[-border_pixels:, :] = 255  # Bottom
        mask[:, :border_pixels] = 255  # Left
        mask[:, -border_pixels:] = 255  # Right
        
        # Apply inpainting
        if len(orig_array.shape) == 3:
            result = cv2.inpaint(extended_img, mask, 
                               inpaintRadius=min(border_pixels//2, 15), 
                               flags=cv2.INPAINT_TELEA)
            result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        else:
            result_rgb = cv2.inpaint(extended_img, mask, 
                                   inpaintRadius=min(border_pixels//2, 15), 
                                   flags=cv2.INPAINT_TELEA)
        
        return Image.fromarray(result_rgb)
    
    def _generate_gradient_content(self, original_image, border_pixels):
        """
        Generate content with gradient borders
        
        Args:
            original_image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Content with gradient borders
        """
        orig_array = np.array(original_image)
        orig_height, orig_width = orig_array.shape[:2]
        
        # Create final content array
        final_width = orig_width + (2 * border_pixels)
        final_height = orig_height + (2 * border_pixels)
        
        if len(orig_array.shape) == 3:
            content_array = np.zeros((final_height, final_width, orig_array.shape[2]), dtype=orig_array.dtype)
        else:
            content_array = np.zeros((final_height, final_width), dtype=orig_array.dtype)
        
        # Place original in center
        content_array[border_pixels:border_pixels+orig_height, 
                     border_pixels:border_pixels+orig_width] = orig_array.copy()
        
        # Create gradient borders
        for i in range(border_pixels):
            gradient_factor = max(0.1, 1.0 - (i / border_pixels))
            
            # Get edge colors
            top_color = orig_array[0, :].astype(np.float32)
            bottom_color = orig_array[-1, :].astype(np.float32)
            left_color = orig_array[:, 0].astype(np.float32)
            right_color = orig_array[:, -1].astype(np.float32)
            
            # Apply gradient
            content_array[border_pixels-1-i, border_pixels:border_pixels+orig_width] = (top_color * gradient_factor).astype(orig_array.dtype)
            content_array[border_pixels+orig_height+i, border_pixels:border_pixels+orig_width] = (bottom_color * gradient_factor).astype(orig_array.dtype)
            content_array[border_pixels:border_pixels+orig_height, border_pixels-1-i] = (left_color * gradient_factor).astype(orig_array.dtype)
            content_array[border_pixels:border_pixels+orig_height, border_pixels+orig_width+i] = (right_color * gradient_factor).astype(orig_array.dtype)
        
        # Fill corners
        for i in range(border_pixels):
            for j in range(border_pixels):
                distance = np.sqrt(i**2 + j**2)
                fade = max(0.1, 1.0 - (distance / (border_pixels * 1.2)))
                
                # Corner pixels
                tl_pixel = (orig_array[0, 0].astype(np.float32) * fade).astype(orig_array.dtype)
                tr_pixel = (orig_array[0, -1].astype(np.float32) * fade).astype(orig_array.dtype)
                bl_pixel = (orig_array[-1, 0].astype(np.float32) * fade).astype(orig_array.dtype)
                br_pixel = (orig_array[-1, -1].astype(np.float32) * fade).astype(orig_array.dtype)
                
                content_array[border_pixels-1-i, border_pixels-1-j] = tl_pixel
                content_array[border_pixels-1-i, border_pixels+orig_width+j] = tr_pixel
                content_array[border_pixels+orig_height+i, border_pixels-1-j] = bl_pixel
                content_array[border_pixels+orig_height+i, border_pixels+orig_width+j] = br_pixel
        
        return Image.fromarray(content_array)
    
    def _mm_to_pixels(self, mm, dpi):
        """
        Convert millimeters to pixels based on DPI
        
        Args:
            mm (float): Millimeters
            dpi (int): Dots per inch
            
        Returns:
            int: Pixels
        """
        inches = mm / 25.4  # Convert mm to inches
        pixels = int(inches * dpi)
        return max(1, pixels)  # Ensure at least 1 pixel
