# TCD-Swipekit YAML Schema Reference

## `deck.yaml` (GitHub, Hybrid, or Custom Slides)

```yaml
topic: "5 Trending Open-Source Tools"
language: en            # en (default) | id
aspect_ratio: "3:4"     # 3:4 (1180x1572) | 4:5 (1080x1350) | 9:16 (1080x1920) | 1:1 (1080x1080)
part: 1

theme:
  preset: midnight-emerald # preset name or path to custom .yaml theme
  watermark: "@yourhandle"
  watermark_position: bottom-right  # bottom-right | top-right | bottom-left

cover:
  mode: gradient        # photo | gradient | minimal
  image_path: null      # required when mode: photo
  badge_icon: github    # github | globe | sparkles | none
  badge_text: "TRENDING THIS WEEK · PART 1"
  title_lines:
    - "5 GitHub repos"
    - "*blowing up*"    # wrap highlight words in *...*
    - "right now."
  subtitle: "#1 is **Univer** — open-source AI Office SDK."
  cta_text: "Swipe to see them →"

outro:
  enabled: true
  badge_text: "DONE · WANT PART 2?"
  title_lines:
    - "Save this post"
    - "*& follow*"
    - "for more tools."
  subtitle: "Weekly curated **open-source repos & useful websites**."
  actions:
    - icon: bookmark    # bookmark | follow | comment | share
      label: "Save this post"
      sublabel: "Keep it handy for your next build"
      accent: false
    - icon: follow
      label: "Follow @yourhandle"
      sublabel: "Don't miss Part 2 and weekly updates"
      accent: true
    - icon: comment
      label: "Comment 'PART 2'"
      sublabel: "Drop your favorite tool below"
      accent: false
  handle: "@yourhandle"
  footer_note: "OPEN SOURCE · AI · DEV TOOLS"

items:
  - source: github      # github | website | manual
    repo: "dream-num/univer"
    eyebrow: "dream-num /"
    title: "univer"
    description: "Open-source AI Office SDK for spreadsheets, docs, and slides."
    badges:
      - { text: "★ 31,817", style: "glass" }
      - { text: "+3,278 this week", style: "accent" }
      - { text: "Apache-2.0", style: "glass" }
    command_or_url: "$ npm install @univerjs/presets"
    footnote: "SHEETS · DOCS · SLIDES"
    footnote_accent: true
    image_fit: "cover"  # contain | cover
```

## `sites.yml` (Auto-Screenshotted Useful Websites)

```yaml
topic: "5 Useful Websites Worth Bookmarking"
language: en
aspect_ratio: "3:4"
part: 1

theme:
  preset: cyber-indigo
  watermark: "@yourhandle"

cover:
  mode: gradient
  badge_icon: globe
  badge_text: "USEFUL WEBSITES · PART 1"

outro:
  enabled: true
  badge_text: "PART 1 DONE · WANT PART 2?"
  title_lines: ["Save this post", "*& follow*", "for more sites."]
  actions:
    - { icon: bookmark, label: "Save this post", sublabel: "Bookmark for later" }
    - { icon: follow, label: "Follow @yourhandle", sublabel: "Weekly web gems", accent: true }

sites:
  - url: "https://excalidraw.com"
    title: "Excalidraw"
    description: "Hand-drawn virtual whiteboard for diagrams and wireframes. Free, no login."
    pricing: "Free"
    category: "Whiteboard"
    dark_mode: false
    footnote: "OPEN SOURCE · REAL-TIME COLLAB"
    footnote_accent: true
```

## Slide Layouts (`layout: code` & `layout: versus`)

In any `deck.yaml`, mix regular `showcase` slides with `code` (syntax-highlighted code/diff) or `versus` (A-vs-B comparison) slides:

```yaml
items:
  - source: manual
    layout: code              # auto-inferred when `code_block:` is set
    eyebrow: "python / refactor"
    title: "Avoid N+1 Loops"
    description: "Replace nested lookups with a single indexed dict."
    code_block:
      filename: "orders.py"
      language: "diff"        # python, typescript, bash, diff, json, etc.
      diff_mode: true         # highlights + (green) and - (red) lines
      highlight_lines: [2, 3] # 1-indexed lines highlighted in theme accent
      show_line_numbers: true
      code: |
        - for u in users:
        + user = by_id.get(order["user_id"])

  - source: manual
    layout: versus            # auto-inferred when `versus:` is set
    eyebrow: "tooling / compare"
    title: "pip vs uv"
    description: "Why Python teams migrate local & CI workflows to uv."
    versus:
      left:
        label: "pip + venv"
        badge: "LEGACY"
        points: ["Slower resolution", "Multiple CLIs"]
        code: "pip install -r requirements.txt"
        accent: false
      right:
        label: "uv"
        badge: "RECOMMENDED"
        points: ["10-100x faster installs", "Single Rust binary"]
        code: "uv sync --frozen"
        accent: true
      verdict: "Switch to uv for instant setups and faster CI."

  - source: manual
    layout: checklist         # auto-inferred when `checklist:` is set
    eyebrow: "release / audit"
    title: "Pre-Ship Checklist"
    description: "Four essential checks before deploying to production."
    checklist:
      numbered: true
      items:
        - { title: "Lock dependencies", detail: "Commit uv.lock for deterministic builds.", badge: "CI/CD", accent: true }
        - { title: "Enforce Ruff & types", detail: "Block merges on lint regressions.", badge: "QUALITY" }
      summary: "Automate all checks in GitHub Actions."
```

## Creator Brand Profile (`.swipekit.yaml` / `~/.config/swipekit/config.yaml`)

```yaml
theme: midnight-emerald
watermark: "@yourhandle"
watermark_position: bottom-right
language: en
aspect_ratio: "3:4"
# ratios: ["3:4", "4:5", "1:1"]
export_pdf: false
export_gif: false
outro:
  enabled: true
  badge_text: "DONE · WANT PART 2?"
```

