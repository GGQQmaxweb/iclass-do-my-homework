import argparse
import os
import re
import datetime
import asyncio
import json
import mimetypes
import shutil
from pathlib import Path
from dotenv import load_dotenv
from google import genai  # New SDK
from PyPDF2 import PdfReader
from markdown_pdf import MarkdownPdf, Section
import markdown
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Auto submit selected TronClass homework.')
    parser.add_argument(
        '-u', '--homework',
        nargs='*',
        help='Select homework tasks to process by task id or keywords from the title/course name. If omitted after -u, a list will be shown for index selection.',
        metavar='HOMEWORK'
    )
    return parser.parse_args()


def strip_html(text):
    if not text: return ""
    return re.sub('<[^<]+?>', '', text)


def parse_homework_selection(selection: list[str]) -> tuple[set[int], list[str]]:
    ids = set()
    terms = []
    for value in selection:
        normalized = value.strip()
        if normalized.isdigit():
            ids.add(int(normalized))
        elif normalized:
            terms.append(normalized.lower())
    return ids, terms


def select_homework_by_index(todos: list[dict]) -> list[str]:
    if not todos:
        print("No homework found.")
        return []

    print("Available homework tasks:")
    for idx, item in enumerate(todos, start=1):
        print(f"{idx}. {item.get('title', '<no title>')} (Course: {item.get('course_name', '<no course>')})")

    selection = input("Enter indexes separated by spaces or commas: ").strip()
    if not selection:
        print("No selection entered.")
        return []

    selected_ids = []
    for part in re.split(r'[,\s]+', selection):
        if part.isdigit():
            index = int(part)
            if 1 <= index <= len(todos):
                selected_ids.append(str(todos[index - 1].get('id')))
            else:
                print(f"Index {index} is out of range, ignoring.")
        else:
            print(f"Ignoring invalid index '{part}'.")

    return selected_ids


def is_selected_homework(item: dict, selection: list[str]) -> bool:
    if not selection:
        return True

    selected_ids, selected_terms = parse_homework_selection(selection)
    task_id = item.get('id')
    title = str(item.get('title', '')).lower()
    course_name = str(item.get('course_name', '')).lower()

    if task_id is not None and task_id in selected_ids:
        return True

    for term in selected_terms:
        if term in title or term in course_name:
            return True

    return False


def is_text_file(file_path: str) -> bool:
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type.startswith('text/') or mime_type in (
            'application/json',
            'application/xml',
            'application/javascript',
            'application/xhtml+xml'
        )
    return file_path.lower().endswith(('.txt', '.md', '.json', '.csv', '.xml', '.html', '.py', '.js', '.css', '.pdf'))

def read_text_file(file_path: str, max_chars: int = 20000) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(max_chars)
    except Exception:
        return ''

def read_pdf_file(file_path: str, max_chars: int = 20000) -> str:
    try:
        reader = PdfReader(file_path)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
                if sum(len(t) for t in text) >= max_chars:
                    break
        return ''.join(text)[:max_chars]
    except Exception:
        return ''

def extract_file_text(file_path: str, max_chars: int = 20000) -> str:
    if file_path.lower().endswith('.pdf'):
        return read_pdf_file(file_path, max_chars)
    return read_text_file(file_path, max_chars)


def convert_markdown_to_pdf(markdown_text: str, pdf_path: str) -> bool:
    try:
        pdf = MarkdownPdf(toc_level=2)
        pdf.add_section(Section(markdown_text))
        pdf.save(pdf_path)
        
        file_size = os.path.getsize(pdf_path)
        print(f"✅ PDF generated successfully: {pdf_path} ({file_size} bytes)")
        return True
    except Exception as e:
        print(f"⚠ PDF conversion exception: {e}")
        return False


def clean_tmp_dir(tmp_dir: Path) -> None:
    try:
        if tmp_dir.exists() and tmp_dir.is_dir():
            shutil.rmtree(tmp_dir)
    except Exception as e:
        print(f"⚠ Failed to clean tmp directory {tmp_dir}: {e}")


def summarize_course_info(course_info: dict) -> str:
    if not course_info:
        return ''

    data = course_info.get('data') if isinstance(course_info, dict) else course_info
    if isinstance(data, list):
        titles = [str(item.get('title') or item.get('name') or item.get('course_name', 'Unnamed')) for item in data[:5]]
        return f"Course activity list: {len(data)} items. First activities: {', '.join(titles)}."

    if isinstance(data, dict):
        if 'title' in data or 'name' in data:
            title = data.get('title') or data.get('name')
            return f"Course activity info title: {title}."
        keys = ', '.join(data.keys())
        return f"Course activity info keys: {keys}."

    return str(course_info)

def extract_download_references(activity_data: dict) -> list[dict]:
    refs = []
    if not isinstance(activity_data, dict):
        return refs

    possible_lists = []
    for key in ('attachments', 'files', 'resources', 'materials', 'uploads', 'references'):
        value = activity_data.get(key)
        if isinstance(value, list):
            possible_lists.append(value)
        elif isinstance(value, dict):
            possible_lists.append([value])

    for source in possible_lists:
        for item in source:
            if not isinstance(item, dict):
                continue
            if item.get('reference_id'):
                refs.append({'type': 'reference', 'id': item.get('reference_id'), 'name': item.get('name') or item.get('filename')})
            elif item.get('file_id'):
                refs.append({'type': 'file', 'id': item.get('file_id'), 'name': item.get('name') or item.get('filename')})
            elif item.get('id') and item.get('type') == 'file':
                refs.append({'type': 'file', 'id': item.get('id'), 'name': item.get('name') or item.get('filename')})
            elif item.get('id') and any(k in item for k in ('filename', 'name', 'reference_id')):
                refs.append({'type': 'reference', 'id': item.get('id'), 'name': item.get('name') or item.get('filename')})

    return refs

async def download_files_for_activity(api: TronClassAPI, activity_data: dict) -> str:
    references = extract_download_references(activity_data)
    if not references:
        return ''

    downloaded_texts = []
    for ref in references:
        try:
            if ref['type'] == 'reference':
                print(f"📥 Downloading file reference {ref['id']}...")
                file_path = await api.download(ref['id'])  #sym:download
            else:
                print(f"📥 Downloading file id {ref['id']}...")
                file_path = await api.myfiledownload(ref['id'])

            if file_path and os.path.exists(file_path) and is_text_file(file_path):
                text_content = extract_file_text(file_path)
                if text_content:
                    downloaded_texts.append(f"File {os.path.basename(file_path)} content:\n{text_content}")
        except Exception as e:
            print(f"⚠ Failed to download or read attachment {ref.get('id')}: {e}")

    return '\n\n'.join(downloaded_texts)

async def build_homework_prompt(api: TronClassAPI, title: str, course_name: str, task_id: int, course_id: int | None, description: str) -> str:
    course_summary = ''
    print(f"🔍 Fetching course info for course_id={course_id}...")
    if course_id is not None:
        course_info = await api.get_activities(course_id)  #sym:get_activities
        course_summary = summarize_course_info(course_info)

    activity_details = await api.get_activitie(task_id)
    raw_description = activity_details.get('data', {}).get('description', '')
    detailed_description = strip_html(raw_description) or description

    file_context = await download_files_for_activity(api, activity_details.get('data', {}))
    file_section = f"\n\nAdditional file contents:\n{file_context}" if file_context else ''

    prompt_parts = [
        f"Course: {course_name}",
        f"Homework title: {title}",
        f"Course info: {course_summary}",
        f"Homework instruction: {detailed_description}",
    ]

    if file_section:
        prompt_parts.append(file_section)

    prompt_parts.append(
        "Provide a student submission as valid markdown. No emoji, keep answer short, use ZH-TW as main language except for single English words exactly as they appear in the question."
    )

    return '\n\n'.join([part for part in prompt_parts if part])

async def main():
    args = parse_args()
    tmp_dir = Path("./tmp")
    tmp_dir.mkdir(exist_ok=True)

    auth = Authenticator()
    try:
        session = auth.perform_auth()
        api = TronClassAPI(session, download_dir=tmp_dir)
        print("🔓 Authenticated.")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    data = await api.get_todos()
    todos = data.get('todo_list', [])
    now = datetime.datetime.now(datetime.timezone.utc)

    if args.homework is not None and len(args.homework) == 0:
        args.homework = select_homework_by_index(todos)

    if args.homework:
        print(f"🔎 Selected homework filters: {args.homework}")
    elif args.homework is not None:
        print("No homework selected. Exiting.")
        return

    for item in todos:
        if not is_selected_homework(item, args.homework or []):
            continue
        course_name = item.get('course_name', '').strip()
        title = item['title']
        task_id = item['id']

        # 1. Check Blacklist
        if any(blacklisted in course_name for blacklisted in BLACKLIST_COURSES):
            print(f"🛡 Skipping '{title}' - Course '{course_name}' is on the blacklist.")
            continue

        # 2. Check Deadline (skip if user explicitly selected homework via -u)
        end_time_str = item['end_time']
        due_date = datetime.datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        time_remaining = due_date - now

        if (args.homework is not None) or (0 < time_remaining.days <= DUE_SOON_DAYS):
            print(f"\n📝 Processing Boring Homework: {title} (Course: {course_name})")

            course_id = item.get('course_id') or (item.get('course') or {}).get('id')
            raw_desc = item.get('description') or ''
            description = strip_html(raw_desc)

            prompt = await build_homework_prompt(api, title, course_name, task_id, course_id, description)

            try:
                response = client.models.generate_content(
                    model=selected_model_name,
                    contents=prompt
                )
                ai_content = response.text
                print(f"🤖 AI Generated Content:\n{ai_content[:500]}...")  # Print first 500 chars
            except Exception as e:
                print(f"❌ AI Generation failed: {e}")
                continue

            # 5. File Handling & Submission
            markdown_path = tmp_dir / f"auto_submit_{task_id}.md"
            pdf_path = tmp_dir / f"auto_submit_{task_id}.pdf"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(ai_content)

            if not convert_markdown_to_pdf(ai_content, str(pdf_path)):
                print("❌ PDF conversion failed")
                #clean_tmp_dir(tmp_dir)
                tmp_dir.mkdir(exist_ok=True)
                continue

            try:
                print(f"📤 Uploading PDF...")
                upload_id = await api.upload_file(str(pdf_path))

                if upload_id:
                    #success = await api.submit_homework(task_id, [upload_id])
                    #if success:
                    #   print(f"✅ Successfully submitted {title}")
                    pass
                else:
                    print("❌ Failed to get Upload ID.")
            except Exception as e:
                print(f"❌ Submission error: {e}")
            finally:
                #clean_tmp_dir(tmp_dir)
                tmp_dir.mkdir(exist_ok=True)
        else:
            print(f"😴 Skipping '{title}' (Not urgent).")

if __name__ == "__main__":
    asyncio.run(main())
