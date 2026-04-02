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

## Architecture

```plaintext
User → [Cloudflare Worker](https://github.com/labex-labs/course-cover-service) → [jsDelivr CDN](https://www.jsdelivr.com/package/gh/labex-labs/course-cover) → Default Cover (fallback)
```
