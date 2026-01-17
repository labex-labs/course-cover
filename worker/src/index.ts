const DEFAULT_COVER = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover@master/default.png';
const JSDELIVR_BASE = 'https://cdn.jsdelivr.net/gh/labex-labs/course-cover@latest/public';

interface Env { }

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
		const headers = new Headers({
			'content-type': contentType || 'image/png',
			'cache-control': 'public, max-age=2592000',
		});

		return new Response(response.body, { headers });
	} catch {
		return null;
	}
}


export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		try {
			const url = new URL(request.url);

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
			const supportedLangs = new Set(['en', 'zh', 'es', 'fr', 'de', 'ja', 'ru', 'ko', 'pt']);

			// Validate query parameters strictly
			const allowedParams = new Set(['lang']);
			const receivedParams = new Set(url.searchParams.keys());

			// Check for any unsupported parameters
			for (const param of receivedParams) {
				if (!allowedParams.has(param)) {
					return new Response(`Unsupported parameter: ${param}`, { status: 400 });
				}
			}

			// Validate language parameter
			let lang = url.searchParams.get('lang') || 'en';
			if (!supportedLangs.has(lang)) {
				lang = 'en';
			}

			// Extract course alias from path
			const match = url.pathname.match(/\/([a-z0-9-]+)\.png$/);
			if (!match) {
				console.log(`[GET ${url.pathname}] result=invalid_path, fallback=default`);
				const defaultImage = await fetchImage(DEFAULT_COVER);
				return defaultImage || new Response('Image not found', { status: 404 });
			}

			const courseAlias = match[1];

			// Construct cover URL
			const coverUrl = `${JSDELIVR_BASE}/${lang}/${courseAlias}.png`;

			// Check if cover exists
			const coverExists = await checkImageExists(coverUrl);

			if (coverExists) {
				console.log(`[GET ${url.pathname}] course=${courseAlias}, lang=${lang}, result=exists, url=${coverUrl}`);
				const image = await fetchImage(coverUrl);
				if (image) return image;
			}

			// If cover doesn't exist, return default cover
			console.log(`[GET ${url.pathname}] course=${courseAlias}, lang=${lang}, result=not_found, fallback=default`);
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		} catch (error) {
			const url = new URL(request.url);
			console.error(`[GET ${url.pathname}] result=error, message=${error instanceof Error ? error.message : String(error)}, fallback=default`);
			const defaultImage = await fetchImage(DEFAULT_COVER);
			return defaultImage || new Response('Image not found', { status: 404 });
		}
	},
} satisfies ExportedHandler<Env>;
