import { db } from '#lib/server/db.js';
import { PUBLIC_CACHE, search } from '#lib/server/browse.js';

// The search box's form target: Enter, or a browser without JavaScript.
export const load = async ({ url, setHeaders }) => {
	setHeaders(PUBLIC_CACHE);
	const q = url.searchParams.get('q') ?? '';
	return { q, hits: await search(db, q) };
};
