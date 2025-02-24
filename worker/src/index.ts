import { KVNamespace } from '@cloudflare/workers-types';

const DEFAULT_COVER = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover/default.png';
const JSDELIVR_BASE = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover/public';
const GITHUB_API = 'https://api.github.com/repos/labex-labs/course-cover/actions/workflows/generate-course-cover.yml/dispatches';

interface Env {
	GITHUB_TOKEN: string;
	COURSE_COVER_KV: KVNamespace;
}

async function triggerGithubAction(courseAlias: string, lang: string, overwrite: boolean, token: string, kv: KVNamespace) {
	const key = `trigger:${courseAlias}:${lang}`;
	const lastTrigger = await kv.get(key);
	if (lastTrigger) {
		console.log(`Action recently triggered for ${courseAlias}, skipping`);
		return true;
	}

	try {
		console.log(`Triggering GitHub Action for course: ${courseAlias}, lang: ${lang}, overwrite: ${overwrite}`);
		const response = await fetch(GITHUB_API, {
			method: 'POST',
			headers: {
				Accept: 'application/vnd.github+json',
				Authorization: `Bearer ${token}`,
				'X-GitHub-Api-Version': '2022-11-28',
				'Content-Type': 'application/json',
				'User-Agent': 'LabEx-Course-Cover-Generator',
			},
			body: JSON.stringify({
				ref: 'master',
				inputs: {
					course_alias: courseAlias,
					course_lang: lang,
					overwrite: overwrite,
				},
			}),
		});

		if (response.ok) {
			await kv.put(key, Date.now().toString(), { expirationTtl: 600 });

			// 当 Action 触发成功后，清除原有的存在性缓存
			// 这样下次请求会重新检查图片是否存在
			const coverUrl = `${JSDELIVR_BASE}/${lang}/${courseAlias}.png`;
			const cacheKey = `exists:${coverUrl}`;
			await kv.delete(cacheKey);
		}

		console.log(`GitHub Action trigger ${response.ok ? 'succeeded' : 'failed'}`);
		return response.ok;
	} catch (error) {
		console.error('Error triggering GitHub Action:', error);
		return false;
	}
}

async function checkImageExists(url: string, kv: KVNamespace): Promise<boolean> {
	const cacheKey = `exists:${url}`;

	// 先检查 KV 缓存
	const cached = await kv.get(cacheKey);
	if (cached !== null) {
		console.log(`Using cached result for ${url}`);
		return cached === 'true';
	}

	try {
		console.log(`Checking if image exists at: ${url}`);
		const response = await fetch(url, { method: 'HEAD' });
		const exists = response.ok;

		// 缓存结果，设置 1 天的过期时间
		await kv.put(cacheKey, exists.toString(), { expirationTtl: 86400 });

		console.log(`Image check result: ${exists ? 'exists' : 'not found'}`);
		return exists;
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

async function checkCourseExists(courseAlias: string, lang: string): Promise<{ exists: boolean; error?: string }> {
	try {
		const response = await fetch(`https://labex.io/api/v2/courses/${courseAlias}?lang=${lang}`, {
			headers: {
				'User-Agent':
					'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
			},
		});

		if (response.status === 404) {
			return { exists: false, error: `Course ${courseAlias} not found` };
		}

		if (!response.ok) {
			return { exists: false, error: `Failed to check course: ${response.statusText}` };
		}

		const data = await response.json();
		return { exists: !!data.course };
	} catch (error) {
		console.error('Error checking course existence:', error);
		return { exists: false, error: 'Failed to check course existence' };
	}
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		try {
			const url = new URL(request.url);
			console.log(`Processing request for URL: ${url.toString()}`);

			// Skip browser special requests
			const skipPaths = ['/favicon.png', '/favicon.ico', '/apple-touch-icon.png', '/apple-touch-icon-precomposed.png', '/robots.txt'];

			if (skipPaths.includes(url.pathname)) {
				return new Response('Not Found', { status: 404 });
			}

			// Validate URL path format
			const pathRegex = /^\/[a-z0-9-]+\.png$/;
			if (!pathRegex.test(url.pathname)) {
				return new Response('Invalid URL format', { status: 400 });
			}

			// Define supported languages
			const supportedLangs = new Set(['en', 'zh', 'es', 'fr', 'de', 'ja', 'ru']);

			// Validate query parameters strictly
			const allowedParams = new Set(['lang', 'overwrite']);
			const receivedParams = new Set(url.searchParams.keys());

			// Check for any unsupported parameters
			for (const param of receivedParams) {
				if (!allowedParams.has(param)) {
					return new Response(`Unsupported parameter: ${param}`, { status: 400 });
				}
			}

			// Validate language parameter
			const lang = url.searchParams.get('lang') || 'en';
			if (!supportedLangs.has(lang)) {
				return new Response(`Unsupported language: ${lang}. Supported languages are: ${Array.from(supportedLangs).join(', ')}`, {
					status: 400,
				});
			}

			const overwrite = url.searchParams.get('overwrite') === 'true';

			// Extract course alias from path
			const match = url.pathname.match(/\/([a-z0-9-]+)\.png$/);
			if (!match) {
				console.log('No course alias found in URL, returning default cover');
				const defaultImage = await fetchImage(DEFAULT_COVER);
				return defaultImage || new Response('Image not found', { status: 404 });
			}

			const courseAlias = match[1];
			console.log(`Request parameters - Course: ${courseAlias}, Lang: ${lang}, Overwrite: ${overwrite}`);

			// Construct cover URL
			const coverUrl = `${JSDELIVR_BASE}/${lang}/${courseAlias}.png`;

			// First check if cover exists
			const coverExists = await checkImageExists(coverUrl, env.COURSE_COVER_KV);

			if (coverExists && !overwrite) {
				console.log('Using existing cover image');
				const image = await fetchImage(coverUrl);
				if (image) return image;
			}

			// Only check course existence if we need to generate a new cover
			console.log('Checking course existence before generating cover');
			const { exists, error } = await checkCourseExists(courseAlias, lang);
			if (!exists) {
				console.log(`Course check failed: ${error}`);
				const defaultImage = await fetchImage(DEFAULT_COVER);
				return defaultImage || new Response(error, { status: 404 });
			}

			console.log('Cover needs to be generated');
			await triggerGithubAction(courseAlias, lang, overwrite, env.GITHUB_TOKEN, env.COURSE_COVER_KV);

			console.log('Returning default cover while generating');
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		} catch (error) {
			console.error('Error processing request:', error);
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		}
	},
} satisfies ExportedHandler<Env>;
