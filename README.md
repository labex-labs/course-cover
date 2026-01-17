# LabEx Course Cover Service

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

```
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

```
User → Cloudflare Worker → jsDelivr CDN → Default Cover (fallback)
```
