"""The :help page - every command and every skill, with the parameters each takes."""

from __future__ import annotations

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from ..models import Skill
from ..parse import COMMANDS, format_duration

# Rows that are not colon commands but belong in the same directory.
SHORTCUTS = (
    ("<skill> <duration> [date] [note...]", "log a session - see Logging below"),
    ("d <id>", "open a skill's panel: recent sessions, numbered for :rm and :edit"),
)

DATE_FORMS = "today · yesterday · mon..sun · M/D · YYYY-MM-DD · -N (N days ago)"
# A skill with many metrics wraps its usage rather than squeezing the
# description column to nothing.
USAGE_WIDTH = 48
DURATION_FORMS = "90 · 90m · 1.5h · 1h30 · 1h30m (max 24h)"


def skill_usage(skill: Skill) -> str:
    metrics = "".join(f" [{key}=...]" for key in skill.metrics)
    return f"{skill.id} <duration> [date]{metrics} [note...]"


Section = tuple[str, list[tuple[str, str]]]


def help_sections(skills: list[Skill], default_minutes: int | None) -> list[Section]:
    """(heading, [(what you type, what it does)]) - plain data, so tests can
    check the page's content without rendering it."""
    commands = list(SHORTCUTS) + [(usage, effect) for _, _, usage, effect in COMMANDS.values()]
    logging = [
        ("duration", DURATION_FORMS),
        ("date", DATE_FORMS + " - third word only"),
        ("metric", "key=value, anywhere after the duration, for keys the skill declares"),
    ]
    if default_minutes is not None:
        logging.append(("default", f"a skill name on its own logs {format_duration(default_minutes)}"))
    rows = []
    for skill in sorted(skills, key=lambda s: (s.archived, s.id)):
        bits = [skill.name + (" (archived)" if skill.archived else "")]
        if skill.aliases:
            bits.append("aliases " + ", ".join(skill.aliases))
        bits.append("metrics " + (", ".join(skill.metrics) if skill.metrics else "none - add with :metric"))
        rows.append((skill_usage(skill), "  ·  ".join(bits)))
    if not rows:
        rows.append((":new <id> [display name]", "no skills yet - create one"))
    return [("Commands", commands), ("Logging", logging), ("Skills", rows)]


def render_sections(sections: list[Section]) -> Group:
    """A two-column grid per section, so a long description wraps inside its
    own column instead of back under the usage. Cells go in as Text, not
    str: a str would be read as Rich markup and `[date]` would vanish."""
    width = min(USAGE_WIDTH, max(len(usage) for _, rows in sections for usage, _ in rows))
    parts = []
    for heading, rows in sections:
        grid = Table.grid(padding=(0, 3))
        grid.add_column(style="cyan", width=width, overflow="fold")
        grid.add_column(style="dim")
        for usage, effect in rows:
            grid.add_row(Text(usage), Text(effect))
        parts += [Text(heading, style="bold"), grid, Text("")]
    return Group(*parts)


class HelpScreen(Screen):
    """A separate page rather than a panel: the directory is long, and the
    dashboard underneath is untouched when it closes.

    The scroll area is not focusable, matching the rest of the app; the
    screen's own bindings scroll it instead.
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("q", "app.pop_screen", "back", show=False),
        Binding("up,k", "scroll(-1)", show=False),
        Binding("down,j", "scroll(1)", show=False),
        Binding("pageup", "scroll(-10)", show=False),
        Binding("pagedown,space", "scroll(10)", show=False),
    ]

    def __init__(self, skills: list[Skill], default_minutes: int | None) -> None:
        super().__init__()
        self.sections = help_sections(skills, default_minutes)

    def compose(self) -> ComposeResult:
        yield Static(" help  ·  esc to go back  ·  ↑↓ to scroll", id="help-header")
        body = VerticalScroll(Static(render_sections(self.sections)), id="help-body")
        body.can_focus = False
        yield body

    def action_scroll(self, lines: int) -> None:
        self.query_one("#help-body", VerticalScroll).scroll_relative(y=lines, animate=False)
