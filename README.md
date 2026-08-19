# LabEx Course Cover

[![JSDelivr](https://data.jsdelivr.com/v1/package/gh/labex-labs/course-cover/badge)](https://www.jsdelivr.com/package/gh/labex-labs/course-cover)

Multi-language course cover image service for LabEx.

## Features

- Multi-language support (9 languages)
- Auto fallback to default cover
- 30-day CDN cache

## Usage

### Basic Examples

```bash
# English (default)
https://course-cover.labex.io/keepalived-high-availability.png

# Chinese
https://course-cover.labex.io/keepalived-high-availability.png?lang=zh
```

### URL Format

```plaintext
https://course-cover.labex.io/{course-alias}.png?lang={lang}
```

**Parameters:**

- `lang` (optional): `en` | `zh` | `es` | `fr` | `de` | `ja` | `ru` | `ko` | `pt`

## Development

```bash
cd worker
pnpm install
pnpm dev          # Local: http://localhost:8787
wrangler deploy   # Deploy to production
```

### Icon-only covers

Title-free covers are generated separately from the primary localized covers:

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/generate-icon-only-cover.py python-for-beginners
# Generate every course in config/course-covers.json
python3 scripts/generate-icon-only-cover.py --all
```

The generated image is written to `public/icon-only/{course-alias}.png`. It uses
the existing icon and background color with a centered icon on the same
1400 x 720 canvas. Existing files under `public/{lang}` are not changed.

After changes to the cover config, source icons, or icon-only generator are
pushed to `master`, the `Sync icon-only covers` GitHub Actions workflow runs the
full synchronization and commits any changed icon-only covers automatically.

## Architecture

User → [Cloudflare Worker](https://github.com/labex-labs/course-cover-service) → [jsDelivr CDN](https://www.jsdelivr.com/package/gh/labex-labs/course-cover) → Default Cover (fallback)
