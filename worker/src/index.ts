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

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		try {
			const url = new URL(request.url);

			// Extract course alias from path
			const match = url.pathname.match(/\/(.+)\.png$/);
			if (!match) {
				return Response.redirect(DEFAULT_COVER, 302);
			}

			const courseAlias = match[1];
			const lang = url.searchParams.get('lang') || 'en';
			const overwrite = url.searchParams.get('overwrite') === 'true';

			// Construct cover URL
			const coverUrl = `${JSDELIVR_BASE}/${lang}/${courseAlias}.png`;

			// Check if cover exists
			const exists = await checkImageExists(coverUrl);

			if (exists && !overwrite) {
				// Return existing cover
				return Response.redirect(coverUrl, 302);
			} else {
				// Trigger GitHub Action to generate cover
				await triggerGithubAction(courseAlias, lang, overwrite, env.GITHUB_TOKEN);
				// Return default cover while generating
				return Response.redirect(DEFAULT_COVER, 302);
			}
		} catch (error) {
			console.error('Error processing request:', error);
			return Response.redirect(DEFAULT_COVER, 302);
		}
	},
} satisfies ExportedHandler<Env>;
