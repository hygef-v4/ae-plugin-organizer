# Plugin Organizer

**Plugin Organizer** is a tool designed to help users organize their After Effects plugin files. It automatically groups related files into neat, structured folders based on file names, making it easier to manage, access, and organize plugin assets. The application offers features like custom folder naming, a preview of changes, and the ability to undo actions, with all actions logged for tracking.

## Features

- **Directory Selection**: Browse and select the folder containing your After Effects plugin files.
- **File Grouping**: Organizes `.aex` files and their associated files (e.g., `PluginLicense.dll`, `Plugin Presets`).
- **Custom Folder Naming**: Optionally add prefixes or suffixes to the created folders for better organization.
- **Preview & Organize**: View all planned moves before applying them.
- **Undo Last Action**: Revert the most recent changes and restore files to their original locations.
- **History Log**: View the action log to track changes made.
- **Logging**: All actions are logged in `plugin_organizer.log` for easy tracking.

## Requirements

- **Windows** operating system.
- **Administrator rights** for system folders (required for certain operations).
- A **backup** of your plugin folder is recommended before making any changes.

## Installation

### Precompiled Executable

1. **Download the latest release**:  
   You can download the precompiled `.exe` file from the [Releases](https://github.com/hygef-v4/plugin-organizer/releases) page.

2. **Run the Program**:  
   Simply double-click the downloaded `PluginOrganizer.exe` file to launch the application.

### Build the Executable Using PyInstaller

If you want to build the executable from the source, follow these steps:

1. **Install PyInstaller**:
   Make sure you have **PyInstaller** installed. You can install it using pip:

   ```bash
   pip install pyinstaller
   ```

2. **Run PyInstaller Command**:  
   In your terminal or command prompt, navigate to your project directory and run the following command to create the executable:

   ```bash
   pyinstaller --noconfirm --onefile --windowed --name "PluginOrganizer" --icon "E:\script code\app_icon.ico" --clean --uac-admin --add-data "E:\script code\app_icon.ico;app-icon" "E:\script code\plugin_organizer.py"
   ```

   ### Explanation of the PyInstaller Flags:
   - `--noconfirm`: Automatically confirms any prompts during the build process.
   - `--onefile`: Packages the script and all dependencies into a single executable file.
   - `--windowed`: Prevents the terminal window from appearing when the executable is run (useful for GUI-based applications).
   - `--name "PluginOrganizer"`: Specifies the name of the final executable file.
   - `--icon "E:\script code\app_icon.ico"`: Adds an icon to the executable.
   - `--clean`: Cleans temporary files generated during the build process.
   - `--uac-admin`: Requests Administrator rights when running the executable (for system folder access).
   - `--add-data`: Includes additional files (like the icon file) in the packaged executable.
   - `"E:\script code\plugin_organizer.py"`: Path to the Python script you want to convert.

3. **Locate the Executable**:  
   After running the command, PyInstaller will create a `dist` folder in your project directory. Inside the `dist` folder, you’ll find the `PluginOrganizer.exe` file that you can distribute and run.

4. **Run the Executable**:  
   Navigate to the `dist` folder and double-click the `PluginOrganizer.exe` to run the application.

## Usage

1. **Select Directory**: Click the "Browse" button to select the folder containing your After Effects plugin files.
2. **Folder Naming**: Optionally, specify a prefix or suffix for the folders where the plugins will be grouped.
3. **Preview & Organize**: Click "Preview & Organize" to see all planned moves. Review the changes, and click "Proceed" to apply them.
4. **Undo Last Action**: If you made a mistake, you can click "Undo Last" to revert the last action.
5. **View History**: Click "View History" to see a log of all actions performed.

## Logging

All actions are logged in the `plugin_organizer.log` file, and you can track the progress and changes made during the organization.

## Important Notes

- The tool requires **Administrator rights** for certain operations (e.g., when working with system folders).
- **Backup your plugin folder** before making any changes to prevent data loss.
- The **Undo** feature relies on an `undo_log.json` file created after a successful operation.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository.
2. Create your branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.
