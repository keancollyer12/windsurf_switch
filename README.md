# 🚀 Windsurf account switcher

**The ultimate solution to break through the quota limits**

Through multi-account polling and switching, unlimited use.Support **Windows** and **macOS**dual platforms.

>***If you find it useful, please give a Star support!**

---

## � Download and install

###Method 1: Download the executable file directly (recommended)

Go to [Releases page] (https://github.com/keancollyer12/windsurf_switch/releases/ ) download：

| System | Download file |
|------|---------|
| Windows |'Windsurf-Switcher-Windows.zip` |
| macOS |'Windsurf-Switcher-Mac.zip` |

###Method 2: Run from source code

```bash
# Clone warehouse
git clone https://github.com/keancollyer12/windsurf_switch.git
cd winsurf-switch

# macOS run
python3 windsurf_mac.py

# Windows runs
python windsurf_win.py
```

---

## Features

- 🔄** Quick switch between multiple accounts**-Switch saved Windsurf accounts with one click
-*** Account configuration backup**-Full backup of login status, no need to log in repeatedly
-️️**Dual platform support**-Native adaptation for Windows and macOS
-***Graphical interface**-Simple and intuitive GUI operation
-*** Local storage**-Account data is stored locally, safe and reliable

---

## 📋 Usage scenario

When using Windsurf, the official limit is that only a certain number of requests can be sent daily.Through this tool, you can：

1. Register multiple Windsurf accounts
2. Back up the login status of each account to this tool
3. When one account reaches the limit, switch to another account to continue using
4. Implement **Claude 4.5 without waiting for polling use**

---

##️️ Installation and use

### Environmental requirements

-**Python 3.6+**(both Windows and macOS need to be installed)
-**Tkinter**(Python comes with it, no additional installation required)

### macOS usage steps

####Step 1: Backup your account

1. In Windsurf**Manually log in** the first account
2. **Completely close Windsurf** (make sure the process has exited)
3. Run the account switcher：
   ```bash
   python3 windsurf_mac.py
   ```
4. Click the **"Save current account"** button
5. Enter the configuration name (it is recommended to use the mailbox prefix for easy identification)
6. Repeat the above steps to back up all accounts

####Step 2: Switch account

1. **Turn off Windsurf completely**
2. Run the account switcher
3. Select the target account in the list
4. Click the **"Switch account"**button
5. Wait for the prompt to switch successfully
6. Restart Windsurf to use the new account

### Windows usage steps

####Step 1: Backup your account

1. In Windsurf**Manually log in** the first account
2. **Completely close Windsurf** (check the task manager to make sure the process has exited)
3. Run the account switcher：
   ```cmd
   python windsurf_win.py
   ```
4. Click the **"Save current account"** button
5. Enter the configuration name (it is recommended to use the mailbox prefix for easy identification)
6. Repeat the above steps to back up all accounts

####Step 2: Switch account

1. **Turn off Windsurf completely**(make sure there is no Windsurf in the task manager.exe process)
2. Run the account switcher
3. Select the target account in the list
4. Click the **"Switch account"**button
5. Wait for the prompt to switch successfully
6. Restart Windsurf to use the new account

---

##️️ Important notes

### Must log in manually

This tool**does not provide automatic login function**, you need：

1. First complete the login manually in Windsurf
2. Close Windsurf after successful login
3. Use this tool to back up the status of the logged-in account

### Windsurf must be closed

Before performing the **save** or **switch** operation, Windsurf must be completely closed：

-**macOS**: Use`Cmd + Q' to exit, or click force close in the program
-**Windows**: Make sure there is no'windsurf in the task manager.exe' process

If Windsurf is running, the tool will prompt whether to force shutdown.

### Account data security

-The account configuration is saved in the`windsurf_profiles/' directory
-The directory is already in`.Excluded from gitignore` and will not be uploaded to Git
-Please keep this catalog safe and do not disclose it

---

## 📁 Project structure

```
windsurf-switch/
─── windsurf_mac.py # macOS version main program
─── windsurf_win.py # Windows version main program
─── windsurf_profiles / # Account configuration storage directory (automatically created)
─── README.md # Description document
└── .gitignore # Git ignores configuration
```

---

## 🔧Technical principle

This tool realizes account switching by backing up and restoring the following Windsurf data：

| Data type | macOS Path | Windows Path |
|---------|-----------|-------------|
|Authentication status|'~/Library/Application Support/Windsurf/User/GLOBALSTORATION|`/`%APPDATA%\Windsurf\User\globalstoration\`|
| Session | `~/Library/Application Support/Windsurf/Session Storage/` | `%APPDATA%\Windsurf\Session Storage\` |
| Cookies | `~/Library/Application Support/Windsurf/Cookies` | `%APPDATA%\Windsurf\Network\` |
| Codeium | `~/.codeium/windsurf/` | `%USERPROFILE%\.codeium\windsurf\` |

---

## Polling usage recommendations

In order to use the this efficiently, it is recommended：

1. **Prepare 2-3 accounts**-Basically meet the needs of continuous use
2. **Switch in time**-Switch immediately when the prompt reaches the limit
3. **Reasonable planning**-Prioritize important tasks and avoid frequent switching
4. **Record status**-You can mark the purpose of the account in the configuration name

---

## Disclaimer

This tool is for learning and personal use only, please comply with Windsurf's terms of service.The author is not responsible for any abuse.

---

## StarStar support

If this tool helps you, welcome to give a Star as support!
