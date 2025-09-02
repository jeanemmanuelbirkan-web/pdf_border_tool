"""
Image Processor - Handles border creation algorithms with proper edge stretching
"""

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2

class ImageProcessor:
    """Image processing for border creation with intelligent edge stretching"""
    
    def __init__(self, settings):
        self.settings = settings
    
    def add_border(self, image, border_width_mm, dpi):
        """
        Add border to image by stretching edge content
        
        Args:
            image (PIL.Image): Original image
            border_width_mm (float): Border width in millimeters
            dpi (int): Dots per inch for calculation
            
        Returns:
            PIL.Image: Image with added border
        """
        # Convert mm to pixels
        border_pixels = self._mm_to_pixels(border_width_mm, dpi)
        
        # Get stretch method from settings
        method = self.settings.get('stretch_method', 'edge_repeat')
        
        print(f"Creating {border_width_mm}mm border ({border_pixels} pixels) using {method} method")
        
        # Apply appropriate border method
        if method == 'edge_repeat':
            return self._intelligent_edge_stretch(image, border_pixels)
        elif method == 'smart_fill':
            return self._smart_fill_border(image, border_pixels)
        elif method == 'gradient_fade':
            return self._gradient_border(image, border_pixels)
        else:
            # Default to intelligent edge stretch
            return self._intelligent_edge_stretch(image, border_pixels)
    
    def _intelligent_edge_stretch(self, image, border_pixels):
        """
        Create border by intelligently stretching 1mm of edge content to fill 3mm border
        
        Args:
            image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Image with stretched edge border
        """
        # Convert to numpy array for easier manipulation
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # Calculate stretch source zone (1mm worth of pixels, minimum 3 pixels)
        stretch_source_pixels = max(3, border_pixels // 3)
        
        print(f"Stretching {stretch_source_pixels} pixels of edge content to create {border_pixels} pixel border")
        
        # Create new image with border space
        if len(img_array.shape) == 3:
            new_array = np.zeros((height + 2*border_pixels, width + 2*border_pixels, img_array.shape[2]), dtype=img_array.dtype)
        else:
            new_array = np.zeros((height + 2*border_pixels, width + 2*border_pixels), dtype=img_array.dtype)
        
        # Place original image in center
        new_array[border_pixels:border_pixels+height, border_pixels:border_pixels+width] = img_array
        
        # Extract edge regions for stretching
        top_edge = img_array[:stretch_source_pixels, :]
        bottom_edge = img_array[-stretch_source_pixels:, :]
        left_edge = img_array[:, :stretch_source_pixels]
        right_edge = img_array[:, -stretch_source_pixels:]
        
        # Stretch top edge
        for i in range(border_pixels):
            # Determine which source row to use (with some blending)
            source_row_index = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            
            # Create smooth blending
            blend_factor = max(0.3, 1.0 - (i / border_pixels))
            source_row = top_edge[source_row_index, :].astype(np.float32)
            
            # Apply subtle fade for natural appearance
            faded_row = (source_row * blend_factor).astype(img_array.dtype)
            new_array[border_pixels - 1 - i, border_pixels:border_pixels + width] = faded_row
        
        # Stretch bottom edge
        for i in range(border_pixels):
            source_row_index = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            blend_factor = max(0.3, 1.0 - (i / border_pixels))
            source_row = bottom_edge[-(source_row_index + 1), :].astype(np.float32)
            faded_row = (source_row * blend_factor).astype(img_array.dtype)
            new_array[border_pixels + height + i, border_pixels:border_pixels + width] = faded_row
        
        # Stretch left edge
        for i in range(border_pixels):
            source_col_index = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            blend_factor = max(0.3, 1.0 - (i / border_pixels))
            source_col = left_edge[:, source_col_index].astype(np.float32)
            faded_col = (source_col * blend_factor).astype(img_array.dtype)
            new_array[border_pixels:border_pixels + height, border_pixels - 1 - i] = faded_col
        
        # Stretch right edge
        for i in range(border_pixels):
            source_col_index = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            blend_factor = max(0.3, 1.0 - (i / border_pixels))
            source_col = right_edge[:, -(source_col_index + 1)].astype(np.float32)
            faded_col = (source_col * blend_factor).astype(img_array.dtype)
            new_array[border_pixels:border_pixels + height, border_pixels + width + i] = faded_col
        
        # Fill corners by blending adjacent edges intelligently
        self._fill_corners_intelligently(new_array, border_pixels, width, height, img_array)
        
        # Convert back to PIL Image
        result_image = Image.fromarray(new_array)
        
        print(f"Border creation complete: {image.size} → {result_image.size}")
        return result_image
    
    def _fill_corners_intelligently(self, new_array, border_pixels, width, height, original_array):
        """
        Fill corner areas by intelligently blending corner pixels from original image
        
        Args:
            new_array (np.array): New image array with borders
            border_pixels (int): Border width
            width (int): Original image width
            height (int): Original image height
            original_array (np.array): Original image array
        """
        # Get corner pixels from original image
        top_left_pixel = original_array[0, 0]
        top_right_pixel = original_array[0, -1]
        bottom_left_pixel = original_array[-1, 0]
        bottom_right_pixel = original_array[-1, -1]
        
        # Fill corners with gradient based on corner pixels
        for i in range(border_pixels):
            for j in range(border_pixels):
                # Calculate distance from corner for gradient effect
                distance_factor = np.sqrt(i**2 + j**2) / (border_pixels * 1.4)
                fade_factor = max(0.2, 1.0 - distance_factor)
                
                # Top-left corner
                if len(new_array.shape) == 3:
                    new_array[border_pixels - 1 - i, border_pixels - 1 - j] = (top_left_pixel * fade_factor).astype(new_array.dtype)
                    # Top-right corner
                    new_array[border_pixels - 1 - i, border_pixels + width + j] = (top_right_pixel * fade_factor).astype(new_array.dtype)
                    # Bottom-left corner
                    new_array[border_pixels + height + i, border_pixels - 1 - j] = (bottom_left_pixel * fade_factor).astype(new_array.dtype)
                    # Bottom-right corner
                    new_array[border_pixels + height + i, border_pixels + width + j] = (bottom_right_pixel * fade_factor).astype(new_array.dtype)
                else:
                    new_array[border_pixels - 1 - i, border_pixels - 1 - j] = (top_left_pixel * fade_factor).astype(new_array.dtype)
                    new_array[border_pixels - 1 - i, border_pixels + width + j] = (top_right_pixel * fade_factor).astype(new_array.dtype)
                    new_array[border_pixels + height + i, border_pixels - 1 - j] = (bottom_left_pixel * fade_factor).astype(new_array.dtype)
                    new_array[border_pixels + height + i, border_pixels + width + j] = (bottom_right_pixel * fade_factor).astype(new_array.dtype)
    
    def _smart_fill_border(self, image, border_pixels):
        """
        Create border using content-aware fill (OpenCV inpainting)
        """
        try:
            # Convert PIL to OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            height, width = img_cv.shape[:2]
            
            # Create extended canvas
            extended_img = np.zeros((height + 2*border_pixels, width + 2*border_pixels, 3), dtype=np.uint8)
            
            # Place original image in center
            extended_img[border_pixels:border_pixels+height, border_pixels:border_pixels+width] = img_cv
            
            # Create mask for border area
            mask = np.zeros((height + 2*border_pixels, width + 2*border_pixels), dtype=np.uint8)
            mask[:border_pixels, :] = 255  # Top border
            mask[-border_pixels:, :] = 255  # Bottom border
            mask[:, :border_pixels] = 255  # Left border
            mask[:, -border_pixels:] = 255  # Right border
            
            # Apply inpainting
            result = cv2.inpaint(extended_img, mask, inpaintRadius=min(border_pixels//2, 20), flags=cv2.INPAINT_TELEA)
            
            # Convert back to PIL
            result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            return Image.fromarray(result_rgb)
            
        except Exception as e:
            print(f"Smart fill failed, falling back to edge stretch: {e}")
            return self._intelligent_edge_stretch(image, border_pixels)
    
    def _gradient_border(self, image, border_pixels):
        """
        Create gradient border that fades from edge colors
        """
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # Create new image with border space
        if len(img_array.shape) == 3:
            new_array = np.zeros((height + 2*border_pixels, width + 2*border_pixels, img_array.shape[2]), dtype=img_array.dtype)
        else:
            new_array = np.zeros((height + 2*border_pixels, width + 2*border_pixels), dtype=img_array.dtype)
        
        # Place original image in center
        new_array[border_pixels:border_pixels+height, border_pixels:border_pixels+width] = img_array
        
        # Create gradient borders
        for i in range(border_pixels):
            gradient_factor = max(0.1, 1.0 - (i / border_pixels))
            
            # Get edge colors
            top_color = img_array[0, :].astype(np.float32)
            bottom_color = img_array[-1, :].astype(np.float32)
            left_color = img_array[:, 0].astype(np.float32)
            right_color = img_array[:, -1].astype(np.float32)
            
            # Apply gradient
            new_array[border_pixels-1-i, border_pixels:border_pixels+width] = (top_color * gradient_factor).astype(img_array.dtype)
            new_array[border_pixels+height+i, border_pixels:border_pixels+width] = (bottom_color * gradient_factor).astype(img_array.dtype)
            new_array[border_pixels:border_pixels+height, border_pixels-1-i] = (left_color * gradient_factor).astype(img_array.dtype)
            new_array[border_pixels:border_pixels+height, border_pixels+width+i] = (right_color * gradient_factor).astype(img_array.dtype)
        
        # Fill corners with gradients
        self._fill_corners_intelligently(new_array, border_pixels, width, height, img_array)
        
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
