# ==============================================================================
# Rubika Self-Bot - Automated Roll-Call & Scheduled Messaging
# Copyright (C) 2026 Open Source Contributors
# Licensed under GNU General Public License v3.0 (GPL-3.0)
# ==============================================================================

import asyncio
import os
import json
import sys
from datetime import datetime, timedelta

# Fix Windows Console UTF-8
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass
    os.system("title Rubika Self-Bot")

# Support for Persian BiDi reshaping in Windows CMD
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False

CONFIG_FILE = "config.json"
SESSION_NAME = "selfbot"

def load_config():
    default_config = {
        "message_text": "سلام، من حاضر هستم",
        "scheduled_time": "08:00/2026/09/27",
        "target_group_title": "",
        "target_group_guid": "",
        "repeat_daily": False,
        "fix_bidi": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_config.update(data)
                return default_config
        except Exception:
            pass
    return default_config

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

def disp(text, config):
    """
    Renders Persian text properly in Windows console.
    Reverses and reshapes characters so they appear in correct reading order in CMD.
    """
    if not text:
        return ""
    text_str = str(text)
    if config.get("fix_bidi", True) and HAS_BIDI:
        if any('\u0600' <= c <= '\u06FF' for c in text_str):
            try:
                reshaped = arabic_reshaper.reshape(text_str)
                return get_display(reshaped)
            except Exception:
                return text_str
    return text_str

def parse_scheduled_time(time_str):
    time_str = time_str.strip()
    now = datetime.now()
    
    # Instant Message Mode
    if time_str == "..":
        return now, False
    
    if "/" in time_str:
        parts = time_str.split("/")
        if len(parts) == 4:
            try:
                time_part = parts[0]
                year_part = int(parts[1])
                month_part = int(parts[2])
                day_part = int(parts[3])
                hour, minute = map(int, time_part.split(":"))
                target_dt = datetime(year_part, month_part, day_part, hour, minute, 0)
                return target_dt, False
            except Exception as e:
                raise ValueError(f"Invalid format! Expected 'HH:MM/YYYY/MM/DD' (e.g. 08:00/2026/09/27). Error: {e}")
        else:
            raise ValueError("Invalid format! Expected 'HH:MM/YYYY/MM/DD' (e.g. 08:00/2026/09/27)")
    elif ":" in time_str:
        try:
            hour, minute = map(int, time_str.split(":"))
            target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_dt <= now:
                target_dt += timedelta(days=1)
            return target_dt, True
        except Exception as e:
            raise ValueError(f"Invalid format! Expected 'HH:MM' (e.g. 08:00). Error: {e}")
    else:
        raise ValueError("Unknown format! Use 'HH:MM/YYYY/MM/DD', 'HH:MM' or '..' for instant message")

def get_countdown_str(delta):
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "Now (0 seconds)"
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} day(s)")
    if hours > 0:
        parts.append(f"{hours} hour(s)")
    if minutes > 0:
        parts.append(f"{minutes} minute(s)")
    parts.append(f"{seconds} second(s)")
    return ", ".join(parts)

def extract_chat_info(chat):
    """Extracts title, guid, and type accurately from Rubika get_chats response"""
    title = ""
    guid = ""
    chat_type = "Group"
    
    abs_obj = getattr(chat, 'abs_object', None)
    if abs_obj:
        title = getattr(abs_obj, 'title', '') or ''
        guid = getattr(abs_obj, 'object_guid', '') or ''
        chat_type = getattr(abs_obj, 'type', 'Group') or 'Group'
        
    if not title and hasattr(chat, 'original_update') and isinstance(chat.original_update, dict):
        orig_abs = chat.original_update.get('abs_object', {})
        if isinstance(orig_abs, dict):
            title = orig_abs.get('title', '')
            guid = orig_abs.get('object_guid', '')
            chat_type = orig_abs.get('type', 'Group')
            
    if not title:
        title = getattr(chat, 'title', '') or ''
    if not guid:
        guid = getattr(chat, 'object_guid', '') or getattr(chat, 'guid', '') or ''
        
    return str(title).strip(), str(guid).strip(), str(chat_type).strip()

async def search_and_select_group(client, config):
    print("\n" + "="*55)
    print("              GROUP SEARCH & SELECTION")
    print("="*55)
    keyword = input("[?] Enter keyword to search in group titles: ").strip()
    if not keyword:
        print("[-] Empty search keyword. Aborted.")
        return

    print(f"[*] Scanning your Rubika dialogs for '{disp(keyword, config)}'...")
    try:
        dialogs = []
        if hasattr(client, 'get_chats'):
            res = await client.get_chats()
            if hasattr(res, 'chats'):
                dialogs = res.chats
            elif isinstance(res, dict) and 'chats' in res:
                dialogs = res['chats']
            elif isinstance(res, list):
                dialogs = res
        elif hasattr(client, 'get_dialogs'):
            res = await client.get_dialogs()
            dialogs = res if isinstance(res, list) else []

        matched_groups = []
        for chat in dialogs:
            title, guid, chat_type = extract_chat_info(chat)
            if title and guid:
                if keyword.lower() in title.lower():
                    matched_groups.append((title, guid, chat_type))

        if not matched_groups:
            print(f"[-] No groups found matching '{disp(keyword, config)}'.")
            return

        print(f"\n[+] Found {len(matched_groups)} matching group(s):")
        for idx, (title, guid, chat_type) in enumerate(matched_groups, start=1):
            display_title = disp(title, config)
            print(f"  [{idx}] [{chat_type}] {display_title}  (GUID: {guid[:8]}...)")

        while True:
            choice = input(f"\n[?] Select number [1-{len(matched_groups)}] (or 'c' to cancel): ").strip()
            if choice.lower() == 'c':
                print("[*] Selection cancelled.")
                return
            if choice.isdigit() and 1 <= int(choice) <= len(matched_groups):
                selected_title, selected_guid, selected_type = matched_groups[int(choice) - 1]
                config["target_group_title"] = selected_title
                config["target_group_guid"] = selected_guid
                save_config(config)
                print(f"[✓] Group selected successfully: '{disp(selected_title, config)}'")
                break
            else:
                print("[-] Invalid number. Please enter a valid number from the list.")

    except Exception as e:
        print(f"[-] Error while searching groups: {e}")

def edit_message(config):
    print("\n" + "="*55)
    print("                 EDIT MESSAGE TEXT")
    print("="*55)
    print(f"[i] Current Message: \"{disp(config.get('message_text', ''), config)}\"")
    new_msg = input("[?] Enter new message text (or press Enter to keep current): ").strip()
    if new_msg:
        config["message_text"] = new_msg
        save_config(config)
        print("[✓] Message updated successfully!")
    else:
        print("[*] Message unchanged.")

async def edit_schedule(client, config):
    print("\n" + "="*55)
    print("              EDIT SCHEDULE (TIME & DATE)")
    print("="*55)
    print("Available Formats:")
    print("  • Specific Date : HH:MM/YYYY/MM/DD (e.g. 08:00/2026/09/27)")
    print("  • Daily Routine : HH:MM (e.g. 08:00)")
    print("  • Instant Send  : .. (Send immediately right now)")
    print(f"[i] Current Scheduled Time: {config.get('scheduled_time', '')}")
    
    new_time = input("[?] Enter target time (or '..' for instant send): ").strip()
    if not new_time:
        print("[*] Schedule unchanged.")
        return
        
    # Instant Message Mode ("..")
    if new_time == "..":
        group_guid = config.get("target_group_guid")
        group_title = config.get("target_group_title")
        msg_text = config.get("message_text")
        
        print("\n" + "-"*50)
        print("          INSTANT MESSAGE CONFIRMATION")
        print("-" * 50)
        print("[⚡] Instant Message Mode Activated ('..')!")
        print(f"[i] Target Group    : {disp(group_title or '(Not set yet!)', config)}")
        print(f"[i] Message Preview : \"{disp(msg_text or '', config)}\"")
        print("[i] Trigger Time    : RIGHT NOW (Immediately)")
        print("-" * 50)
        
        if not group_guid:
            print("[-] Warning: Target group is not set yet! Please select a group in option [3].")
            config["scheduled_time"] = ".."
            config["repeat_daily"] = False
            save_config(config)
            print("[✓] Saved schedule as '..'. Please select target group in option [3].")
            return

        confirm = input("[?] Send this message to the group right now? (y/n): ").strip().lower()
        if confirm == 'y':
            print(f"[*] Sending instant message to '{disp(group_title, config)}'...")
            try:
                await client.send_message(object_guid=group_guid, text=msg_text)
                print(f"[✓] SUCCESS: Instant message sent successfully at {datetime.now().strftime('%H:%M:%S')}!")
            except Exception as e:
                print(f"[-] ERROR sending message: {e}")
            config["scheduled_time"] = ".."
            config["repeat_daily"] = False
            save_config(config)
        else:
            config["scheduled_time"] = ".."
            config["repeat_daily"] = False
            save_config(config)
            print("[✓] Saved schedule as '..' (Instant). You can launch it anytime from option [4].")
        return

    try:
        target_dt, is_daily = parse_scheduled_time(new_time)
        now = datetime.now()
        delta = target_dt - now
        
        print("\n" + "-"*50)
        print("               CONFIRMATION SUMMARY")
        print("-" * 50)
        print(f"[✓] Format is valid!")
        print(f"[i] Configured Time : {new_time}")
        print(f"[i] Target DateTime : {target_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[i] Target Group    : {disp(config.get('target_group_title') or '(Not set yet!)', config)}")
        print(f"[i] Message Preview : \"{disp(config.get('message_text', ''), config)}\"")
        print(f"[i] Time Remaining  : {get_countdown_str(delta)} from now")
        print("-" * 50)
        
        confirm = input("[?] Confirm this schedule? (y/n): ").strip().lower()
        if confirm == 'y':
            config["scheduled_time"] = new_time
            config["repeat_daily"] = is_daily
            save_config(config)
            print("[✓] Schedule updated and saved!")
        else:
            print("[*] Schedule update cancelled.")
    except Exception as e:
        print(f"[-] {e}")

async def run_bot_worker(client, config):
    print("\n" + "="*55)
    print("                 STARTING SELF-BOT")
    print("="*55)
    
    group_guid = config.get("target_group_guid")
    group_title = config.get("target_group_title")
    msg_text = config.get("message_text")
    sched_str = config.get("scheduled_time")
    
    if not group_guid:
        print("[-] Target group is NOT configured! Please select a group in option [3].")
        return
    if not msg_text:
        print("[-] Message text is empty! Please set a message in option [1].")
        return
    if not sched_str:
        print("[-] Scheduled time is not set! Please set time in option [2].")
        return

    # Instant Message Mode
    if sched_str.strip() == "..":
        print(f"[✓] Active Target Group : \"{disp(group_title, config)}\"")
        print(f"[✓] Message to Send     : \"{disp(msg_text, config)}\"")
        print("[⚡] Trigger Mode       : INSTANT DISPATCH ('..')")
        print(f"[*] Sending message immediately to '{disp(group_title, config)}'...")
        try:
            await client.send_message(object_guid=group_guid, text=msg_text)
            print(f"[✓] SUCCESS: Instant message sent successfully at {datetime.now().strftime('%H:%M:%S')}!")
        except Exception as e:
            print(f"[-] ERROR sending message: {e}")
        input("\n[Press Enter to return to main menu...]")
        return

    try:
        target_dt, is_daily = parse_scheduled_time(sched_str)
    except Exception as e:
        print(f"[-] Invalid scheduled time: {e}")
        return

    now = datetime.now()
    delta = target_dt - now
    if delta.total_seconds() < 0 and not is_daily:
        print(f"[-] Configured time {target_dt} has already passed in the past!")
        print("[-] Please update the scheduled time in option [2].")
        return

    print(f"[✓] Active Target Group : \"{disp(group_title, config)}\"")
    print(f"[✓] Message to Send     : \"{disp(msg_text, config)}\"")
    print(f"[✓] Trigger Clock Time  : {target_dt.strftime('%H:%M:%S on %Y/%m/%d')}")
    print(f"[✓] Countdown Remaining : {get_countdown_str(delta)}")
    print("\n[*] Self-Bot is now WAITING for trigger time... (Press Ctrl+C to cancel)\n")

    while True:
        now = datetime.now()
        remaining = (target_dt - now).total_seconds()
        
        if remaining <= 0:
            print(f"\n[!] Trigger time reached: {now.strftime('%H:%M:%S')}")
            print(f"[*] Sending message to '{disp(group_title, config)}'...")
            try:
                await client.send_message(object_guid=group_guid, text=msg_text)
                print(f"[✓] SUCCESS: Message sent successfully at {now.strftime('%H:%M:%S')}!")
            except Exception as e:
                print(f"[-] ERROR sending message: {e}")
                
            if is_daily:
                target_dt += timedelta(days=1)
                print(f"[+] Rescheduling for tomorrow at {target_dt.strftime('%H:%M:%S')}...")
            else:
                print("[*] One-time dispatch completed.")
                break
                
        sleep_chunk = min(remaining, 10)
        if sleep_chunk > 0:
            await asyncio.sleep(sleep_chunk)
            rem_sec = int((target_dt - datetime.now()).total_seconds())
            if rem_sec > 0 and rem_sec % 60 == 0:
                print(f"[i] Clock: {datetime.now().strftime('%H:%M:%S')} | Remaining: {rem_sec // 60} min {rem_sec % 60} sec")

    input("\n[Press Enter to return to main menu...]")

async def main():
    config = load_config()
    
    print("\n" + "="*58)
    print("                RUBIKA SELF-BOT CLIENT")
    print("="*58)
    print(f"[i] System Clock : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        from rubpy import Client
    except ImportError:
        print("[-] 'rubpy' library is not installed.")
        print("[*] Installing requirements automatically...")
        os.system(f'"{sys.executable}" -m pip install -r requirements.txt')
        from rubpy import Client

    client = Client(name=SESSION_NAME)
    
    print("[*] Connecting to Rubika...")
    await client.start()
    print("[✓] Connected successfully! Session active.")

    # Main Interactive Control Panel Loop
    while True:
        now = datetime.now()
        target_display = disp(config.get('target_group_title') or '(Not set yet)', config)
        msg_display = disp(config.get('message_text') or '', config)
        bidi_status = "ON (Windows CMD Fix)" if config.get("fix_bidi", True) else "OFF (Raw Unicode)"
        
        sched_time_val = config.get('scheduled_time') or '(Not set)'
        if str(sched_time_val).strip() == "..":
            sched_display = ".. [⚡ Instant Message]"
        else:
            sched_display = sched_time_val

        print("\n" + "="*58)
        print("            RUBIKA SELF-BOT CONTROL PANEL")
        print("="*58)
        print(f"[i] System Clock     : {now.strftime('%H:%M:%S  %Y/%m/%d')}")
        print(f"[i] Target Group     : {target_display}")
        print(f"[i] Scheduled Time   : {sched_display}")
        print(f"[i] Message Text     : \"{msg_display}\"")
        print("="*58)
        print(" [1] Edit Message Text")
        print(" [2] Edit Schedule (Date/Time or '..' for Instant Send)")
        print(" [3] Search & Select Target Group (Editable anytime)")
        print(" [4] Start Self-Bot (Wait for trigger time and send)")
        print(f" [5] Toggle Persian Display Fix [Current: {bidi_status}]")
        print(" [0] Exit")
        print("="*58)
        
        choice = input("[?] Select an option [0-5]: ").strip()
        
        if choice == "1":
            edit_message(config)
        elif choice == "2":
            await edit_schedule(client, config)
        elif choice == "3":
            await search_and_select_group(client, config)
        elif choice == "4":
            await run_bot_worker(client, config)
        elif choice == "5":
            config["fix_bidi"] = not config.get("fix_bidi", True)
            save_config(config)
            new_status = "ENABLED" if config["fix_bidi"] else "DISABLED"
            print(f"[✓] Persian Console Display Fix is now {new_status}!")
        elif choice == "0":
            print("\n[*] Exiting Self-Bot. Have a great day!")
            break
        else:
            print("[-] Invalid choice. Please enter a number between 0 and 5.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Stopped by user.")
