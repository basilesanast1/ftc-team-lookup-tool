#!/usr/bin/env python3
"""Menu-driven FIRST Tech Challenge team lookup with a rich terminal UI."""

import base64
import datetime
import json
import os
import time
from pathlib import Path

import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

API_BASE = "https://ftc-api.firstinspires.org/v2.0"
CREDENTIALS_PATH = Path(__file__).resolve().parent / "ftc_credentials.json"

console = Console()


# ---------- Credentials ----------

def load_credentials() -> tuple[str | None, str | None]:
    """Return (username, token) from the credentials file, or (None, None)."""
    if not CREDENTIALS_PATH.exists():
        return None, None
    try:
        data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        console.print(f"[yellow]Could not read {CREDENTIALS_PATH.name}. Please enter credentials again.[/]")
        return None, None
    user = (data.get("username") or "").strip()
    token = (data.get("token") or "").strip()
    return (user, token) if user and token else (None, None)


def save_credentials(user: str, token: str) -> None:
    """Write the credentials file, creating it if it doesn't exist."""
    CREDENTIALS_PATH.write_text(
        json.dumps({"username": user, "token": token}, indent=2), encoding="utf-8"
    )
    try:
        os.chmod(CREDENTIALS_PATH, 0o600)  # readable only by your user account
    except OSError:
        pass  # Windows ignores chmod


def prompt_credentials() -> tuple[str, str]:
    """Ask for credentials and save them to the credentials file."""
    console.print()
    console.print(Panel(
        "Enter your FTC Events API credentials.\n"
        "[dim]Get them at https://ftc-events.firstinspires.org/services/API[/]",
        title="[bold]Credentials[/]", border_style="yellow", box=box.ROUNDED,
    ))
    user = Prompt.ask("  [cyan]Username[/]").strip()
    token = Prompt.ask("  [cyan]API token[/]", password=True).strip()
    save_credentials(user, token)
    console.print(f"[green]✓ Saved to {CREDENTIALS_PATH.name}[/]")
    return user, token


# ---------- API client ----------

class FTCClient:
    def __init__(self, user: str, token: str):
        creds = base64.b64encode(f"{user}:{token}".encode()).decode()
        self.headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}

    def _get(self, path: str, params: dict | None = None, retries: int = 3) -> dict:
        for attempt in range(retries):
            resp = requests.get(f"{API_BASE}/{path}", headers=self.headers,
                                params=params, timeout=30)
            if resp.status_code in (502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt)  # wait 1s, then 2s
                continue
            if resp.status_code == 401:
                raise PermissionError("Authentication failed. Update your credentials (option 5).")
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("Request failed after retries.")

    def team(self, number: int, season: int) -> dict | None:
        teams = self._get(f"{season}/teams", {"teamNumber": number}).get("teams", [])
        return teams[0] if teams else None

    def awards(self, number: int, season: int) -> list[dict]:
        try:
            data = self._get(f"{season}/awards/{number}")
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return []  # no awards recorded for this team in this season
            raise
        return data.get("awards") or []

    def events(self, number: int, season: int) -> list[dict]:
        try:
            data = self._get(f"{season}/events", {"teamNumber": number})
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return []  # no events recorded for this team in this season
            raise
        return data.get("events") or []


# ---------- Helpers ----------

def default_season() -> int:
    today = datetime.date.today()
    return today.year if today.month >= 8 else today.year - 1


def season_label(season: int) -> str:
    return f"{season}-{str(season + 1)[-2:]}"


def location_of(team: dict) -> str:
    parts = [team.get("city"), team.get("stateProv"), team.get("country")]
    return ", ".join(str(p) for p in parts if p) or "—"


def award_label(award: dict) -> str:
    return award.get("name") or award.get("awardName") or "Award"


def event_label(award: dict) -> str:
    return award.get("eventName") or award.get("eventCode") or "—"


# ---------- Display ----------

def banner() -> None:
    title = Text("FTC TEAM LOOKUP", style="bold cyan", justify="center")
    subtitle = Text("FIRST Tech Challenge team info, awards, and history", style="dim", justify="center")
    console.print(Panel(Text.assemble(title, "\n", subtitle), box=box.DOUBLE, border_style="cyan", padding=(1, 4)))


def print_menu(season: int) -> None:
    menu = Table.grid(padding=(0, 2))
    menu.add_column(style="bold yellow", justify="right")
    menu.add_column()
    menu.add_row("1", "Look up a team")
    menu.add_row("2", "Team summary")
    menu.add_row("3", "Full award list")
    menu.add_row("4", "Change season")
    menu.add_row("5", "Update credentials")
    menu.add_row("6", "Quit")
    console.print(Panel(
        menu,
        title="[bold]Menu[/]",
        subtitle=f"[dim]Season {season_label(season)}[/]",
        border_style="blue", box=box.ROUNDED,
    ))


def print_team(team: dict, season: int) -> None:
    short_name = team.get("nameShort") or "—"
    full_name = team.get("nameFull") or "—"

    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold cyan", justify="right")
    info.add_column(overflow="fold", max_width=60)
    info.add_row("Name", Text(short_name, style="bold green"))
    info.add_row("School", Text(full_name))
    info.add_row("Location", location_of(team))
    info.add_row("Rookie year", str(team.get("rookieYear") or "—"))
    info.add_row("Website", team.get("website") or "—")
    info.add_row("Season", season_label(season))

    console.print(Panel(
        info,
        title=f"[bold]Team {team.get('teamNumber')}[/]",
        border_style="green", box=box.ROUNDED,
    ))


def print_awards(awards: list[dict], heading: str, season: int) -> None:
    if not awards:
        console.print(f"  [dim]{heading}: none[/]")
        return
    table = Table(
        title=f"{heading} ({len(awards)})", title_justify="left",
        header_style="bold magenta", border_style="magenta",
        box=box.SIMPLE_HEAVY, expand=True,
    )
    table.add_column("Season", style="cyan", no_wrap=True)
    table.add_column("Award", style="bold", overflow="fold")
    table.add_column("Event", style="dim", overflow="fold")
    for award in awards:
        table.add_row(season_label(season), award_label(award), event_label(award))
    console.print(table)


def print_full_award_list(rows: list[tuple[int, dict]], number: int) -> None:
    if not rows:
        console.print("[dim]No awards recorded in any season.[/]")
        return
    table = Table(
        title=f"All awards for team {number} ({len(rows)})", title_justify="left",
        header_style="bold magenta", border_style="magenta",
        box=box.SIMPLE_HEAVY, expand=True,
    )
    table.add_column("Season", style="cyan", no_wrap=True)
    table.add_column("Award", style="bold", overflow="fold")
    table.add_column("Event", style="dim", overflow="fold")
    for yr, award in rows:
        table.add_row(season_label(yr), award_label(award), event_label(award))
    console.print(table)


def print_summary(number: int, awards_by_season: dict[int, list[dict]], events_total: int) -> None:
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold cyan", justify="right")
    summary.add_column()
    summary.add_row("Events participated", str(events_total))

    console.print(Panel(
        summary,
        title=f"[bold]Summary: Team {number}[/]",
        border_style="green", box=box.ROUNDED,
    ))

    table = Table(
        title="Awards per season", title_justify="left",
        header_style="bold magenta", border_style="magenta",
        box=box.SIMPLE_HEAVY, expand=True,
    )
    table.add_column("Season", style="cyan")
    table.add_column("Awards", justify="right")
    for yr in sorted(awards_by_season):
        table.add_row(season_label(yr), str(len(awards_by_season[yr])))
    console.print(table)


def show_error(message: str) -> None:
    console.print(f"[bold red]✗ {message}[/]")


# ---------- Menu actions ----------

def view_team(client: FTCClient, season: int) -> None:
    number = IntPrompt.ask("  [cyan]Team number[/]")
    with console.status("[cyan]Fetching team...[/]"):
        team = client.team(number, season)
    if team is None:
        show_error(f"No team {number} found for the {season_label(season)} season.")
        return

    print_team(team, season)
    with console.status("[cyan]Fetching awards...[/]"):
        awards = client.awards(number, season)
    print_awards(awards, f"Awards in {season_label(season)}", season)


def team_summary(client: FTCClient, season: int) -> None:
    number = IntPrompt.ask("  [cyan]Team number[/]")
    with console.status("[cyan]Fetching team...[/]"):
        team = client.team(number, season)
    if team is None:
        show_error(f"No team {number} found for the {season_label(season)} season.")
        return

    rookie = int(team.get("rookieYear") or season)
    awards_by_season: dict[int, list[dict]] = {}
    events_total = 0

    with console.status("[cyan]Building summary...[/]"):
        for yr in range(rookie, season + 1):
            awards_by_season[yr] = client.awards(number, yr)
            events_total += len(client.events(number, yr))

    print_summary(number, awards_by_season, events_total)


def award_list(client: FTCClient, season: int) -> None:
    number = IntPrompt.ask("  [cyan]Team number[/]")
    with console.status("[cyan]Fetching team...[/]"):
        team = client.team(number, season)
    if team is None:
        show_error(f"No team {number} found for the {season_label(season)} season.")
        return

    rookie = int(team.get("rookieYear") or season)
    rows: list[tuple[int, dict]] = []
    with console.status("[cyan]Collecting awards...[/]"):
        for yr in range(rookie, season + 1):
            rows.extend((yr, award) for award in client.awards(number, yr))

    print_full_award_list(rows, number)


def change_season(current: int) -> int:
    console.print(f"  [dim]Current season: {season_label(current)}[/]")
    return IntPrompt.ask("  [cyan]Season start year (e.g. 2025)[/]", default=current)


# ---------- Main ----------

def main() -> None:
    console.clear()
    banner()

    user, token = load_credentials()
    if not user or not token:
        console.print(f"[yellow]No saved credentials. Creating {CREDENTIALS_PATH.name}.[/]")
        user, token = prompt_credentials()
    client = FTCClient(user, token)
    season = default_season()

    while True:
        console.print()
        print_menu(season)
        choice = Prompt.ask("[bold]Select an option[/]", choices=["1", "2", "3", "4", "5", "6"],
                            show_choices=False)
        console.print()
        try:
            if choice == "1":
                view_team(client, season)
            elif choice == "2":
                team_summary(client, season)
            elif choice == "3":
                award_list(client, season)
            elif choice == "4":
                season = change_season(season)
                console.print(f"[green]✓ Season set to {season_label(season)}[/]")
            elif choice == "5":
                user, token = prompt_credentials()
                client = FTCClient(user, token)
            elif choice == "6":
                console.print("[dim]Goodbye.[/]")
                break
        except PermissionError as exc:
            show_error(str(exc))
        except requests.RequestException as exc:
            show_error(f"Network or API error: {exc}")
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye.[/]")
            break


if __name__ == "__main__":
    main()