# 🤖 AI Skill Update System

## Overview

The system now automatically **analyzes course materials** using AI to suggest skill improvements. This keeps your skills up-to-date and course-relevant.

## How It Works

### 1. Course Material Downloads
When processing homework:
```
🔍 Fetching course info for course_id=123...
📚 Downloading course materials for 進階程式設計...
  📥 Downloading: lecture_notes.pdf...
  📥 Downloading: assignment_rubric.md...
```

Files are:
- Downloaded from course activities
- Stored in `./tmp/course_name/`
- Read and analyzed (first 1000 chars per file)
- Limited to first 3 activities

### 2. AI Analysis
The system analyzes materials and suggests skill updates:

```
💡 AI Skill Suggestions for 進階程式設計:
────────────────────────────────────────────────────
## Key Topics Found
- Object-Oriented Design Patterns
- Concurrency & Threading
- Memory Management

## Suggested Additions
- Add focus on Design Patterns (Factory, Observer, Strategy)
- Emphasize thread-safe code
- Include performance optimization tips

## Important Areas
✓ Code quality over quantity
✓ Efficient algorithms
✓ Proper error handling
────────────────────────────────────────────────────

📝 Update skill file with these suggestions? (y/n):
```

### 3. Interactive Updates
When AI finds suggestions:
- Shows you the suggestions
- Asks if you want to update the skill
- Appends suggestions to the skill file with timestamp
- Shows confirmation

## New Functions

### `async download_course_materials(api, course_info, course_name, tmp_dir) -> str`
Downloads and reads course material files.

**Features:**
- Extracts files from course activities
- Stores in `./tmp/course_name/`
- Limits to text files only
- Caches up to 5KB per file
- Handles download errors gracefully

### `async suggest_skill_update(api, course_name, course_materials) -> str`
Uses AI to analyze materials and suggest skill improvements.

**Input:**
- Current skill content
- Downloaded course materials

**Output:**
- Key topics found
- Suggested skill additions
- Emphasis areas
- Recommended changes

### Updated `build_homework_prompt()`
Now includes:
- Download course materials
- Get AI suggestions
- Interactive update prompt
- Auto-append to skill file

## Directory Structure

```
./tmp/
├── course_name/              # Course materials cache
│   ├── file_1.txt
│   ├── assignment_guide.md
│   └── lecture_slides.pdf
└── auto_submit_123.pdf       # Generated homework

./skills/
├── skill_進階程式設計.md      # Updated with AI suggestions
│
│   ## AI Suggestions (Updated: 2026-06-03)
│   - Found key topics...
└── ...
```

## Usage Example

```
python main.py -u

📝 Processing Boring Homework: Assign 1 (Course: 進階程式設計)
🔍 Fetching course info...
📚 Downloading course materials...
  📥 Downloading: lecture_notes.pdf...
  📥 Downloading: assignment_guide.md...
🤖 Analyzing course materials for skill improvements...

💡 AI Skill Suggestions for 進階程式設計:
────────────────────────────────────────────────────
## Key Topics from Materials
- Design Patterns (Factory, Observer, Strategy)
- Thread-safe Programming
- Memory Optimization

## Recommended Skill Updates
1. Add emphasis on design patterns
2. Include concurrency best practices
3. Focus on performance metrics

────────────────────────────────────────────────────
📝 Update skill file with these suggestions? (y/n): y
✅ Skill file updated: ./skills/skill_進階程式設計.md
```

## Features

✅ **Automatic Detection** - Finds when skills need updating
✅ **AI-Powered** - Uses Gemini to analyze relevance
✅ **Interactive** - User controls when to update
✅ **Non-Destructive** - Appends suggestions, preserves history
✅ **Timestamped** - Tracks when updates were made
✅ **Error Handling** - Graceful failures
✅ **Limited Scope** - Only first 3 activities analyzed
✅ **Text Files Only** - Avoids binary file issues

## Configuration

The system limits:
- **Activities analyzed**: 3 per course
- **File size read**: 5KB per material file
- **Maximum AI prompt**: 2000 chars of materials
- **Storage**: `./tmp/course_name/`

## Error Handling

If download/analysis fails:
- Continues with homework generation
- Shows warning message
- Keeps existing skill unchanged
- Logs error details

## Tips

💡 **Best Practices:**
1. Review AI suggestions before accepting
2. Edit skill files manually for major changes
3. Keep skills focused on key topics
4. Update on major course changes

⚠️ **Limitations:**
- Only text files are analyzed
- Binary files are skipped
- Limited to 3 activities per run
- AI suggestions may be generic

## Privacy

Materials are:
- Downloaded to local `./tmp/` only
- Not sent to external services
- Cached locally during session
- Cleaned up after processing (optional)

## Example AI Suggestion Flow

```
Course Materials (Downloaded):
- lecture_01.md: "Chapter 1-3 covers SOLID principles..."
- assignment.pdf: "Implement factory pattern..."
- rubric.md: "50% design quality, 50% performance..."

AI Analysis:
✓ Detects: factory pattern important
✓ Detects: SOLID principles emphasized
✓ Detects: performance optimization required

Generated Suggestion:
- Add factory pattern emphasis
- Include SOLID principles section
- Add performance testing guidelines
```

This ensures skills evolve with course content!
