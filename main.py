import os
import re
import datetime
import asyncio
from dotenv import load_dotenv
from google import genai  # New SDK
from api.auth_module import Authenticator
from api.iclass_api import TronClassAPI

# --- Configuration ---
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DUE_SOON_DAYS = 1

# 🚫 Add course names here that you want to do manually
BLACKLIST_COURSES = [
    "資安企業實務應用",
    "進階程式設計"
]

# Initialize the new Client
client = genai.Client(api_key=GEMINI_API_KEY)

def get_latest_flash_model():
    """
    Dynamically finds the latest available Flash model using the new SDK.
    """
    try:
        # Fetch available models via the client
        available_models = [
            m.name for m in client.models.list()
        ]

        # Filter for 'flash' models
        flash_models = [m for m in available_models if 'flash' in m.lower()]

        if flash_models:
            # Sort them so 'gemini-2.0-flash' or 'gemini-1.5-flash' comes first
            flash_models.sort(reverse=True)
            latest = flash_models[0]
            print(f"🤖 Dynamic Model Selection: Using {latest}")
            return latest

    except Exception as e:
        print(f"⚠ Could not list models: {e}")

    # Fallback to a stable default
    return 'gemini-2.5-flash'

selected_model_name = get_latest_flash_model()

def strip_html(text):
    if not text: return ""
    return re.sub('<[^<]+?>', '', text)

async def main():
    auth = Authenticator()
    try:
        session = auth.perform_auth()
        api = TronClassAPI(session)
        print("🔓 Authenticated.")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    data = await api.get_todos()
    todos = data.get('todo_list', [])
    now = datetime.datetime.now(datetime.timezone.utc)

    for item in todos:
        course_name = item.get('course_name', '').strip()
        title = item['title']
        task_id = item['id']

        # 1. Check Blacklist
        if any(blacklisted in course_name for blacklisted in BLACKLIST_COURSES):
            print(f"🛡 Skipping '{title}' - Course '{course_name}' is on the blacklist.")
            continue

        # 2. Check Deadline
        end_time_str = item['end_time']
        due_date = datetime.datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        time_remaining = due_date - now

        if 0 < time_remaining.days <= DUE_SOON_DAYS:
            print(f"\n📝 Processing Boring Homework: {title} (Course: {course_name})")

            # 3. Get Details (AWAITED)
            details = await api.get_activitie(task_id)
            raw_desc = details.get('data', {}).get('description', '')
            description = strip_html(raw_desc)

            # 4. AI Generation (New SDK Syntax)
            prompt = f"Assignment: {title}\nInstructions: {description}\n\nProvide a student submission. No markdown, No emoji, keep answer short use ZH-TW as main only if one word use english in question then that word keep as english"
            try:
                response = client.models.generate_content(
                    model=selected_model_name,
                    contents=prompt
                )
                ai_content = response.text
            except Exception as e:
                print(f"❌ AI Generation failed: {e}")
                continue

            # 5. File Handling & Submission
            file_path = f"auto_submit_{task_id}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(ai_content)

            try:
                print(f"📤 Uploading...")
                # Assuming upload_file is also async
                upload_id = await api.upload_file(file_path)

                if upload_id:
                    # Assuming submit_homework is also async
                    success = await api.submit_homework(task_id, [upload_id])
                    if success:
                        print(f"✅ Successfully submitted {title}")
                else:
                    print("❌ Failed to get Upload ID.")
            except Exception as e:
                print(f"❌ Submission error: {e}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        else:
            print(f"😴 Skipping '{title}' (Not urgent).")

if __name__ == "__main__":
    asyncio.run(main())
