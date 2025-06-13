# windows_banner.py
import datetime
import random

def generate_banner(username):
    now = datetime.datetime.now()
    version = "10.0.19041.1"
    motd = [
        "WARNING: Unauthorized access to this system is prohibited.",
        "All activities are monitored and recorded.",
        "Violators will be prosecuted to the fullest extent of the law."
    ]

    banner = f"""Microsoft Windows [Version {version}]
(c) 2020 Microsoft Corporation. All rights reserved.

{random.choice(motd)}

C:\\Users\\{username}> """
    return banner
