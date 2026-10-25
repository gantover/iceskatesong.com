import { error } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { PUBLIC_CACHE, performancePage } from '#lib/server/browse.js';

export const load = async ({ params, setHeaders }) => {
	// A bigint id, else 404 instead of a cast error.
	const page = /^\d{1,18}$/.test(params.id) && (await performancePage(db, params.id));
	if (!page) error(404);
	setHeaders(PUBLIC_CACHE);
	return page;
};
