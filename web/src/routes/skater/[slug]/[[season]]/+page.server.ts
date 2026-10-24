import { error } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { PUBLIC_CACHE, pickSeason, skaterPage } from '#lib/server/browse.js';

export const load = async ({ params, setHeaders }) => {
	const page = await skaterPage(db, params.slug);
	if (!page) error(404);
	setHeaders(PUBLIC_CACHE);
	return { skater: page.skater, ...pickSeason(page.performances, params.season) };
};
