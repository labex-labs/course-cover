const DEFAULT_COVER = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover/default.png';
const JSDELIVR_BASE = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover/public';
const GITHUB_API = 'https://api.github.com/repos/labex-labs/course-cover/actions/workflows/generate-course-cover.yml/dispatches';

interface Env {
	GITHUB_TOKEN: string;
}

async function triggerGithubAction(courseAlias: string, lang: string, overwrite: boolean, token: string) {
	try {
		const response = await fetch(GITHUB_API, {
			method: 'POST',
			headers: {
				Accept: 'application/vnd.github.v3+json',
				Authorization: `Bearer ${token}`,
			},
			body: JSON.stringify({
				ref: 'main',
				inputs: {
					course_alias: courseAlias,
					course_lang: lang,
					overwrite: overwrite.toString(),
				},
			}),
		});
		return response.ok;
	} catch (error) {
		console.error('Error triggering GitHub Action:', error);
		return false;
	}
}

async function checkImageExists(url: string): Promise<boolean> {
	try {
		const response = await fetch(url, { method: 'HEAD' });
		return response.ok;
	} catch {
		return false;
	}
}

async function fetchImage(url: string): Promise<Response | null> {
	try {
		const response = await fetch(url);
		if (!response.ok) return null;

		const contentType = response.headers.get('content-type');
		return new Response(response.body, {
			headers: {
				'content-type': contentType || 'image/png',
				'cache-control': 'public, max-age=3600',
			},
		});
	} catch {
		return null;
	}
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		try {
			const url = new URL(request.url);

			// Extract course alias from path
			const match = url.pathname.match(/\/(.+)\.png$/);
			if (!match) {
				const defaultImage = await fetchImage(DEFAULT_COVER);
				return defaultImage || new Response('Image not found', { status: 404 });
			}

			const courseAlias = match[1];
			const lang = url.searchParams.get('lang') || 'en';
			const overwrite = url.searchParams.get('overwrite') === 'true';

			// Construct cover URL
			const coverUrl = `${JSDELIVR_BASE}/${lang}/${courseAlias}.png`;

			// Check if cover exists
			const exists = await checkImageExists(coverUrl);

			if (exists && !overwrite) {
				// Return existing cover directly
				const image = await fetchImage(coverUrl);
				if (image) return image;
			} else {
				// Trigger GitHub Action to generate cover
				await triggerGithubAction(courseAlias, lang, overwrite, env.GITHUB_TOKEN);
			}

			// Return default cover if anything fails or while generating
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		} catch (error) {
			console.error('Error processing request:', error);
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		}
	},
} satisfies ExportedHandler<Env>;
