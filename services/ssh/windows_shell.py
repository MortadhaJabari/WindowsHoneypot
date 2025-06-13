import random

class WindowsShell:
    def __init__(self, users=None):
        self.base_dir = "C:\\Users"
        self.users = users or []
        self.current_user = self.get_valid_usernames()[0] if self.get_valid_usernames() else "Default"
        self.current_dir = f"{self.base_dir}\\{self.current_user}"
        self.fake_fs = self._init_fake_fs()

    def _init_fake_fs(self):
        """
        Initializes a fake file system structure for each user.
        """
        # Each user gets their own directories and files
        fs = {}
        for user in self.get_valid_usernames():
            user_dir = f"{self.base_dir}\\{user}"
            fs[user_dir] = ["Documents", "Downloads", "Desktop", "Secrets"]
            fs[f"{user_dir}\\Documents"] = ["notes.txt"]
            fs[f"{user_dir}\\Downloads"] = ["readme.txt"]
            fs[f"{user_dir}\\Desktop"] = ["passwords.docx"]
            fs[f"{user_dir}\\Secrets"] = ["secret.txt"]
        return fs

    def get_valid_usernames(self):
        if self.users:
            return [user['username'] for user in self.users]
        # fallback to default users if not provided
        return ["Administrator", "Guest", "Default", "John", "Alice"]

    def handle_command(self, username, command):
        """
        Simulates a Windows shell command. Supported commands:

        - exit, logout: End the session.
        - cd <dir>: Change directory (supports Documents, Downloads, Desktop, Secrets, .., .)
        - dir: List files in the current directory.
        - cls: Clear the screen.
        - whoami: Show the current user (domain\\username).
        - hostname: Show the computer name.
        - net user: List all user accounts (from config or defaults).
        - net user <username>: Show details for a user (case-insensitive, from config or defaults).
        - type <filename>: Show contents of a file (only certain fake files supported).
        - ipconfig: Show fake network configuration.
        - systeminfo: Show fake system information.
        - ver: Show Windows version.
        - powershell: Simulate entering PowerShell prompt.
        - <anything else>: Returns a Windows-style error for unrecognized commands.
        """
        cmd = command.strip().lower()
        self.current_user = username

        # If the user just presses enter, return an empty string (no error)
        if cmd == "":
            return ""

        # Built-in commands
        if cmd in ["exit", "logout"]:
            return "__exit__"

        elif cmd.startswith("cd "):
            return self.change_directory(username, command[3:].strip())

        elif cmd.startswith("dir"):
            return self.fake_dir_listing()

        elif cmd == "cls":
            return "\n" * 50

        elif cmd == "whoami":
            return f"domain\\{username}"

        elif cmd == "hostname":
            return "DC01"

        elif cmd == "net user":
            user_list = "  ".join(self.get_valid_usernames())
            return (
                f"User accounts for \\DC01\n"
                "---------------------------------------------------\n"
                f"{user_list}\n\n"
                "The command completed successfully."
            )

        elif cmd.startswith("net user "):
            user_input = cmd.split("net user ", 1)[1].strip()
            # Find the actual username from config, case-insensitive match
            valid_users = self.get_valid_usernames()
            matched_user = next((u for u in valid_users if u.lower() == user_input.lower()), None)
            if matched_user:
                return (
                    f"User name                    {matched_user}\n"
                    f"Full Name                    {matched_user.capitalize()} User\n"
                    "Account active               Yes\n"
                    "Account expires              Never\n"
                    "Password last set            1/1/2025 10:00 AM\n"
                    "Password expires             Never\n"
                    "Password changeable          1/1/2025 10:00 AM\n"
                    "Password required            Yes\n"
                    "User may change password     Yes\n"
                    "\nThe command completed successfully."
                )
            else:
                return f"The user name could not be found: {user_input}"

        elif cmd == "type secret.txt":
            return "Access is denied."

        elif cmd.startswith("type "):
            filename = cmd.split("type ", 1)[1].strip()
            fake_files = {
                "passwords.docx": "This file is binary and cannot be displayed.",
                "notes.txt": "Remember to update the honeypot logs.",
                "readme.txt": "Welcome to the WindowsServerHoneypot!",
            }
            return fake_files.get(filename, f"The system cannot find the file specified: {filename}")

        elif cmd == "ipconfig":
            return (
                "Windows IP Configuration\n\n"
                "Ethernet adapter Ethernet:\n"
                "   Connection-specific DNS Suffix  . : localdomain\n"
                "   IPv4 Address. . . . . . . . . . . : 192.168.1.100\n"
                "   Subnet Mask . . . . . . . . . . . : 255.255.255.0\n"
                "   Default Gateway . . . . . . . . . : 192.168.1.1"
            )

        elif cmd == "systeminfo":
            return (
                "Host Name:                 DC01\n"
                "OS Name:                   Microsoft Windows Server 2019 Standard\n"
                "OS Version:                10.0.17763 N/A Build 17763\n"
                "OS Manufacturer:           Microsoft Corporation\n"
                "OS Configuration:          Standalone Server\n"
                "OS Build Type:             Multiprocessor Free\n"
                "Registered Owner:          Windows User\n"
                "Registered Organization:   Contoso\n"
                "Product ID:                12345-67890-ABCDE-FGHIJ\n"
                "Original Install Date:     1/1/2025, 9:00:00 AM\n"
                "System Boot Time:          6/12/2025, 8:00:00 AM\n"
                "System Manufacturer:       Dell Inc.\n"
                "System Model:              PowerEdge T40\n"
                "System Type:               x64-based PC\n"
                "Processor(s):              1 Processor(s) Installed.\n"
                "                           [01]: Intel64 Family 6 Model 85 Stepping 7 GenuineIntel ~2200 Mhz\n"
                "BIOS Version:              Dell Inc. 1.0.0, 12/01/2024\n"
                "Windows Directory:         C:\\Windows\n"
                "System Directory:          C:\\Windows\\system32\n"
                "Boot Device:               \\Device\\HarddiskVolume1\n"
                "System Locale:             en-us;English (United States)\n"
                "Time Zone:                 (UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna\n"
                "Total Physical Memory:     8,192 MB\n"
                "Available Physical Memory: 6,000 MB\n"
                "Virtual Memory: Max Size:  9,216 MB\n"
                "Virtual Memory: Available: 7,000 MB\n"
                "Virtual Memory: In Use:    2,216 MB\n"
                "Page File Location(s):     C:\\pagefile.sys\n"
                "Domain:                    CONTOSO\n"
                "Logon Server:              \\DC01\n"
                "Hotfix(s):                 5 Hotfix(s) Installed.\n"
                "Network Card(s):           1 NIC(s) Installed.\n"
                "                           [01]: Intel(R) Ethernet Connection\n"
            )

        elif cmd == "ver":
            return "Microsoft Windows [Version 10.0.17763.1]"

        elif cmd.startswith("powershell"):
            return (
                "Windows PowerShell\n"
                "Copyright (C) Microsoft Corporation. All rights reserved.\n\n"
                f"PS {self.current_dir}>"
            )

        else:
            return f"'{command}' is not recognized as an internal or external command, operable program or batch file."

    def change_directory(self, username, path):
        """
        Simulates the 'cd' command.
        Usage:
            cd <dir>      # Change to a fake directory (Documents, Downloads, Desktop, Secrets)
            cd ..         # Go up one directory
            cd . or cd    # Stay in the current directory
        Returns an error if the directory does not exist.
        """
        # Always use the username provided for the base path
        user_base = f"{self.base_dir}\\{username}"
        if self.current_dir.startswith(user_base):
            base = user_base
        else:
            base = user_base
            self.current_dir = base
        if path in [".", ""]:
            return ""
        elif path == "..":
            if self.current_dir != base:
                self.current_dir = self.current_dir.rsplit("\\", 1)[0]
            return ""
        else:
            # Check if the directory exists in the fake file system
            target = f"{self.current_dir}\\{path}"
            if target in self.fake_fs:
                self.current_dir = target
                return ""
            elif path in self.fake_fs.get(self.current_dir, []):
                self.current_dir = f"{self.current_dir}\\{path}"
                return ""
            else:
                return f"The system cannot find the path specified: {path}"

    def fake_dir_listing(self):
        """
        Simulates the 'dir' command.
        Lists a static set of fake files in the current directory.
        """
        # List directories and files for the current directory
        entries = self.fake_fs.get(self.current_dir, [])
        files = []
        dirs = []
        for entry in entries:
            if entry.endswith('.txt') or entry.endswith('.docx'):
                files.append(entry)
            else:
                dirs.append(entry)
        header = (
            " Volume in drive C has no label.\n"
            " Volume Serial Number is {:04X}-{:04X}\n\n"
            " Directory of {}\n\n".format(random.randint(0, 0xFFFF), random.randint(0, 0xFFFF), self.current_dir)
        )
        listing = ""
        for d in dirs:
            listing += f"{random.choice(['01/06/2025', '02/06/2025'])}  09:00 AM    <DIR>          {d}\n"
        for f in files:
            listing += f"{random.choice(['01/06/2025', '02/06/2025'])}  09:15 AM               {random.randint(100,2048):<12} {f}\n"
        footer = (
            f"               {len(files)} File(s)        {sum([random.randint(100,2048) for _ in files])} bytes\n"
            f"               {len(dirs)} Dir(s)  14,348,484,608 bytes free"
        )
        return header + listing + footer
