# Skills Directory

This folder contains **course-specific AI strategies** that customize how homework is generated for each course.

## How It Works

1. **First Run**: When you process homework from a course for the first time, a default skill file is automatically created
   - Named: `skill_COURSENAME.md` (e.g., `skill_data_structures.md`)
   
2. **Customization**: Edit the skill file to define:
   - Key topics and concepts to emphasize
   - Preferred writing style or format
   - Special requirements or preferences
   - Important chapters or resources to reference

3. **Usage**: The skill instructions are automatically added to the AI prompt when generating homework

## Example Skill File

```markdown
# Skill: Database Design

## Focus Areas
- SQL query optimization
- Entity-Relationship Diagrams (ERD)
- Database normalization (1NF, 2NF, 3NF, BCNF)

## Style Guidelines
- Include SQL code examples where relevant
- Use proper database terminology
- Structure answers with clear sections

## Common Topics
- ACID properties
- Transaction management
- Indexing strategies
```

## File Naming

Skills are automatically created with the course name sanitized:
- Spaces → underscores
- Special characters removed
- Converted to lowercase

Example: `"Advanced Programming"` → `skill_advanced_programming.md`

## Tips

✅ **DO:**
- Be specific about what the AI should focus on
- Reference textbooks or course materials
- Include formatting preferences
- Update skills as the course evolves

❌ **DON'T:**
- Give away complete answers
- Include unrelated information
- Make the skill too long (keep it focused)

## Auto-Created Skills

On first use with a new course, a template skill is created that you can edit:

```
✨ Created new skill file: ./skills/skill_course_name.md
```

Just open the file and customize it for that specific course!
