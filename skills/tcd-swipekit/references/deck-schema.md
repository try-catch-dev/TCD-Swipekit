# TCD-Swipekit YAML Schema Reference

## `deck.yaml` (GitHub, Hybrid, or Custom Slides)

```yaml
topic: "5 Trending Open-Source Tools"
language: en            # en (default) | id
aspect_ratio: "3:4"     # 3:4 (1180x1572) | 4:5 (1080x1350) | 9:16 (1080x1920) | 1:1 (1080x1080)
part: 1

theme:
  preset: tcd-neon-lime # preset name or path to custom .yaml theme
  watermark: "@trycatchdev"
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
      label: "Follow @trycatchdev"
      sublabel: "Don't miss Part 2 and weekly updates"
      accent: true
    - icon: comment
      label: "Comment 'PART 2'"
      sublabel: "Drop your favorite tool below"
      accent: false
  handle: "@trycatchdev"
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
  preset: tcd-neon-lime
  watermark: "@trycatchdev"

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
    - { icon: follow, label: "Follow @trycatchdev", sublabel: "Weekly web gems", accent: true }

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
