# What this is?
An TronClass homework Auto-Submitter

* AI-Powered: Uses Gemini to read homework descriptions and generate high-quality responses.
- Smart Deadlines: Only processes tasks that are "going out of date" (e.g., due within 1 days).
- Course Blacklist: Add your blacklist at BLACKLIST_COURSES = [] at 17 line
- Fully Automated: Includes a systemd timer to run every morning at 8:00 AM. you can change by script
- Isolated Environment: Install script sets up a Python venv to keep your system clean.

# How do you setup this?

get a linux server with systemd and python venv package on it. And run the follow command.
```bash
# git clone this project
git clone https://github.com/GGQQmaxweb/iclass-do-my-homework.git
cd iclass-do-my-homework/
# run the install
chmod +x install.sh
./install.sh
```

And editing .env file on the project folder
```.env
USERNAMEID="Your Student id"
PASSWORD="Your sso PASSWORD"
GEMINI_API_KEY="Yor GEMINI api key"
DISCORD_BOT_TOKEN="Your Discord Bot Token"
```

# Discord Bot

You can also interact with your TronClass homework through Discord!

### Run the Bot
```bash
source .venv/bin/activate
python bot.py
```

### Discord Commands
- `/do_homework`: Fetches your pending TronClass homework list and presents an interactive dropdown.
  1. **Select Homework**: Pick an assignment from the dropdown menu.
  2. **Review AI Generation**: Inspect the generated solution preview or download the attached markdown.
  3. **Refine / Redo**: Click **Redo / Add to Prompt** to give additional prompt instructions via a modal.
  4. **Confirm & Submit**: Click **Confirm & Submit** to convert the markdown to PDF, upload it to TronClass, and submit the homework automatically.

### Run as a systemd Service (Background Daemon)
To keep the bot running 24/7 in the background:

```bash
# 1. Copy the service file
sudo cp tronclass-bot.service /etc/systemd/system/

# 2. Reload systemd daemon
sudo systemctl daemon-reload

# 3. Enable and start the bot service
sudo systemctl enable --now tronclass-bot.service

# 4. Check status or logs
sudo systemctl status tronclass-bot.service
journalctl -u tronclass-bot.service -f
```


