# What this is?
An TronClass homework Auto-Submitter

* AI-Powered: Uses Gemini to read homework descriptions and generate high-quality responses.
- Smart Deadlines: Only processes tasks that are "going out of date" (e.g., due within 1 days).
- Course Blacklist: Add your blacklist at BLACKLIST_COURSES = [] at 17 line
- Fully Automated: Includes a systemd timer to run every morning at 8:00 AM. you can change by script
- Isolated Environment: Install script sets up a Python venv to keep your system clean.

# How do you setup this?

get a linux server with systemd and python venv package on it
run the script
```bash
# git clone this project
git clone https://github.com/GGQQmaxweb/iclass-do-my-homework.git
cd iclass-do-my-homework/
# run the install
chmod +x install.sh
./install.sh
```

And editing .env file on the projeck folder
```.env
USERNAMEID="Your Student id"
PASSWORD="Your sso PASSWORD"
GEMINI_API_KEY="Yor GEMINI api key"
```
