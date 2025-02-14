#!/usr/bin/env python3

import curses
import os
import json
from typing import List, Tuple, Dict, Optional

class ConfigSelector:
    def __init__(self, screen):
        self.screen = screen
        self.selected_items = set()
        self.disabled_items = set()

    def select_configurations(self, configs: List[Tuple[int, int, bytes, str]], title: str, disabled_configs: List[Tuple[int, int, bytes, str]] = None) -> List[int]:
        """Display a selection menu for configurations"""
        # Clear any previous selections
        self.selected_items.clear()
        current_row = 0
        offset = 0
        max_rows = curses.LINES - 4

        # Combine new and disabled configs
        all_configs = list(configs)
        if disabled_configs:
            # Add a separator line
            if configs:
                all_configs.append((None, None, None, "------- Existing Configurations -------"))
            all_configs.extend(disabled_configs)
            # Mark disabled items
            self.disabled_items = {config[0] for config in disabled_configs if config[0] is not None}

        # Show appropriate message if there are no configurations to select
        if not configs and not disabled_configs:
            self.screen.clear()
            self.screen.addstr(0, 0, title, curses.A_BOLD)
            self.screen.addstr(2, 0, "No presets found in folder", curses.A_DIM)
            self.screen.addstr(4, 0, "Press any key to continue...")
            self.screen.refresh()
            self.screen.getch()
            return []
        elif not configs and disabled_configs:
            self.screen.clear()
            self.screen.addstr(0, 0, title, curses.A_BOLD)
            self.screen.addstr(2, 0, "All presets are already imported", curses.A_DIM)
            self.screen.addstr(4, 0, "Press any key to continue...")
            self.screen.refresh()
            self.screen.getch()
            return []

        while True:
            self.screen.clear()
            self.screen.addstr(0, 0, title, curses.A_BOLD)
            self.screen.addstr(1, 0, "Use ↑/↓ to navigate, SPACE to select, ENTER to confirm, 'q' to cancel")

            visible_configs = all_configs[offset:offset + max_rows]
            for idx, (rowid, pk0, _, name) in enumerate(visible_configs):
                y = idx + 3
                
                # Handle separator line
                if rowid is None:
                    self.screen.attron(curses.A_BOLD)
                    self.screen.addstr(y, 0, name)
                    self.screen.attroff(curses.A_BOLD)
                    continue

                # Handle regular items
                prefix = "[*]" if rowid in self.selected_items else "[ ]"
                item_str = f"{prefix} {name} (ID: {pk0})"
                
                if rowid in self.disabled_items:
                    # Display disabled items in dim color
                    self.screen.attron(curses.A_DIM)
                    self.screen.addstr(y, 0, item_str)
                    self.screen.attroff(curses.A_DIM)
                elif idx == current_row:
                    self.screen.attron(curses.color_pair(1))
                    self.screen.addstr(y, 0, item_str)
                    self.screen.attroff(curses.color_pair(1))
                else:
                    self.screen.addstr(y, 0, item_str)

            self.screen.refresh()

            key = self.screen.getch()
            if key == ord('q'):
                return []
            elif key == ord(' '):
                rowid = visible_configs[current_row][0]
                # Only allow selection if the item is not disabled
                if rowid is not None and rowid not in self.disabled_items:
                    if rowid in self.selected_items:
                        self.selected_items.remove(rowid)
                    else:
                        self.selected_items.add(rowid)
            elif key == curses.KEY_UP:
                if current_row > 0:
                    current_row -= 1
                elif offset > 0:
                    offset -= 1
            elif key == curses.KEY_DOWN:
                if current_row < len(visible_configs) - 1:
                    current_row += 1
                elif offset + len(visible_configs) < len(configs):
                    offset += 1
            elif key == ord('\n'):
                return list(self.selected_items)

def export_configurations(configs: List[Tuple[int, int, bytes, str]], export_dir: str) -> None:
    """Export selected configurations to .dtp files (combined format)"""
    os.makedirs(export_dir, exist_ok=True)
    
    for rowid, pk0, data, name in configs:
        # Create combined .dtp file with only the name
        dtp_filename = f"{name}.dtp"
        dtp_path = os.path.join(export_dir, dtp_filename)
        
        # Check if file already exists
        if os.path.exists(dtp_path):
            # Return False to indicate file exists and user chose not to overwrite
            return False
        
        # Prepare metadata as JSON bytes
        metadata = {
            'id': pk0,
            'name': name
        }
        metadata_bytes = json.dumps(metadata).encode('utf-8')
        
        # Write combined file with metadata length header
        with open(dtp_path, 'wb') as f:
            # Write metadata length as 4-byte integer
            f.write(len(metadata_bytes).to_bytes(4, byteorder='big'))
            # Write metadata
            f.write(metadata_bytes)
            # Write binary data
            f.write(data)
    
    # Return True to indicate successful export
    return True

def get_presets_dir() -> str:
    """Get the path to the presets directory"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets')

def import_configurations(import_dir: str, config_manager) -> Tuple[List[Dict], List[Dict]]:
    """Import configurations from directory and return new and existing configs"""
    new_configs = []
    existing_configs = []

    for filename in os.listdir(import_dir):
        config = None
        
        # Handle .dtp format
        if filename.endswith('.dtp'):
            dtp_path = os.path.join(import_dir, filename)
            
            with open(dtp_path, 'rb') as f:
                # Read metadata length
                metadata_length = int.from_bytes(f.read(4), byteorder='big')
                # Read metadata
                metadata_bytes = f.read(metadata_length)
                metadata = json.loads(metadata_bytes.decode('utf-8'))
                # Read remaining binary data
                bin_data = f.read()

            config = {
                'id': metadata['id'],
                'name': metadata['name'],
                'data': bin_data
            }
        
        # Handle legacy .json/.bin format
        elif filename.endswith('.json'):
            json_path = os.path.join(import_dir, filename)
            bin_path = os.path.join(import_dir, filename[:-5] + '.bin')
            
            # Skip if corresponding .bin file doesn't exist
            if not os.path.exists(bin_path):
                continue
                
            try:
                # Read JSON metadata
                with open(json_path, 'r') as f:
                    metadata = json.load(f)
                
                # Read binary data
                with open(bin_path, 'rb') as f:
                    bin_data = f.read()
                
                config = {
                    'id': metadata['id'],
                    'name': metadata['name'],
                    'data': bin_data
                }
            except (json.JSONDecodeError, KeyError, IOError):
                continue

        if config:
            # Check if configuration with this ID exists in the database
            if config_manager.check_configuration_exists(config['id']):
                existing_configs.append(config)
            else:
                new_configs.append(config)

    return new_configs, existing_configs