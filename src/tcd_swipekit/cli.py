"""Command-line interface for TCD-Swipekit (`swipekit` / `tcd-swipekit`)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from tcd_swipekit import __version__
from tcd_swipekit.models import AspectRatio, CoverMode, CreatorProfile, Language, WatermarkPosition
from tcd_swipekit.pipeline import (
    generate_github_deck,
    generate_website_deck,
    parse_ratios,
    render_deck_file,
)
from tcd_swipekit.profile import GLOBAL_PROFILE_PATHS, STARTER_PROFILE_YAML, load_profile
from tcd_swipekit.skill_installer import get_bundled_skill_dir, install_skill
from tcd_swipekit.themes.loader import list_presets, load_theme

app = typer.Typer(
    name="swipekit",
    help="TCD-Swipekit — Generate modern photo-slide carousels from GitHub repos & websites.",
    no_args_is_help=True,
)
generate_app = typer.Typer(help="Generate a carousel deck from a content source.", no_args_is_help=True)
skill_app = typer.Typer(help="Install or inspect the TCD-Swipekit AI Agent Skill.", no_args_is_help=True)
app.add_typer(generate_app, name="generate")
app.add_typer(skill_app, name="skill")

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold green]TCD-Swipekit[/bold green] v{__version__}")
        raise typer.Exit()


def _resolve_cli_profile(
    profile_path: Path | None,
    no_profile: bool,
) -> tuple[CreatorProfile | None, Path | None]:
    try:
        return load_profile(explicit_path=profile_path, enabled=not no_profile)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Profile error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _resolve_cli_ratios(ratios_raw: str | None) -> list[AspectRatio] | None:
    try:
        return parse_ratios(ratios_raw)
    except ValueError as exc:
        console.print(f"[bold red]Invalid --ratios:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _print_render_summary(topic: str, paths: list[Path], output: Path, multi_ratio: bool, pdf: bool) -> None:
    console.print(f"\n[bold green]Done![/bold green] Rendered [bold]{len(paths)}[/bold] slides for [cyan]{topic}[/cyan]:")
    for p in paths:
        console.print(f"  • {p}")
    if not multi_ratio:
        console.print(f"  • Caption: {output / 'caption.md'}")
        console.print(f"  • Preview: {output / 'preview.html'}")
        if pdf and (output / "carousel.pdf").is_file():
            console.print(f"  • PDF:     {output / 'carousel.pdf'}")


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """TCD-Swipekit CLI."""


@generate_app.command("github")
def generate_github(
    topic: Annotated[str | None, typer.Option("--topic", "-t", help="Topic or keyword filter (e.g., 'ai', 'devtools').")] = None,
    repos: Annotated[list[str] | None, typer.Option("--repo", "-r", help="Explicit owner/repo slugs (repeatable).")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=15, help="Number of repository slides.")] = 6,
    since: Annotated[str, typer.Option("--since", help="GitHub trending range: daily, weekly, monthly.")] = "weekly",
    prog_lang: Annotated[str | None, typer.Option("--prog-lang", help="Filter by programming language (e.g., python).")] = None,
    lang: Annotated[Language | None, typer.Option("--lang", help="Content language: en (default) or id.")] = None,
    ratio: Annotated[AspectRatio | None, typer.Option("--ratio", help="Single aspect ratio: 3:4, 4:5, 9:16, 1:1.")] = None,
    ratios: Annotated[str | None, typer.Option("--ratios", help="Multi-ratio batch export, e.g. '3:4,4:5,1:1' or 'all'.")] = None,
    part: Annotated[int, typer.Option("--part", help="Series part number on cover badge.")] = 1,
    theme: Annotated[str | None, typer.Option("--theme", help="Preset name or path to custom .yaml theme.")] = None,
    accent: Annotated[str | None, typer.Option("--accent", help="Override theme accent hex color (e.g. #38BDF8).")] = None,
    watermark: Annotated[str | None, typer.Option("--watermark", "-w", help="Creator watermark handle (e.g. @yourhandle).")] = None,
    watermark_pos: Annotated[WatermarkPosition | None, typer.Option("--watermark-pos", help="Watermark position.")] = None,
    cover_mode: Annotated[CoverMode | None, typer.Option("--cover-mode", help="Cover mode: photo, gradient, minimal.")] = None,
    cover_image: Annotated[Path | None, typer.Option("--cover-image", help="Custom cover background photo path.")] = None,
    cover_badge: Annotated[str | None, typer.Option("--cover-badge", help="Custom cover badge pill text.")] = None,
    cover_cta: Annotated[str | None, typer.Option("--cover-cta", help="Custom cover CTA button text.")] = None,
    outro: Annotated[bool | None, typer.Option("--outro/--no-outro", help="Include or disable a closing Save/Follow CTA slide.")] = None,
    pdf: Annotated[bool | None, typer.Option("--pdf/--no-pdf", help="Also export combined carousel.pdf (great for LinkedIn).")] = None,
    profile: Annotated[Path | None, typer.Option("--profile", help="Path to custom Creator Brand Profile YAML.")] = None,
    no_profile: Annotated[bool, typer.Option("--no-profile", help="Ignore local/global Creator Brand Profile.")] = False,
    ai: Annotated[bool, typer.Option("--ai", help="Polish descriptions with OpenAI-compatible LLM.")] = False,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory for PNG slides.")] = Path("./output/github_deck"),
) -> None:
    """Generate a photo-slide carousel from GitHub trending or topic-matched repositories."""
    loaded_profile, profile_path = _resolve_cli_profile(profile, no_profile)
    parsed_ratios = _resolve_cli_ratios(ratios)
    if profile_path:
        console.print(f"[dim]Using creator profile: {profile_path}[/dim]")

    with console.status("[bold green]Fetching GitHub repos & rendering slides..."):
        deck, paths = generate_github_deck(
            output_dir=output,
            topic=topic,
            repos=repos,
            limit=limit,
            since=since,
            prog_lang=prog_lang,
            language=lang,
            aspect_ratio=ratio,
            ratios=parsed_ratios,
            part=part,
            theme_name=theme,
            accent_color=accent,
            watermark=watermark,
            watermark_position=watermark_pos,
            cover_mode=cover_mode,
            cover_image=cover_image,
            cover_badge=cover_badge,
            cover_cta=cover_cta,
            include_outro=outro,
            export_pdf=pdf,
            use_ai=ai,
            profile=loaded_profile,
        )

    is_multi = bool(
        (parsed_ratios and len(parsed_ratios) > 1)
        or (not parsed_ratios and not ratio and loaded_profile and loaded_profile.ratios and len(loaded_profile.ratios) > 1)
    )
    effective_pdf = bool(pdf if pdf is not None else (loaded_profile.export_pdf if loaded_profile else False))
    _print_render_summary(deck.topic, paths, output, multi_ratio=is_multi, pdf=effective_pdf)


@generate_app.command("web")
def generate_web(
    sites: Annotated[Path, typer.Option("--sites", "-s", exists=True, readable=True, help="Path to sites.yml configuration file.")] = Path("sites.yml"),
    limit: Annotated[int | None, typer.Option("--limit", "-n", min=1, max=15, help="Optional max number of sites.")] = None,
    topic: Annotated[str | None, typer.Option("--topic", "-t", help="Override deck topic.")] = None,
    lang: Annotated[Language | None, typer.Option("--lang", help="Override language (en / id).")] = None,
    ratio: Annotated[AspectRatio | None, typer.Option("--ratio", help="Override single aspect ratio.")] = None,
    ratios: Annotated[str | None, typer.Option("--ratios", help="Multi-ratio batch export, e.g. '3:4,4:5,1:1' or 'all'.")] = None,
    part: Annotated[int | None, typer.Option("--part", help="Override series part number.")] = None,
    theme: Annotated[str | None, typer.Option("--theme", help="Override preset name or custom .yaml theme.")] = None,
    accent: Annotated[str | None, typer.Option("--accent", help="Override accent hex color.")] = None,
    watermark: Annotated[str | None, typer.Option("--watermark", "-w", help="Override creator watermark handle.")] = None,
    watermark_pos: Annotated[WatermarkPosition | None, typer.Option("--watermark-pos", help="Override watermark position.")] = None,
    cover_mode: Annotated[CoverMode | None, typer.Option("--cover-mode", help="Override cover mode.")] = None,
    cover_image: Annotated[Path | None, typer.Option("--cover-image", help="Override cover photo path.")] = None,
    outro: Annotated[bool | None, typer.Option("--outro/--no-outro", help="Include or disable a closing Save/Follow CTA slide.")] = None,
    pdf: Annotated[bool | None, typer.Option("--pdf/--no-pdf", help="Also export combined carousel.pdf (great for LinkedIn).")] = None,
    profile: Annotated[Path | None, typer.Option("--profile", help="Path to custom Creator Brand Profile YAML.")] = None,
    no_profile: Annotated[bool, typer.Option("--no-profile", help="Ignore local/global Creator Brand Profile.")] = False,
    ai: Annotated[bool, typer.Option("--ai", help="Polish descriptions with OpenAI-compatible LLM.")] = False,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory for PNG slides.")] = Path("./output/web_deck"),
) -> None:
    """Generate a photo-slide carousel from websites listed in `sites.yml`."""
    loaded_profile, profile_path = _resolve_cli_profile(profile, no_profile)
    parsed_ratios = _resolve_cli_ratios(ratios)
    if profile_path:
        console.print(f"[dim]Using creator profile: {profile_path}[/dim]")

    with console.status("[bold cyan]Capturing website screenshots & rendering slides..."):
        deck, paths = generate_website_deck(
            sites_file=sites,
            output_dir=output,
            limit=limit,
            topic=topic,
            language=lang,
            aspect_ratio=ratio,
            ratios=parsed_ratios,
            part=part,
            theme_name=theme,
            accent_color=accent,
            watermark=watermark,
            watermark_position=watermark_pos,
            cover_mode=cover_mode,
            cover_image=cover_image,
            include_outro=outro,
            export_pdf=pdf,
            use_ai=ai,
            profile=loaded_profile,
        )

    is_multi = bool(parsed_ratios and len(parsed_ratios) > 1)
    effective_pdf = bool(pdf if pdf is not None else (loaded_profile.export_pdf if loaded_profile else False))
    _print_render_summary(deck.topic, paths, output, multi_ratio=is_multi, pdf=effective_pdf)


@app.command("render")
def render(
    deck_file: Annotated[Path, typer.Argument(exists=True, readable=True, help="Path to deck.yaml file.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory.")] = Path("./output/rendered_deck"),
    theme: Annotated[str | None, typer.Option("--theme", help="Override theme preset or custom .yaml path.")] = None,
    accent: Annotated[str | None, typer.Option("--accent", help="Override accent hex color.")] = None,
    watermark: Annotated[str | None, typer.Option("--watermark", "-w", help="Override watermark handle.")] = None,
    watermark_pos: Annotated[WatermarkPosition | None, typer.Option("--watermark-pos", help="Override watermark position.")] = None,
    cover_mode: Annotated[CoverMode | None, typer.Option("--cover-mode", help="Override cover mode.")] = None,
    cover_image: Annotated[Path | None, typer.Option("--cover-image", help="Override cover photo path.")] = None,
    ratio: Annotated[AspectRatio | None, typer.Option("--ratio", help="Override single aspect ratio.")] = None,
    ratios: Annotated[str | None, typer.Option("--ratios", help="Multi-ratio batch export, e.g. '3:4,4:5,1:1' or 'all'.")] = None,
    outro: Annotated[bool | None, typer.Option("--outro/--no-outro", help="Include or disable a closing Save/Follow CTA slide.")] = None,
    pdf: Annotated[bool | None, typer.Option("--pdf/--no-pdf", help="Also export combined carousel.pdf (great for LinkedIn).")] = None,
    profile: Annotated[Path | None, typer.Option("--profile", help="Path to custom Creator Brand Profile YAML.")] = None,
    no_profile: Annotated[bool, typer.Option("--no-profile", help="Ignore local/global Creator Brand Profile.")] = False,
) -> None:
    """Re-render a saved or hand-edited `deck.yaml` file (supports Showcase, Code, and Versus slides)."""
    loaded_profile, profile_path = _resolve_cli_profile(profile, no_profile)
    parsed_ratios = _resolve_cli_ratios(ratios)
    if profile_path:
        console.print(f"[dim]Using creator profile: {profile_path}[/dim]")

    with console.status("[bold green]Rendering deck.yaml..."):
        deck, paths = render_deck_file(
            deck_file=deck_file,
            output_dir=output,
            theme_name=theme,
            accent_color=accent,
            watermark=watermark,
            watermark_position=watermark_pos,
            cover_image=cover_image,
            cover_mode=cover_mode,
            aspect_ratio=ratio,
            ratios=parsed_ratios,
            include_outro=outro,
            export_pdf=pdf,
            profile=loaded_profile,
        )

    is_multi = bool(parsed_ratios and len(parsed_ratios) > 1)
    effective_pdf = bool(pdf if pdf is not None else (loaded_profile.export_pdf if loaded_profile else False))
    _print_render_summary(deck.topic, paths, output, multi_ratio=is_multi, pdf=effective_pdf)


@app.command("init")
def init_template(
    kind: Annotated[str, typer.Argument(help="Template type: 'sites' (sites.yml), 'deck' (deck.yaml), or 'profile' (.swipekit.yaml).")] = "sites",
    target: Annotated[Path | None, typer.Option("--output", "-o", help="Destination file path.")] = None,
    global_profile: Annotated[bool, typer.Option("--global", "-g", help="When kind='profile', write to ~/.config/swipekit/config.yaml.")] = False,
) -> None:
    """Scaffold a starter `sites.yml`, `deck.yaml`, or `.swipekit.yaml` creator brand profile."""
    if kind == "profile":
        dest = target or (GLOBAL_PROFILE_PATHS[0] if global_profile else Path(".swipekit.yaml"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(STARTER_PROFILE_YAML, encoding="utf-8")
        console.print(f"[bold green]Created creator brand profile:[/bold green] {dest}")
        return

    if kind == "sites":
        dest = target or Path("sites.yml")
        content = """topic: "Useful Websites Worth Bookmarking"
language: en
aspect_ratio: "3:4"
part: 1

theme:
  preset: cyber-indigo
  watermark: "@yourhandle"
  watermark_position: bottom-right

cover:
  mode: gradient
  badge_icon: globe
  badge_text: "USEFUL WEBSITES · PART 1"
  title_lines:
    - "4 Websites"
    - "*worth saving*"
    - "right now."
  cta_text: "Swipe to see them →"

sites:
  - url: "https://excalidraw.com"
    title: "Excalidraw"
    description: "Virtual hand-drawn whiteboard for architecture diagrams and wireframes. Free, fast, no login."
    pricing: "Free"
    category: "Whiteboard"
    footnote: "OPEN SOURCE · REAL-TIME COLLAB · EXPORT SVG/PNG"
    footnote_accent: true

  - url: "https://transform.tools"
    title: "Transform.tools"
    description: "Instant polyglot converter for JSON, TypeScript, GraphQL, SVG, and CSS right in your browser."
    pricing: "Free"
    category: "Dev Utilities"
    footnote: "100% CLIENT-SIDE · NO SIGNUP REQUIRED"
"""
    else:
        dest = target or Path("deck.yaml")
        content = """topic: "Open Source Gems"
language: en
aspect_ratio: "3:4"
part: 1

theme:
  preset: midnight-emerald
  watermark: "@yourhandle"
  watermark_position: bottom-right

cover:
  mode: gradient
  badge_icon: github
  badge_text: "TRENDING THIS WEEK · PART 1"
  title_lines:
    - "3 GitHub tools"
    - "*worth starring*"
    - "this week."
  cta_text: "Swipe to see them →"

items:
  - source: github
    repo: "localsend/localsend"
    title: "localsend"
    description: "Free, open-source AirDrop for every device. Windows, Mac, Linux, Android, and iPhone."
"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    console.print(f"[bold green]Created starter config:[/bold green] {dest}")


@app.command("profile")
def show_profile(
    profile: Annotated[Path | None, typer.Option("--profile", help="Inspect a specific profile YAML file.")] = None,
) -> None:
    """Show the active Creator Brand Profile and its resolved default values."""
    loaded, path = _resolve_cli_profile(profile, no_profile=False)
    if loaded is None or path is None:
        console.print("[yellow]No active Creator Brand Profile found.[/yellow]")
        console.print("Run [bold cyan]swipekit init profile[/bold cyan] (local) or [bold cyan]swipekit init profile --global[/bold cyan] to create one.")
        return

    table = Table(title=f"Active Creator Profile ({path})")
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value")
    data = loaded.model_dump(mode="json", exclude_none=True)
    for key, val in data.items():
        if key == "outro" and isinstance(val, dict):
            summary = f"enabled={val.get('enabled', True)} ({len(val.get('actions', []))} actions)"
            table.add_row(key, summary)
        else:
            table.add_row(key, str(val))
    console.print(table)


@app.command("doctor")
def doctor() -> None:
    """Check Python, Chromium/Playwright, dependencies, profile, and optional API tokens."""
    from tcd_swipekit.profile import find_profile_path
    from tcd_swipekit.renderer import _find_chromium_executable

    table = Table(title=f"TCD-Swipekit Doctor (v{__version__})")
    table.add_column("Check", style="bold cyan")
    table.add_column("Status")
    table.add_column("Details")

    ok = True

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python", "[bold green]OK[/bold green]", f"{py_ver} (>= 3.10)")

    # Check Chromium / Playwright browser
    system_chrome = _find_chromium_executable()
    pw_chrome: str | None = None
    if not system_chrome:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                candidate = Path(p.chromium.executable_path)
                if candidate.is_file():
                    pw_chrome = str(candidate)
        except Exception:
            pw_chrome = None

    browser_path = system_chrome or pw_chrome
    if browser_path:
        table.add_row("Chromium (Playwright)", "[bold green]OK[/bold green]", browser_path)
    else:
        ok = False
        table.add_row(
            "Chromium (Playwright)",
            "[bold red]FAIL[/bold red]",
            "Not found — run: playwright install chromium",
        )

    # Check Pillow & Pygments
    for pkg_name, import_name in (("Pillow (PNG/PDF)", "PIL"), ("Pygments (Code Highlight)", "pygments")):
        try:
            __import__(import_name)
            table.add_row(pkg_name, "[bold green]OK[/bold green]", "Installed")
        except ImportError:
            ok = False
            table.add_row(pkg_name, "[bold red]FAIL[/bold red]", f"Missing — pip install {import_name.lower()}")

    # Built-in themes count
    presets = list_presets()
    table.add_row("Built-in Themes", "[bold green]OK[/bold green]", f"{len(presets)} presets ({', '.join(presets[:4])}...)")

    # Creator Brand Profile
    profile_path = find_profile_path()
    if profile_path:
        table.add_row("Creator Profile", "[bold green]OK[/bold green]", str(profile_path))
    else:
        table.add_row(
            "Creator Profile",
            "[dim]INFO[/dim]",
            "None active (optional — run: swipekit init profile)",
        )

    # Optional GITHUB_TOKEN & OPENAI_API_KEY
    if os.environ.get("GITHUB_TOKEN"):
        table.add_row("GITHUB_TOKEN", "[bold green]OK[/bold green]", "Set (5,000 req/hr GitHub API limit)")
    else:
        table.add_row(
            "GITHUB_TOKEN",
            "[yellow]OPTIONAL[/yellow]",
            "Unset (60 req/hr unauthenticated GitHub API limit)",
        )

    if os.environ.get("OPENAI_API_KEY"):
        table.add_row("OPENAI_API_KEY", "[bold green]OK[/bold green]", "Set (enables --ai copywriting)")
    else:
        table.add_row("OPENAI_API_KEY", "[dim]OPTIONAL[/dim]", "Unset (not required; needed only for --ai)")

    console.print(table)
    if not ok:
        raise typer.Exit(code=1)


@app.command("themes")
def show_themes() -> None:
    """List all built-in theme presets and their primary colors."""
    table = Table(title="TCD-Swipekit Built-in Themes")
    table.add_column("Preset Name", style="bold cyan")
    table.add_column("Mode")
    table.add_column("Background")
    table.add_column("Accent")
    table.add_column("Ambient Blur")

    for name in list_presets():
        cfg = load_theme(name)
        table.add_row(
            name,
            "Light" if cfg.is_light else "Dark",
            cfg.bg_color,
            cfg.accent_color,
            "Yes" if cfg.ambient_blur else "No",
        )
    console.print(table)


@skill_app.command("install")
def skill_install(
    agent: Annotated[
        str,
        typer.Option(
            "--agent",
            "-a",
            help="Target AI agent: antigravity, claude, codex, cursor, gemini, copilot, agents, or all.",
        ),
    ] = "antigravity",
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Custom destination directory (overrides --agent)."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite/--no-overwrite", help="Overwrite existing skill directory if present."),
    ] = True,
) -> None:
    """Install the TCD-Swipekit Agent Skill (SKILL.md + references) for AI coding agents."""
    try:
        installed = install_skill(agent=agent, target_dir=target, overwrite=overwrite)
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[bold green]Installed TCD-Swipekit Agent Skill to:[/bold green]")
    for dest in installed:
        console.print(f"  • {dest}")


@skill_app.command("show")
def skill_show() -> None:
    """Print the path and contents of the bundled SKILL.md."""
    skill_dir = get_bundled_skill_dir()
    skill_md = skill_dir / "SKILL.md"
    console.print(f"[bold cyan]Skill directory:[/bold cyan] {skill_dir}\n")
    console.print(skill_md.read_text(encoding="utf-8"))
