# AI Skill Update System - Quick Reference

## What's New

Added **two powerful new async functions** to enhance skill management:

### 1️⃣ `async download_course_materials()`
```python
async def download_course_materials(
    api: TronClassAPI, 
    course_info: dict, 
    course_name: str, 
    tmp_dir: Path
) -> str
```

**What it does:**
- Downloads files from course activities (first 3)
- Reads text content (PDFs, docs, markdown)
- Stores in `./tmp/course_name/`
- Returns summarized content for AI analysis
- Gracefully handles errors

**Example output:**
```
📚 Downloading course materials for 進階程式設計...
  📥 Downloading: lecture_notes.pdf...
  📥 Downloading: assignment_guide.md...
```

### 2️⃣ `async suggest_skill_update()`
```python
async def suggest_skill_update(
    api: TronClassAPI, 
    course_name: str, 
    course_materials: str
) -> str
```

**What it does:**
- Analyzes downloaded course materials
- Compares with existing skill
- Uses AI to suggest improvements
- Returns actionable recommendations

**Example suggestion:**
```
## Key Topics Found
- Design Patterns (Factory, Observer)
- Thread-safe Programming

## Recommended Additions
- Add factory pattern examples
- Include concurrency best practices
```

## Integration Points

### Modified: `build_homework_prompt()`

Now includes:
1. Download course materials
2. Get AI suggestions
3. Show user the suggestions
4. Ask: "Update skill file? (y/n)"
5. Auto-append to skill file if yes

**New parameter:** `tmp_dir: Path`

### Updated: `main()`
Passes `tmp_dir` to `build_homework_prompt()`

## Workflow

```
User runs: python main.py -u

↓

Course detected → Build prompt

↓

Fetch course activities

↓

Download course materials → analyze files

↓

AI suggests skill improvements

↓

Show suggestions to user

↓

User decides: y/n

↓ (if YES)

Append suggestions to skill file with timestamp

↓

Generate homework with updated skill
```

## Files Modified

1. **main.py**
   - Added `download_course_materials()` (async)
   - Added `suggest_skill_update()` (async)
   - Updated `build_homework_prompt()` signature
   - Updated main() call to pass tmp_dir

## Files Created

1. **AI_SKILL_UPDATE.md** - Full documentation
2. **This file** - Quick reference

## Directory Changes

```
./tmp/
├── 進階程式設計/           ← NEW (course materials cache)
│   ├── lecture_notes.pdf
│   └── assignment.md
└── auto_submit_*.pdf
```

## Key Features

✅ **Smart Analysis** - AI understands course content
✅ **User Control** - Interactive approval before changes
✅ **Non-Destructive** - Appends suggestions, keeps history
✅ **Error Resilient** - Continues even if downloads fail
✅ **Timestamp Tracked** - Shows when updates happened
✅ **Scope Limited** - Only first 3 activities per run
✅ **Text-Focused** - Binary files safely skipped

## Usage Example

```bash
$ python main.py -u

📝 Processing: Assignment 1 (Course: 進階程式設計)

🔍 Fetching course info...

📚 Downloading course materials for 進階程式設計...
  📥 Downloading: lecture_notes.pdf...
  📥 Downloading: programming_guide.md...

🤖 Analyzing course materials for skill improvements...

💡 AI Skill Suggestions for 進階程式設計:
────────────────────────────────────────────────────
Key Topics:
- Design Patterns
- Memory Management
- Thread Safety

Recommendations:
- Add design pattern examples
- Include memory profiling tips
- Emphasize thread-safe practices
────────────────────────────────────────────────────

📝 Update skill file with these suggestions? (y/n): y
✅ Skill file updated: ./skills/skill_進階程式設計.md

🤖 AI Generated Content:
```

## Configuration

These are built-in limits (can be adjusted):
- **Max activities**: 3 per course
- **Max file read**: 5KB per material
- **Max prompt**: 2000 chars for AI analysis

## Error Handling

If something fails:
```
⚠ Failed to download lecture.pdf: [error details]
```
→ System continues with homework generation
→ Existing skill remains unchanged
→ No blocking errors

## Next Steps

1. Run the system normally: `python main.py -u`
2. On first course encounter, see AI suggestions
3. Review and approve suggested updates
4. Skills evolve automatically with course content!

## Technical Notes

- Both functions are **async** (non-blocking)
- Files downloaded to `./tmp/course_name/`
- Text extraction uses existing `extract_file_text()`
- AI uses current `selected_model_name` (Gemini Flash)
- Suggestions appended with date timestamp

---

**Status:** ✅ Complete and tested
**Syntax:** ✅ Valid Python
**Ready to use:** ✅ Yes
