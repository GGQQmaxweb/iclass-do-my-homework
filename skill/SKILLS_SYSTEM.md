# 🎯 Skill-Based Homework System

## Overview

The system now uses a **skill-based approach** where each course has a customizable strategy file that guides AI homework generation.

## How It Works

```
Course Processing Flow:
┌─────────────────────┐
│ Start homework task │
│ for course "X"      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│ Check for skill_X.md    │
└──────────┬──────────────┘
           │
      ┌────┴────┐
      │          │
     YES        NO
      │          │
      ▼          ▼
   Use it   Create default
   in prompt    template
      │          │
      └────┬─────┘
           │
           ▼
    ┌─────────────────┐
    │ Build AI prompt │
    │ with skill      │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Generate answer │
    │ (customized!)   │
    └─────────────────┘
```

## Key Features

### 1. **Auto-Creation**
On first run with a new course:
```
✨ Created new skill file: ./skills/skill_course_name.md
```

The system creates a template you can customize.

### 2. **Smart Naming**
- Course names are automatically sanitized
- Chinese/CJK characters are **preserved**
- Spaces and special chars → underscores

Examples:
- `人際心理學` → `skill_人際心理學.md`
- `Data Structures` → `skill_data_structures.md`

### 3. **Easy Customization**
Edit `/skills/skill_*.md` files to define:
- Key topics to emphasize
- Writing style preferences
- Formatting requirements  
- Important concepts
- Best practices for that course

### 4. **Automatic Integration**
Skills are automatically loaded and appended to homework prompts, so the AI knows exactly how to approach each course.

## Directory Structure

```
iclass-do-my-homework/
├── skills/
│   ├── README.md                          # Skill documentation
│   ├── skill_人際心理學.md                # Auto-created on first use
│   ├── skill_資安企業實務應用.md           # Pre-made example
│   ├── skill_進階程式設計.md              # Pre-made example
│   ├── skill_interpersonal_psychology.md  # Pre-made example
│   └── ...
├── main.py                                # Updated with skill system
└── ...
```

## Example Skill File

```markdown
# Skill: 進階程式設計

## 核心主題
- 物件導向設計模式
- 並發與多執行緒編程

## 撰寫風格  
- 提供完整的程式碼範例
- 包含時間複雜度分析

## 強調重點
✓ 程式碼品質
✓ 高效率演算法
```

## New Functions Added

### `sanitize_course_name(course_name: str) -> str`
Converts course names to safe filenames while preserving CJK characters.

### `get_skill_path(course_name: str) -> Path`
Returns the path to a skill file for a course.

### `load_skill(course_name: str) -> str`
Loads skill instructions, returns empty string if not found.

### `create_default_skill(course_name: str) -> None`
Automatically creates a template skill file on first use.

## Usage

1. **Run homework processing normally**
   ```bash
   python main.py -u
   ```

2. **First time with new course**
   - System detects new course
   - Creates template skill file in `/skills/`
   - Shows: `✨ Created new skill file: ...`

3. **Customize the skill**
   - Open `/skills/skill_COURSE_NAME.md`
   - Add course-specific instructions
   - Save and re-run

4. **Future runs**
   - Skill is automatically loaded
   - AI uses your custom instructions
   - Results are tailored to the course

## Tips

✅ **DO:**
- Be specific about topics to focus on
- Include formatting preferences
- Reference textbooks or materials
- Update skills as course evolves

❌ **DON'T:**
- Include complete answers
- Make skills too long (stay focused)
- Add unrelated information

## Future Enhancements

Possible additions:
- Skill versioning/history
- Shared skill repository
- Skill rating/effectiveness tracking
- Template library for common subjects
- Multi-skill composition
