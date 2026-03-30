"""
Windsurf Account Quick Switcher (Mac Version)
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
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path

# ============================================================
# Mac System Path Configuration
# ============================================================
HOME = os.path.expanduser('~')

# Windsurf application data directory (Mac path)
WINDSURF_DATA = os.path.join(HOME, 'Library', 'Application Support', 'Windsurf')
WINDSURF_USER = os.path.join(WINDSURF_DATA, 'User')
WINDSURF_GLOBAL_STORAGE = os.path.join(WINDSURF_USER, 'globalStorage')
STATE_DB = os.path.join(WINDSURF_GLOBAL_STORAGE, 'state.vscdb')
STORAGE_JSON = os.path.join(WINDSURF_GLOBAL_STORAGE, 'storage.json')

# Additional directories to back up
SESSION_STORAGE = os.path.join(WINDSURF_DATA, 'Session Storage')
LOCAL_STORAGE = os.path.join(WINDSURF_DATA, 'Local Storage')

# Mac-specific authentication files (unlike Windows, Mac has no Network directory)
COOKIES_FILE = os.path.join(WINDSURF_DATA, 'Cookies')
COOKIES_JOURNAL = os.path.join(WINDSURF_DATA, 'Cookies-journal')
NETWORK_STATE_FILE = os.path.join(WINDSURF_DATA, 'Network Persistent State')

# Codeium config directory (Mac path)
CODEIUM_DIR = os.path.join(HOME, '.codeium', 'windsurf')

# Profile storage directory (saved to the script's current directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(SCRIPT_DIR, 'windsurf_profiles')


# ============================================================
# Windsurf Account Switcher Main Class
# ============================================================
class WindsurfAccountSwitcher:
    def __init__(self, root):
        """
        Initialize the account switcher
        Args:
            root: tkinter main window object
        """
        self.root = root
        self.root.title("Windsurf Account Switcher (Mac) - Open Source & Free")
        self.root.geometry("550x560")
        self.root.resizable(True, True)
        
        # Ensure profile directory exists
        os.makedirs(PROFILES_DIR, exist_ok=True)
        
        # Initialize UI and data
        self.setup_ui()
        self.refresh_profiles()
        self.show_current_account()
    
    # --------------------------------------------------------
    # UI Setup
    # --------------------------------------------------------
    def setup_ui(self):
        """Set up the user interface"""
        # Current account info section
        info_frame = ttk.LabelFrame(self.root, text="Current Account", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Mac uses system default font
        self.current_account_label = ttk.Label(info_frame, text="Loading...", font=('PingFang SC', 12))
        self.current_account_label.pack(anchor=tk.W)
        
        self.current_email_label = ttk.Label(info_frame, text="", foreground='gray')
        self.current_email_label.pack(anchor=tk.W)
        
        # Profile list section
        list_frame = ttk.LabelFrame(self.root, text="Saved Account Profiles", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create Treeview table
        columns = ('name', 'email', 'date')
        self.profile_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        self.profile_tree.heading('name', text='Profile Name')
        self.profile_tree.heading('email', text='Email')
        self.profile_tree.heading('date', text='Saved At')
        self.profile_tree.column('name', width=120)
        self.profile_tree.column('email', width=200)
        self.profile_tree.column('date', width=160)
        
        # Scrollbar
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
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_all).pack(side=tk.RIGHT, padx=5)
        
        # Author watermark section
        author_frame = ttk.LabelFrame(self.root, text="✨ Author Info ✨", padding=8)
        author_frame.pack(fill=tk.X, padx=10, pady=8)
        
        # Author name
        author_name = ttk.Label(
            author_frame, 
            text="👨‍💻 ChuanKang KK (Universal Programmer)",
            foreground='#e91e63',
            font=('PingFang SC', 12, 'bold')
        )
        author_name.pack(anchor=tk.CENTER, pady=(0, 5))
        
        # WeChat contact
        wechat_info = ttk.Label(
            author_frame,
            text="📱 WeChat: 1837620622    📧 Email: 2040168455@qq.com",
            foreground='#1a73e8',
            font=('PingFang SC', 10)
        )
        wechat_info.pack(anchor=tk.CENTER, pady=2)
        
        # Platform info
        platform_info = ttk.Label(
            author_frame,
            text="🎬 Xianyu/Bilibili: Universal Programmer    ⭐ GitHub: github.com/1837620622",
            foreground='#666666',
            font=('PingFang SC', 10)
        )
        platform_info.pack(anchor=tk.CENTER, pady=2)
        
        # Star prompt
        star_info = ttk.Label(
            author_frame,
            text="🌟 Open source & free — please give us a Star!",
            foreground='#ff9800',
            font=('PingFang SC', 10, 'bold')
        )
        star_info.pack(anchor=tk.CENTER, pady=(5, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready | Open source & free — give us a Star!")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    # --------------------------------------------------------
    # Account Info Reading
    # --------------------------------------------------------
    def get_current_account_info(self):
        """
        Read current logged-in account info from the state.vscdb database
        Returns:
            (name, email): tuple of account name and email, or (None, None) on failure
        """
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
        """Display current account info on the UI"""
        name, email = self.get_current_account_info()
        if name:
            self.current_account_label.config(text=f"👤 {name}")
            self.current_email_label.config(text=f"📧 {email}")
        else:
            self.current_account_label.config(text="Not logged in or unable to read")
            self.current_email_label.config(text="")
    
    # --------------------------------------------------------
    # Profile List Management
    # --------------------------------------------------------
    def refresh_profiles(self):
        """Refresh the profile list, reading all saved profiles from storage directory"""
        # Clear the list
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        
        if not os.path.exists(PROFILES_DIR):
            return
        
        # Iterate through profile directory
        for profile_name in os.listdir(PROFILES_DIR):
            profile_path = os.path.join(PROFILES_DIR, profile_name)
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
        """Refresh all information (current account and profile list)"""
        self.show_current_account()
        self.refresh_profiles()
        self.status_var.set("Refreshed")
    
    def open_profiles_dir(self):
        """Open the profile storage directory"""
        # Ensure directory exists
        os.makedirs(PROFILES_DIR, exist_ok=True)
        # Mac uses the open command to open directories
        subprocess.run(['open', PROFILES_DIR])
        self.status_var.set(f"Opened directory: {PROFILES_DIR}")
    
    # --------------------------------------------------------
    # Process Detection (Mac Version)
    # --------------------------------------------------------
    def is_windsurf_running(self):
        """
        Check if Windsurf is currently running (Mac version uses pgrep)
        Returns:
            bool: True if running, False if not
        """
        try:
            # Check main process
            result = subprocess.run(
                ['pgrep', '-f', 'Windsurf'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True
            # Check for Windsurf Helper process
            result2 = subprocess.run(
                ['pgrep', '-f', 'Windsurf Helper'],
                capture_output=True, text=True
            )
            return result2.returncode == 0
        except:
            return False
    
    def force_quit_windsurf(self):
        """
        Force quit the Windsurf process
        """
        try:
            subprocess.run(['pkill', '-9', '-f', 'Windsurf'], capture_output=True)
            import time
        time.sleep(1)  # Wait for process to fully exit
            return not self.is_windsurf_running()
        except:
            return False
    
    def verify_switch(self, expected_email):
        """
        Verify whether the account switch was successful
        Args:
            expected_email: the email address expected after switching
        Returns:
            bool: True if switch succeeded, False if failed
        """
        _, current_email = self.get_current_account_info()
        return current_email == expected_email
    
    # --------------------------------------------------------
    # Event Handlers
    # --------------------------------------------------------
    def on_switch_click(self):
        """Handle switch button click event"""
        try:
            self.status_var.set("Switching...")
            self.root.update()  # Force UI update
            self.switch_profile()
        except Exception as e:
            messagebox.showerror("Error", f"An exception occurred during switching:\n{e}")
            import traceback
            traceback.print_exc()
    
    # --------------------------------------------------------
    # Save Profile
    # --------------------------------------------------------
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
            messagebox.showerror("Error", "Unable to read account info. Please make sure you are logged in to Windsurf.")
            return
        
        # Use email prefix as default profile name
        default_name = email.split('@')[0] if email else "profile"
        profile_name = simpledialog.askstring("Save Profile", "Enter a profile name:", initialvalue=default_name)
        
        if not profile_name:
            return
        
        # Remove invalid characters, keep only alphanumeric and select symbols
        profile_name = "".join(c for c in profile_name if c.isalnum() or c in ('_', '-', '.'))
        
        profile_path = os.path.join(PROFILES_DIR, profile_name)
        
        # Check if a profile with the same name already exists
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
            
            # Copy Cookies files (Mac-specific, critical for authentication)
            if os.path.exists(COOKIES_FILE):
                shutil.copy2(COOKIES_FILE, os.path.join(profile_path, 'Cookies'))
            if os.path.exists(COOKIES_JOURNAL):
                shutil.copy2(COOKIES_JOURNAL, os.path.join(profile_path, 'Cookies-journal'))
            
            # Copy Network Persistent State file
            if os.path.exists(NETWORK_STATE_FILE):
                shutil.copy2(NETWORK_STATE_FILE, os.path.join(profile_path, 'Network Persistent State'))
            
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
    
    # --------------------------------------------------------
    # Switch Profile
    # --------------------------------------------------------
    def switch_profile(self):
        """Switch to the selected Profile"""
        selected = self.profile_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a profile to switch to first.")
            return
        
        # Get selected profile info
        profile_name = str(self.profile_tree.item(selected[0])['values'][0])
        target_email = str(self.profile_tree.item(selected[0])['values'][1])
        profile_path = os.path.join(PROFILES_DIR, profile_name)
        
        print(f"[DEBUG] Switch operation started")
        print(f"[DEBUG] profile_name: {profile_name}")
        print(f"[DEBUG] target_email: {target_email}")
        
        # Check if profile directory exists
        if not os.path.exists(profile_path):
            messagebox.showerror("Error", f"Profile directory does not exist: {profile_path}")
            return
        
        # Get current account info
        _, current_email = self.get_current_account_info()
        
        # Check if already on the target account
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
            try:
                if os.path.exists(state_backup):
                    shutil.copy2(state_backup, STATE_DB)
                    success_items.append("state.vscdb")
            except Exception as e:
                errors.append(f"state.vscdb: {e}")
        
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
        
        # 4. Copy Cookies files (critical for Mac authentication)
        cookies_backup = os.path.join(profile_path, 'Cookies')
        cookies_journal_backup = os.path.join(profile_path, 'Cookies-journal')
        try:
            if os.path.exists(cookies_backup):
                shutil.copy2(cookies_backup, COOKIES_FILE)
                success_items.append("Cookies")
            if os.path.exists(cookies_journal_backup):
                shutil.copy2(cookies_journal_backup, COOKIES_JOURNAL)
        except Exception as e:
            errors.append(f"Cookies: {str(e)[:50]}")
        
        # 5. Copy Network Persistent State file
        network_state_backup = os.path.join(profile_path, 'Network Persistent State')
        try:
            if os.path.exists(network_state_backup):
                shutil.copy2(network_state_backup, NETWORK_STATE_FILE)
                success_items.append("Network State")
        except Exception as e:
            errors.append(f"Network State: {str(e)[:50]}")
        
        # 6. Copy codeium config files
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
        self.root.update()
        
        # Verify switch result
        _, new_email = self.get_current_account_info()
        print(f"[DEBUG] Account after switch: {new_email}")
        
        if new_email == target_email:
            self.status_var.set(f"[OK] Switched successfully: {profile_name}")
            msg = f"Switch successful!\n\nCurrent account: {target_email}\n\nCopied successfully: {', '.join(success_items)}"
            if errors:
                msg += f"\n\nSome files failed to copy (may not affect functionality):\n" + "\n".join(errors)
            msg += "\n\nPlease launch Windsurf to verify."
            messagebox.showinfo("Switch Successful", msg)
        else:
            self.status_var.set(f"[FAIL] Switch failed")
            msg = f"Switch may not have fully succeeded\n\nExpected: {target_email}\nShowing: {new_email}\n\nCopied: {', '.join(success_items)}"
            if errors:
                msg += f"\n\nErrors:\n" + "\n".join(errors)
            msg += "\n\nPlease launch Windsurf to verify the actual login state."
            messagebox.showwarning("Switch Notice", msg)
    
    # --------------------------------------------------------
    # Delete Profile
    # --------------------------------------------------------
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
            profile_path = os.path.join(PROFILES_DIR, profile_name)
            shutil.rmtree(profile_path)
            self.refresh_profiles()
            self.status_var.set(f"Profile deleted: {profile_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")


# ============================================================
# Program Entry Point
# ============================================================
def main():
    """Main function, launches the application"""
    root = tk.Tk()
    
    # Set style theme
    style = ttk.Style()
    # Mac uses aqua theme for native look
    try:
        style.theme_use('aqua')
    except:
        style.theme_use('clam')
    
    app = WindsurfAccountSwitcher(root)
    root.mainloop()


if __name__ == '__main__':
    main()
