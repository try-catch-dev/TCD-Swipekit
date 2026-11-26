# Built-in & Custom Brand Themes

List all available presets at any time via `swipekit themes`.

## Built-in Presets

| Preset | Mode | Base Background | Primary Accent | Best For |
| :--- | :--- | :--- | :--- | :--- |
| `tcd-neon-lime` | Dark | `#080B10` (Deep Obsidian) | `#D4F93A` (Neon Lime) | Official Try Catch Dev brand palette (`#0D121F` cards, `#161F30` borders, `#94A3B8` slate) |
| `midnight-emerald` | Dark | `#0B0C0F` | `#48DF76` | Classic GitHub trending aesthetic |
| `cyber-indigo` | Dark | `#070B16` | `#38BDF8` | SaaS & useful website carousels |
| `neon-violet` | Dark | `#0D0915` | `#C084FC` | AI, creative & design tools |
| `editorial-light` | Light | `#F6F4EF` | `#16A34A` | Clean light magazine-style slides |

## Creating a Custom Theme YAML

Save a `.yaml` file and pass `--theme ./my-brand.yaml`:

```yaml
preset: my-brand
is_light: false
bg_color: "#080B10"
cover_bg_color: "#080B10"
text_color: "#FFFFFF"
muted_color: "#94A3B8"
subtle_color: "#94A3B8"
divider_color: "#161F30"
accent_color: "#D4F93A"
accent_text_color: "#080B10"
pill_accent_bg: "#D4F93A"
pill_accent_text: "#080B10"
pill_glass_bg: "#0D121F"
pill_glass_border: "#161F30"
cli_bg: "#0D121F"
cli_border: "#161F30"
cli_text: "#FFFFFF"
ambient_blur: true
card_radius: 24
watermark: "@yourhandle"
watermark_position: bottom-right
```
