import { sql } from 'kysely';
import { afterAll, beforeEach, expect, inject, test } from 'vitest';
import { createDb } from './db.js';
import { importStatus, queueImport, youtubeCacheStaleSince } from './imports.js';

const db = createDb(inject('databaseUrl'));
afterAll(() => db.destroy());
beforeEach(() => db.deleteFrom('imports').execute());

const pendingCount = async () =>
	(await db.selectFrom('imports').where('status', '=', 'pending').select('id').execute()).length;

test('an Import press queues one pending Import, even when pressed many times at once', async () => {
	// Open the pool's connections first, so the presses overlap instead of queueing behind connects.
	await Promise.all(Array.from({ length: 10 }, () => sql`select pg_sleep(0.05)`.execute(db)));
	await Promise.all(Array.from({ length: 10 }, () => queueImport(db, 'full')));
	await queueImport(db, 'full');
	expect(await pendingCount()).toBe(1);
});

test('an Import press queues behind a running Import', async () => {
	await db.insertInto('imports').values({ status: 'running' }).execute();
	await queueImport(db, 'full');
	expect(await pendingCount()).toBe(1);
});

test('a quick Import is queued and shown as quick', async () => {
	await queueImport(db, 'quick');
	expect((await importStatus(db)).current).toMatchObject({ status: 'pending', scope: 'quick' });
});

test('status shows the current and last Import, and the last one\'s problems grouped by kind', async () => {
	const [old, last] = await db
		.insertInto('imports')
		.values([
			{ status: 'failed', error: 'interrupted' },
			{ status: 'succeeded', problem_count: 3, counts: JSON.stringify({ skater: { created: 2, updated: 1 } }) }
		])
		.returning('id')
		.execute();
	await db.insertInto('imports').values({ status: 'running' }).execute();
	await db
		.insertInto('import_problems')
		.values([
			{ import_id: old.id, step: 'fetch', kind: 'fetch failed', key: 'https://old' },
			{ import_id: last.id, step: 'isu', kind: 'parse failed', key: 'https://a', detail: JSON.stringify({ error: 'x' }) },
			{ import_id: last.id, step: 'fetch', kind: 'fetch failed', key: 'https://b' },
			{ import_id: last.id, step: 'isu', kind: 'parse failed', key: 'https://c' }
		])
		.execute();

	const status = await importStatus(db);

	expect(status.current).toMatchObject({ status: 'running' });
	expect(status.last).toMatchObject({ status: 'succeeded', problem_count: 3, counts: { skater: { created: 2, updated: 1 } } });
	expect(status.problems).toEqual([
		{ kind: 'fetch failed', rows: [{ key: 'https://b', detail: {} }] },
		{
			kind: 'parse failed',
			rows: [
				{ key: 'https://a', detail: { error: 'x' } },
				{ key: 'https://c', detail: {} }
			]
		}
	]);
});

test('status with no Imports yet', async () => {
	expect(await importStatus(db)).toEqual({ current: undefined, last: undefined, problems: [] });
});

test('the YouTube cache is stale when its oldest row is older than 25 days', async () => {
	await db.deleteFrom('youtube_videos').execute();
	expect(await youtubeCacheStaleSince(db)).toBeNull();

	const row = (youtube_id: string, days: number) => ({
		youtube_id,
		title: 't',
		channel_id: 'c',
		published_at: new Date(),
		duration_seconds: 300,
		embeddable: true,
		made_for_kids: false,
		refreshed_at: new Date(Date.now() - days * 86_400_000)
	});
	await db.insertInto('youtube_videos').values([row('a', 1), row('b', 24)]).execute();
	expect(await youtubeCacheStaleSince(db)).toBeNull();

	await db.insertInto('youtube_videos').values(row('c', 26)).execute();
	const since = await youtubeCacheStaleSince(db);
	expect(Math.round((Date.now() - since!.getTime()) / 86_400_000)).toBe(26);
});
