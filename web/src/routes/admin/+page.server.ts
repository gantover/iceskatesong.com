import { db } from '#lib/server/db.js';
import { importStatus, queueImport, youtubeCacheStaleSince } from '#lib/server/imports.js';

// hooks.server.ts checks the Cloudflare Access JWT on every /admin request, actions included.
export const load = async () => ({
	...(await importStatus(db)),
	youtubeStaleSince: await youtubeCacheStaleSince(db)
});

export const actions = {
	importNow: () => queueImport(db)
};
