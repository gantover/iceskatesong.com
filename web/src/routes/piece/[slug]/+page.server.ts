import { error } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { PUBLIC_CACHE, piecePage } from '#lib/server/browse.js';

export const load = async ({ params, setHeaders }) => {
	const page = await piecePage(db, params.slug);
	if (!page) error(404);
	setHeaders(PUBLIC_CACHE);
	return page;
};
