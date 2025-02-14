# DrawThings Presets Manager

A tool for managing DrawThings presets. With this tool, you can export, import, and delete presets.

## Installation

1. Make sure Python 3.x is installed on your system
2. Clone this repository:
   ```bash
   git clone https://github.com/osxdoc/dt_preset.git
   cd dt_presets
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Start the tool with:
```bash
phython config_manager.py
```

### Main Functions

1. **Export Preset**
   - Select presets to export
   - By default, they are saved in the `presets` folder
   - Option to specify a custom export path

2. **Import Preset**
   - Import presets from the `presets` folder or a custom path
   - Supports .dtp format and legacy .json/.bin format
   - Shows existing presets

3. **Delete Preset**
   - Select presets to delete
   - Confirm the selection

### Navigation

- Use arrow keys ↑/↓ for navigation
- SPACE to select
- ENTER to confirm
- 'q' to cancel

## Important Notes

⚠️ **Before Using**:
- Back up your database
- Make sure DrawThings is not running

### Database Path

By default, the database is expected to be located at:
```
~/Library/Containers/com.liuliu.draw-things/Data/Library/Application Support/config.sqlite3
```
You can specify an alternative database path at startup.

## File Formats

### .dtp Format
Combined format for presets:
- 4-byte integer for metadata length
- JSON metadata (id, name)
- Binary preset data

### Legacy Format
- .json file for metadata
- .bin file for preset data

## Error Handling

- Checks for database and directory existence
- Validates preset files during import
- Displays error messages for common issues
