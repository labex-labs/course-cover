const DEFAULT_COVER = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover/default.png';
const JSDELIVR_BASE = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover/public';
const GITHUB_API = 'https://api.github.com/repos/labex-labs/course-cover/actions/workflows/generate-course-cover.yml/dispatches';

interface Env {
	GITHUB_TOKEN: string;
}

async function triggerGithubAction(courseAlias: string, lang: string, overwrite: boolean, token: string) {
	try {
		console.log(`Triggering GitHub Action for course: ${courseAlias}, lang: ${lang}, overwrite: ${overwrite}`);
		const response = await fetch(GITHUB_API, {
			method: 'POST',
			headers: {
				Accept: 'application/vnd.github.v3+json',
				Authorization: `Bearer ${token}`,
			},
			body: JSON.stringify({
				ref: 'master',
				inputs: {
					course_alias: courseAlias,
					course_lang: lang,
					overwrite: overwrite.toString(),
				},
			}),
		});
		console.log(`GitHub Action trigger ${response.ok ? 'succeeded' : 'failed'}`);
		return response.ok;
	} catch (error) {
		console.error('Error triggering GitHub Action:', error);
		return false;
	}
}

async function checkImageExists(url: string): Promise<boolean> {
	try {
		console.log(`Checking if image exists at: ${url}`);
		const response = await fetch(url, { method: 'HEAD' });
		console.log(`Image check result: ${response.ok ? 'exists' : 'not found'}`);
		return response.ok;
	} catch {
		console.error(`Failed to check image at: ${url}`);
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
			console.log(`Processing request for URL: ${url.toString()}`);

			// Extract course alias from path
			const match = url.pathname.match(/\/(.+)\.png$/);
			if (!match) {
				console.log('No course alias found in URL, returning default cover');
				const defaultImage = await fetchImage(DEFAULT_COVER);
				return defaultImage || new Response('Image not found', { status: 404 });
			}

			const courseAlias = match[1];
			const lang = url.searchParams.get('lang') || 'en';
			const overwrite = url.searchParams.get('overwrite') === 'true';
			console.log(`Request parameters - Course: ${courseAlias}, Lang: ${lang}, Overwrite: ${overwrite}`);

			// Construct cover URL
			const coverUrl = `${JSDELIVR_BASE}/${lang}/${courseAlias}.png`;

			// Check if cover exists
			const exists = await checkImageExists(coverUrl);

			if (exists && !overwrite) {
				console.log('Using existing cover image');
				const image = await fetchImage(coverUrl);
				if (image) return image;
			} else {
				console.log('Cover needs to be generated');
				await triggerGithubAction(courseAlias, lang, overwrite, env.GITHUB_TOKEN);
			}

			console.log('Returning default cover while generating or after failure');
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		} catch (error) {
			console.error('Error processing request:', error);
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		}
	},
} satisfies ExportedHandler<Env>;
