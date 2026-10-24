import { sql, type Kysely } from 'kysely';
import type { DB } from './db-types.js';

/** "Import now": queues a `pending` Import for the import service, unless one is already queued. */
export async function queueImport(db: Kysely<DB>) {
	await db.transaction().execute(async (trx) => {
		// Serialises concurrent presses so `not exists` can't race. Not the runner's 'import' lock,
		// which is held for the whole apply phase.
		await sql`select pg_advisory_xact_lock(hashtext('import now'))`.execute(trx);
		await sql`insert into imports (status) select 'pending'
			where not exists (select from imports where status = 'pending')`.execute(trx);
	});
}

/** When the oldest YouTube cache row was refreshed, if over 25 days ago (the API terms allow 30), else null. */
export async function youtubeCacheStaleSince(db: Kysely<DB>) {
	const row = await db
		.selectFrom('youtube_videos')
		.select((eb) => eb.fn.min('refreshed_at').as('oldest'))
		.where('refreshed_at', '<', sql<Date>`now() - interval '25 days'`)
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
