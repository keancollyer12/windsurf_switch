"""
Windsurf Account Quick Switcher
Features:
1. Save current account as a Profile
2. Switch to a saved Profile
3. List all Profiles
4. Delete a Profile
"""

import os
import sys
import json
import shutil
import sqlite3
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
from pathlib import Path

# Config paths
APPDATA = os.environ.get('APPDATA', '')
LOCALAPPDATA = os.environ.get('LOCALAPPDATA', '')
USERPROFILE = os.environ.get('USERPROFILE', '')

WINDSURF_DATA = os.path.join(APPDATA, 'Windsurf')
WINDSURF_USER = os.path.join(WINDSURF_DATA, 'User')
WINDSURF_GLOBAL_STORAGE = os.path.join(WINDSURF_USER, 'globalStorage')
STATE_DB = os.path.join(WINDSURF_GLOBAL_STORAGE, 'state.vscdb')

# Additional directories to back up
SESSION_STORAGE = os.path.join(WINDSURF_DATA, 'Session Storage')
LOCAL_STORAGE = os.path.join(WINDSURF_DATA, 'Local Storage')
NETWORK_DIR = os.path.join(WINDSURF_DATA, 'Network')

CODEIUM_DIR = os.path.join(USERPROFILE, '.codeium', 'windsurf')

# Profile storage directory (saved to the script's current directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES_DIR = os.path.join(SCRIPT_DIR, 'windsurf_profiles')

# Settings file (stores user preferences like custom profiles directory)
SETTINGS_FILE = os.path.join(os.environ.get('APPDATA', SCRIPT_DIR), 'windsurf-switcher', 'settings.json')


class WindsurfAccountSwitcher:
    def __init__(self, root):
        self.root = root
        self.root.title("Windsurf Account Switcher (Windows) - Open Source & Free")
        self.root.geometry("550x540")
        self.root.resizable(True, True)
        
        # Ensure profile directory exists
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        self.setup_ui()
        self.refresh_profiles()
        self.show_current_account()
    
    def setup_ui(self):
        # Current account info
        info_frame = ttk.LabelFrame(self.root, text="Current Account", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.current_account_label = ttk.Label(info_frame, text="Loading...", font=('Microsoft YaHei', 10))
        self.current_account_label.pack(anchor=tk.W)
        
        self.current_email_label = ttk.Label(info_frame, text="", foreground='gray')
        self.current_email_label.pack(anchor=tk.W)
        
        # Profile list
        list_frame = ttk.LabelFrame(self.root, text="Saved Account Profiles", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create Treeview
        columns = ('name', 'email', 'date')
        self.profile_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        self.profile_tree.heading('name', text='Profile Name')
        self.profile_tree.heading('email', text='Email')
        self.profile_tree.heading('date', text='Saved At')
        self.profile_tree.column('name', width=120)
        self.profile_tree.column('email', width=180)
        self.profile_tree.column('date', width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.profile_tree.yview)
        self.profile_tree.configure(yscrollcommand=scrollbar.set)
        
        self.profile_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Button area
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Save Current Account", command=self.save_current_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Switch Account", command=self.on_switch_click).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Profile", command=self.delete_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Open Directory", command=self.open_profiles_dir).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⚙️ Settings", command=self.open_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_all).pack(side=tk.RIGHT, padx=5)
        
        # Author watermark section
        author_frame = ttk.LabelFrame(self.root, text="✨ Author Info ✨", padding=8)
        author_frame.pack(fill=tk.X, padx=10, pady=8)
        
        # Author name
        author_name = ttk.Label(
            author_frame, 
            text="👨‍💻 ChuanKang KK (Universal Programmer)",
            foreground='#e91e63',
            font=('Microsoft YaHei', 11, 'bold')
        )
        author_name.pack(anchor=tk.CENTER, pady=(0, 5))
        
        # WeChat contact
        wechat_info = ttk.Label(
            author_frame,
            text="📱 WeChat: 1837620622    📧 Email: 2040168455@qq.com",
            foreground='#1a73e8',
            font=('Microsoft YaHei', 9)
        )
        wechat_info.pack(anchor=tk.CENTER, pady=2)
        
        # Platform info
        platform_info = ttk.Label(
            author_frame,
            text="🎬 Xianyu/Bilibili: Universal Programmer    ⭐ GitHub: github.com/1837620622",
            foreground='#666666',
            font=('Microsoft YaHei', 9)
        )
        platform_info.pack(anchor=tk.CENTER, pady=2)
        
        # Star prompt
        star_info = ttk.Label(
            author_frame,
            text="🌟 Open source & free — please give us a Star!",
            foreground='#ff9800',
            font=('Microsoft YaHei', 9, 'bold')
        )
        star_info.pack(anchor=tk.CENTER, pady=(5, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready | Open source & free — give us a Star!")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def load_profiles_dir(self):
        """Load the profiles directory from settings, fallback to default."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                custom_dir = settings.get('profiles_dir', '')
                if custom_dir and os.path.isdir(os.path.dirname(custom_dir)):
                    return custom_dir
        except Exception:
            pass
        return DEFAULT_PROFILES_DIR

    def save_profiles_dir(self, new_dir):
        """Save the chosen profiles directory to settings."""
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            settings = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            settings['profiles_dir'] = new_dir
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def open_settings(self):
        """Open the Settings window."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("480x160")
        settings_win.resizable(False, False)
        settings_win.grab_set()  # Make it modal

        # Title label
        ttk.Label(settings_win, text="Settings", font=('Microsoft YaHei', 12, 'bold')).pack(pady=(14, 8))

        # Profiles directory row
        dir_frame = ttk.LabelFrame(settings_win, text="Select directory to save profiles", padding=10)
        dir_frame.pack(fill=tk.X, padx=14, pady=4)

        self.settings_dir_var = tk.StringVar(value=self.profiles_dir)

        dir_entry = ttk.Entry(dir_frame, textvariable=self.settings_dir_var, width=42)
        dir_entry.pack(side=tk.LEFT, padx=(0, 6))

        def browse_dir():
            chosen = filedialog.askdirectory(
                title="Select directory to save profiles",
                initialdir=self.profiles_dir
            )
            if chosen:
                self.settings_dir_var.set(chosen)

        ttk.Button(dir_frame, text="Browse...", command=browse_dir).pack(side=tk.LEFT)

        # Save / Cancel buttons
        btn_row = ttk.Frame(settings_win, padding=(10, 6))
        btn_row.pack()

        def save_settings():
            new_dir = self.settings_dir_var.get().strip()
            if not new_dir:
                messagebox.showwarning("Warning", "Please select a directory.", parent=settings_win)
                return
            os.makedirs(new_dir, exist_ok=True)
            self.profiles_dir = new_dir
            self.save_profiles_dir(new_dir)
            self.refresh_profiles()
            self.status_var.set(f"Profiles directory set to: {new_dir}")
            settings_win.destroy()

        ttk.Button(btn_row, text="Save", command=save_settings).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Cancel", command=settings_win.destroy).pack(side=tk.LEFT, padx=6)

    def get_current_account_info(self):
        """Read current account info from state.vscdb"""
        try:
            if not os.path.exists(STATE_DB):
                return None, None
            
            conn = sqlite3.connect(STATE_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key='windsurfAuthStatus'")
            row = cursor.fetchone()
            conn.close()
            
            if row:
                data = json.loads(row[0])
                return data.get('name', 'Unknown'), data.get('email', 'Unknown')
            return None, None
        except Exception as e:
            print(f"Failed to read account info: {e}")
            return None, None
    
    def show_current_account(self):
        """Display current account info"""
        name, email = self.get_current_account_info()
        if name:
            self.current_account_label.config(text=f"👤 {name}")
            self.current_email_label.config(text=f"📧 {email}")
        else:
            self.current_account_label.config(text="Not logged in or unable to read")
            self.current_email_label.config(text="")
    
    def refresh_profiles(self):
        """Refresh the profile list"""
        # Clear the list
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        
        if not os.path.exists(self.profiles_dir):
            return
        
        for profile_name in os.listdir(self.profiles_dir):
            profile_path = os.path.join(self.profiles_dir, profile_name)
            if os.path.isdir(profile_path):
                meta_file = os.path.join(profile_path, 'profile_meta.json')
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        self.profile_tree.insert('', tk.END, values=(
                            profile_name,
                            meta.get('email', 'Unknown'),
                            meta.get('saved_at', 'Unknown')
                        ))
                    except:
                        self.profile_tree.insert('', tk.END, values=(profile_name, 'Read failed', ''))
    
    def refresh_all(self):
        """Refresh all information"""
        self.show_current_account()
        self.refresh_profiles()
        self.status_var.set("Refreshed")
    
    def open_profiles_dir(self):
        """Open the profile storage directory"""
        # Ensure directory exists
        os.makedirs(self.profiles_dir, exist_ok=True)
        # Open directory with Windows Explorer
        os.startfile(self.profiles_dir)
        self.status_var.set(f"Opened directory: {self.profiles_dir}")
    
    def is_windsurf_running(self):
        """Check if Windsurf is currently running"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq Windsurf.exe'],
                capture_output=True, text=True
            )
            return 'Windsurf.exe' in result.stdout
        except:
            return False
    
    def verify_switch(self, expected_email):
        """Verify whether the switch was successful"""
        _, current_email = self.get_current_account_info()
        return current_email == expected_email
    
    def on_switch_click(self):
        """Switch button click event"""
        try:
            self.status_var.set("Switching...")
            self.root.update()  # Force UI update
            self.switch_profile()
        except Exception as e:
            messagebox.showerror("Error", f"An exception occurred during switching:\n{e}")
            import traceback
            traceback.print_exc()
    
    def force_quit_windsurf(self):
        """Force quit the Windsurf process"""
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'Windsurf.exe'], capture_output=True)
            import time
            time.sleep(1)  # Wait for process to fully exit
            return not self.is_windsurf_running()
        except:
            return False
    
    def save_current_profile(self):
        """Save the current account as a Profile"""
        # Check if Windsurf is running
        if self.is_windsurf_running():
            result = messagebox.askyesno(
            "Warning",
            "Windsurf is currently running!\n\n"
            "To ensure authentication data is saved completely, please close Windsurf first.\n\n"
            "Do you want to force-close Windsurf and continue?"
            )
            if result:
                self.status_var.set("Closing Windsurf...")
                self.root.update()
                if not self.force_quit_windsurf():
                    messagebox.showerror("Error", "Unable to close Windsurf. Please close it manually and try again.")
                    return
            else:
                return
        
        name, email = self.get_current_account_info()
        if not name:
            messagebox.showerror("Error", "Unable to read current account info. Please make sure you are logged in to Windsurf.")
            return
        
        # Use email prefix as default name
        default_name = email.split('@')[0] if email else "profile"
        profile_name = simpledialog.askstring("Save Profile", "Enter a profile name:", initialvalue=default_name)
        
        if not profile_name:
            return
        
        # Remove invalid characters
        profile_name = "".join(c for c in profile_name if c.isalnum() or c in ('_', '-', '.'))
        
        profile_path = os.path.join(self.profiles_dir, profile_name)
        
        if os.path.exists(profile_path):
            if not messagebox.askyesno("Confirm", f"Profile '{profile_name}' already exists. Overwrite?"):
                return
            shutil.rmtree(profile_path)
        
        try:
            os.makedirs(profile_path)
            
            # ★★★ Core improvement: copy entire globalStorage directory ★★★
            global_storage_backup = os.path.join(profile_path, 'globalStorage')
            if os.path.exists(WINDSURF_GLOBAL_STORAGE):
                # Copy entire directory, excluding large backup files
                shutil.copytree(
                    WINDSURF_GLOBAL_STORAGE, 
                    global_storage_backup,
                    ignore=shutil.ignore_patterns('*.backup.*', 'ms-*')
                )
            
            # Copy Session Storage
            if os.path.exists(SESSION_STORAGE):
                shutil.copytree(SESSION_STORAGE, os.path.join(profile_path, 'Session Storage'))
            
            # Copy Local Storage
            if os.path.exists(LOCAL_STORAGE):
                shutil.copytree(LOCAL_STORAGE, os.path.join(profile_path, 'Local Storage'))
            
            # Copy Network directory (includes Cookies)
            if os.path.exists(NETWORK_DIR):
                shutil.copytree(NETWORK_DIR, os.path.join(profile_path, 'Network'))
            
            # Copy key files from .codeium directory
            codeium_backup = os.path.join(profile_path, 'codeium')
            if os.path.exists(CODEIUM_DIR):
                # Only copy key files, skip large caches
                os.makedirs(codeium_backup, exist_ok=True)
                for item in ['installation_id', 'user_settings.pb']:
                    src = os.path.join(CODEIUM_DIR, item)
                    if os.path.exists(src):
                        shutil.copy2(src, codeium_backup)
            
            # Save metadata
            meta = {
                'name': name,
                'email': email,
                'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(os.path.join(profile_path, 'profile_meta.json'), 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            self.refresh_profiles()
            self.status_var.set(f"Profile saved: {profile_name}")
            messagebox.showinfo("Success", f"Profile '{profile_name}' saved successfully!\n\nFull globalStorage directory has been backed up.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")
    
    def switch_profile(self):
        """Switch to the selected Profile"""
        selected = self.profile_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a profile to switch to first.")
            return
        
        # Note: Treeview values may be integers, convert to string
        profile_name = str(self.profile_tree.item(selected[0])['values'][0])
        target_email = str(self.profile_tree.item(selected[0])['values'][1])
        profile_path = os.path.join(self.profiles_dir, profile_name)
        
        # Debug info
        print(f"[DEBUG] Switch operation started")
        print(f"[DEBUG] profile_name: {profile_name}, type: {type(profile_name)}")
        print(f"[DEBUG] target_email: {target_email}")
        print(f"[DEBUG] profile_path: {profile_path}")
        print(f"[DEBUG] profile_path exists: {os.path.exists(profile_path)}")
        
        # Check if profile directory exists
        if not os.path.exists(profile_path):
            messagebox.showerror("Error", f"Profile directory does not exist: {profile_path}")
            return
        
        # Get current account
        _, current_email = self.get_current_account_info()
        print(f"[DEBUG] current_email: {current_email}")
        
        if current_email == target_email:
            messagebox.showinfo("Info", f"Already using account '{target_email}'")
            return
        
        # Check if Windsurf is running
        if self.is_windsurf_running():
            result = messagebox.askyesno(
            "Warning",
            f"Windsurf is currently running!\n\n"
            f"Current account: {current_email}\n"
            f"Target account: {target_email}\n\n"
            f"You need to close Windsurf before switching accounts.\n\n"
            f"Do you want to force-close Windsurf and continue?"
            )
            if result:
                self.status_var.set("Closing Windsurf...")
                self.root.update()
                if not self.force_quit_windsurf():
                    messagebox.showerror("Error", "Unable to close Windsurf. Please close it manually and try again.")
                    return
            else:
                return
        else:
            # Windsurf is not running, confirm switch
            if not messagebox.askyesno("Confirm Switch", f"Current account: {current_email}\nTarget account: {target_email}\n\nAre you sure you want to switch?"):
                return
        
        errors = []
        success_items = []
        
        # ★★★ Core improvement: check and restore entire globalStorage directory ★★★
        global_storage_backup = os.path.join(profile_path, 'globalStorage')
        if os.path.exists(global_storage_backup):
            try:
                # Delete existing globalStorage directory
                if os.path.exists(WINDSURF_GLOBAL_STORAGE):
                    shutil.rmtree(WINDSURF_GLOBAL_STORAGE)
                # Copy backed-up globalStorage directory
                shutil.copytree(global_storage_backup, WINDSURF_GLOBAL_STORAGE)
                success_items.append("globalStorage (full directory)")
                print(f"[DEBUG] globalStorage directory restored successfully")
            except Exception as e:
                errors.append(f"globalStorage: {str(e)[:80]}")
                print(f"[DEBUG] globalStorage restore failed: {e}")
        else:
            # Legacy compatibility: copy only state.vscdb
            state_backup = os.path.join(profile_path, 'state.vscdb')
            print(f"[DEBUG] state_backup: {state_backup}, exists: {os.path.exists(state_backup)}")
            try:
                if os.path.exists(state_backup):
                    shutil.copy2(state_backup, STATE_DB)
                    success_items.append("state.vscdb")
                    print(f"[DEBUG] state.vscdb copied successfully")
                else:
                    errors.append("state.vscdb: file not found")
            except Exception as e:
                errors.append(f"state.vscdb: {e}")
                print(f"[DEBUG] state.vscdb copy failed: {e}")
        
        # 2. Try copying Session Storage
        session_backup = os.path.join(profile_path, 'Session Storage')
        try:
            if os.path.exists(session_backup):
                if os.path.exists(SESSION_STORAGE):
                    shutil.rmtree(SESSION_STORAGE)
                shutil.copytree(session_backup, SESSION_STORAGE)
                success_items.append("Session Storage")
        except Exception as e:
            errors.append(f"Session Storage: {str(e)[:50]}")
        
        # 3. Try copying Local Storage
        local_backup = os.path.join(profile_path, 'Local Storage')
        try:
            if os.path.exists(local_backup):
                if os.path.exists(LOCAL_STORAGE):
                    shutil.rmtree(LOCAL_STORAGE)
                shutil.copytree(local_backup, LOCAL_STORAGE)
                success_items.append("Local Storage")
        except Exception as e:
            errors.append(f"Local Storage: {str(e)[:50]}")
        
        # 4. Try copying Network
        network_backup = os.path.join(profile_path, 'Network')
        try:
            if os.path.exists(network_backup):
                if os.path.exists(NETWORK_DIR):
                    shutil.rmtree(NETWORK_DIR)
                shutil.copytree(network_backup, NETWORK_DIR)
                success_items.append("Network")
        except Exception as e:
            errors.append(f"Network: {str(e)[:50]}")
        
        # 5. Copy codeium config
        codeium_backup = os.path.join(profile_path, 'codeium')
        try:
            if os.path.exists(codeium_backup):
                for item in os.listdir(codeium_backup):
                    src = os.path.join(codeium_backup, item)
                    dst = os.path.join(CODEIUM_DIR, item)
                    shutil.copy2(src, dst)
                success_items.append("codeium")
        except Exception as e:
            errors.append(f"codeium: {str(e)[:50]}")
        
        # Refresh display
        self.show_current_account()
        
        # Refresh display
        self.root.update()  # Force UI update
        
        # Verify switch result
        _, new_email = self.get_current_account_info()
        print(f"[DEBUG] Account after switch: {new_email}")
        
        if new_email == target_email:
            self.status_var.set(f"[OK] Switched successfully: {profile_name}")
            msg = f"[OK] Switch successful!\n\nCurrent account: {target_email}\n\nCopied successfully: {', '.join(success_items)}"
            if errors:
                msg += f"\n\nSome files failed to copy (this may not affect functionality):\n" + "\n".join(errors)
            msg += "\n\nPlease restart Windsurf for the changes to take effect."
            messagebox.showinfo("Switch Successful", msg)
        else:
            self.status_var.set(f"[FAIL] Switch failed")
            msg = f"[FAIL] Switch failed\n\nExpected: {target_email}\nActual: {new_email}\n\nErrors:\n" + "\n".join(errors) if errors else f"Expected: {target_email}\nActual: {new_email}"
            messagebox.showerror("Switch Failed", msg)
    
    def delete_profile(self):
        """Delete the selected Profile"""
        selected = self.profile_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a profile to delete first.")
            return
        
        # Convert to string to avoid type errors with numeric profile names
        profile_name = str(self.profile_tree.item(selected[0])['values'][0])
        
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile '{profile_name}'?\n\nThis action cannot be undone."):
            return
        
        try:
            profile_path = os.path.join(self.profiles_dir, profile_name)
            shutil.rmtree(profile_path)
            self.refresh_profiles()
            self.status_var.set(f"Profile deleted: {profile_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")


def main():
    root = tk.Tk()
    
    # Set style
    style = ttk.Style()
    style.theme_use('clam')
    
    app = WindsurfAccountSwitcher(root)
    root.mainloop()


if __name__ == '__main__':
    main()

