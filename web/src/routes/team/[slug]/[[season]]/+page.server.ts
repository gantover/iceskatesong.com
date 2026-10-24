import { error } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { PUBLIC_CACHE, pickSeason, teamPage } from '#lib/server/browse.js';

export const load = async ({ params, setHeaders }) => {
	const page = await teamPage(db, params.slug);
	const season = page && pickSeason(page.performances, params.season);
	if (!season) error(404);
	setHeaders(PUBLIC_CACHE);
	return { team: page.team, skaters: page.skaters, ...season };
};
