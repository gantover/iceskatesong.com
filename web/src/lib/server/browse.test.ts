import { sql, type Kysely } from 'kysely';
import { afterAll, expect, inject, test } from 'vitest';
import { createDb } from './db.js';
import type { DB } from './db-types.js';
import { performancePage, playOrder, search, skaterPage } from './browse.js';

const db = createDb(inject('databaseUrl'));
afterAll(() => db.destroy());

// Test files share one database: each test's rows are rolled back.
async function rolledBack(fn: (trx: Kysely<DB>) => Promise<void>) {
	const trx = await db.startTransaction().execute();
	try {
		await fn(trx);
	} finally {
		await trx.rollback().execute();
	}
}

/** A Skater as the Import writes one: the record, its display name as an 'isu' name, and a slug. */
async function skater(trx: Kysely<DB>, name: string, slug: string, aliases: string[] = []) {
	const { id } = await trx.insertInto('skaters').values({ name, nation: 'FRA' }).returning('id').executeTakeFirstOrThrow();
	await trx
		.insertInto('names')
		.values([{ name, origin: 'isu' }, ...aliases.map((alias) => ({ name: alias, origin: 'wikidata' }))].map((n) => ({ ...n, entity: 'skater', entity_id: id })))
		.execute();
	await trx.insertInto('keys').values({ system: 'slug', value: slug, entity: 'skater', entity_id: id }).execute();
	return id;
}

async function team(trx: Kysely<DB>, skater1_id: string, skater2_id: string, name: string, slug: string) {
	const { id } = await trx.insertInto('teams').values({ name, skater1_id, skater2_id }).returning('id').executeTakeFirstOrThrow();
	await trx.insertInto('names').values({ entity: 'team', entity_id: id, name, origin: 'isu' }).execute();
	await trx.insertInto('keys').values({ system: 'slug', value: slug, entity: 'team', entity_id: id }).execute();
	return id;
}

const names = (hits: { name: string }[]) => hits.map((h) => h.name);

test('a query without accents finds the accented name', () =>
	rolledBack(async (trx) => {
		await skater(trx, 'Kévin AYMOZ', 'kevin-aymoz');
		expect(names((await search(trx, 'kevin aym')).skaters)).toEqual(['Kévin AYMOZ']);
	}));

test('a typo finds the name, the closest first', () =>
	rolledBack(async (trx) => {
		await skater(trx, 'Aleksandr PLIUSHCHENKO', 'aleksandr-pliushchenko');
		await skater(trx, 'Evgeni PLUSHENKO', 'evgeni-plushenko');
		expect(names((await search(trx, 'plushchenko')).skaters)).toEqual(['Evgeni PLUSHENKO', 'Aleksandr PLIUSHCHENKO']);
	}));

test('under 3 characters, only the start of a word matches', () =>
	rolledBack(async (trx) => {
		await skater(trx, 'Kévin AYMOZ', 'kevin-aymoz');
		expect(names((await search(trx, 'ay')).skaters)).toEqual(['Kévin AYMOZ']);
		expect(names((await search(trx, 'K')).skaters)).toEqual(['Kévin AYMOZ']);
		expect(names((await search(trx, 'ev')).skaters)).toEqual([]);
	}));

test('LIKE wildcards in the query are plain characters', () =>
	rolledBack(async (trx) => {
		await skater(trx, 'Kévin AYMOZ', 'kevin-aymoz');
		expect(names((await search(trx, '%')).skaters)).toEqual([]);
		expect(names((await search(trx, 'k_vin')).skaters)).toEqual([]);
	}));

test('an alias finds its Skater once, and Teams come in their own group', () =>
	rolledBack(async (trx) => {
		const yuzuru = await skater(trx, 'Yuzuru HANYU', 'yuzuru-hanyu', ['羽生結弦', 'Hanyu Yuzuru']);
		const other = await skater(trx, 'Someone ELSE', 'someone-else');
		await team(trx, yuzuru, other, 'Yuzuru HANYU / Someone ELSE', 'yuzuru-hanyu-someone-else');
		expect(await search(trx, '羽生結弦')).toEqual({ skaters: [{ slug: 'yuzuru-hanyu', name: 'Yuzuru HANYU' }], teams: [] });
		expect(await search(trx, 'hanyu')).toEqual({
			skaters: [{ slug: 'yuzuru-hanyu', name: 'Yuzuru HANYU' }],
			teams: [{ slug: 'yuzuru-hanyu-someone-else', name: 'Yuzuru HANYU / Someone ELSE' }]
		});
	}));

const video = (youtube_id: string, start_seconds: number | null, origin = 'official') => ({ youtube_id, start_seconds, origin });
const ids = (videos: { youtube_id: string }[]) => videos.map((v) => v.youtube_id);

test('clips and timed streams play first, untimed streams last, each in origin order', () => {
	const order = playOrder(
		[video('untimed-official', null), video('clip-submitted', 0, 'submitted'), video('timed-admin', 95, 'admin'), video('untimed-admin', null, 'admin'), video('clip-official', 0)]
	);
	expect(ids(order)).toEqual(['clip-official', 'timed-admin', 'clip-submitted', 'untimed-official', 'untimed-admin']);
});

/** One Segment of a new Competition, and a Performance in it of a Skater or Team: of a new Program unless `program_id` is given. */
async function performance(
	trx: Kysely<DB>,
	who: { skater_id: string } | { team_id: string },
	{ discipline = 'men', segment_type = 'short program', gone = false, rank = 1, program_id = '' } = {}
) {
	const competition = await trx
		.insertInto('competitions')
		.values({ name: 'Grand Prix Final', city: 'Nagoya', start_date: '2025-12-04', end_date: '2025-12-07', level: 'senior' })
		.returning('id')
		.executeTakeFirstOrThrow();
	const segment = await trx
		.insertInto('segments')
		.values({ competition_id: competition.id, discipline, level: 'senior', segment_type, url: 'https://results.isu.org/x' })
		.returning('id')
		.executeTakeFirstOrThrow();
	const program = program_id
		? { id: program_id }
		: await trx.insertInto('programs').values({ ...who, season: 2025, segment_type }).returning('id').executeTakeFirstOrThrow();
	const { id } = await trx
		.insertInto('performances')
		.values({ ...who, segment_id: segment.id, program_id: program.id, entry_key: 'k', name: 'n', nation: 'FRA', rank, tss: '90.12', gone })
		.returning('id')
		.executeTakeFirstOrThrow();
	return id;
}

test("a Skater's page lists their Team's Performances, without gone Performances or hidden videos", () =>
	rolledBack(async (trx) => {
		const her = await skater(trx, 'Anna PARTNER', 'anna-partner');
		const him = await skater(trx, 'Boris PARTNER', 'boris-partner');
		const pair = await team(trx, her, him, 'Anna PARTNER / Boris PARTNER', 'anna-partner-boris-partner');
		const singles = await performance(trx, { skater_id: her }, { discipline: 'women', rank: 3 });
		const pairs = await performance(trx, { team_id: pair }, { discipline: 'pairs', segment_type: 'free skating' });
		await performance(trx, { skater_id: her }, { discipline: 'women', segment_type: 'free skating', gone: true });
		await trx
			.insertInto('performance_videos')
			.values([
				{ youtube_id: 'clip', start_seconds: 0, performance_id: singles, origin: 'official' },
				{ youtube_id: 'hidden', start_seconds: 0, performance_id: pairs, origin: 'official', status: 'hidden' }
			])
			.execute();

		const page = await skaterPage(trx, 'anna-partner');

		expect(page?.skater).toMatchObject({ name: 'Anna PARTNER' });
		expect(page?.performances.map((p) => ({ id: p.id, rank: p.rank, team: p.team, video: p.video }))).toEqual([
			{ id: singles, rank: 3, team: null, video: true },
			{ id: pairs, rank: 1, team: { slug: 'anna-partner-boris-partner', name: 'Anna PARTNER / Boris PARTNER' }, video: false }
		]);
		expect(await skaterPage(trx, 'nobody')).toBeUndefined();
	}));

test('a Performance page shows its active videos in play order and its Program\'s other Performances, never a gone one', () =>
	rolledBack(async (trx) => {
		const her = await skater(trx, 'Anna PARTNER', 'anna-partner');
		const page = await performance(trx, { skater_id: her });
		const { program_id } = await trx.selectFrom('performances').select('program_id').where('id', '=', page).executeTakeFirstOrThrow();
		const other = await performance(trx, { skater_id: her }, { program_id, rank: 2 });
		const gone = await performance(trx, { skater_id: her }, { program_id, gone: true });
		await trx
			.insertInto('performance_videos')
			.values([
				{ youtube_id: 'perf-page-stream', start_seconds: null, performance_id: page, origin: 'official' },
				{ youtube_id: 'perf-page-clip', start_seconds: 0, performance_id: page, origin: 'official' },
				{ youtube_id: 'perf-page-hidden', start_seconds: 0, performance_id: page, origin: 'official', status: 'hidden' },
				{ youtube_id: 'perf-page-other', start_seconds: 0, performance_id: other, origin: 'official' }
			])
			.execute();
		// Only the clip has a YouTube cache row: the stream's has expired, and its link stays.
		await trx
			.insertInto('youtube_videos')
			.values({ youtube_id: 'perf-page-clip', title: 'GPF clip', channel_id: 'c', published_at: new Date(), duration_seconds: 300, embeddable: true, made_for_kids: false, refreshed_at: new Date() })
			.execute();

		const shown = await performancePage(trx, page);

		expect(shown?.performance).toMatchObject({ name: 'Anna PARTNER', entity: 'skater', slug: 'anna-partner', url: 'https://results.isu.org/x' });
		expect(shown?.videos.map((v) => [v.youtube_id, v.title])).toEqual([
			['perf-page-clip', 'GPF clip'],
			['perf-page-stream', null]
		]);
		expect(shown?.sameProgram.map((p) => ({ id: p.id, video: p.video }))).toEqual([{ id: other, video: true }]);
		expect(await performancePage(trx, gone)).toBeUndefined();
	}));

test('a Program shows its raw Wikipedia music and revision on the Performance and Skater pages, with human music taking precedence', () =>
	rolledBack(async (trx) => {
		const owner = await skater(trx, 'Ilia MALININ', 'ilia-malinin');
		const id = await performance(trx, { skater_id: owner });
		const { program_id } = await trx.selectFrom('performances').select('program_id').where('id', '=', id).executeTakeFirstOrThrow();
		await sql`insert into music_claims (program_id, origin, raw_text, article_title, revision)
			values (${program_id}, 'wikipedia', 'Running by NF', 'Ilia Malinin', 1378424980)`.execute(trx);

		expect((await performancePage(trx, id))?.performance.music).toEqual({
			raw_text: 'Running by NF', origin: 'wikipedia', article_title: 'Ilia Malinin', revision: '1378424980'
		});
		expect((await skaterPage(trx, 'ilia-malinin'))?.performances[0].music?.raw_text).toBe('Running by NF');
		await sql`insert into music_claims (program_id, origin, raw_text) values (${program_id}, 'admin', 'Corrected music')`.execute(trx);
		expect((await performancePage(trx, id))?.performance.music?.raw_text).toBe('Corrected music');
	}));
