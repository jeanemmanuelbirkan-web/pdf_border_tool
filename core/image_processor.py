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
        Create border by stretching edge pixels around unchanged original image
        
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
        
        # STEP 2: Extract edge regions from original (1mm worth of pixels)
        stretch_source_pixels = max(3, border_pixels // 3)  # 1mm source for 3mm border
        
        # Get edge strips from original image
        top_edge = original_array[:stretch_source_pixels, :]
        bottom_edge = original_array[-stretch_source_pixels:, :]
        left_edge = original_array[:, :stretch_source_pixels]
        right_edge = original_array[:, -stretch_source_pixels:]
        
        # Corner pixels for corner areas
        top_left_corner = original_array[:stretch_source_pixels, :stretch_source_pixels]
        top_right_corner = original_array[:stretch_source_pixels, -stretch_source_pixels:]
        bottom_left_corner = original_array[-stretch_source_pixels:, :stretch_source_pixels]
        bottom_right_corner = original_array[-stretch_source_pixels:, -stretch_source_pixels:]
        
        print(f"  ✓ Extracted edge regions ({stretch_source_pixels} pixels wide)")
        
        # STEP 3: Fill border areas with stretched edge content
        
        # Fill TOP border
        for i in range(border_pixels):
            # Determine which source row to use
            source_row_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            # Add subtle fade effect
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            
            source_row = top_edge[source_row_idx, :].astype(np.float32)
            faded_row = (source_row * fade_factor).astype(original_array.dtype)
            
            # Place in top border (extending across full width including corners)
            new_array[border_pixels - 1 - i, :] = faded_row
        
        # Fill BOTTOM border
        for i in range(border_pixels):
            source_row_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            
            source_row = bottom_edge[-(source_row_idx + 1), :].astype(np.float32)
            faded_row = (source_row * fade_factor).astype(original_array.dtype)
            
            # Place in bottom border
            new_array[border_pixels + orig_height + i, :] = faded_row
        
        # Fill LEFT border (only the middle section, not corners)
        for i in range(border_pixels):
            source_col_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            
            source_col = left_edge[:, source_col_idx].astype(np.float32)
            faded_col = (source_col * fade_factor).astype(original_array.dtype)
            
            # Place in left border (middle section only)
            new_array[border_pixels:border_pixels + orig_height, border_pixels - 1 - i] = faded_col
        
        # Fill RIGHT border (only the middle section, not corners)  
        for i in range(border_pixels):
            source_col_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            fade_factor = max(0.4, 1.0 - (i / border_pixels) * 0.6)
            
            source_col = right_edge[:, -(source_col_idx + 1)].astype(np.float32)
            faded_col = (source_col * fade_factor).astype(original_array.dtype)
            
            # Place in right border (middle section only)
            new_array[border_pixels:border_pixels + orig_height, border_pixels + orig_width + i] = faded_col
        
        # STEP 4: Fill corner areas
        self._fill_corner_areas(new_array, border_pixels, orig_width, orig_height, 
                               top_left_corner, top_right_corner, 
                               bottom_left_corner, bottom_right_corner)
        
        print("  ✓ Border areas filled with stretched edge content")
        
        # Convert back to PIL Image
        result_image = Image.fromarray(new_array)
        
        return result_image
    
    def _fill_corner_areas(self, new_array, border_pixels, orig_width, orig_height, 
                          tl_corner, tr_corner, bl_corner, br_corner):
        """
        Fill corner areas with appropriately stretched corner content
        
        Args:
            new_array: New image array being constructed
            border_pixels: Border width in pixels
            orig_width, orig_height: Original image dimensions
            tl_corner, tr_corner, bl_corner, br_corner: Corner image data
        """
        
        # Top-left corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                # Calculate fade based on distance from corner
                distance_factor = np.sqrt(i**2 + j**2) / (border_pixels * 1.2)
                fade_factor = max(0.3, 1.0 - distance_factor * 0.7)
                
                # Use appropriate corner pixel
                corner_i = min(i, tl_corner.shape[0] - 1)
                corner_j = min(j, tl_corner.shape[1] - 1)
                
                corner_pixel = tl_corner[corner_i, corner_j].astype(np.float32)
                faded_pixel = (corner_pixel * fade_factor).astype(new_array.dtype)
                
                new_array[border_pixels - 1 - i, border_pixels - 1 - j] = faded_pixel
        
        # Top-right corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                distance_factor = np.sqrt(i**2 + j**2) / (border_pixels * 1.2)
                fade_factor = max(0.3, 1.0 - distance_factor * 0.7)
                
                corner_i = min(i, tr_corner.shape[0] - 1)
                corner_j = min(j, tr_corner.shape[1] - 1)
                
                corner_pixel = tr_corner[corner_i, -(corner_j + 1)].astype(np.float32)
                faded_pixel = (corner_pixel * fade_factor).astype(new_array.dtype)
                
                new_array[border_pixels - 1 - i, border_pixels + orig_width + j] = faded_pixel
        
        # Bottom-left corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                distance_factor = np.sqrt(i**2 + j**2) / (border_pixels * 1.2)
                fade_factor = max(0.3, 1.0 - distance_factor * 0.7)
                
                corner_i = min(i, bl_corner.shape[0] - 1)
                corner_j = min(j, bl_corner.shape[1] - 1)
                
                corner_pixel = bl_corner[-(corner_i + 1), corner_j].astype(np.float32)
                faded_pixel = (corner_pixel * fade_factor).astype(new_array.dtype)
                
                new_array[border_pixels + orig_height + i, border_pixels - 1 - j] = faded_pixel
        
        # Bottom-right corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                distance_factor = np.sqrt(i**2 + j**2) / (border_pixels * 1.2)
                fade_factor = max(0.3, 1.0 - distance_factor * 0.7)
                
                corner_i = min(i, br_corner.shape[0] - 1)
                corner_j = min(j, br_corner.shape[1] - 1)
                
                corner_pixel = br_corner[-(corner_i + 1), -(corner_j + 1)].astype(np.float32)
                faded_pixel = (corner_pixel * fade_factor).astype(new_array.dtype)
                
                new_array[border_pixels + orig_height + i, border_pixels + orig_width + j] = faded_pixel
    
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
