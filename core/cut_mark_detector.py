"""
Cut Mark Detector - Identifies and analyzes cut marks in PDF pages
"""

import numpy as np
import cv2
from PIL import Image
import fitz

class CutMarkDetector:
    """Detects cut marks and registration marks in PDF pages"""
    
    def __init__(self, settings):
        self.settings = settings
        
        # Standard cut mark patterns (in relative coordinates)
        self.cut_mark_templates = {
            'corner_cross': self._create_corner_cross_template(),
            'center_line': self._create_center_line_template(),
            'registration_dot': self._create_registration_dot_template()
        }
    
    def detect_cut_marks(self, page):
        """
        Detect cut marks on a PDF page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            dict: Cut mark detection results
        """
        if not self.settings.get('auto_detect_cut_marks', True):
            return {'detected': False, 'marks': []}
        
        try:
            # Convert page to image for analysis
            page_image = self._page_to_image(page)
            
            # Detect different types of cut marks
            corner_marks = self._detect_corner_marks(page_image)
            edge_marks = self._detect_edge_marks(page_image)
            registration_marks = self._detect_registration_marks(page_image)
            
            # Combine and validate results
            all_marks = corner_marks + edge_marks + registration_marks
            validated_marks = self._validate_marks(all_marks, page_image.shape)
            
            # Calculate safe zone
            safe_zone = self._calculate_safe_zone(validated_marks, page_image.shape)
            
            return {
                'detected': len(validated_marks) > 0,
                'marks': validated_marks,
                'safe_zone': safe_zone,
                'page_size': page_image.shape
            }
            
        except Exception as e:
            print(f"Cut mark detection failed: {e}")
            return {'detected': False, 'marks': [], 'error': str(e)}
    
    def _page_to_image(self, page, dpi=150):
        """
        Convert PDF page to OpenCV image
        
        Args:
            page: PyMuPDF page object
            dpi: Resolution for conversion
            
        Returns:
            np.array: Page as OpenCV image
        """
        # Render page to pixmap
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array
        img_data = pix.tobytes("ppm")
        pil_image = Image.open(io.BytesIO(img_data))
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        return cv_image
    
    def _detect_corner_marks(self, image):
        """
        Detect corner cut marks (cross-hair patterns)
        
        Args:
            image: OpenCV image
            
        Returns:
            list: Detected corner marks
        """
        marks = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # Define corner regions to search (10% of page from each corner)
        corner_size = min(width, height) // 10
        corners = [
            (0, 0, corner_size, corner_size),  # Top-left
            (width-corner_size, 0, corner_size, corner_size),  # Top-right
            (0, height-corner_size, corner_size, corner_size),  # Bottom-left
            (width-corner_size, height-corner_size, corner_size, corner_size)  # Bottom-right
        ]
        
        for i, (x, y, w, h) in enumerate(corners):
            corner_region = gray[y:y+h, x:x+w]
            
            # Look for cross-hair patterns using line detection
            lines = cv2.HoughLinesP(corner_region, 1, np.pi/180, threshold=20, 
                                  minLineLength=10, maxLineGap=5)
            
            if lines is not None and len(lines) >= 2:
                # Check if lines form a cross pattern
                cross_detected = self._verify_cross_pattern(lines, corner_region.shape)
                
                if cross_detected:
                    marks.append({
                        'type': 'corner_cross',
                        'position': (x + w//2, y + h//2),
                        'corner': i,
                        'confidence': 0.8,
                        'region': (x, y, w, h)
                    })
        
        return marks
    
    def _detect_edge_marks(self, image):
        """
        Detect edge cut marks (line marks on page edges)
        
        Args:
            image: OpenCV image
            
        Returns:
            list: Detected edge marks
        """
        marks = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # Define edge regions
        edge_width = 20  # pixels from edge
        edges = [
            ('top', 0, 0, width, edge_width),
            ('bottom', 0, height-edge_width, width, edge_width),
            ('left', 0, 0, edge_width, height),
            ('right', width-edge_width, 0, edge_width, height)
        ]
        
        for edge_name, x, y, w, h in edges:
            edge_region = gray[y:y+h, x:x+w]
            
            # Detect lines in edge region
            if edge_name in ['top', 'bottom']:
                # Look for vertical lines
                lines = cv2.HoughLinesP(edge_region, 1, np.pi/180, threshold=15,
                                      minLineLength=5, maxLineGap=3)
            else:
                # Look for horizontal lines  
                lines = cv2.HoughLinesP(edge_region, 1, np.pi/180, threshold=15,
                                      minLineLength=5, maxLineGap=3)
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    
                    # Convert coordinates back to full image
                    abs_x1, abs_y1 = x + x1, y + y1
                    abs_x2, abs_y2 = x + x2, y + y2
                    
                    marks.append({
                        'type': 'edge_line',
                        'position': ((abs_x1 + abs_x2)//2, (abs_y1 + abs_y2)//2),
                        'edge': edge_name,
                        'line': (abs_x1, abs_y1, abs_x2, abs_y2),
                        'confidence': 0.6
                    })
        
        return marks
    
    def _detect_registration_marks(self, image):
        """
        Detect circular registration marks
        
        Args:
            image: OpenCV image
            
        Returns:
            list: Detected registration marks
        """
        marks = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use HoughCircles to detect circular marks
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1, minDist=50,
                                 param1=50, param2=30, minRadius=3, maxRadius=20)
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            
            for (x, y, r) in circles:
                # Verify it's near page edges (likely registration mark)
                height, width = gray.shape
                edge_distance = min(x, y, width-x, height-y)
                
                if edge_distance < min(width, height) * 0.1:  # Within 10% of edge
                    marks.append({
                        'type': 'registration_circle',
                        'position': (x, y),
                        'radius': r,
                        'confidence': 0.7,
                        'edge_distance': edge_distance
                    })
        
        return marks
    
    def _verify_cross_pattern(self, lines, region_shape):
        """
        Verify if detected lines form a cross pattern
        
        Args:
            lines: Detected lines
            region_shape: Shape of the region
            
        Returns:
            bool: True if cross pattern detected
        """
        if len(lines) < 2:
            return False
        
        # Look for perpendicular lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2-y1, x2-x1)
            angles.append(angle)
        
        # Check for perpendicular angles (roughly 90 degrees apart)
        for i in range(len(angles)):
            for j in range(i+1, len(angles)):
                angle_diff = abs(angles[i] - angles[j])
                if abs(angle_diff - np.pi/2) < 0.3:  # Within ~17 degrees of 90°
                    return True
        
        return False
    
    def _validate_marks(self, marks, image_shape):
        """
        Validate and filter detected cut marks
        
        Args:
            marks: List of detected marks
            image_shape: Shape of the image
            
        Returns:
            list: Validated marks
        """
        validated = []
        height, width = image_shape[:2]
        
        for mark in marks:
            x, y = mark['position']
            
            # Basic position validation
            if 0 <= x < width and 0 <= y < height:
                # Additional validation based on mark type
                if mark['type'] == 'corner_cross':
                    # Should be near corners
                    edge_dist = min(x, y, width-x, height-y)
                    if edge_dist < min(width, height) * 0.15:
                        validated.append(mark)
                        
                elif mark['type'] == 'registration_circle':
                    # Should have reasonable size and position
                    if 3 <= mark.get('radius', 0) <= 20:
                        validated.append(mark)
                        
                else:
                    # Default validation
                    if mark.get('confidence', 0) > 0.5:
                        validated.append(mark)
        
        return validated
    
    def _calculate_safe_zone(self, marks, image_shape):
        """
        Calculate safe zone that doesn't interfere with cut marks
        
        Args:
            marks: Validated cut marks
            image_shape: Shape of the image
            
        Returns:
            dict: Safe zone information
        """
        if not marks:
            # No marks detected, use conservative margins
            height, width = image_shape[:2]
            margin = min(width, height) * 0.05  # 5% margin
            
            return {
                'x': margin,
                'y': margin,
                'width': width - 2*margin,
                'height': height - 2*margin,
                'margins': {'top': margin, 'bottom': margin, 
                           'left': margin, 'right': margin}
            }
        
        # Calculate margins based on detected marks
        height, width = image_shape[:2]
        
        # Find minimum distances to marks from each edge
        top_margin = 0
        bottom_margin = 0
        left_margin = 0
        right_margin = 0
        
        for mark in marks:
            x, y = mark['position']
            
            # Add buffer around each mark
            buffer = 20  # pixels
            
            top_margin = max(top_margin, y + buffer)
            bottom_margin = max(bottom_margin, height - y + buffer)
            left_margin = max(left_margin, x + buffer)
            right_margin = max(right_margin, width - x + buffer)
        
        # Ensure reasonable minimums
        min_margin = min(width, height) * 0.02
        top_margin = max(top_margin, min_margin)
        bottom_margin = max(bottom_margin, min_margin)
        left_margin = max(left_margin, min_margin)
        right_margin = max(right_margin, min_margin)
        
        return {
            'x': left_margin,
            'y': top_margin,
            'width': width - left_margin - right_margin,
            'height': height - top_margin - bottom_margin,
            'margins': {
                'top': top_margin,
                'bottom': bottom_margin,
                'left': left_margin, 
                'right': right_margin
            }
        }
    
    def _create_corner_cross_template(self):
        """Create template for corner cross marks"""
        template = np.zeros((20, 20), dtype=np.uint8)
        # Draw cross pattern
        cv2.line(template, (5, 10), (15, 10), 255, 1)  # Horizontal line
        cv2.line(template, (10, 5), (10, 15), 255, 1)  # Vertical line
        return template
    
    def _create_center_line_template(self):
        """Create template for center line marks"""
        template = np.zeros((30, 5), dtype=np.uint8)
        cv2.line(template, (2, 5), (2, 25), 255, 1)
        return template
    
    def _create_registration_dot_template(self):
        """Create template for registration dots"""
        template = np.zeros((20, 20), dtype=np.uint8)
        cv2.circle(template, (10, 10), 5, 255, -1)
        return template