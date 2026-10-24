import { error } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { performancePage } from '#lib/server/browse.js';

export const load = async ({ params, request, setHeaders }) => {
	// A bigint id, else 404 instead of a cast error.
	const page = /^\d{1,18}$/.test(params.id) && (await performancePage(db, params.id, request.headers.get('cf-ipcountry')));
	if (!page) error(404);
	// The play order depends on the visitor's country: no shared cache may keep it.
	setHeaders({ 'cache-control': 'private, max-age=300' });
	return page;
};
