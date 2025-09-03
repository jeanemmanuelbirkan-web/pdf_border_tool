"""
Image Processor - Generates border content with proper corner stretching
"""

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2

class ImageProcessor:
    """Generates border content from edge pixels with corner stretching"""
    
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
            result = self._generate_clean_gradient_content(original_image, border_pixels)
        else:
            result = self._generate_edge_stretched_content(original_image, border_pixels)
        
        print(f"Generated content size: {result.size}")
        return result
    
    def _generate_edge_stretched_content(self, original_image, border_pixels):
        """
        Generate content: original in center + stretched edges + stretched corners (1mm→3mm)
        
        Args:
            original_image (PIL.Image): Original image (unchanged)
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Complete content with proper corner stretching
        """
        # Convert original to array (read-only)
        original_array = np.array(original_image)
        orig_height, orig_width = original_array.shape[:2]
        
        # Calculate final dimensions
        final_width = orig_width + (2 * border_pixels)
        final_height = orig_height + (2 * border_pixels)
        
        print(f"  Original: {orig_width} x {orig_height}")
        print(f"  Final content: {final_width} x {final_height}")
        print(f"  Border: {border_pixels} pixels")
        
        # Create final content array
        if len(original_array.shape) == 3:
            content_array = np.zeros((final_height, final_width, original_array.shape[2]), dtype=original_array.dtype)
        else:
            content_array = np.zeros((final_height, final_width), dtype=original_array.dtype)
        
        # STEP 1: Place original image in center (EXACT copy, no modifications)
        content_array[border_pixels:border_pixels+orig_height, 
                     border_pixels:border_pixels+orig_width] = original_array.copy()
        
        print("  ✓ Original placed in center (pixel-perfect copy)")
        
        # STEP 2: Calculate source regions
        # For 3mm border, use 1mm from original edges as source
        stretch_source_pixels = max(1, min(border_pixels // 3, orig_width // 10, orig_height // 10))
        corner_source_pixels = stretch_source_pixels  # 1mm x 1mm corner areas
        
        print(f"  ✓ Edge source: {stretch_source_pixels} pixels")
        print(f"  ✓ Corner source: {corner_source_pixels} x {corner_source_pixels} pixels")
        print("  ✓ NO fading - full color preservation")
        
        # STEP 3: Fill edge borders (clean stretching, no gradients)
        
        # TOP border (100mm x 3mm) - stretch top edge downward
        for i in range(border_pixels):
            source_row_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            
            # Get source row from top edge (FULL COLOR - NO FADING)
            source_row = original_array[source_row_idx, :].copy()
            
            # Place in top border (middle section only, excluding corners)
            content_array[border_pixels - 1 - i, border_pixels:border_pixels + orig_width] = source_row
        
        # BOTTOM border (100mm x 3mm) - stretch bottom edge upward
        for i in range(border_pixels):
            source_row_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            
            # Get source row from bottom edge (FULL COLOR - NO FADING)
            source_row = original_array[orig_height - 1 - source_row_idx, :].copy()
            
            # Place in bottom border (middle section only, excluding corners)
            content_array[border_pixels + orig_height + i, border_pixels:border_pixels + orig_width] = source_row
        
        # LEFT border (100mm x 3mm) - stretch left edge rightward
        for i in range(border_pixels):
            source_col_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            
            # Get source column from left edge (FULL COLOR - NO FADING)
            source_col = original_array[:, source_col_idx].copy()
            
            # Place in left border (middle section only, excluding corners)
            content_array[border_pixels:border_pixels + orig_height, border_pixels - 1 - i] = source_col
        
        # RIGHT border (100mm x 3mm) - stretch right edge leftward
        for i in range(border_pixels):
            source_col_idx = min(i * stretch_source_pixels // border_pixels, stretch_source_pixels - 1)
            
            # Get source column from right edge (FULL COLOR - NO FADING)
            source_col = original_array[:, orig_width - 1 - source_col_idx].copy()
            
            # Place in right border (middle section only, excluding corners)
            content_array[border_pixels:border_pixels + orig_height, border_pixels + orig_width + i] = source_col
        
        print("  ✓ Edge borders filled with clean stretching (no fading)")
        
        # STEP 4: Fill corner areas with STRETCHED CORNER REGIONS (1mm → 3mm)
        
        # Extract 1mm x 1mm corner regions from original
        tl_corner_region = original_array[:corner_source_pixels, :corner_source_pixels].copy()
        tr_corner_region = original_array[:corner_source_pixels, -corner_source_pixels:].copy()
        bl_corner_region = original_array[-corner_source_pixels:, :corner_source_pixels].copy()
        br_corner_region = original_array[-corner_source_pixels:, -corner_source_pixels:].copy()
        
        print(f"  ✓ Extracted {corner_source_pixels}x{corner_source_pixels} corner regions")
        
        # Stretch each corner region to fill 3mm x 3mm corner areas
        
        # TOP-LEFT corner: stretch 1mm×1mm → 3mm×3mm
        tl_stretched = self._stretch_corner_region(tl_corner_region, border_pixels)
        content_array[:border_pixels, :border_pixels] = tl_stretched
        
        # TOP-RIGHT corner: stretch 1mm×1mm → 3mm×3mm
        tr_stretched = self._stretch_corner_region(tr_corner_region, border_pixels)
        content_array[:border_pixels, border_pixels + orig_width:] = tr_stretched
        
        # BOTTOM-LEFT corner: stretch 1mm×1mm → 3mm×3mm
        bl_stretched = self._stretch_corner_region(bl_corner_region, border_pixels)
        content_array[border_pixels + orig_height:, :border_pixels] = bl_stretched
        
        # BOTTOM-RIGHT corner: stretch 1mm×1mm → 3mm×3mm
        br_stretched = self._stretch_corner_region(br_corner_region, border_pixels)
        content_array[border_pixels + orig_height:, border_pixels + orig_width:] = br_stretched
        
        print("  ✓ Corner areas filled with stretched corner regions (1mm→3mm)")
        
        # Convert back to PIL Image
        result_image = Image.fromarray(content_array)
        return result_image
    
    def _stretch_corner_region(self, corner_region, target_size):
        """
        Stretch a corner region (e.g., 1mm×1mm) to target size (e.g., 3mm×3mm)
        
        Args:
            corner_region (np.array): Source corner region
            target_size (int): Target size in pixels
            
        Returns:
            np.array: Stretched corner region
        """
        source_height, source_width = corner_region.shape[:2]
        
        # Create target array
        if len(corner_region.shape) == 3:
            stretched = np.zeros((target_size, target_size, corner_region.shape[2]), dtype=corner_region.dtype)
        else:
            stretched = np.zeros((target_size, target_size), dtype=corner_region.dtype)
        
        # Stretch the corner region to fill target area
        for target_y in range(target_size):
            for target_x in range(target_size):
                # Map target coordinates back to source coordinates
                source_y = min(target_y * source_height // target_size, source_height - 1)
                source_x = min(target_x * source_width // target_size, source_width - 1)
                
                # Copy pixel from source to target
                stretched[target_y, target_x] = corner_region[source_y, source_x]
        
        return stretched
    
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
        
        # Apply inpainting with NO fading
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
    
    def _generate_clean_gradient_content(self, original_image, border_pixels):
        """
        Generate content with CLEAN gradients (no fading to black)
        
        Args:
            original_image (PIL.Image): Original image
            border_pixels (int): Border width in pixels
            
        Returns:
            PIL.Image: Content with clean gradient borders
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
        
        # Create VERY MILD gradients (90% to 100% of original color - almost no change)
        for i in range(border_pixels):
            # MINIMAL gradient: from 100% color to 90% color (barely noticeable)
            gradient_factor = 1.0 - (i / border_pixels) * 0.1  # Only 10% maximum reduction
            gradient_factor = max(0.9, gradient_factor)  # Never go below 90% of original color
            
            # Get edge colors
            top_color = orig_array[0, :].astype(np.float32)
            bottom_color = orig_array[-1, :].astype(np.float32)
            left_color = orig_array[:, 0].astype(np.float32)
            right_color = orig_array[:, -1].astype(np.float32)
            
            # Apply MINIMAL gradient (edges only, no corners)
            content_array[border_pixels-1-i, border_pixels:border_pixels+orig_width] = (top_color * gradient_factor).astype(orig_array.dtype)
            content_array[border_pixels+orig_height+i, border_pixels:border_pixels+orig_width] = (bottom_color * gradient_factor).astype(orig_array.dtype)
            content_array[border_pixels:border_pixels+orig_height, border_pixels-1-i] = (left_color * gradient_factor).astype(orig_array.dtype)
            content_array[border_pixels:border_pixels+orig_height, border_pixels+orig_width+i] = (right_color * gradient_factor).astype(orig_array.dtype)
        
        # Fill corners with STRETCHED corner regions (same as edge_repeat method)
        corner_source_pixels = max(1, border_pixels // 3)
        
        # Extract and stretch corner regions
        tl_corner_region = orig_array[:corner_source_pixels, :corner_source_pixels].copy()
        tr_corner_region = orig_array[:corner_source_pixels, -corner_source_pixels:].copy()
        bl_corner_region = orig_array[-corner_source_pixels:, :corner_source_pixels].copy()
        br_corner_region = orig_array[-corner_source_pixels:, -corner_source_pixels:].copy()
        
        # Stretch corner regions to fill corner areas
        tl_stretched = self._stretch_corner_region(tl_corner_region, border_pixels)
        tr_stretched = self._stretch_corner_region(tr_corner_region, border_pixels)
        bl_stretched = self._stretch_corner_region(bl_corner_region, border_pixels)
        br_stretched = self._stretch_corner_region(br_corner_region, border_pixels)
        
        # Place stretched corners
        content_array[:border_pixels, :border_pixels] = tl_stretched
        content_array[:border_pixels, border_pixels + orig_width:] = tr_stretched
        content_array[border_pixels + orig_height:, :border_pixels] = bl_stretched
        content_array[border_pixels + orig_height:, border_pixels + orig_width:] = br_stretched
        
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
