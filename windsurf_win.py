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
import base64
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

# Profile storage directory (configurable; default stored under APPDATA to avoid PyInstaller temp dir)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES_DIR = os.path.join(APPDATA or SCRIPT_DIR, 'WindsurfSwitcher', 'windsurf_profiles')
CONFIG_DIR = os.path.join(APPDATA or SCRIPT_DIR, 'WindsurfSwitcher')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')


def _pb_read_varint(buf, idx):
    shift = 0
    result = 0
    while True:
        if idx >= len(buf):
            raise ValueError('Truncated varint')
        b = buf[idx]
        idx += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, idx
        shift += 7
        if shift > 64:
            raise ValueError('Varint too long')


def _pb_extract_string_fields(buf, wanted_fields, max_depth=4, _depth=0):
    found = {}
    idx = 0
    while idx < len(buf) and len(found) < len(wanted_fields):
        try:
            key, idx = _pb_read_varint(buf, idx)
        except Exception:
            break

        field_number = key >> 3
        wire_type = key & 0x07

        if wire_type == 0:
            try:
                _, idx = _pb_read_varint(buf, idx)
            except Exception:
                break
        elif wire_type == 1:
            idx += 8
        elif wire_type == 5:
            idx += 4
        elif wire_type == 2:
            try:
                length, idx = _pb_read_varint(buf, idx)
            except Exception:
                break
            if length < 0 or idx + length > len(buf):
                break
            payload = buf[idx:idx + length]
            idx += length

            if field_number in wanted_fields and field_number not in found:
                try:
                    s = payload.decode('utf-8')
                    if s:
                        found[field_number] = s
                except Exception:
                    pass

            if _depth < max_depth and payload:
                nested = _pb_extract_string_fields(payload, wanted_fields, max_depth=max_depth, _depth=_depth + 1)
                for k, v in nested.items():
                    if k not in found and v:
                        found[k] = v
        else:
            break

    return found


class WindsurfAccountSwitcher:
    def __init__(self, root):
        self.root = root
        self.root.title("Windsurf Account Switcher")
        self.root.geometry("750x500")
        self.root.resizable(True, True)

        self.profiles_dir = self._load_profiles_dir()
        os.makedirs(self.profiles_dir, exist_ok=True)
         
        self.setup_ui()
        self.refresh_profiles()
        self.show_current_account()

    def _has_custom_profiles_dir(self):
        try:
            if not os.path.exists(CONFIG_FILE):
                return False
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            configured = (data.get('profiles_dir') or '').strip()
            if not configured:
                return False
            if os.path.normcase(os.path.abspath(configured)) == os.path.normcase(os.path.abspath(DEFAULT_PROFILES_DIR)):
                return False
            return True
        except Exception:
            return False

    def _require_custom_profiles_dir(self):
        if not self._has_custom_profiles_dir():
            messagebox.showerror("Error", "Please add a directory via settings first.")
            return False
        return True

    def _get_codeium_auth_name(self):
        try:
            if not os.path.exists(STATE_DB):
                return None

            conn = sqlite3.connect(STATE_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key='codeium.windsurf-windsurf_auth'")
            row = cursor.fetchone()
            conn.close()

            if row and isinstance(row[0], str):
                name = row[0].strip()
                return name if name else None
            return None
        except Exception as e:
            print(f"Failed to read Codeium auth name: {e}")
            return None

    def _load_profiles_dir(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                configured = data.get('profiles_dir')
                if configured and os.path.isdir(configured):
                    return configured
                if configured and not os.path.exists(configured):
                    return configured
        except Exception:
            pass
        return DEFAULT_PROFILES_DIR

    def _save_profiles_dir(self, path):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'profiles_dir': path}, f, ensure_ascii=False, indent=2)

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
        
        # Configure tag for current account highlighting
        self.profile_tree.tag_configure('current', foreground='red')
        
        # Button area
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Save Current Account", command=self.save_current_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Switch Account", command=self.on_switch_click).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Profile", command=self.delete_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Open Directory", command=self.open_profiles_dir).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_all).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Settings", command=self.open_settings).pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready | Created By CyberToxic7")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
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
                name = data.get('name')
                email = data.get('email')
                if name or email:
                    return name or 'Unknown', email or 'Unknown'

                proto_b64 = data.get('userStatusProtoBinaryBase64')
                if proto_b64:
                    try:
                        proto_b64 = proto_b64.strip()
                        missing_padding = (-len(proto_b64)) % 4
                        if missing_padding:
                            proto_b64 += '=' * missing_padding
                        raw = base64.urlsafe_b64decode(proto_b64)
                        extracted = _pb_extract_string_fields(raw, wanted_fields={3, 7})
                        pb_name = extracted.get(3)
                        pb_email = extracted.get(7)
                        if pb_name or pb_email:
                            return pb_name or 'Unknown', pb_email or 'Unknown'
                    except Exception as e:
                        print(f"Failed to decode protobuf account info: {e}")

                codeium_name = self._get_codeium_auth_name()
                if codeium_name:
                    return codeium_name, 'Unknown'

                return 'Unknown', 'Unknown'
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
        
        # Get current account info for highlighting
        _, current_email = self.get_current_account_info()
        
        for profile_name in os.listdir(self.profiles_dir):
            profile_path = os.path.join(self.profiles_dir, profile_name)
            if os.path.isdir(profile_path):
                meta_file = os.path.join(profile_path, 'profile_meta.json')
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        email = meta.get('email', 'Unknown')
                        saved_at = meta.get('saved_at', 'Unknown')
                        tags = ('current',) if (current_email and current_email != 'Unknown' and email == current_email) else ()
                        self.profile_tree.insert('', tk.END, values=(profile_name, email, saved_at), tags=tags)
                    except:
                        self.profile_tree.insert('', tk.END, values=(profile_name, 'Read failed', ''), tags=())
    
    def refresh_all(self):
        """Refresh all information"""
        self.show_current_account()
        self.refresh_profiles()
        self.status_var.set("Refreshed")
    
    def open_profiles_dir(self):
        """Open the profile storage directory"""
        if not self._require_custom_profiles_dir():
            return
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
        if not self._require_custom_profiles_dir():
            return
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

        target_name = None
        meta_file = os.path.join(profile_path, 'profile_meta.json')
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                target_name = meta.get('name')
            except Exception:
                target_name = None
        
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
        current_name, current_email = self.get_current_account_info()
        print(f"[DEBUG] current_email: {current_email}")

        email_available = bool(current_email) and current_email != 'Unknown'
        target_email_available = bool(target_email) and target_email != 'Unknown'
        if email_available and target_email_available and current_email == target_email:
            messagebox.showinfo("Info", f"Already using account '{target_email}'")
            return

        if (not email_available or not target_email_available) and target_name:
            if current_name and current_name != 'Unknown' and current_name == target_name:
                messagebox.showinfo("Info", f"Already using account '{target_name}'")
                return
        
        # Check if Windsurf is running
        if self.is_windsurf_running():
            result = messagebox.askyesno(
            "Warning",
            f"Windsurf is currently running!\n\n"
            f"Current account: {current_email if email_available else (current_name or 'Unknown')}\n"
            f"Target account: {target_email if target_email_available else (target_name or 'Unknown')}\n\n"
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
            if not messagebox.askyesno("Confirm Switch", f"Current account: {current_email if email_available else (current_name or 'Unknown')}\nTarget account: {target_email if target_email_available else (target_name or 'Unknown')}\n\nAre you sure you want to switch?"):
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
        new_name, new_email = self.get_current_account_info()
        print(f"[DEBUG] Account after switch: {new_email}")

        new_email_available = bool(new_email) and new_email != 'Unknown'
        if target_email_available and new_email_available and new_email == target_email:
            self.status_var.set(f"[OK] Switched successfully: {profile_name}")
            msg = f"[OK] Switch successful!\n\nCurrent account: {target_email}\n\nCopied successfully: {', '.join(success_items)}"
            if errors:
                msg += f"\n\nSome files failed to copy (this may not affect functionality):\n" + "\n".join(errors)
            msg += "\n\nPlease restart Windsurf for the changes to take effect."
            messagebox.showinfo("Switch Successful", msg)
        elif (not target_email_available or not new_email_available) and target_name and new_name and new_name != 'Unknown' and new_name == target_name:
            self.status_var.set(f"[OK] Switched successfully: {profile_name}")
            msg = f"[OK] Switch successful!\n\nCurrent account: {target_name}\n\nCopied successfully: {', '.join(success_items)}"
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

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.resizable(False, False)

        win.transient(self.root)
        win.grab_set()
        win.lift()
        win.focus_force()

        container = ttk.Frame(win, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Select directory to save profiles").grid(row=0, column=0, columnspan=3, sticky=tk.W)

        initial_dir_value = self.profiles_dir if self._has_custom_profiles_dir() else ""
        dir_var = tk.StringVar(value=initial_dir_value)
        entry = ttk.Entry(container, textvariable=dir_var, width=52)
        entry.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        def browse():
            win.attributes('-topmost', True)
            current_value = dir_var.get().strip()
            default_documents = os.path.join(USERPROFILE or (APPDATA or ""), 'Documents')
            initialdir = current_value if current_value else (default_documents if os.path.isdir(default_documents) else (USERPROFILE or APPDATA or ""))
            chosen = filedialog.askdirectory(parent=win, initialdir=initialdir)
            win.attributes('-topmost', False)
            win.lift()
            win.focus_force()
            if chosen:
                dir_var.set(chosen)

        def save():
            new_dir = dir_var.get().strip()
            if not new_dir:
                messagebox.showwarning("Settings", "Please select a directory.")
                return
            try:
                os.makedirs(new_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Settings", f"Unable to create directory:\n{e}")
                return

            self._save_profiles_dir(new_dir)
            self.profiles_dir = new_dir
            self.refresh_profiles()
            self.status_var.set(f"Profiles directory set: {new_dir}")
            win.destroy()

        ttk.Button(container, text="Select...", command=browse).grid(row=1, column=2, sticky=tk.W, padx=(8, 0), pady=(6, 0))

        btns = ttk.Frame(container)
        btns.grid(row=2, column=0, columnspan=3, sticky=tk.E, pady=(12, 0))
        ttk.Button(btns, text="Save", command=save).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.RIGHT)

        win.update_idletasks()
        w = 440
        h = max(win.winfo_reqheight(), 120)
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        x = root_x + max((root_w - w) // 2, 0)
        y = root_y + max((root_h - h) // 2, 0)
        win.geometry(f"{w}x{h}+{x}+{y}")


def main():
    root = tk.Tk()
    
    # Set style
    style = ttk.Style()
    style.theme_use('clam')
    
    app = WindsurfAccountSwitcher(root)
    root.mainloop()


if __name__ == '__main__':
    main()
