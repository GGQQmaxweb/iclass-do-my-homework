#!/usr/bin/env python3
import asyncio
import datetime
import io
import os
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from api.auth_module import Authenticator
from api.iclass_api import TronClassAPI
from main import (
    BLACKLIST_COURSES,
    generate_homework_solution,
    submit_homework_solution,
    strip_html,
)

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TMP_DIR = Path("./tmp")
TMP_DIR.mkdir(exist_ok=True)

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)


def format_preview(text: str, max_length: int = 1500) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "\n\n... *(Truncated. See attached .md file for full response)*"


class HomeworkPromptModal(discord.ui.Modal, title="Add Prompt Instructions"):
    custom_prompt = discord.ui.TextInput(
        label="Additional Instructions / Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Enter adjustments (e.g., 'Focus more on section 2', 'Format as bullet points', etc.)",
        required=True,
        max_length=2000,
    )

    def __init__(self, review_view: "HomeworkReviewView"):
        super().__init__()
        self.review_view = review_view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_instructions = self.custom_prompt.value.strip()
        await self.review_view.handle_redo(interaction, user_instructions)


class HomeworkReviewView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        api: TronClassAPI,
        item: dict,
        ai_content: str,
        accumulated_instructions: Optional[str] = None,
        timeout: float = 600.0,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.api = api
        self.item = item
        self.ai_content = ai_content
        self.accumulated_instructions = accumulated_instructions
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You are not allowed to interact with this session.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm & Submit", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Disable buttons while processing
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)

        status_msg = await interaction.followup.send("⏳ Converting to PDF and submitting to TronClass...")

        task_id = self.item["id"]
        title = self.item.get("title", f"Homework #{task_id}")

        success, result_message, pdf_path = await submit_homework_solution(
            api=self.api,
            task_id=task_id,
            ai_content=self.ai_content,
            tmp_dir=TMP_DIR
        )

        embed = discord.Embed(
            title=f"{'✅ Submission Success' if success else '❌ Submission Failed'}: {title}",
            description=result_message,
            color=discord.Color.green() if success else discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        files = []
        if pdf_path and pdf_path.exists():
            files.append(discord.File(str(pdf_path), filename=f"submitted_{task_id}.pdf"))

        await status_msg.edit(content=None, embed=embed, attachments=files)
        self.stop()

    @discord.ui.button(label="Redo / Add to Prompt", style=discord.ButtonStyle.primary, emoji="🔄")
    async def redo(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = HomeworkPromptModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="🚫 Homework submission was cancelled.", embed=None, attachments=[], view=self
        )
        self.stop()

    async def handle_redo(self, interaction: discord.Interaction, new_instruction: str):
        if self.accumulated_instructions:
            self.accumulated_instructions += f"\n- {new_instruction}"
        else:
            self.accumulated_instructions = f"- {new_instruction}"

        # Notify regenerating
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(content="🤖 Regenerating solution with your instructions...", view=self)

        task_id = self.item["id"]
        title = self.item.get("title", f"Homework #{task_id}")
        course_name = self.item.get("course_name", "").strip()

        try:
            new_content = await generate_homework_solution(
                api=self.api,
                item=self.item,
                tmp_dir=TMP_DIR,
                additional_instructions=self.accumulated_instructions,
                interactive_skill=False,
            )
            self.ai_content = new_content

            embed = discord.Embed(
                title=f"📝 AI Solution Preview (Updated): {title}",
                description=format_preview(new_content),
                color=discord.Color.blue(),
            )
            embed.add_field(name="Course", value=course_name or "Unknown", inline=True)
            embed.add_field(name="Task ID", value=str(task_id), inline=True)
            embed.add_field(name="Custom Instructions", value=self.accumulated_instructions[:1000], inline=False)

            file = discord.File(
                io.BytesIO(new_content.encode("utf-8")),
                filename=f"homework_{task_id}.md",
            )

            for child in self.children:
                child.disabled = False

            if self.message:
                await self.message.edit(
                    content=None,
                    embed=embed,
                    attachments=[file],
                    view=self,
                )
        except Exception as e:
            for child in self.children:
                child.disabled = False
            if self.message:
                await self.message.edit(
                    content=f"❌ Regeneration failed: {e}",
                    view=self
                )


class HomeworkSelect(discord.ui.Select):
    def __init__(self, author_id: int, api: TronClassAPI, todos: list[dict]):
        self.author_id = author_id
        self.api = api
        self.todos_map = {str(item["id"]): item for item in todos}

        options = []
        # Discord Select components accept up to 25 items
        for item in todos[:25]:
            task_id = str(item["id"])
            title = item.get("title", "<No Title>")[:95]
            course = item.get("course_name", "<No Course>")[:45]
            due = item.get("end_time", "")
            if due:
                try:
                    due_dt = datetime.datetime.fromisoformat(due.replace("Z", "+00:00"))
                    due_str = due_dt.strftime("%m/%d %H:%M")
                except Exception:
                    due_str = due[:16]
            else:
                due_str = "No due date"

            desc = f"{course} | Due: {due_str}"[:100]
            options.append(
                discord.SelectOption(
                    label=title,
                    description=desc,
                    value=task_id,
                )
            )

        super().__init__(
            placeholder="Select a homework to process...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You are not allowed to select this homework.", ephemeral=True
            )
            return

        selected_id = self.values[0]
        item = self.todos_map.get(selected_id)
        if not item:
            await interaction.response.send_message("❌ Task not found.", ephemeral=True)
            return

        await interaction.response.defer()
        title = item.get("title", f"Homework #{selected_id}")
        course_name = item.get("course_name", "").strip()

        # Update message to show processing
        await interaction.edit_original_response(
            content=f"🤖 Analyzing materials & generating AI solution for **{title}** ({course_name})... Please wait.",
            view=None,
            embed=None,
        )

        try:
            ai_content = await generate_homework_solution(
                api=self.api,
                item=item,
                tmp_dir=TMP_DIR,
                interactive_skill=False,
            )

            embed = discord.Embed(
                title=f"📝 AI Solution Preview: {title}",
                description=format_preview(ai_content),
                color=discord.Color.blue(),
            )
            embed.add_field(name="Course", value=course_name or "Unknown", inline=True)
            embed.add_field(name="Task ID", value=str(selected_id), inline=True)
            embed.set_footer(text="Click 'Confirm & Submit' to submit, or 'Redo' to add instructions.")

            file = discord.File(
                io.BytesIO(ai_content.encode("utf-8")),
                filename=f"homework_{selected_id}.md",
            )

            review_view = HomeworkReviewView(
                author_id=self.author_id,
                api=self.api,
                item=item,
                ai_content=ai_content,
            )
            message = await interaction.edit_original_response(
                content=None,
                embed=embed,
                attachments=[file],
                view=review_view,
            )
            review_view.message = message

        except Exception as e:
            cancel_view = SimpleCancelView(author_id=self.author_id)
            await interaction.edit_original_response(
                content=f"❌ Error generating solution for **{title}**: {e}",
                view=cancel_view,
            )


class SimpleCancelView(discord.ui.View):
    def __init__(self, author_id: int, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You are not allowed to interact with this.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="🚫 Cancelled.", embed=None, attachments=[], view=self
        )
        self.stop()


class HomeworkSelectView(discord.ui.View):
    def __init__(self, author_id: int, api: TronClassAPI, todos: list[dict], timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.add_item(HomeworkSelect(author_id, api, todos))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You are not allowed to use this selection.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="🚫 Homework selection was cancelled.", embed=None, attachments=[], view=self
        )
        self.stop()


async def handle_do_homework(interaction_or_ctx, author: discord.User | discord.Member):
    # Determine how to send progress updates (slash interaction vs prefix context)
    is_interaction = isinstance(interaction_or_ctx, discord.Interaction)

    if is_interaction:
        await interaction_or_ctx.response.defer()
        send_func = interaction_or_ctx.followup.send
    else:
        send_func = interaction_or_ctx.send

    init_msg = await send_func("🔐 Logging into TronClass and fetching homework list...")

    try:
        auth = Authenticator()
        session = await asyncio.to_thread(auth.perform_auth)
        api = TronClassAPI(session, download_dir=TMP_DIR)
        data = await api.get_todos()
    except Exception as e:
        content = f"❌ Failed to fetch TronClass todos: {e}"
        cancel_view = SimpleCancelView(author_id=author.id)
        if is_interaction:
            await interaction_or_ctx.edit_original_response(content=content, view=cancel_view)
        else:
            await init_msg.edit(content=content, view=cancel_view)
        return

    todos = data.get("todo_list", [])
    if not todos:
        content = "🎉 No pending homework tasks found on TronClass!"
        cancel_view = SimpleCancelView(author_id=author.id)
        if is_interaction:
            await interaction_or_ctx.edit_original_response(content=content, view=cancel_view)
        else:
            await init_msg.edit(content=content, view=cancel_view)
        return

    # Filter out blacklisted courses if needed
    active_todos = []
    skipped_count = 0
    for item in todos:
        course_name = item.get("course_name", "").strip()
        if any(blacklisted in course_name for blacklisted in BLACKLIST_COURSES):
            skipped_count += 1
            continue
        active_todos.append(item)

    if not active_todos:
        content = f"ℹ️ All {len(todos)} pending tasks belong to blacklisted courses."
        cancel_view = SimpleCancelView(author_id=author.id)
        if is_interaction:
            await interaction_or_ctx.edit_original_response(content=content, view=cancel_view)
        else:
            await init_msg.edit(content=content, view=cancel_view)
        return

    embed = discord.Embed(
        title="📚 TronClass Homework List",
        description="Select a homework from the dropdown below to generate a solution with AI.",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )

    for idx, item in enumerate(active_todos[:10], start=1):
        task_id = item.get("id")
        title = item.get("title", "<No Title>")
        course = item.get("course_name", "<No Course>")
        due = item.get("end_time", "Unknown")
        embed.add_field(
            name=f"{idx}. {title}",
            value=f"**Course**: {course}\n**Due**: {due}\n**ID**: `{task_id}`",
            inline=False,
        )

    if len(active_todos) > 10:
        embed.set_footer(text=f"Showing 10 of {len(active_todos)} assignments. (Dropdown has up to 25)")

    view = HomeworkSelectView(author_id=author.id, api=api, todos=active_todos)

    if is_interaction:
        await interaction_or_ctx.edit_original_response(content=None, embed=embed, view=view)
    else:
        await init_msg.edit(content=None, embed=embed, view=view)


@bot.tree.command(name="do_homework", description="List TronClass homework, generate AI solution, review & submit.")
async def do_homework_command(interaction: discord.Interaction):
    await handle_do_homework(interaction, interaction.user)


@bot.command(name="do_homework", aliases=["dohomework"])
async def do_homework_prefix(ctx: commands.Context):
    await handle_do_homework(ctx, ctx.author)


@bot.event
async def on_ready():
    print(f"🤖 Bot logged in as {bot.user.name} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} application slash command(s).")
    except Exception as e:
        print(f"⚠ Failed to sync slash commands: {e}")


def run():
    if not DISCORD_BOT_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN is not set in environment or .env file.")
        print("Please set DISCORD_BOT_TOKEN in your .env file.")
        return
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run()
