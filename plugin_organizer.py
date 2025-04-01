import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ctypes
import sys
import json
import datetime
import time

# Auto-elevation
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception: return False

if __name__ == "__main__" and not is_admin():
    try:
        script_path = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}" {params}', None, 1)
        if ret <= 32: print(f"Failed to elevate privileges (Error code: {ret}).")
    except Exception as e: print(f"Error requesting admin privileges: {e}")
    finally: sys.exit()

# Globals
if getattr(sys, 'frozen', False): SCRIPT_DIR = os.path.dirname(sys.executable)
else: SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "plugin_organizer.log")
UNDO_FILE = os.path.join(SCRIPT_DIR, "undo_log.json")

# Logging
def log_action(message):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    try:
        with open(LOG_FILE, "a", encoding='utf-8') as log: log.write(f"{timestamp} {message}\n")
    except Exception as e: print(f"CRITICAL: Error writing to log file '{LOG_FILE}': {e}")


# --- Core Logic ---

def compute_moves(directory, prefix, suffix):
    """
    Compute moves for .aex files and their associated items (files/folders).
    Skips moving an associated folder if its name matches the target folder name.
    """
    moves = []
    processed_items = set()
    KNOWN_SUFFIXES = ["license", "presets", "textures", "data", "config",
                      "key", "lib", "sdk", "settings", "pack", "bundle",
                      "docs", "help", "support", "extra", "install"]

    if not os.path.isdir(directory):
        messagebox.showerror("Error", f"Directory not found or invalid:\n{directory}")
        log_action(f"Error: compute_moves called with invalid directory: {directory}")
        return []

    try:
        all_item_names = os.listdir(directory)
        item_paths = {name: os.path.join(directory, name) for name in all_item_names}
        aex_base_to_target_folder = {}

        # --- Pass 1: Identify .aex files and targets ---
        log_action("Starting pass 1: Identifying .aex files and targets.")
        for item_name, item_path in item_paths.items():
            if os.path.isfile(item_path) and item_name.lower().endswith('.aex'):
                aex_base_name = os.path.splitext(item_name)[0]
                if aex_base_name.startswith('_'): continue # Skip internal/temp

                target_folder_name = f"{prefix}{aex_base_name}{suffix}"
                target_folder_path = os.path.join(directory, target_folder_name)
                aex_base_lower = aex_base_name.lower()

                if aex_base_lower in aex_base_to_target_folder: continue # Use first encountered

                aex_base_to_target_folder[aex_base_lower] = target_folder_path
                log_action(f"Identified .aex: '{item_name}', Base: '{aex_base_name}', Target Folder: '{target_folder_name}'")

                destination_aex = os.path.join(target_folder_path, item_name)
                moves.append((item_path, destination_aex))
                processed_items.add(item_name)

        if not aex_base_to_target_folder:
            log_action("Pass 1 complete: No organizable .aex files found.")
            return []
        else:
             log_action(f"Pass 1 complete: Found {len(aex_base_to_target_folder)} unique .aex base name(s) to process.")

        # --- Pass 2: Find related files and folders ---
        log_action("Starting pass 2: Identifying associated files and folders.")
        sorted_aex_bases = sorted(aex_base_to_target_folder.keys(), key=len, reverse=True)

        for item_name, item_path in item_paths.items():
            if item_name in processed_items: continue

            item_name_lower = item_name.lower()
            item_is_folder = os.path.isdir(item_path)
            item_base_lower = item_name_lower if item_is_folder else os.path.splitext(item_name_lower)[0]

            for aex_base_lower in sorted_aex_bases:
                if not item_name_lower.startswith(aex_base_lower): continue

                match_len = len(aex_base_lower)
                item_len = len(item_name_lower)
                is_related = False
                log_reason = "No match"

                if item_len == match_len: # Exact name match, likely a folder
                    is_related = True
                    log_reason = "Exact name match"
                elif os.path.splitext(item_name_lower)[0] == aex_base_lower: # Exact base name (file)
                     is_related = True
                     log_reason = "Exact base name match (file)"
                else:
                    follow_char = item_name_lower[match_len]
                    if not follow_char.isalpha():
                        is_related = True
                        log_reason = f"Followed by non-letter ('{follow_char}')"
                    else:
                        suffix_part = item_name_lower[match_len:]
                        for known in KNOWN_SUFFIXES:
                            if suffix_part.startswith(known):
                                suffix_end_index = match_len + len(known)
                                if suffix_end_index == item_len or not item_name_lower[suffix_end_index].isalpha():
                                    is_related = True
                                    log_reason = f"Followed by known suffix ('{known}')"
                                    break

                if is_related:
                    target_folder_path = aex_base_to_target_folder[aex_base_lower]
                    target_folder_basename = os.path.basename(target_folder_path) # Get name of folder to be created

                    if item_is_folder and item_name == target_folder_basename:
                        log_action(f"Skipping associated Folder: '{item_name}' because its name matches the target folder name derived from '{aex_base_lower}.aex'.")
                        # Also mark as processed so it doesn't get matched again later by mistake
                        processed_items.add(item_name)
                        break # Stop checking other bases for this specific item


                    # If not skipped, add the move
                    destination_item = os.path.join(target_folder_path, item_name)
                    item_type = "Folder" if item_is_folder else "File"
                    log_action(f"Identified associated {item_type}: '{item_name}' for base '{aex_base_lower}'. Reason: {log_reason}. Moving to '{target_folder_basename}'")
                    moves.append((item_path, destination_item))
                    processed_items.add(item_name)
                    break # Stop checking other aex bases for this item

        log_action("Pass 2 complete.")

    except PermissionError as e:
         messagebox.showerror("Permission Error", f"Permission denied scanning directory:\n{directory}")
         log_action(f"PermissionError scanning directory {directory}: {e}")
         return []
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred while scanning directory {directory}:\n{e}")
        log_action(f"Error scanning directory {directory}: {e}")
        return []

    log_action(f"Computed {len(moves)} move operations.")
    return moves



# execute_moves function (no changes)
def execute_moves(moves):
    undo_mapping = {}
    errors_encountered = False
    moved_sources = set()
    created_folders = set() # Track folders created by *this* process

    log_action(f"Starting execution of {len(moves)} move operations.")

    for source, destination in moves:
        if source in moved_sources:
            log_action(f"Skipping move for '{source}' as it appears to have already been processed in this batch.")
            continue

        folder_path = os.path.dirname(destination) # This is the target folder (e.g., ".../Element")

        try:
            # Create target folder if it doesn't exist and hasn't been created yet
            if not os.path.exists(folder_path) and folder_path not in created_folders:
                try:
                    os.makedirs(folder_path)
                    log_action(f"Created folder: {folder_path}")
                    created_folders.add(folder_path) # Mark as created
                except FileExistsError:
                    log_action(f"Folder already exists (race condition?): {folder_path}")
                    created_folders.add(folder_path)
                    pass
                except PermissionError as pe:
                    errors_encountered = True
                    error_msg = f"Permission denied creating folder '{os.path.basename(folder_path)}': {pe}"
                    log_action(f"PermissionError: {error_msg}")
                    messagebox.showerror("Permission Error", error_msg + "\n\nEnsure the application is running as Administrator.")
                    break # Stop if we can't create a needed folder
                except Exception as e_mkdir:
                    errors_encountered = True
                    error_msg = f"Error creating folder '{os.path.basename(folder_path)}': {e_mkdir}"
                    log_action(f"Error: {error_msg}")
                    messagebox.showerror("Folder Creation Error", error_msg)
                    break # Stop if folder creation fails critically

            # Perform the move (works for files and folders)
            if os.path.exists(source):
                 item_type = "Folder" if os.path.isdir(source) else "File"
                 log_detail = f"Moving {item_type}: '{os.path.basename(source)}' -> '{os.path.relpath(destination, start=os.path.dirname(folder_path))}' in '{os.path.basename(folder_path)}'"
                 log_action(log_detail)
                 shutil.move(source, destination)
                 undo_mapping[destination] = source # Use absolute paths for robust undo
                 moved_sources.add(source)
            else:
                 log_action(f"Warning: Source item '{source}' not found for moving. Already moved or deleted?")

        except PermissionError as e:
             errors_encountered = True
             # Try to determine type even on error for logging
             item_type = "Item"
             try: item_type = "Folder" if os.path.isdir(source) else "File"
             except Exception: pass
             error_msg = f"Permission denied moving {item_type} '{os.path.basename(source)}': {e}"
             log_action(f"PermissionError: {error_msg}")
             messagebox.showerror("Permission Error", error_msg + "\n\nEnsure the application is running as Administrator.")
             break # Stop on permission errors

        except Exception as e:
            errors_encountered = True
            item_type = "Item"
            try: item_type = "Folder" if os.path.isdir(source) else "File"
            except Exception: pass
            error_msg = f"Error moving {item_type} '{os.path.basename(source)}': {e}"
            # Specific check for the self-move error, although compute_moves should prevent it now.
            if "into itself" in str(e):
                log_action(f"Error (Self-Move Detected): {error_msg}") # Log specifically
                messagebox.showerror("Move Error", f"Cannot move '{os.path.basename(source)}' into itself. This usually means a folder with the same name as the plugin already exists. The move for this folder has been skipped.")
                continue # Skip to the next move
            else:
                 log_action(f"Error: {error_msg}")
                 messagebox.showerror("Move Error", error_msg)
                 break # Stop on other unexpected move errors

    # --- Save Undo Info ---
    if undo_mapping and not errors_encountered:
        try:
            with open(UNDO_FILE, "w", encoding='utf-8') as f:
                json.dump(undo_mapping, f, indent=4)
            log_action(f"Undo information for {len(undo_mapping)} item(s) saved to {UNDO_FILE}")
        except Exception as e:
             errors_encountered = True # Mark as error because undo is compromised
             log_action(f"CRITICAL ERROR: Failed saving undo file {UNDO_FILE}: {e}")
             messagebox.showerror("Critical Error", f"Could not save undo information to {UNDO_FILE}:\n{e}\n\nUNDO WILL NOT BE POSSIBLE for this operation.")
             undo_mapping.clear()

    # --- Final User Feedback ---
    total_moves_planned = len(moves) # Note: This count includes the skipped self-move if one occurred
    actual_moves_logged = len(undo_mapping)

    log_action(f"Execution finished. Planned(incl. potential skips)={total_moves_planned}, Succeeded/Logged={actual_moves_logged}, Errors Encountered={errors_encountered}")

    if actual_moves_logged == 0 and not errors_encountered and total_moves_planned > 0:
         # Handle case where only moves skipped were self-moves
         messagebox.showinfo("Information", "Organization complete. No files/folders needed moving (or only self-moves were skipped).")
    elif total_moves_planned == 0: # No .aex files found initially
         if not os.path.exists(LOG_FILE) or "No organizable .aex files found" not in open(LOG_FILE, encoding='utf-8').read().splitlines()[-1]:
              messagebox.showinfo("Information", "No plugin (.aex) files found directly in the selected directory to organize.")
    elif not errors_encountered:
        messagebox.showinfo("Success", f"Successfully organized {actual_moves_logged} item(s) (files/folders) into subfolders!")
        log_action(f"Organization successful for {actual_moves_logged} item(s).")
    else:
        error_summary = f"Organization attempted for {total_moves_planned} potential item moves, but errors occurred."
        if actual_moves_logged > 0: error_summary += f" {actual_moves_logged} item(s) may have been moved."
        else: error_summary += " No items appear to have been successfully moved."

        undo_save_failed = not os.path.exists(UNDO_FILE) and actual_moves_logged > 0 and errors_encountered
        if undo_save_failed :
             error_summary += "\n\nCRITICAL: Undo information could not be saved. Manual reversal may be required."
             messagebox.showerror("Completed with Critical Errors", error_summary + "\n\nCheck the log file for details.")
        else:
             messagebox.showwarning("Completed with Errors", error_summary + "\n\nCheck the log file ('plugin_organizer.log') for details.")
        log_action("Organization completed with errors.")

# preview_moves function (no changes)
def preview_moves(moves):
    """Show a preview window with planned moves. On confirmation, execute moves."""
    if not moves:
        try:
            # Check log more reliably for the specific message
            log_found = False
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding='utf-8') as f:
                    log_lines = f.readlines()
                # Check last few lines for efficiency
                if any("No organizable .aex files found" in line for line in log_lines[-10:]):
                    log_found = True
            if log_found:
                messagebox.showinfo("Preview", "No plugin (.aex) files found directly in the selected directory to organize.")
            else:
                 messagebox.showinfo("Preview", "No associated files or folders need moving for the found .aex plugins (or moves were skipped, see log).")
        except Exception: # Fallback if reading log fails
             messagebox.showinfo("Preview", "No items need moving.")

        log_action("Preview requested: No moves to preview.")
        return

    preview_win = tk.Toplevel(app)
    preview_win.title("Preview Planned Moves")
    preview_win.geometry("650x500") # Wider/taller for more info
    preview_win.minsize(500, 400)
    preview_win.grab_set() # Make preview modal
    preview_win.transient(app) # Associate with main window

    lbl = tk.Label(preview_win, text="The following files and folders will be moved:")
    lbl.pack(pady=5)

    text_area = scrolledtext.ScrolledText(preview_win, width=80, height=25, wrap=tk.WORD, borderwidth=1, relief="solid")
    text_area.pack(padx=10, pady=5, expand=True, fill=tk.BOTH)

    log_action("Preview window shown with the following planned moves:")
    moves_by_folder = {}

    # Group moves by target folder
    for source, destination in moves:
        folder_path = os.path.dirname(destination)
        folder_name = os.path.basename(folder_path)
        if folder_name not in moves_by_folder: moves_by_folder[folder_name] = []
        # Store source basename and whether it's a folder
        is_folder = os.path.isdir(source)
        moves_by_folder[folder_name].append((os.path.basename(source), is_folder))

    # Display grouped moves
    for folder_name, item_details in sorted(moves_by_folder.items()):
        text_area.insert(tk.END, f"📁 Into Folder: .\\{folder_name}\\\n")
        log_action(f"  Preview Target Folder: {folder_name}")
        # Sort items alphabetically within each folder
        item_details.sort(key=lambda x: x[0])

        for item_basename, is_folder in item_details:
             icon = "📁" if is_folder else "📄"
             preview_text = f"  {icon} Move: '{item_basename}'\n"
             text_area.insert(tk.END, preview_text)
             log_action(f"    - Preview Move {icon}: {item_basename}")
        text_area.insert(tk.END, "\n") # Add space between folders

    text_area.configure(state="disabled") # Make read-only after inserting text

    # --- Buttons ---
    def proceed():
        log_action("User confirmed preview. Proceeding with moves.")
        preview_win.destroy()
        execute_moves(moves) # Execute the moves passed to this preview instance
    def cancel():
        log_action("User cancelled operation from preview.")
        preview_win.destroy()

    btn_frame = tk.Frame(preview_win); btn_frame.pack(pady=10)
    btn_proceed = tk.Button(btn_frame, text="Proceed", command=proceed, width=10, bg="#D0E0D0", activebackground="#B0C0B0")
    btn_proceed.grid(row=0, column=0, padx=10)
    btn_cancel = tk.Button(btn_frame, text="Cancel", command=cancel, width=10, bg="#F0D0D0", activebackground="#D0B0B0")
    btn_cancel.grid(row=0, column=1, padx=10)

    btn_proceed.focus_set() # Set focus to Proceed button
    preview_win.wait_window() # Wait for the preview window to close


# undo_moves function (no changes needed from previous corrected version)
def undo_moves():
    """Undo the last plugin organization by reading the undo mapping and reverting the moves."""
    log_action("Undo operation initiated by user.")
    if not os.path.exists(UNDO_FILE):
        messagebox.showinfo("Undo", "No undo information found (undo_log.json missing). Cannot undo.")
        log_action("Undo failed: undo_log.json not found."); return

    try:
        with open(UNDO_FILE, "r", encoding='utf-8') as f: undo_mapping = json.load(f)
    except Exception as e:
         messagebox.showerror("Undo Error", f"Could not read or parse undo file {UNDO_FILE}:\n{e}")
         log_action(f"Undo Error: Failed reading/parsing {UNDO_FILE}: {e}"); return

    if not undo_mapping:
        messagebox.showinfo("Undo", "Undo information file is empty. Nothing to revert.")
        log_action("Undo: undo_log.json was empty.")
        try:
            if os.path.exists(UNDO_FILE): os.remove(UNDO_FILE); log_action(f"Removed empty undo file: {UNDO_FILE}")
        except OSError as e: log_action(f"Could not remove empty undo file {UNDO_FILE}: {e}")
        return

    errors = []; success_count = 0; folders_to_potentially_remove = set()
    items_to_undo = list(undo_mapping.items())
    log_action(f"Attempting to undo {len(items_to_undo)} item moves.")

    for new_location, original_location in items_to_undo:
        try:
            # Check if the item *still* exists at the new location before attempting move
            if os.path.exists(new_location):
                orig_dir = os.path.dirname(original_location) # Parent dir where item should go back
                # Check if original parent directory exists
                if not os.path.isdir(orig_dir):
                     log_action(f"Warning: Original parent directory '{orig_dir}' not found during undo for '{os.path.basename(original_location)}'. Attempting move anyway.")

                # Check if target location already exists (e.g., partial manual revert?)
                if os.path.exists(original_location):
                     # Determine type for logging before skipping
                     item_type = "Item" # Default
                     try:
                         if os.path.exists(new_location): # Check again just in case
                             item_type = "Folder" if os.path.isdir(new_location) else "File"
                     except Exception: pass # Ignore errors in type detection here
                     log_action(f"Undo Warning: Target location '{original_location}' already exists. Skipping revert for {item_type} '{os.path.basename(new_location)}' to avoid data loss.")
                     errors.append(f"{os.path.basename(new_location)} -> Skipped (Target Exists)")
                     continue # Skip this file move

                # Determine type before moving for logging
                item_type = "Folder" if os.path.isdir(new_location) else "File"
                # Make log path relative to original directory for clarity
                try:
                    rel_orig_path = os.path.relpath(original_location, start=orig_dir)
                except ValueError: # Happens if paths are on different drives
                    rel_orig_path = original_location # Fallback to absolute path
                log_detail = f"Reverting {item_type}: '{os.path.basename(new_location)}' -> '{rel_orig_path}' in '{os.path.basename(orig_dir)}'"
                log_action(log_detail)

                # Perform the move
                shutil.move(new_location, original_location)
                success_count += 1
                # Add the parent folder (the one created by the tool, e.g., "Element")
                # to the list of folders to potentially remove later
                folders_to_potentially_remove.add(os.path.dirname(new_location))

            else:
                # Log if the item that was supposed to be moved back is missing
                log_action(f"Undo Warning: Item not found at expected location '{new_location}'. Skipping revert for this item.")

        except PermissionError as e:
             # --- Safely determine type for error message ---
             item_type = "Item" # Default
             try:
                 if os.path.exists(new_location): # Check exists first
                      item_type = "Folder" if os.path.isdir(new_location) else "File"
             except Exception: pass # Keep default "Item" if check fails
             error_msg = f"Permission denied reverting {item_type} '{os.path.basename(new_location)}': {e}"
             log_action(f"Undo PermissionError: {error_msg}")
             errors.append(f"{os.path.basename(new_location)} -> Permission Denied")

        except Exception as e:
            # Safely determine type within the except block
            item_type = "Item" # Default value
            try:
                 if os.path.exists(new_location):
                     item_type = "Folder" if os.path.isdir(new_location) else "File"
            except Exception:
                 pass # Keep default "Item" if this check fails
            error_msg = f"Error undoing move for {item_type} '{os.path.basename(new_location)}': {e}"
            log_action(f"Undo Error: {error_msg}")
            errors.append(f"{os.path.basename(new_location)} -> {e}")


    # --- Attempt to Remove Folders ---
    removed_folders_count = 0
    log_action(f"Attempting removal of {len(folders_to_potentially_remove)} potentially empty created folders.")
    sorted_folders = sorted(list(folders_to_potentially_remove), key=lambda x: x.count(os.sep), reverse=True)

    for folder_path in sorted_folders:
        try:
            # Check again: exists, is directory, is empty
            if os.path.isdir(folder_path) and not os.listdir(folder_path):
                os.rmdir(folder_path); log_action(f"Removed empty created folder: {folder_path}"); removed_folders_count += 1
            elif os.path.isdir(folder_path):
                 log_action(f"Undo Info: Created folder '{folder_path}' was not empty after revert attempts. Did not remove.")
        except Exception as e: # Catch PermissionError or OSError here
             log_action(f"Undo Warning: Could not remove folder '{folder_path}': {e}")


    # --- Final Undo User Feedback ---
    if errors:
        err_preview = "\n".join(errors[:5]) + ('\n...' if len(errors)>5 else '')
        messagebox.showerror("Undo Completed with Errors", f"Undo process finished, but {len(errors)} item(s) had issues (see log):\n\n{err_preview}\n\nSuccessfully reverted {success_count} item(s).\n{removed_folders_count} empty created folder(s) removed.\nCheck log for full details.")
        log_action(f"Undo completed with {len(errors)} errors/warnings. {success_count} items reverted. {removed_folders_count} folders removed.")
    elif success_count > 0:
        messagebox.showinfo("Undo Successful", f"{success_count} item(s) (files/folders) have been successfully moved back.\n{removed_folders_count} empty created folder(s) removed.")
        log_action(f"Undo successful: {success_count} items reverted, {removed_folders_count} folders removed.")
    else:
         messagebox.showinfo("Undo Information", "Undo process completed. No items required reverting (or items were missing).")
         log_action("Undo complete: No items required reverting or items were missing.")

    # --- Remove Undo File ---
    if not errors and os.path.exists(UNDO_FILE):
        try:
            os.remove(UNDO_FILE); log_action("Undo file removed after successful undo operation.")
        except OSError as e:
            log_action(f"Error removing undo file {UNDO_FILE}: {e}"); messagebox.showwarning("File Warning", f"Could not remove the undo file:\n{e}")
    elif errors:
        log_action("Undo file preserved due to errors during undo process."); messagebox.showwarning("Undo Log Kept", f"Errors occurred during undo. The undo file '{os.path.basename(UNDO_FILE)}' has been kept.")

# select_directory function (no changes)
def select_directory():
    """Open a directory selection dialog and update the entry field."""
    initial_dir = os.path.expanduser("~") # Start in user's home directory as default
    program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
    potential_ae_path = os.path.join(program_files, 'Adobe')
    if os.path.isdir(potential_ae_path):
        try:
            ae_folders = [d for d in os.listdir(potential_ae_path) if 'Adobe After Effects' in d and os.path.isdir(os.path.join(potential_ae_path, d))]
            if ae_folders:
                latest_ae_folder = sorted(ae_folders, reverse=True)[0]
                plugins_path = os.path.join(potential_ae_path, latest_ae_folder, 'Support Files', 'Plug-ins')
                if os.path.isdir(plugins_path): initial_dir = plugins_path
        except Exception as e:
            log_action(f"Minor error guessing AE plugin path: {e}")
            pass

    directory = filedialog.askdirectory(initialdir=initial_dir, title="Select After Effects Plug-ins Directory")
    if directory:
        entry_directory.delete(0, tk.END)
        entry_directory.insert(0, directory)
        log_action(f"User selected directory: {directory}")

# run_preview function (no changes)
def run_preview():
    """Get inputs, compute planned moves, and show the preview window."""
    directory = entry_directory.get().strip()
    if not directory: messagebox.showerror("Error", "Please select a directory first."); return
    if not os.path.isdir(directory): messagebox.showerror("Error", f"Invalid or inaccessible directory path:\n{directory}"); log_action(f"Preview aborted: Invalid directory path: {directory}"); return

    prefix = entry_prefix.get(); suffix = entry_suffix.get()
    log_action(f"Preview initiated for directory: '{directory}', Prefix: '{prefix}', Suffix: '{suffix}'")
    moves = compute_moves(directory, prefix, suffix); preview_moves(moves)

# show_help function (no changes)
def show_help():
    """Show the help/guide information in a message box."""
    help_text = (
    "📌 Plugin Organizer - User Guide\n\n"
    "Plugin Organizer helps you manage and organize your After Effects plugin files by grouping associated files into neat folders for easier management and access.\n\n"
    "🔹 1. Select Directory: Browse for the folder with your After Effects plugin files \n (e.g., ...\\Adobe After Effects XXXX\\Support Files\\Plug-ins).\n\n"
    "🔹 2. Folder Naming: Optionally add a prefix/suffix for the created folders. \nExample: files like 'Plugin.aex', 'PluginLicense.dll', and 'Plugin Presets' will be grouped in '[Prefix]Plugin[Suffix]'.\n\n"
    "🔹 3. Preview & Organize: Click 'Preview & Organize' to see planned moves. \n\n"
    "🔹 4. Undo Last Action: Click 'Undo Last' to revert the most recent change and remove empty folders.\n\n"
    "🔹 5. View History: Click 'View History' to check the action log.\n\n"
    "🔹 6. Logging: Logs are saved in 'plugin_organizer.log'.\n\n"
    "⚠️ IMPORTANT: Requires Administrator rights for system folders. Backup your plugins folder before making big changes. Undo relies on 'undo_log.json' created after a successful run."
)


    messagebox.showinfo("Help / Guide", help_text)
    log_action("Help window displayed.")

# show_history_log function (no changes)
def show_history_log():
    """Displays the content of the log file in a new window."""
    log_action("User requested to view history log.")
    if not os.path.exists(LOG_FILE):
        messagebox.showinfo("History Log", f"Log file ('{os.path.basename(LOG_FILE)}') not found."); log_action("History view aborted: Log file not found."); return
    try:
        log_win = tk.Toplevel(app); log_win.title(f"Action History - {os.path.basename(LOG_FILE)}")
        log_win.geometry("700x500"); log_win.minsize(400, 300); log_win.grab_set(); log_win.transient(app)
        log_text_area = scrolledtext.ScrolledText(log_win, wrap=tk.WORD, borderwidth=1, relief="solid", font=("Consolas", 9))
        log_text_area.pack(padx=10, pady=(10, 5), expand=True, fill=tk.BOTH)
        with open(LOG_FILE, "r", encoding='utf-8') as f: log_content = f.read()
        log_text_area.insert(tk.END, log_content); log_text_area.configure(state="disabled"); log_text_area.see(tk.END)
        close_button = tk.Button(log_win, text="Close", command=log_win.destroy, width=10); close_button.pack(pady=(5, 10))
        log_win.wait_window()
    except Exception as e:
        messagebox.showerror("Error", f"Could not read or display log file:\n{e}"); log_action(f"History view error: {e}")


# --- GUI Setup (no changes) ---
app = tk.Tk()
app.title("Plugin Organizer for AE")
# +++ Add Icon Code (Method 1: .ico) +++
# Determine if running as a bundled executable or as a script
if getattr(sys, 'frozen', False):  # Check if running from a bundled .exe
    # Path inside the bundle
    icon_path = os.path.join(sys._MEIPASS, 'app-icon', 'app_icon.ico') # <--- Path to check
else:
    # Path when running as script (assuming 'app-icon' folder exists next to script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'app-icon', 'app_icon.ico') # <--- Path to check

# ... rest of the try/except block using icon_path ...

try:
    if os.path.exists(icon_path):
        app.iconbitmap(icon_path)
        print(f"Loaded window icon from {icon_path}")
    else:
        print(f"Warning: Icon file not found at {icon_path}")
except tk.TclError as e:
    print(f"Warning: Could not load icon '{icon_path}'. Ensure it's a valid .ico file.")
except Exception as e:
    print(f"Warning: An unexpected error occurred setting the icon: {e}")
# +++ End Icon Code +++

# +++ End Icon Code +++
app.geometry("570x290")
app.minsize(500, 270)

frame = tk.Frame(app, padx=15, pady=15)
frame.pack(expand=True, fill=tk.BOTH)
frame.columnconfigure(1, weight=1)

lbl_dir = tk.Label(frame, text="Plugin Directory:")
lbl_dir.grid(row=0, column=0, sticky="w", pady=(0, 5))
entry_directory = tk.Entry(frame, width=50)
entry_directory.grid(row=0, column=1, padx=(5, 5), sticky="ew", pady=(0, 5))
btn_browse = tk.Button(frame, text="Browse...", command=select_directory)
btn_browse.grid(row=0, column=2, padx=(0, 5), pady=(0, 5))

lbl_prefix = tk.Label(frame, text="Folder Prefix:")
lbl_prefix.grid(row=1, column=0, sticky="w", pady=(0, 5))
entry_prefix = tk.Entry(frame, width=25)
entry_prefix.grid(row=1, column=1, padx=5, sticky="w", pady=(0, 5))

lbl_suffix = tk.Label(frame, text="Folder Suffix:")
lbl_suffix.grid(row=2, column=0, sticky="w", pady=(0, 15))
entry_suffix = tk.Entry(frame, width=25)
entry_suffix.grid(row=2, column=1, padx=5, sticky="w", pady=(0, 15))

button_frame = tk.Frame(frame)
button_frame.grid(row=3, column=0, columnspan=3, pady=(10, 10))
btn_help = tk.Button(button_frame, text="Help / Guide", command=show_help, width=12)
btn_help.pack(side=tk.LEFT, padx=5, pady=5)
btn_history = tk.Button(button_frame, text="View History", command=show_history_log, width=12)
btn_history.pack(side=tk.LEFT, padx=5, pady=5)
btn_preview = tk.Button(button_frame, text="Preview & Organize", command=run_preview, width=15, font=('Segoe UI', 9, 'bold'))
btn_preview.pack(side=tk.LEFT, padx=5, pady=5)
btn_undo = tk.Button(button_frame, text="Undo Last", command=undo_moves, width=12)
btn_undo.pack(side=tk.LEFT, padx=5, pady=5)

credit_label = tk.Label(frame, text="Developed by chal7z", font=("Arial", 8), fg="grey")
credit_label.grid(row=4, column=0, columnspan=3, pady=(15, 0))

# --- Run the application (no changes) ---
if __name__ == "__main__":
    if is_admin():
        log_action("--- Application session started ---")
        app.mainloop()
        log_action("--- Application session finished ---")
    else:
        print("Application requires Administrator privileges.")
        try:
            root = tk.Tk(); root.withdraw(); messagebox.showerror("Admin Rights Required", "Please restart as Administrator."); root.destroy()
        except Exception: pass
        sys.exit(1)