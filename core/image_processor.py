"""
Image Processor - Handles border creation algorithms
"""

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2

class ImageProcessor:
    """Image processing for border creation"""
    
    def __init__(self, settings):
        self.settings = settings
    
    def add_border(self, image, border_width_mm, dpi):
        """
        Add border to image using specified method
        
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
        
        # Apply appropriate border method
        if method == 'edge_repeat':
            return self._edge_repeat_border(image, border_pixels)
        elif method == 'smart_fill':
            return self._smart_fill_border(image, border_pixels)
        elif method == 'gradient_fade':
            return self._gradient_border(image, border_pixels)
        else:
            # Default to edge repeat
            return self._edge_repeat_border(image, border_pixels)
    
    def _edge_repeat_border(self, image, border_pixels):
        """
        Create border by repeating edge pixels
        
        Args:
            image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Image with edge-repeat border
        """
        # Convert to numpy array for easier manipulation
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        
        # Create new image with border space
        if len(img_array.shape) == 3:
            new_array = np.zeros((height + 2*border_pixels, width + 2*border_pixels, img_array.shape[2]), dtype=img_array.dtype)
        else:
            new_array = np.zeros((height + 2*border_pixels, width + 2*border_pixels), dtype=img_array.dtype)
        
        # Place original image in center
        new_array[border_pixels:border_pixels+height, border_pixels:border_pixels+width] = img_array
        
        # Calculate stretch zone (1mm worth of pixels to stretch to 3mm)
        stretch_pixels = max(1, border_pixels // 3)  # Use 1/3 of border for source
        
        # Stretch top edge
        top_edge = img_array[:stretch_pixels, :]
        for i in range(border_pixels):
            blend_factor = 1.0 - (i / border_pixels)  # Fade effect
            edge_row = top_edge[min(i, stretch_pixels-1), :]
            if len(img_array.shape) == 3:
                edge_row = (edge_row * blend_factor).astype(img_array.dtype)
            new_array[border_pixels-1-i, border_pixels:border_pixels+width] = edge_row
        
        # Stretch bottom edge
        bottom_edge = img_array[-stretch_pixels:, :]
        for i in range(border_pixels):
            blend_factor = 1.0 - (i / border_pixels)
            edge_row = bottom_edge[-(min(i+1, stretch_pixels)), :]
            if len(img_array.shape) == 3:
                edge_row = (edge_row * blend_factor).astype(img_array.dtype)
            new_array[border_pixels+height+i, border_pixels:border_pixels+width] = edge_row
        
        # Stretch left edge
        left_edge = img_array[:, :stretch_pixels]
        for i in range(border_pixels):
            blend_factor = 1.0 - (i / border_pixels)
            edge_col = left_edge[:, min(i, stretch_pixels-1)]
            if len(img_array.shape) == 3:
                edge_col = (edge_col * blend_factor).astype(img_array.dtype)
            new_array[border_pixels:border_pixels+height, border_pixels-1-i] = edge_col
        
        # Stretch right edge
        right_edge = img_array[:, -stretch_pixels:]
        for i in range(border_pixels):
            blend_factor = 1.0 - (i / border_pixels)
            edge_col = right_edge[:, -(min(i+1, stretch_pixels))]
            if len(img_array.shape) == 3:
                edge_col = (edge_col * blend_factor).astype(img_array.dtype)
            new_array[border_pixels:border_pixels+height, border_pixels+width+i] = edge_col
        
        # Fill corners by blending adjacent edges
        self._fill_corners(new_array, border_pixels, width, height)
        
        # Convert back to PIL Image
        return Image.fromarray(new_array)
    
    def _smart_fill_border(self, image, border_pixels):
        """
        Create border using content-aware fill (OpenCV inpainting)
        
        Args:
            image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Image with smart-fill border
        """
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
        try:
            result = cv2.inpaint(extended_img, mask, inpaintRadius=border_pixels//2, flags=cv2.INPAINT_TELEA)
            # Convert back to PIL
            result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            return Image.fromarray(result_rgb)
        except Exception as e:
            print(f"Smart fill failed, falling back to edge repeat: {e}")
            return self._edge_repeat_border(image, border_pixels)
    
    def _gradient_border(self, image, border_pixels):
        """
        Create gradient border that fades to edge colors
        
        Args:
            image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Image with gradient border
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
            # Calculate gradient factor (0 = transparent/edge color, 1 = full edge color)
            gradient_factor = 1.0 - (i / border_pixels)
            
            # Get edge colors
            top_color = img_array[0, :].astype(np.float32)
            bottom_color = img_array[-1, :].astype(np.float32)
            left_color = img_array[:, 0].astype(np.float32)
            right_color = img_array[:, -1].astype(np.float32)
            
            # Apply gradient
            if len(img_array.shape) == 3:
                # Color image
                new_array[border_pixels-1-i, border_pixels:border_pixels+width] = (top_color * gradient_factor).astype(img_array.dtype)
                new_array[border_pixels+height+i, border_pixels:border_pixels+width] = (bottom_color * gradient_factor).astype(img_array.dtype)
                new_array[border_pixels:border_pixels+height, border_pixels-1-i] = (left_color * gradient_factor).astype(img_array.dtype)
                new_array[border_pixels:border_pixels+height, border_pixels+width+i] = (right_color * gradient_factor).astype(img_array.dtype)
            else:
                # Grayscale image
                new_array[border_pixels-1-i, border_pixels:border_pixels+width] = (top_color * gradient_factor).astype(img_array.dtype)
                new_array[border_pixels+height+i, border_pixels:border_pixels+width] = (bottom_color * gradient_factor).astype(img_array.dtype)
                new_array[border_pixels:border_pixels+height, border_pixels-1-i] = (left_color * gradient_factor).astype(img_array.dtype)
                new_array[border_pixels:border_pixels+height, border_pixels+width+i] = (right_color * gradient_factor).astype(img_array.dtype)
        
        # Fill corners with gradients
        self._fill_corners_gradient(new_array, border_pixels, width, height)
        
        return Image.fromarray(new_array)
    
    def _fill_corners(self, img_array, border_pixels, width, height):
        """
        Fill corner areas by blending adjacent border edges
        
        Args:
            img_array (np.array): Image array to modify
            border_pixels (int): Border width
            width (int): Original image width
            height (int): Original image height
        """
        # Top-left corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                # Blend top and left edges
                top_pixel = img_array[i, border_pixels]
                left_pixel = img_array[border_pixels, j]
                
                # Simple average blend
                if len(img_array.shape) == 3:
                    blended = ((top_pixel.astype(np.float32) + left_pixel.astype(np.float32)) / 2).astype(img_array.dtype)
                else:
                    blended = ((top_pixel + left_pixel) / 2).astype(img_array.dtype)
                
                img_array[i, j] = blended
        
        # Top-right corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                top_pixel = img_array[i, border_pixels + width - 1]
                right_pixel = img_array[border_pixels, border_pixels + width + j]
                
                if len(img_array.shape) == 3:
                    blended = ((top_pixel.astype(np.float32) + right_pixel.astype(np.float32)) / 2).astype(img_array.dtype)
                else:
                    blended = ((top_pixel + right_pixel) / 2).astype(img_array.dtype)
                
                img_array[i, border_pixels + width + j] = blended
        
        # Bottom-left corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                bottom_pixel = img_array[border_pixels + height + i, border_pixels]
                left_pixel = img_array[border_pixels + height - 1, j]
                
                if len(img_array.shape) == 3:
                    blended = ((bottom_pixel.astype(np.float32) + left_pixel.astype(np.float32)) / 2).astype(img_array.dtype)
                else:
                    blended = ((bottom_pixel + left_pixel) / 2).astype(img_array.dtype)
                
                img_array[border_pixels + height + i, j] = blended
        
        # Bottom-right corner
        for i in range(border_pixels):
            for j in range(border_pixels):
                bottom_pixel = img_array[border_pixels + height + i, border_pixels + width - 1]
                right_pixel = img_array[border_pixels + height - 1, border_pixels + width + j]
                
                if len(img_array.shape) == 3:
                    blended = ((bottom_pixel.astype(np.float32) + right_pixel.astype(np.float32)) / 2).astype(img_array.dtype)
                else:
                    blended = ((bottom_pixel + right_pixel) / 2).astype(img_array.dtype)
                
                img_array[border_pixels + height + i, border_pixels + width + j] = blended
    
    def _fill_corners_gradient(self, img_array, border_pixels, width, height):
        """
        Fill corners with gradient effect
        
        Args:
            img_array (np.array): Image array to modify
            border_pixels (int): Border width
            width (int): Original image width  
            height (int): Original image height
        """
        # Get corner pixels from original image
        if len(img_array.shape) == 3:
            top_left = img_array[border_pixels, border_pixels]
            top_right = img_array[border_pixels, border_pixels + width - 1]
            bottom_left = img_array[border_pixels + height - 1, border_pixels]
            bottom_right = img_array[border_pixels + height - 1, border_pixels + width - 1]
        else:
            top_left = img_array[border_pixels, border_pixels]
            top_right = img_array[border_pixels, border_pixels + width - 1]
            bottom_left = img_array[border_pixels + height - 1, border_pixels]
            bottom_right = img_array[border_pixels + height - 1, border_pixels + width - 1]
        
        # Fill corners with gradual fade
        for i in range(border_pixels):
            for j in range(border_pixels):
                # Distance from corner
                dist = np.sqrt(i**2 + j**2)
                max_dist = np.sqrt(2 * border_pixels**2)
                fade_factor = 1.0 - (dist / max_dist)
                
                # Top-left
                if len(img_array.shape) == 3:
                    img_array[border_pixels-1-i, border_pixels-1-j] = (top_left * fade_factor).astype(img_array.dtype)
                    # Top-right
                    img_array[border_pixels-1-i, border_pixels+width+j] = (top_right * fade_factor).astype(img_array.dtype)
                    # Bottom-left
                    img_array[border_pixels+height+i, border_pixels-1-j] = (bottom_left * fade_factor).astype(img_array.dtype)
                    # Bottom-right
                    img_array[border_pixels+height+i, border_pixels+width+j] = (bottom_right * fade_factor).astype(img_array.dtype)
                else:
                    img_array[border_pixels-1-i, border_pixels-1-j] = (top_left * fade_factor).astype(img_array.dtype)
                    img_array[border_pixels-1-i, border_pixels+width+j] = (top_right * fade_factor).astype(img_array.dtype)
                    img_array[border_pixels+height+i, border_pixels-1-j] = (bottom_left * fade_factor).astype(img_array.dtype)
                    img_array[border_pixels+height+i, border_pixels+width+j] = (bottom_right * fade_factor).astype(img_array.dtype)
    
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
    
    def enhance_image_quality(self, image):
        """
        Apply quality enhancements to image
        
        Args:
            image (PIL.Image): Image to enhance
            
        Returns:
            PIL.Image: Enhanced image
        """
        # Apply subtle sharpening
        sharpening_filter = ImageFilter.UnsharpMask(radius=1, percent=110, threshold=3)
        enhanced = image.filter(sharpening_filter)
        
        # Slight contrast enhancement
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(1.05)
        
        return enhanced