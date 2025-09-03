"""
Image Processor - Creates borders by stretching edge pixels around unchanged original image
"""

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2

class ImageProcessor:
    """Image processing for border creation - keeps original image unchanged"""
    
    def __init__(self, settings):
        self.settings = settings
    
    def add_border(self, image, border_width_mm, dpi):
        """
        Add border around unchanged original image by stretching edge content
        
        Args:
            image (PIL.Image): Original image (will remain unchanged)
            border_width_mm (float): Border width in millimeters
            dpi (int): Dots per inch for calculation
            
        Returns:
            PIL.Image: Original image + border (larger image)
        """
        # Convert mm to pixels
        border_pixels = self._mm_to_pixels(border_width_mm, dpi)
        
        # Get stretch method from settings
        method = self.settings.get('stretch_method', 'edge_repeat')
        
        print(f"Creating {border_width_mm}mm border ({border_pixels} pixels) around unchanged original")
        print(f"Original image size: {image.size}")
        
        # Apply border creation method
        if method == 'edge_repeat':
            result = self._create_stretched_edge_border(image, border_pixels)
        elif method == 'smart_fill':
            result = self._create_smart_border(image, border_pixels)
        elif method == 'gradient_fade':
            result = self._create_gradient_border(image, border_pixels)
        else:
            result = self._create_stretched_edge_border(image, border_pixels)
        
        print(f"Final image size: {result.size}")
        return result
    
    def _create_stretched_edge_border(self, original_image, border_pixels):
        """
        FIXED: Create border by stretching edge pixels around unchanged original image
        
        Args:
            original_image (PIL.Image): Original image (unchanged)
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Original image with stretched edge border around it
        """
        # Convert to numpy array
        original_array = np.array(original_image)
        orig_height, orig_width = original_array.shape[:2]
        
        # Calculate new dimensions (original + border on all sides)
        new_width = orig_width + (2 * border_pixels)
        new_height = orig_height + (2 * border_pixels)
        
        print(f"  Original: {orig_width} x {orig_height}")
        print(f"  With border: {new_width} x {new_height}")
        print(f"  Border size: {border_pixels} pixels")
        
        # Create larger canvas
        if len(original_array.shape) == 3:
            new_array = np.zeros((new_height, new_width, original_array.shape[2]), dtype=original_array.dtype)
        else:
            new_array = np.zeros((new_height, new_width), dtype=original_array.dtype)
        
        # STEP 1: Place original image in center (UNCHANGED)
        new_array[border_pixels:border_pixels+orig_height, 
                 border_pixels:border_pixels+orig_width] = original_array
        
        print("  ✓ Original image placed in center (unchanged)")
        
        # STEP 2: Calculate source region for stretching (1mm worth)
        stretch_source_pixels = max(3, border_pixels // 3)
        stretch_source_pixels = min(stretch_source_pixels, min(orig_width//4, orig_height//4))  # Safety limit
        
        print(f"  ✓ Using {stretch_source_pixels} pixels from edges for stretching")
        
        # STEP 3: Fill border areas systematically
        
        # Fill TOP border area
        for i in range(border_pixels):
            # Determine which source row to use from original image
            source_row_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            source_row_idx = min(source_row_idx, orig_height - 1)  # Safety check
            
            # Get the source row from original image
            source_row = original_array[source_row_idx, :].copy()
            
            # Create fading effect
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            if len(original_array.shape) == 3:
                faded_row = (source_row.astype(np.float32) * fade_factor).astype(original_array.dtype)
            else:
                faded_row = (source_row.astype(np.float32) * fade_factor).astype(original_array.dtype)
            
            # Extend the row to fill full width (including corner areas)
            extended_row = np.zeros((new_width,) + source_row.shape[1:], dtype=original_array.dtype)
            
            # Fill center part with the faded row
            extended_row[border_pixels:border_pixels+orig_width] = faded_row
            
            # Fill left corner area
            if len(original_array.shape) == 3:
                left_pixel = faded_row[0]  # First pixel of the row
                for j in range(border_pixels):
                    corner_fade = fade_factor * max(0.3, 1.0 - j / border_pixels)
                    extended_row[border_pixels-1-j] = (left_pixel.astype(np.float32) * corner_fade).astype(original_array.dtype)
            else:
                left_pixel = faded_row[0]
                for j in range(border_pixels):
                    corner_fade = fade_factor * max(0.3, 1.0 - j / border_pixels)
                    extended_row[border_pixels-1-j] = (left_pixel * corner_fade).astype(original_array.dtype)
            
            # Fill right corner area  
            if len(original_array.shape) == 3:
                right_pixel = faded_row[-1]  # Last pixel of the row
                for j in range(border_pixels):
                    corner_fade = fade_factor * max(0.3, 1.0 - j / border_pixels)
                    extended_row[border_pixels+orig_width+j] = (right_pixel.astype(np.float32) * corner_fade).astype(original_array.dtype)
            else:
                right_pixel = faded_row[-1]
                for j in range(border_pixels):
                    corner_fade = fade_factor * max(0.3, 1.0 - j / border_pixels)
                    extended_row[border_pixels+orig_width+j] = (right_pixel * corner_fade).astype(original_array.dtype)
            
            # Place the extended row in the top border
            new_array[border_pixels - 1 - i] = extended_row
        
        # Fill BOTTOM border area
        for i in range(border_pixels):
            source_row_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            source_row_idx = min(source_row_idx, orig_height - 1)
            
            # Get source row from bottom of original image
            source_row = original_array[orig_height - 1 - source_row_idx, :].copy()
            
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            if len(original_array.shape) == 3:
                faded_row = (source_row.astype(np.float32) * fade_factor).astype(original_array.dtype)
            else:
                faded_row = (source_row.astype(np.float32) * fade_factor).astype(original_array.dtype)
            
            # Extend the row to fill full width
            extended_row = np.zeros((new_width,) + source_row.shape[1:], dtype=original_array.dtype)
            extended_row[border_pixels:border_pixels+orig_width] = faded_row
            
            # Fill corners
            left_pixel = faded_row[0]
            right_pixel = faded_row[-1]
            
            for j in range(border_pixels):
                corner_fade = fade_factor * max(0.3, 1.0 - j / border_pixels)
                if len(original_array.shape) == 3:
                    extended_row[border_pixels-1-j] = (left_pixel.astype(np.float32) * corner_fade).astype(original_array.dtype)
                    extended_row[border_pixels+orig_width+j] = (right_pixel.astype(np.float32) * corner_fade).astype(original_array.dtype)
                else:
                    extended_row[border_pixels-1-j] = (left_pixel * corner_fade).astype(original_array.dtype)
                    extended_row[border_pixels+orig_width+j] = (right_pixel * corner_fade).astype(original_array.dtype)
            
            # Place in bottom border
            new_array[border_pixels + orig_height + i] = extended_row
        
        # Fill LEFT border area (middle part only, corners already done)
        for i in range(border_pixels):
            source_col_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            source_col_idx = min(source_col_idx, orig_width - 1)
            
            # Get source column from left edge of original
            source_col = original_array[:, source_col_idx].copy()
            
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            if len(original_array.shape) == 3:
                faded_col = (source_col.astype(np.float32) * fade_factor).astype(original_array.dtype)
            else:
                faded_col = (source_col.astype(np.float32) * fade_factor).astype(original_array.dtype)
            
            # Place in left border (middle section only, corners already filled)
            new_array[border_pixels:border_pixels + orig_height, border_pixels - 1 - i] = faded_col
        
        # Fill RIGHT border area (middle part only, corners already done)
        for i in range(border_pixels):
            source_col_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            source_col_idx = min(source_col_idx, orig_width - 1)
            
            # Get source column from right edge of original
            source_col = original_array[:, orig_width - 1 - source_col_idx].copy()
            
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            if len(original_array.shape) == 3:
                faded_col = (source_col.astype(np.float32) * fade_factor).astype(original_array.dtype)
            else:
                faded_col = (source_col.astype(np.float32) * fade_factor).astype(original_array.dtype)
            
            # Place in right border (middle section only)
            new_array[border_pixels:border_pixels + orig_height, border_pixels + orig_width + i] = faded_col
        
        print("  ✓ All border areas filled successfully")
        
        # Convert back to PIL Image
        result_image = Image.fromarray(new_array)
        return result_image
    
    def _create_smart_border(self, original_image, border_pixels):
        """
        Create border using content-aware fill around unchanged original
        
        Args:
            original_image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Image with smart border
        """
        try:
            # Convert to OpenCV format
            orig_array = np.array(original_image)
            orig_height, orig_width = orig_array.shape[:2]
            
            # Create larger canvas
            new_width = orig_width + (2 * border_pixels)
            new_height = orig_height + (2 * border_pixels)
            
            if len(orig_array.shape) == 3:
                extended_img = np.zeros((new_height, new_width, 3), dtype=np.uint8)
                img_cv = cv2.cvtColor(orig_array, cv2.COLOR_RGB2BGR)
            else:
                extended_img = np.zeros((new_height, new_width), dtype=np.uint8)
                img_cv = orig_array
            
            # Place original in center
            extended_img[border_pixels:border_pixels+orig_height, 
                        border_pixels:border_pixels+orig_width] = img_cv
            
            # Create mask for border areas only
            mask = np.zeros((new_height, new_width), dtype=np.uint8)
            mask[:border_pixels, :] = 255  # Top
            mask[-border_pixels:, :] = 255  # Bottom  
            mask[:, :border_pixels] = 255  # Left
            mask[:, -border_pixels:] = 255  # Right
            
            # Apply inpainting to border areas only
            if len(orig_array.shape) == 3:
                result = cv2.inpaint(extended_img, mask, 
                                   inpaintRadius=min(border_pixels//2, 10), 
                                   flags=cv2.INPAINT_TELEA)
                result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            else:
                result_rgb = cv2.inpaint(extended_img, mask, 
                                       inpaintRadius=min(border_pixels//2, 10), 
                                       flags=cv2.INPAINT_TELEA)
            
            return Image.fromarray(result_rgb)
            
        except Exception as e:
            print(f"Smart border failed, falling back to edge stretch: {e}")
            return self._create_stretched_edge_border(original_image, border_pixels)
    
    def _create_gradient_border(self, original_image, border_pixels):
        """
        Create gradient border around unchanged original
        
        Args:
            original_image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Image with gradient border
        """
        orig_array = np.array(original_image)
        orig_height, orig_width = orig_array.shape[:2]
        
        # Create larger canvas
        new_width = orig_width + (2 * border_pixels)
        new_height = orig_height + (2 * border_pixels)
        
        if len(orig_array.shape) == 3:
            new_array = np.zeros((new_height, new_width, orig_array.shape[2]), dtype=orig_array.dtype)
        else:
            new_array = np.zeros((new_height, new_width), dtype=orig_array.dtype)
        
        # Place original in center
        new_array[border_pixels:border_pixels+orig_height, 
                 border_pixels:border_pixels+orig_width] = orig_array
        
        # Create gradient borders
        for i in range(border_pixels):
            gradient_factor = max(0.1, 1.0 - (i / border_pixels))
            
            # Extract edge colors from original
            top_color = orig_array[0, :].astype(np.float32)
            bottom_color = orig_array[-1, :].astype(np.float32)
            left_color = orig_array[:, 0].astype(np.float32)
            right_color = orig_array[:, -1].astype(np.float32)
            
            # Apply gradient
            new_array[border_pixels-1-i, border_pixels:border_pixels+orig_width] = (top_color * gradient_factor).astype(orig_array.dtype)
            new_array[border_pixels+orig_height+i, border_pixels:border_pixels+orig_width] = (bottom_color * gradient_factor).astype(orig_array.dtype)
            new_array[border_pixels:border_pixels+orig_height, border_pixels-1-i] = (left_color * gradient_factor).astype(orig_array.dtype)
            new_array[border_pixels:border_pixels+orig_height, border_pixels+orig_width+i] = (right_color * gradient_factor).astype(orig_array.dtype)
        
        # Fill corners with corner pixels
        for i in range(border_pixels):
            for j in range(border_pixels):
                distance = np.sqrt(i**2 + j**2)
                fade = max(0.1, 1.0 - (distance / (border_pixels * 1.2)))
                
                # Use corner pixels from original
                tl_pixel = (orig_array[0, 0].astype(np.float32) * fade).astype(orig_array.dtype)
                tr_pixel = (orig_array[0, -1].astype(np.float32) * fade).astype(orig_array.dtype)
                bl_pixel = (orig_array[-1, 0].astype(np.float32) * fade).astype(orig_array.dtype)
                br_pixel = (orig_array[-1, -1].astype(np.float32) * fade).astype(orig_array.dtype)
                
                new_array[border_pixels-1-i, border_pixels-1-j] = tl_pixel
                new_array[border_pixels-1-i, border_pixels+orig_width+j] = tr_pixel
                new_array[border_pixels+orig_height+i, border_pixels-1-j] = bl_pixel
                new_array[border_pixels+orig_height+i, border_pixels+orig_width+j] = br_pixel
        
        return Image.fromarray(new_array)
    
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

