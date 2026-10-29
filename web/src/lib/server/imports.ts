import { sql, type Kysely } from 'kysely';
import type { DB } from './db-types.js';

/**
 * "Quick Import" or "Full Import": queues a `pending` Import for the import service, unless one is already queued.
 * A quick Import re-checks only the two newest listed Seasons' ISU pages; a full one every page.
 */
export async function queueImport(db: Kysely<DB>, scope: 'quick' | 'full') {
	await db.transaction().execute(async (trx) => {
		// Serialises concurrent presses so `not exists` can't race. Not the runner's 'import' lock,
		// which is held for the whole apply phase.
		await sql`select pg_advisory_xact_lock(hashtext('import now'))`.execute(trx);
		await sql`insert into imports (status, scope) select 'pending', ${scope}
			where not exists (select from imports where status = 'pending')`.execute(trx);
	});
}

// The Import's youtube.REFRESH_DAYS: it refreshes rows older than that, and the API terms allow 30.
const YOUTUBE_REFRESH_DAYS = 25;

/** When the oldest YouTube cache row was refreshed, if over YOUTUBE_REFRESH_DAYS ago, else null. */
export async function youtubeCacheStaleSince(db: Kysely<DB>) {
	const row = await db
		.selectFrom('youtube_videos')
		.select((eb) => eb.fn.min('refreshed_at').as('oldest'))
		.where('refreshed_at', '<', sql<Date>`now() - make_interval(days => ${YOUTUBE_REFRESH_DAYS})`)
		.executeTakeFirst();
	return row?.oldest ?? null;
}

/** The current (pending or running) and last finished Import, and the last one's problems grouped by kind. */
export async function importStatus(db: Kysely<DB>) {
	const latest = (statuses: string[]) =>
		db
			.selectFrom('imports')
			.selectAll()
			.where('status', 'in', statuses)
			// 'running' sorts before 'pending', so a running Import shows over one queued behind it.
			.orderBy('status', 'desc')
			.orderBy('id', 'desc')
			.limit(1)
			.executeTakeFirst();
	const [current, last] = await Promise.all([latest(['pending', 'running']), latest(['succeeded', 'failed'])]);

	const rows = last
		? await db
				.selectFrom('import_problems')
				.select(['kind', 'key', 'detail'])
				.where('import_id', '=', last.id)
				.orderBy('kind')
				.orderBy('id')
				.execute()
		: [];
	const problems: { kind: string; rows: { key: string; detail: unknown }[] }[] = [];
	for (const { kind, key, detail } of rows) {
		if (problems.at(-1)?.kind !== kind) problems.push({ kind, rows: [] });
		problems.at(-1)!.rows.push({ key, detail });
	}
	return { current, last, problems };
}
