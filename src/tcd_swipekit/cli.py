"""Command-line interface for TCD-Swipekit (`swipekit` / `tcd-swipekit`)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from tcd_swipekit import __version__
from tcd_swipekit.models import AspectRatio, CoverMode, Language, WatermarkPosition
from tcd_swipekit.pipeline import generate_github_deck, generate_website_deck, render_deck_file
from tcd_swipekit.themes.loader import list_presets, load_theme

app = typer.Typer(
    name="swipekit",
    help="TCD-Swipekit — Generate modern photo-slide carousels from GitHub repos & websites.",
    no_args_is_help=True,
)
generate_app = typer.Typer(help="Generate a carousel deck from a content source.", no_args_is_help=True)
app.add_typer(generate_app, name="generate")

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold green]TCD-Swipekit[/bold green] v{__version__}")
        raise typer.Exit()


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
    lang: Annotated[Language, typer.Option("--lang", help="Content language: en (default) or id.")] = Language.EN,
    ratio: Annotated[AspectRatio, typer.Option("--ratio", help="Aspect ratio: 3:4, 4:5, 9:16, 1:1.")] = AspectRatio.PORTRAIT_3_4,
    part: Annotated[int, typer.Option("--part", help="Series part number on cover badge.")] = 1,
    theme: Annotated[str, typer.Option("--theme", help="Preset name or path to custom .yaml theme.")] = "midnight-emerald",
    accent: Annotated[str | None, typer.Option("--accent", help="Override theme accent hex color (e.g. #38BDF8).")] = None,
    watermark: Annotated[str | None, typer.Option("--watermark", "-w", help="Creator watermark handle (e.g. @trycatchdev).")] = None,
    watermark_pos: Annotated[WatermarkPosition | None, typer.Option("--watermark-pos", help="Watermark position.")] = None,
    cover_mode: Annotated[CoverMode | None, typer.Option("--cover-mode", help="Cover mode: photo, gradient, minimal.")] = None,
    cover_image: Annotated[Path | None, typer.Option("--cover-image", help="Custom cover background photo path.")] = None,
    cover_badge: Annotated[str | None, typer.Option("--cover-badge", help="Custom cover badge pill text.")] = None,
    cover_cta: Annotated[str | None, typer.Option("--cover-cta", help="Custom cover CTA button text.")] = None,
    ai: Annotated[bool, typer.Option("--ai", help="Polish descriptions with OpenAI-compatible LLM.")] = False,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory for PNG slides.")] = Path("./output/github_deck"),
) -> None:
    """Generate a photo-slide carousel from GitHub trending or topic-matched repositories."""
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
            part=part,
            theme_name=theme,
            accent_color=accent,
            watermark=watermark,
            watermark_position=watermark_pos,
            cover_mode=cover_mode,
            cover_image=cover_image,
            cover_badge=cover_badge,
            cover_cta=cover_cta,
            use_ai=ai,
        )

    console.print(f"\n[bold green]Done![/bold green] Rendered [bold]{len(paths)}[/bold] slides for [cyan]{deck.topic}[/cyan]:")
    for p in paths:
        console.print(f"  • {p}")
    console.print(f"  • Caption: {output / 'caption.md'}")
    console.print(f"  • Preview: {output / 'preview.html'}")


@generate_app.command("web")
def generate_web(
    sites: Annotated[Path, typer.Option("--sites", "-s", exists=True, readable=True, help="Path to sites.yml configuration file.")] = Path("sites.yml"),
    limit: Annotated[int | None, typer.Option("--limit", "-n", min=1, max=15, help="Optional max number of sites.")] = None,
    topic: Annotated[str | None, typer.Option("--topic", "-t", help="Override deck topic.")] = None,
    lang: Annotated[Language | None, typer.Option("--lang", help="Override language (en / id).")] = None,
    ratio: Annotated[AspectRatio | None, typer.Option("--ratio", help="Override aspect ratio.")] = None,
    part: Annotated[int | None, typer.Option("--part", help="Override series part number.")] = None,
    theme: Annotated[str | None, typer.Option("--theme", help="Override preset name or custom .yaml theme.")] = None,
    accent: Annotated[str | None, typer.Option("--accent", help="Override accent hex color.")] = None,
    watermark: Annotated[str | None, typer.Option("--watermark", "-w", help="Override creator watermark handle.")] = None,
    watermark_pos: Annotated[WatermarkPosition | None, typer.Option("--watermark-pos", help="Override watermark position.")] = None,
    cover_mode: Annotated[CoverMode | None, typer.Option("--cover-mode", help="Override cover mode.")] = None,
    cover_image: Annotated[Path | None, typer.Option("--cover-image", help="Override cover photo path.")] = None,
    ai: Annotated[bool, typer.Option("--ai", help="Polish descriptions with OpenAI-compatible LLM.")] = False,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory for PNG slides.")] = Path("./output/web_deck"),
) -> None:
    """Generate a photo-slide carousel from websites listed in `sites.yml`."""
    with console.status("[bold cyan]Capturing website screenshots & rendering slides..."):
        deck, paths = generate_website_deck(
            sites_file=sites,
            output_dir=output,
            limit=limit,
            topic=topic,
            language=lang,
            aspect_ratio=ratio,
            part=part,
            theme_name=theme,
            accent_color=accent,
            watermark=watermark,
            watermark_position=watermark_pos,
            cover_mode=cover_mode,
            cover_image=cover_image,
            use_ai=ai,
        )

    console.print(f"\n[bold green]Done![/bold green] Rendered [bold]{len(paths)}[/bold] slides for [cyan]{deck.topic}[/cyan]:")
    for p in paths:
        console.print(f"  • {p}")
    console.print(f"  • Caption: {output / 'caption.md'}")
    console.print(f"  • Preview: {output / 'preview.html'}")


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
    ratio: Annotated[AspectRatio | None, typer.Option("--ratio", help="Override aspect ratio.")] = None,
) -> None:
    """Re-render a saved or hand-edited `deck.yaml` file (supports hybrid GitHub + Website slides)."""
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
        )

    console.print(f"\n[bold green]Done![/bold green] Rendered [bold]{len(paths)}[/bold] slides for [cyan]{deck.topic}[/cyan]:")
    for p in paths:
        console.print(f"  • {p}")


@app.command("init")
def init_template(
    kind: Annotated[str, typer.Argument(help="Template type: 'sites' (sites.yml) or 'deck' (deck.yaml).")] = "sites",
    target: Annotated[Path | None, typer.Option("--output", "-o", help="Destination file path.")] = None,
) -> None:
    """Scaffold a starter `sites.yml` or `deck.yaml` config file."""
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
    dest.write_text(content, encoding="utf-8")
    console.print(f"[bold green]Created starter config:[/bold green] {dest}")


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
