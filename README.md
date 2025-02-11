# LabEx Course Cover Generator

A service that automatically generates course cover images for LabEx courses. It includes a GitHub Action workflow for image generation and a Cloudflare Worker for serving and managing cover images.

## Features

- Automated course cover image generation
- Dynamic icon fetching from Freepik API
- Cloudflare Worker for image serving and caching
- GitHub Actions workflow for on-demand generation
- Support for multiple languages
- Fallback to default cover when needed

## Architecture

The service consists of three main components:

1. **Cover Generator Script** (`scripts/generate_cover.py`)
   - Fetches course information from LabEx API
   - Retrieves relevant icons from Freepik
   - Generates cover images using Playwright
   - Supports multiple languages

2. **GitHub Actions Workflow** (`.github/workflows/generate-course-cover.yml`)
   - Handles on-demand cover generation
   - Manages concurrent generation requests
   - Automatically commits and pushes generated covers

3. **Cloudflare Worker** (`worker/src/index.ts`)
   - Serves cover images with caching
   - Triggers cover generation when needed
   - Handles fallback to default covers
   - Manages generation request throttling

## Usage

### Generating a Cover

You can generate a course cover in two ways:

1. **Via GitHub Actions UI**:
   - Go to the Actions tab
   - Select "Generate Course Cover"
   - Fill in the required parameters:
     - `course_alias`: The course identifier (e.g., "html-for-beginners")
     - `course_lang`: Language code (e.g., "en", "zh")
     - `overwrite`: Whether to regenerate existing covers

2. **Via API**:

   ```
   GET https://your-worker-url/{course-alias}.png?lang=en
   ```

   Query Parameters:
   - `lang`: Language code (default: "en")
   - `overwrite`: Set to "true" to force regeneration

## Setup

### Prerequisites

- Python 3.x
- Node.js (for Cloudflare Worker)
- Freepik API key
- GitHub token with workflow permissions

### Local Development

1. Install Python dependencies:

   ```bash
   pip install requests playwright
   playwright install chromium
   ```

2. Set environment variables:

   ```bash
   export FREEPIK_API_KEY=your_api_key
   ```

3. Run the generator script:

   ```bash
   python scripts/generate_cover.py <course_alias> <lang> [overwrite]
   ```

### Deployment

1. **GitHub Actions**:
   - Add `FREEPIK_API_KEY` to repository secrets
   - The workflow will automatically handle deployments

2. **Cloudflare Worker**:
   - Deploy using Wrangler:

     ```bash
     wrangler deploy
     ```

   - Configure environment variables in Cloudflare:
     - `GITHUB_TOKEN`
     - Set up KV namespace for `COURSE_COVER_KV`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
