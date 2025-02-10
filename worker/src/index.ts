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
					overwrite: overwrite.toString(),
				},
			}),
		});

		if (response.ok) {
			await kv.put(key, Date.now().toString(), { expirationTtl: 300 });

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
			const exists = await checkImageExists(coverUrl, env.COURSE_COVER_KV);

			if (exists && !overwrite) {
				console.log('Using existing cover image');
				const image = await fetchImage(coverUrl);
				if (image) return image;
			} else {
				console.log('Cover needs to be generated');
				await triggerGithubAction(courseAlias, lang, overwrite, env.GITHUB_TOKEN, env.COURSE_COVER_KV);
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
