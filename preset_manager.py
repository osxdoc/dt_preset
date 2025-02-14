#!/usr/bin/env python3

import curses
import sqlite3
import os
import json
from typing import List, Tuple, Optional
from preset_operations import ConfigSelector, export_configurations, import_configurations, get_presets_dir

__version__ = "1.1.0"

class PresetManager:
    def __init__(self, db_path: str = os.path.expanduser('~/Library/Containers/com.liuliu.draw-things/Data/Library/Application Support/config.sqlite3')):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            raise Exception(f"Database connection error: {e}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def get_configurations(self) -> List[Tuple[int, int, bytes, str]]:
        """Get all configurations from database"""
        try:
            query = """
            SELECT gc.rowid, gc.__pk0, gc.p, f86.f86
            FROM generationconfiguration gc
            JOIN generationconfiguration__f86 f86 ON gc.rowid = f86.rowid
            WHERE gc.__pk0 != 0
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            raise Exception(f"Error fetching configurations: {e}")

    def check_configuration_exists(self, pk0: int) -> bool:
        """Check if a configuration with given pk0 exists"""
        try:
            query = "SELECT 1 FROM generationconfiguration WHERE __pk0 = ?"
            self.cursor.execute(query, (pk0,))
            return bool(self.cursor.fetchone())
        except sqlite3.Error as e:
            raise Exception(f"Error checking configuration: {e}")

    def import_configuration(self, pk0: int, name: str, data: bytes) -> None:
        """Import a new configuration into database"""
        try:
            # Insert into generationconfiguration
            query1 = "INSERT INTO generationconfiguration (__pk0, p) VALUES (?, ?)"
            self.cursor.execute(query1, (pk0, data))
            rowid = self.cursor.lastrowid

            # Insert into generationconfiguration__f86
            query2 = "INSERT INTO generationconfiguration__f86 (rowid, f86) VALUES (?, ?)"
            self.cursor.execute(query2, (rowid, name))

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise Exception(f"Error importing configuration: {e}")

    def delete_configurations(self, rowids: List[int]) -> None:
        """Delete configurations with given rowids"""
        try:
            # Delete from both tables
            for rowid in rowids:
                self.cursor.execute("DELETE FROM generationconfiguration WHERE rowid = ?", (rowid,))
                self.cursor.execute("DELETE FROM generationconfiguration__f86 WHERE rowid = ?", (rowid,))
            
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise Exception(f"Error deleting configurations: {e}")

class MenuSystem:
    def __init__(self, config_manager: PresetManager):
        self.config_manager = config_manager
        self.screen = None
        self.config_selector = None

    def init_curses(self):
        """Initialize curses screen"""
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        self.config_selector = ConfigSelector(self.screen)

    def cleanup_curses(self):
        """Clean up curses settings"""
        if self.screen:
            self.screen.keypad(False)
            curses.nocbreak()
            curses.echo()
            curses.endwin()

    def show_menu(self) -> int:
        """Display main menu and return selected option"""
        menu_items = [
            "Export presets",
            "Import presets",
            "Delete presets",
            "Exit"
        ]
        current_row = 0

        while True:
            self.screen.clear()
            self.screen.addstr(0, 0, f"Preset Manager v{__version__}", curses.A_BOLD)
            
            for idx, item in enumerate(menu_items):
                x = 2
                y = idx + 2
                if idx == current_row:
                    self.screen.attron(curses.color_pair(1))
                    self.screen.addstr(y, x, item)
                    self.screen.attroff(curses.color_pair(1))
                else:
                    self.screen.addstr(y, x, item)

            self.screen.refresh()

            key = self.screen.getch()
            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(menu_items) - 1:
                current_row += 1
            elif key == ord('\n'):
                return current_row

    def handle_list_configurations(self):
        """Handle listing configurations"""
        configs = self.config_manager.get_configurations()
        if not configs:
            self.screen.clear()
            self.screen.addstr(0, 0, "No configurations found", curses.A_BOLD)
            self.screen.addstr(2, 0, "Press any key to continue...")
            self.screen.refresh()
            self.screen.getch()
            return

        self.config_selector.select_configurations(configs, "Available Configurations")

    def handle_export_configurations(self):
        """Handle exporting presets"""
        configs = self.config_manager.get_configurations()
        if not configs:
            self.screen.clear()
            self.screen.addstr(0, 0, "No presets to export", curses.A_BOLD)
            self.screen.addstr(2, 0, "Press any key to continue...")
            self.screen.refresh()
            self.screen.getch()
            return

        selected_rowids = self.config_selector.select_configurations(configs, "Select Presets to Export")
        if not selected_rowids:
            return

        selected_configs = [config for config in configs if config[0] in selected_rowids]
        
        # Use presets directory as default
        default_dir = get_presets_dir()
        
        # Ask user if they want to use a custom path
        self.screen.clear()
        self.screen.addstr(0, 0, f"Default export directory: {default_dir}", curses.A_BOLD)
        self.screen.addstr(2, 0, "Do you want to use a custom path? [y/N]")
        self.screen.refresh()
        
        choice = self.screen.getch()
        if choice == ord('\n'):  # Enter key pressed, use default 'n'
            choice = ord('n')
        if choice == ord('y'):
            # Clear previous content
            self.screen.clear()
            self.screen.addstr(0, 0, "Enter custom export path:", curses.A_BOLD)
            self.screen.refresh()
            
            # Disable curses to get input
            curses.echo()
            curses.nocbreak()
            custom_path = self.screen.getstr(2, 0).decode('utf-8')
            
            # Restore curses settings
            curses.noecho()
            curses.cbreak()
            
            export_dir = custom_path if custom_path.strip() else default_dir
        else:
            export_dir = default_dir
        
        os.makedirs(export_dir, exist_ok=True)
        
        # Export configurations one by one, asking for confirmation if file exists
        for rowid, pk0, data, name in selected_configs:
            dtp_filename = f"{name}.dtp"
            dtp_path = os.path.join(export_dir, dtp_filename)
            
            # Check if file exists and ask for confirmation
            if os.path.exists(dtp_path):
                self.screen.clear()
                self.screen.addstr(0, 0, f"File already exists: {dtp_filename}", curses.A_BOLD)
                self.screen.addstr(2, 0, "Do you want to overwrite it? [y/N]")
                self.screen.refresh()
                
                choice = self.screen.getch()
                if choice == ord('\n'):  # Enter key pressed, use default 'n'
                    choice = ord('n')
                if choice != ord('y'):
                    continue
            
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

        self.screen.clear()
        self.screen.addstr(0, 0, f"Configurations exported to {export_dir}", curses.A_BOLD)
        self.screen.addstr(2, 0, "Press any key to continue...")
        self.screen.refresh()
        self.screen.getch()

    def handle_import_configurations(self):
        """Handle importing presets"""
        default_dir = get_presets_dir()
        
        # Ask user if they want to use a custom path
        self.screen.clear()
        self.screen.addstr(0, 0, f"Default import directory: {default_dir}", curses.A_BOLD)
        self.screen.addstr(2, 0, "Do you want to use a custom path? [y/N]")
        self.screen.refresh()
        
        choice = self.screen.getch()
        if choice == ord('\n'):  # Enter key pressed, use default 'n'
            choice = ord('n')
        if choice == ord('y'):
            # Clear previous content
            self.screen.clear()
            self.screen.addstr(0, 0, "Enter custom import path:", curses.A_BOLD)
            self.screen.refresh()
            
            # Disable curses to get input
            curses.echo()
            curses.nocbreak()
            custom_path = self.screen.getstr(2, 0).decode('utf-8')
            
            # Restore curses settings
            curses.noecho()
            curses.cbreak()
            
            import_dir = custom_path if custom_path.strip() else default_dir
        else:
            import_dir = default_dir
        
        if not os.path.exists(import_dir):
            self.screen.clear()
            self.screen.addstr(0, 0, f"Import directory not found: {import_dir}", curses.A_BOLD)
            self.screen.addstr(2, 0, "Press any key to continue...")
            self.screen.refresh()
            self.screen.getch()
            return

        new_configs, existing_configs = import_configurations(import_dir, self.config_manager)
        
        # Convert configs to the format expected by select_configurations
        new_config_tuples = [(i, config['id'], config['data'], config['name']) 
                            for i, config in enumerate(new_configs)]
        existing_config_tuples = [(i + len(new_configs), config['id'], config['data'], config['name']) 
                                 for i, config in enumerate(existing_configs)]
        
        # Let user select from new configurations while showing existing ones
        selected_rowids = self.config_selector.select_configurations(
            new_config_tuples, 
            "Select Configurations to Import",
            existing_config_tuples
        )
        
        if not selected_rowids:
            return
            
        # Import selected configurations
        imported_configs = [new_configs[rowid] for rowid in selected_rowids]
        for config in imported_configs:
            self.config_manager.import_configuration(config['id'], config['name'], config['data'])
            
        self.screen.clear()
        self.screen.addstr(0, 0, f"Imported {len(imported_configs)} new configurations", curses.A_BOLD)
        self.screen.addstr(2, 0, "Press any key to continue...")
        self.screen.refresh()
        self.screen.getch()

    def handle_delete_configurations(self):
        """Handle deleting presets"""
        configs = self.config_manager.get_configurations()
        if not configs:
            self.screen.clear()
            self.screen.addstr(0, 0, "No presets to delete", curses.A_BOLD)
            self.screen.addstr(2, 0, "Press any key to continue...")
            self.screen.refresh()
            self.screen.getch()
            return

        selected_rowids = self.config_selector.select_configurations(configs, "Select Presets to Delete")
        if not selected_rowids:
            return

        self.config_manager.delete_configurations(selected_rowids)

        self.screen.clear()
        self.screen.addstr(0, 0, f"Deleted {len(selected_rowids)} presets", curses.A_BOLD)
        self.screen.addstr(2, 0, "Press any key to continue...")
        self.screen.refresh()
        self.screen.getch()

def main():
    # Initialize curses for the startup dialogs
    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    screen.keypad(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)

    try:
        # Show warning about database backup
        screen.clear()
        screen.addstr(0, 0, "IMPORTANT WARNING", curses.A_BOLD)
        screen.addstr(2, 0, "Please ensure you have backed up your database file before proceeding.")
        screen.addstr(3, 0, "Make sure DrawThings is NOT running while using this tool.")
        screen.addstr(5, 0, "Press any key to continue...")
        screen.refresh()
        screen.getch()

        # Show and allow modification of database path
        default_path = os.path.expanduser('~/Library/Containers/com.liuliu.draw-things/Data/Library/Application Support/config.sqlite3')
        screen.clear()
        screen.addstr(0, 0, "Database Configuration", curses.A_BOLD)
        screen.addstr(2, 0, f"Default database path: {default_path}")
        screen.addstr(4, 0, "Do you want to use a different database file? [y/N]")
        screen.refresh()

        choice = screen.getch()
        if choice == ord('\n'):  # Enter key pressed, use default 'n'
            choice = ord('n')
        if choice == ord('y'):
            screen.clear()
            screen.addstr(0, 0, "Enter new database path:", curses.A_BOLD)
            screen.addstr(2, 0, "Current path: " + default_path)
            screen.addstr(4, 0, "New path: ")
            screen.refresh()

            # Enable echo for path input
            curses.echo()
            curses.nocbreak()
            new_path = screen.getstr(4, 10).decode('utf-8')
            # Restore curses settings
            curses.noecho()
            curses.cbreak()

            if new_path.strip():
                default_path = new_path

        # Clean up the startup screen
        curses.endwin()

        # Initialize the main application
        config_manager = PresetManager(default_path)
        menu_system = MenuSystem(config_manager)

        config_manager.connect()
        menu_system.init_curses()

        while True:
            choice = menu_system.show_menu()
            try:
                if choice == 0:  # Export configurations
                    menu_system.handle_export_configurations()
                elif choice == 1:  # Import configurations
                    menu_system.handle_import_configurations()
                elif choice == 2:  # Delete configurations
                    menu_system.handle_delete_configurations()
                elif choice == 3:  # Exit
                    break
            except Exception as e:
                menu_system.screen.clear()
                menu_system.screen.addstr(0, 0, f"Error: {str(e)}", curses.A_BOLD)
                menu_system.screen.addstr(2, 0, "Press any key to continue...")
                menu_system.screen.refresh()
                menu_system.screen.getch()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'menu_system' in locals():
            menu_system.cleanup_curses()
        else:
            curses.endwin()
        if 'config_manager' in locals():
            config_manager.close()

if __name__ == "__main__":
    main()