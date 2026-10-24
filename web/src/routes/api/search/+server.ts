import { json } from '@sveltejs/kit';
import { db } from '#lib/server/db.js';
import { PUBLIC_CACHE, search } from '#lib/server/browse.js';

// The search box's as-you-type dropdown.
export const GET = async ({ url }) => json(await search(db, url.searchParams.get('q') ?? ''), { headers: PUBLIC_CACHE });
