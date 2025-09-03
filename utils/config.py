"""
Configuration Manager - Handles application settings and preferences
"""

import configparser
import os
from pathlib import Path
import json

class Config:
    """Configuration management for PDF Border Tool"""
    
    def __init__(self):
        self.config_dir = self._get_config_directory()
        self.config_file = self.config_dir / "settings.ini"
        self.config = configparser.ConfigParser()
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create default configuration
        self.load_settings()
    
    def _get_config_directory(self):
        """
        Get platform-appropriate configuration directory
        
        Returns:
            Path: Configuration directory path
        """
        if os.name == 'nt':  # Windows
            config_base = Path(os.environ.get('APPDATA', Path.home()))
        elif os.name == 'posix':  # macOS/Linux
            config_base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        else:
            config_base = Path.home()
        
        return config_base / 'PDFBorderTool'
    
    def get_default_settings(self):
        """
        Get default application settings
        
        Returns:
            dict: Default settings
        """
        return {
            # Border settings
            'border_width_mm': 3.0,
            'stretch_source_width_mm': 1.0,  # NEW: Configurable source width
            'stretch_method': 'edge_repeat',
            'output_dpi': 300,
            
            # Processing options
            'auto_detect_cut_marks': True,
            'show_preview': False,
            'backup_original': True,
            'preserve_metadata': True,
            'add_processing_info': False,
            
            # Output settings
            'filename_suffix': '_bordered',
            'use_output_directory': False,
            'output_directory': '',
            'include_timestamp': False,
            
            # Quality settings
            'compression_level': 85,
            'preserve_color_space': True,
            'memory_limit_mb': 1024,
            'thread_count': 2,
            
            # UI settings
            'window_width': 1000,
            'window_height': 700,
            'window_x': 100,
            'window_y': 100,
            'splitter_sizes': [600, 400],
            
            # Advanced settings
            'border_color': '#FFFFFF',
            'max_file_size_mb': 100,
            'temp_directory': '',
            'log_level': 'INFO',
            
            # Recent files
            'recent_files': [],
            'max_recent_files': 10,
        }
    
    def load_settings(self):
        """Load settings from configuration file"""
        # Set defaults first
        defaults = self.get_default_settings()
        
        # Create sections
        self.config.add_section('GENERAL')
        self.config.add_section('PROCESSING') 
        self.config.add_section('OUTPUT')
        self.config.add_section('UI')
        self.config.add_section('ADVANCED')
        
        # Set defaults in config
        for key, value in defaults.items():
            section = self._get_setting_section(key)
            if isinstance(value, list):
                self.config.set(section, key, json.dumps(value))
            else:
                self.config.set(section, key, str(value))
        
        # Load from file if exists
        if self.config_file.exists():
            try:
                self.config.read(self.config_file)
                print(f"Loaded settings from: {self.config_file}")
            except Exception as e:
                print(f"Error loading settings: {e}")
                print("Using default settings")
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            print(f"Settings saved to: {self.config_file}")
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get_setting(self, key, default=None):
        """
        Get a specific setting value
        
        Args:
            key (str): Setting key
            default: Default value if key not found
            
        Returns:
            Setting value with appropriate type conversion
        """
        section = self._get_setting_section(key)
        
        try:
            if not self.config.has_option(section, key):
                return default
            
            value = self.config.get(section, key)
            
            # Convert to appropriate type based on key
            return self._convert_setting_value(key, value)
            
        except Exception as e:
            print(f"Error getting setting {key}: {e}")
            return default
    
    def set_setting(self, key, value):
        """
        Set a specific setting value
        
        Args:
            key (str): Setting key
            value: Setting value
        """
        section = self._get_setting_section(key)
        
        # Ensure section exists
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        # Convert value to string for storage
        if isinstance(value, list):
            str_value = json.dumps(value)
        elif isinstance(value, bool):
            str_value = str(value)
        else:
            str_value = str(value)
        
        self.config.set(section, key, str_value)
    
    def get_all_settings(self):
        """
        Get all settings as a dictionary
        
        Returns:
            dict: All settings with proper type conversion
        """
        settings = {}
        
        for section_name in self.config.sections():
            for key, value in self.config.items(section_name):
                settings[key] = self._convert_setting_value(key, value)
        
        return settings
    
    def restore_defaults(self):
        """Restore all settings to defaults"""
        defaults = self.get_default_settings()
        
        # Clear current config
        for section in self.config.sections():
            self.config.remove_section(section)
        
        # Recreate with defaults
        self.config.add_section('GENERAL')
        self.config.add_section('PROCESSING')
        self.config.add_section('OUTPUT') 
        self.config.add_section('UI')
        self.config.add_section('ADVANCED')
        
        for key, value in defaults.items():
            section = self._get_setting_section(key)
            if isinstance(value, list):
                self.config.set(section, key, json.dumps(value))
            else:
                self.config.set(section, key, str(value))
        
        print("Settings restored to defaults")
    
    def add_recent_file(self, file_path):
        """
        Add file to recent files list
        
        Args:
            file_path (str): Path to recently processed file
        """
        recent_files = self.get_setting('recent_files', [])
        
        # Remove if already exists
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # Add to beginning
        recent_files.insert(0, file_path)
        
        # Limit list size
        max_recent = self.get_setting('max_recent_files', 10)
        recent_files = recent_files[:max_recent]
        
        # Save updated list
        self.set_setting('recent_files', recent_files)
    
    def get_recent_files(self):
        """
        Get list of recent files, filtering out non-existent files
        
        Returns:
            list: List of existing recent file paths
        """
        recent_files = self.get_setting('recent_files', [])
        
        # Filter out files that no longer exist
        existing_files = []
        for file_path in recent_files:
            if Path(file_path).exists():
                existing_files.append(file_path)
        
        # Update list if any files were removed
        if len(existing_files) != len(recent_files):
            self.set_setting('recent_files', existing_files)
        
        return existing_files
    
    def _get_setting_section(self, key):
        """
        Determine which section a setting belongs to
        
        Args:
            key (str): Setting key
            
        Returns:
            str: Section name
        """
        processing_keys = ['border_width_mm', 'stretch_source_width_mm', 'stretch_method', 'output_dpi', 
                          'auto_detect_cut_marks', 'backup_original', 
                          'preserve_metadata', 'compression_level', 
                          'preserve_color_space', 'memory_limit_mb', 'thread_count']
        
        output_keys = ['filename_suffix', 'use_output_directory', 'output_directory',
                      'include_timestamp', 'add_processing_info']
        
        ui_keys = ['window_width', 'window_height', 'window_x', 'window_y',
                  'splitter_sizes', 'show_preview']
        
        advanced_keys = ['border_color', 'max_file_size_mb', 'temp_directory', 
                        'log_level', 'recent_files', 'max_recent_files']
        
        if key in processing_keys:
            return 'PROCESSING'
        elif key in output_keys:
            return 'OUTPUT'
        elif key in ui_keys:
            return 'UI'
        elif key in advanced_keys:
            return 'ADVANCED'
        else:
            return 'GENERAL'
    
    def _convert_setting_value(self, key, value):
        """
        Convert setting value from string to appropriate type
        
        Args:
            key (str): Setting key
            value (str): String value from config file
            
        Returns:
            Converted value with appropriate type
        """
        # Boolean settings
        bool_keys = ['auto_detect_cut_marks', 'show_preview', 'backup_original',
                    'preserve_metadata', 'add_processing_info', 'use_output_directory',
                    'include_timestamp', 'preserve_color_space']
        
        # Integer settings  
        int_keys = ['output_dpi', 'compression_level', 'memory_limit_mb', 'thread_count',
                   'window_width', 'window_height', 'window_x', 'window_y',
                   'max_file_size_mb', 'max_recent_files']
        
        # Float settings
        float_keys = ['border_width_mm', 'stretch_source_width_mm']
        
        # List settings
        list_keys = ['recent_files', 'splitter_sizes']
        
        try:
            if key in bool_keys:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif key in int_keys:
                return int(float(value))  # Handle cases where int stored as float
            elif key in float_keys:
                return float(value)
            elif key in list_keys:
                if value.startswith('[') and value.endswith(']'):
                    return json.loads(value)
                else:
                    # Handle old format or malformed data
                    return []
            else:
                return value  # Return as string
                
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Error converting setting {key}={value}: {e}")
            # Return sensible defaults for known keys
            defaults = self.get_default_settings()
            return defaults.get(key, value)
    
    def export_settings(self, export_path):
        """
        Export settings to file for backup/sharing
        
        Args:
            export_path (str): Path to export file
        """
        try:
            settings = self.get_all_settings()
            
            with open(export_path, 'w') as f:
                json.dump(settings, f, indent=2)
            
            print(f"Settings exported to: {export_path}")
            
        except Exception as e:
            print(f"Error exporting settings: {e}")
    
    def import_settings(self, import_path):
        """
        Import settings from file
        
        Args:
            import_path (str): Path to import file
        """
        try:
            with open(import_path, 'r') as f:
                imported_settings = json.load(f)
            
            # Validate and set imported settings
            defaults = self.get_default_settings()
            
            for key, value in imported_settings.items():
                if key in defaults:  # Only import known settings
                    self.set_setting(key, value)
            
            print(f"Settings imported from: {import_path}")
            
        except Exception as e:
            print(f"Error importing settings: {e}")
    
    def get_temp_directory(self):
        """
        Get temporary directory for processing
        
        Returns:
            Path: Temporary directory path
        """
        temp_dir = self.get_setting('temp_directory', '')
        
        if temp_dir and Path(temp_dir).exists():
            return Path(temp_dir)
        else:
            # Use system temp directory
            import tempfile
            return Path(tempfile.gettempdir()) / 'PDFBorderTool'
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_dir = self.get_temp_directory()
        
        if temp_dir.exists():
            try:
                import shutil
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary files: {temp_dir}")
            except Exception as e:
                print(f"Error cleaning temp files: {e}")
