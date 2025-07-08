"""File system integration utilities for character templates and data."""

import json
import logging
import os
import shutil
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.core.config import get_settings
from app.services.template_engine import template_engine, TemplateValidationError
from app.services.character_service import character_service

logger = logging.getLogger(__name__)


class CharacterFileHandler(FileSystemEventHandler):
    """File system event handler for character templates and data."""
    
    def __init__(self, file_integration_service):
        self.file_integration = file_integration_service
        super().__init__()
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.file_integration.handle_file_change(event.src_path, "created")
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self.file_integration.handle_file_change(event.src_path, "modified")
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self.file_integration.handle_file_change(event.src_path, "deleted")
    
    def on_moved(self, event):
        """Handle file move events."""
        if not event.is_directory:
            self.file_integration.handle_file_change(event.src_path, "moved_from")
            self.file_integration.handle_file_change(event.dest_path, "moved_to")


class FileIntegrationService:
    """Service for managing file system integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.campaign_root = Path(self.settings.campaign_root)
        self.templates_dir = self.campaign_root / "characters" / "templates"
        self.characters_dir = self.campaign_root / "characters" / "pcs"
        
        # File watching
        self.observer = None
        self.file_handler = CharacterFileHandler(self)
        
        # Statistics
        self.stats = {
            "templates_loaded": 0,
            "characters_loaded": 0,
            "file_errors": 0,
            "last_scan": None
        }
        
        # Initialize directories
        self.initialize_directories()
    
    def initialize_directories(self):
        """Initialize required directories if they don't exist."""
        try:
            # Create main campaign structure
            directories = [
                self.campaign_root,
                self.campaign_root / "characters",
                self.campaign_root / "characters" / "templates",
                self.campaign_root / "characters" / "pcs",
                self.campaign_root / "rules",
                self.campaign_root / "lore",
                self.campaign_root / "sessions"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            
            # Create example files if they don't exist
            self.create_example_files()
            
            logger.info(f"Initialized campaign directory structure at {self.campaign_root}")
            
        except Exception as e:
            logger.error(f"Failed to initialize directories: {e}")
            raise
    
    def create_example_files(self):
        """Create example template if none exist."""
        if not any(self.templates_dir.glob("*.yaml")) and not any(self.templates_dir.glob("*.yml")):
            logger.info("No templates found, creating example fighter template")
            self.create_example_fighter_template()
    
    def create_example_fighter_template(self):
        """Create an example fighter template."""
        example_template = {
            "name": "Basic Fighter",
            "description": "A simple fighter template for new players",
            "author": "DM Helper",
            "version": "1.0",
            "race": "Human",
            "character_class": "Fighter",
            "background": "Soldier",
            "level": 1,
            "ability_scores": {
                "strength": 15,
                "dexterity": 13,
                "constitution": 14,
                "intelligence": 10,
                "wisdom": 12,
                "charisma": 8
            },
            "proficiencies": {
                "armor": ["Light armor", "Medium armor", "Heavy armor", "Shields"],
                "weapons": ["Simple weapons", "Martial weapons"],
                "saving_throws": ["Strength", "Constitution"],
                "skills": ["Athletics", "Intimidation"]
            },
            "equipment": [
                {
                    "name": "Chain mail",
                    "type": "armor",
                    "ac": 16,
                    "description": "Heavy armor providing excellent protection"
                },
                {
                    "name": "Shield",
                    "type": "shield",
                    "ac_bonus": 2,
                    "description": "A wooden or metal shield"
                },
                {
                    "name": "Longsword",
                    "type": "weapon",
                    "damage": "1d8",
                    "damage_type": "slashing",
                    "description": "A versatile martial weapon"
                },
                {
                    "name": "Javelin",
                    "type": "weapon",
                    "damage": "1d6",
                    "damage_type": "piercing",
                    "quantity": 4,
                    "range": "30/120",
                    "description": "Light thrown weapons"
                }
            ],
            "features": [
                {
                    "name": "Fighting Style",
                    "description": "Choose a fighting style: Defense, Dueling, Great Weapon Fighting, or Protection",
                    "source": "class",
                    "level_acquired": 1
                },
                {
                    "name": "Second Wind",
                    "description": "Regain 1d10+1 hit points as a bonus action",
                    "source": "class",
                    "level_acquired": 1,
                    "uses_per_rest": 1,
                    "rest_type": "short"
                }
            ],
            "languages": ["Common", "One extra language of your choice"]
        }
        
        try:
            template_path = self.templates_dir / "basic_fighter.yaml"
            with open(template_path, 'w', encoding='utf-8') as f:
                yaml.dump(example_template, f, default_flow_style=False, indent=2)
            
            logger.info(f"Created example fighter template at {template_path}")
            
        except Exception as e:
            logger.error(f"Failed to create example template: {e}")
    
    def start_file_watching(self):
        """Start watching the campaign directory for file changes."""
        if not self.settings.watch_file_changes:
            logger.info("File watching is disabled")
            return
        
        if self.observer and self.observer.is_alive():
            logger.warning("File watcher is already running")
            return
        
        try:
            self.observer = Observer()
            self.observer.schedule(
                self.file_handler,
                str(self.campaign_root),
                recursive=True
            )
            self.observer.start()
            
            logger.info(f"Started file watching for {self.campaign_root}")
            
        except Exception as e:
            logger.error(f"Failed to start file watching: {e}")
    
    def stop_file_watching(self):
        """Stop watching files."""
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped file watching")
    
    def handle_file_change(self, file_path: str, event_type: str):
        """Handle file system changes."""
        try:
            path = Path(file_path)
            
            # Only handle files in relevant directories
            if not (
                str(path).startswith(str(self.templates_dir)) or 
                str(path).startswith(str(self.characters_dir))
            ):
                return
            
            logger.debug(f"File {event_type}: {file_path}")
            
            # Handle template changes
            if str(path).startswith(str(self.templates_dir)) and path.suffix in ['.yaml', '.yml']:
                if event_type in ['created', 'modified', 'moved_to']:
                    self.refresh_templates()
                elif event_type in ['deleted', 'moved_from']:
                    template_engine.scan_templates(force_refresh=True)
            
            # Handle character changes
            elif str(path).startswith(str(self.characters_dir)) and path.suffix == '.json':
                if event_type in ['deleted', 'moved_from']:
                    # Clear character cache
                    character_id = path.stem
                    if hasattr(character_service, '_character_cache'):
                        character_service._character_cache.pop(character_id, None)
                    
        except Exception as e:
            logger.error(f"Error handling file change {file_path}: {e}")
            self.stats["file_errors"] += 1
    
    def refresh_templates(self):
        """Refresh template cache."""
        try:
            template_engine.scan_templates(force_refresh=True)
            self.stats["templates_loaded"] = len(template_engine._template_cache)
            logger.debug("Refreshed template cache")
            
        except Exception as e:
            logger.error(f"Failed to refresh templates: {e}")
            self.stats["file_errors"] += 1
    
    def validate_file_structure(self) -> Dict[str, Any]:
        """Validate the campaign file structure."""
        results = {
            "valid": True,
            "directories": {},
            "templates": {},
            "characters": {},
            "issues": []
        }
        
        # Check directories
        required_dirs = [
            self.campaign_root,
            self.templates_dir,
            self.characters_dir,
            self.campaign_root / "rules",
            self.campaign_root / "lore",
            self.campaign_root / "sessions"
        ]
        
        for directory in required_dirs:
            dir_name = directory.name if directory != self.campaign_root else "campaign_root"
            if directory.exists() and directory.is_dir():
                results["directories"][dir_name] = {
                    "exists": True,
                    "writable": os.access(directory, os.W_OK),
                    "file_count": len(list(directory.iterdir())) if directory.exists() else 0
                }
            else:
                results["directories"][dir_name] = {"exists": False, "writable": False}
                results["issues"].append(f"Missing directory: {directory}")
                results["valid"] = False
        
        # Validate templates
        template_files = list(self.templates_dir.glob("*.yaml")) + list(self.templates_dir.glob("*.yml"))
        results["templates"]["count"] = len(template_files)
        results["templates"]["files"] = []
        
        for template_file in template_files:
            template_info = {
                "name": template_file.name,
                "path": str(template_file),
                "size": template_file.stat().st_size,
                "valid": False,
                "error": None
            }
            
            try:
                template = template_engine.load_template_from_file(template_file)
                if template:
                    template_info["valid"] = True
                    template_info["template_name"] = template.name
                else:
                    template_info["error"] = "Failed to load template"
                    results["issues"].append(f"Invalid template: {template_file.name}")
                    
            except TemplateValidationError as e:
                template_info["error"] = str(e)
                results["issues"].append(f"Template validation error in {template_file.name}: {e}")
            except Exception as e:
                template_info["error"] = str(e)
                results["issues"].append(f"Template error in {template_file.name}: {e}")
            
            results["templates"]["files"].append(template_info)
        
        # Validate characters
        character_files = list(self.characters_dir.glob("*.json"))
        results["characters"]["count"] = len(character_files)
        results["characters"]["files"] = []
        
        for char_file in character_files:
            char_info = {
                "name": char_file.name,
                "path": str(char_file),
                "size": char_file.stat().st_size,
                "valid": False,
                "error": None
            }
            
            try:
                character = character_service.load_character(char_file.stem)
                if character:
                    char_info["valid"] = True
                    char_info["character_name"] = character.name
                    char_info["level"] = character.level
                else:
                    char_info["error"] = "Failed to load character"
                    results["issues"].append(f"Invalid character: {char_file.name}")
                    
            except Exception as e:
                char_info["error"] = str(e)
                results["issues"].append(f"Character error in {char_file.name}: {e}")
            
            results["characters"]["files"].append(char_info)
        
        # Update statistics
        self.stats["templates_loaded"] = results["templates"]["count"]
        self.stats["characters_loaded"] = results["characters"]["count"]
        self.stats["last_scan"] = datetime.now().isoformat()
        
        if results["issues"]:
            results["valid"] = False
        
        return results
    
    def backup_data(self, backup_dir: Optional[Path] = None) -> str:
        """Create a backup of character data."""
        if backup_dir is None:
            backup_dir = self.campaign_root / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"dmhelper_backup_{timestamp}"
        backup_path = backup_dir / f"{backup_name}.tar.gz"
        
        try:
            import tarfile
            
            with tarfile.open(backup_path, "w:gz") as tar:
                # Backup templates
                if self.templates_dir.exists():
                    tar.add(self.templates_dir, arcname="templates")
                
                # Backup characters
                if self.characters_dir.exists():
                    tar.add(self.characters_dir, arcname="characters")
            
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def restore_backup(self, backup_path: str, restore_templates: bool = True, restore_characters: bool = True):
        """Restore data from backup."""
        import tarfile
        
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                if restore_templates:
                    # Extract templates
                    template_members = [m for m in tar.getmembers() if m.name.startswith("templates/")]
                    if template_members:
                        # Clear existing templates
                        if self.templates_dir.exists():
                            shutil.rmtree(self.templates_dir)
                        self.templates_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Extract new templates
                        for member in template_members:
                            member.name = member.name.replace("templates/", "")
                            tar.extract(member, self.templates_dir)
                
                if restore_characters:
                    # Extract characters
                    character_members = [m for m in tar.getmembers() if m.name.startswith("characters/")]
                    if character_members:
                        # Clear existing characters
                        if self.characters_dir.exists():
                            shutil.rmtree(self.characters_dir)
                        self.characters_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Extract new characters
                        for member in character_members:
                            member.name = member.name.replace("characters/", "")
                            tar.extract(member, self.characters_dir)
            
            # Refresh caches
            if restore_templates:
                self.refresh_templates()
            if restore_characters and hasattr(character_service, '_character_cache'):
                character_service._character_cache.clear()
            
            logger.info(f"Restored backup from: {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get file integration statistics."""
        stats = self.stats.copy()
        stats["campaign_root"] = str(self.campaign_root)
        stats["file_watching_enabled"] = self.settings.watch_file_changes
        stats["file_watching_active"] = self.observer and self.observer.is_alive() if self.observer else False
        
        return stats
    
    def cleanup_temp_files(self):
        """Clean up temporary files in the campaign directory."""
        temp_patterns = ["*.tmp", "*.temp", "*~", ".DS_Store", "Thumbs.db"]
        cleaned = 0
        
        try:
            for pattern in temp_patterns:
                for temp_file in self.campaign_root.rglob(pattern):
                    if temp_file.is_file():
                        temp_file.unlink()
                        cleaned += 1
                        logger.debug(f"Cleaned temp file: {temp_file}")
            
            logger.info(f"Cleaned {cleaned} temporary files")
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to clean temp files: {e}")
            return 0


# Global service instance
file_integration = FileIntegrationService() 