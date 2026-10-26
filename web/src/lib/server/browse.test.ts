import { sql, type Kysely } from 'kysely';
import { afterAll, expect, inject, test } from 'vitest';
import { createDb } from './db.js';
import type { DB } from './db-types.js';
import { performancePage, piecePage, playOrder, search, skaterPage } from './browse.js';

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
		expect(await search(trx, '羽生結弦')).toEqual({ skaters: [{ slug: 'yuzuru-hanyu', name: 'Yuzuru HANYU' }], teams: [], music: [], text: [] });
		expect(await search(trx, 'hanyu')).toEqual({
			skaters: [{ slug: 'yuzuru-hanyu', name: 'Yuzuru HANYU' }],
			teams: [{ slug: 'yuzuru-hanyu-someone-else', name: 'Yuzuru HANYU / Someone ELSE' }],
			music: [],
			text: []
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
			raw_text: 'Running by NF', origin: 'wikipedia', article_title: 'Ilia Malinin', revision: '1378424980', pieces: []
		});
		expect((await skaterPage(trx, 'ilia-malinin'))?.performances[0].music?.raw_text).toBe('Running by NF');
		await sql`insert into music_claims (program_id, origin, raw_text) values (${program_id}, 'admin', 'Corrected music')`.execute(trx);
		expect((await performancePage(trx, id))?.performance.music?.raw_text).toBe('Corrected music');
	}));

const programOf = async (trx: Kysely<DB>, performance_id: string) =>
	(await trx.selectFrom('performances').select('program_id').where('id', '=', performance_id).executeTakeFirstOrThrow()).program_id;

/** A Piece as the normaliser writes one: the record, its slug, its title and aliases as names, its composers, Source and QID. */
async function piece(
	trx: Kysely<DB>,
	title: string,
	slug: string,
	{ aliases = [] as string[], composers = [] as string[], source = '', qid = '' } = {}
) {
	const source_id = source
		? (await trx.insertInto('sources').values({ name: source }).returning('id').executeTakeFirstOrThrow()).id
		: null;
	const { id } = await trx.insertInto('pieces').values({ title, source_id }).returning('id').executeTakeFirstOrThrow();
	await trx.insertInto('keys').values({ system: 'slug', value: slug, entity: 'piece', entity_id: id }).execute();
	if (qid) await trx.insertInto('keys').values({ system: 'wikidata', value: qid, entity: 'piece', entity_id: id }).execute();
	await trx
		.insertInto('names')
		.values([title, ...aliases].map((name) => ({ entity: 'piece', entity_id: id, name, origin: 'wikipedia' })))
		.execute();
	for (const name of composers) {
		const artist = await trx.insertInto('artists').values({ name }).returning('id').executeTakeFirstOrThrow();
		await trx.insertInto('piece_artists').values({ piece_id: id, artist_id: artist.id, origin: 'wikipedia' }).execute();
	}
	return id;
}

type Use = [piece_id: string, grade: 'identified' | 'credited' | 'title only', performer_id?: string];

/** A Program's music claim of one origin, its entries graded and linked to Pieces in order. */
async function music(
	trx: Kysely<DB>, program_id: string, raw_text: string, uses: Use[], origin = 'wikipedia',
	attribution: { article_title?: string; revision?: string } = origin === 'wikipedia' ? { article_title: 'Some Skater', revision: '1234' } : {}
) {
	await trx.insertInto('music_claims').values({ program_id, origin, raw_text, ...attribution }).execute();
	const style = await trx
		.insertInto('styles')
		.values({ slug: 'original' })
		.onConflict((oc) => oc.column('slug').doUpdateSet({ slug: 'original' }))
		.returning('id')
		.executeTakeFirstOrThrow();
	for (const [position, [piece_id, grade, performer_id = null]] of uses.entries()) {
		const arrangement = await trx
			.insertInto('arrangements')
			.values({ piece_id, style_id: style.id, performer_id })
			.onConflict((oc) => oc.columns(['piece_id', 'style_id', 'performer_id']).doUpdateSet({ piece_id }))
			.returning('id')
			.executeTakeFirstOrThrow();
		await trx
			.insertInto('music_occurrences')
			.values({ program_id, origin, position, arrangement_id: arrangement.id, grade, raw_text })
			.execute();
	}
}

test('a music search finds the Piece with its grade mix: one best grade per Program', () =>
	rolledBack(async (trx) => {
		const her = await skater(trx, 'Anna PARTNER', 'anna-partner');
		const pirate = await piece(trx, "He's a Pirate", 'hes-a-pirate', { source: 'Pirates of the Caribbean' });
		await piece(trx, 'Swan Lake', 'swan-lake');
		const programs = [
			await programOf(trx, await performance(trx, { skater_id: her })),
			await programOf(trx, await performance(trx, { skater_id: her }, { segment_type: 'free skating' })),
			await programOf(trx, await performance(trx, { skater_id: her }, { segment_type: 'short dance' }))
		];
		await music(trx, programs[0], "He's a Pirate", [[pirate, 'identified']]);
		await music(trx, programs[1], "He's a Pirate by Klaus Badelt", [[pirate, 'credited']]);
		await music(trx, programs[2], "He's a Pirate; He's a Pirate (reprise) by Klaus Badelt", [[pirate, 'title only'], [pirate, 'credited']]);

		expect((await search(trx, 'pirate')).music).toEqual([
			{ slug: 'hes-a-pirate', title: "He's a Pirate", credit: 'Pirates of the Caribbean', programs: 3, grades: { identified: 1, credited: 2 } }
		]);
	}));

test("a Piece's alias, composer, performer or Source finds it, misspelled or unaccented", () =>
	rolledBack(async (trx) => {
		const her = await skater(trx, 'Anna PARTNER', 'anna-partner');
		const dorma = await piece(trx, 'Nessun dorma', 'nessun-dorma', { aliases: ['None shall sleep'], composers: ['Giacomo Puccini'], source: 'Turandot' });
		const { id: tenor } = await trx.insertInto('artists').values({ name: 'Luciano Pavarotti' }).returning('id').executeTakeFirstOrThrow();
		await music(trx, await programOf(trx, await performance(trx, { skater_id: her })), 'Nessun dorma sung by Pavarotti', [[dorma, 'credited', tenor]]);

		const hit = { slug: 'nessun-dorma', title: 'Nessun dorma', credit: 'Turandot', programs: 1, grades: { credited: 1 } };
		for (const query of ['none shall', 'pucini', 'pavarotti', 'turandot', 'nessún'])
			expect((await search(trx, query)).music, query).toEqual([hit]);
	}));

test("a Program's music is its winning claim's Pieces, in order with their grades; a Program only skated in gone Performances counts nowhere", () =>
	rolledBack(async (trx) => {
		const her = await skater(trx, 'Anna PARTNER', 'anna-partner');
		const pirate = await piece(trx, "He's a Pirate", 'hes-a-pirate');
		const swan = await piece(trx, 'Swan Lake', 'swan-lake', { composers: ['Pyotr Ilyich Tchaikovsky'] });
		const id = await performance(trx, { skater_id: her });
		const corrected = await programOf(trx, id);
		await music(trx, corrected, "He's a Pirate", [[pirate, 'identified']]);
		await music(trx, corrected, 'Swan Lake; Pirates', [[swan, 'credited'], [pirate, 'title only']], 'corrections');
		const gone = await programOf(trx, await performance(trx, { skater_id: her }, { segment_type: 'free skating', gone: true }));
		await music(trx, gone, 'Swan Lake', [[swan, 'identified']]);

		expect((await search(trx, 'pirate')).music).toMatchObject([{ programs: 1, grades: { 'title only': 1 } }]);
		expect((await search(trx, 'swan')).music).toMatchObject([{ programs: 1, grades: { credited: 1 } }]);
		const line = [
			{ slug: 'swan-lake', title: 'Swan Lake', grade: 'credited' },
			{ slug: 'hes-a-pirate', title: "He's a Pirate", grade: 'title only' }
		];
		expect((await performancePage(trx, id))?.performance.music?.pieces).toEqual(line);
		expect((await skaterPage(trx, 'anna-partner'))?.performances[0].music?.pieces).toEqual(line);
	}));

test('"In music text" finds the Programs whose text names the music but whose Pieces do not match it', () =>
	rolledBack(async (trx) => {
		const her = await skater(trx, 'Anna PARTNER', 'anna-partner');
		const him = await skater(trx, 'Boris PARTNER', 'boris-partner');
		const pair = await team(trx, her, him, 'Anna PARTNER / Boris PARTNER', 'anna-partner-boris-partner');
		const pirate = await piece(trx, "He's a Pirate", 'hes-a-pirate');
		const swan = await piece(trx, 'Swan Lake', 'swan-lake');
		const program = async (who: { skater_id: string } | { team_id: string }, segment_type: string, gone = false) =>
			programOf(trx, await performance(trx, who, { segment_type, gone }));
		await music(trx, await program({ skater_id: her }, 'short program'), "He's a Pirate from Pirates of the Caribbean", [[pirate, 'credited']]);
		const unparsed = await program({ skater_id: her }, 'free skating');
		await music(trx, unparsed, 'Pirates of the Caribbean medley', []);
		const mislinked = await program({ skater_id: her }, 'short dance');
		await music(trx, mislinked, "Swan Lake; He's a Pirate", [[swan, 'credited']]);
		await music(trx, await program({ skater_id: her }, 'free dance', true), 'Pirates', []);
		const teams = await program({ team_id: pair }, 'free skating');
		await music(trx, teams, 'The Pirates', []);

		const { text } = await search(trx, 'pirate');

		expect(text).toHaveLength(3);
		expect(text).toEqual(
			expect.arrayContaining([
				{ program_id: unparsed, entity: 'skater', slug: 'anna-partner', name: 'Anna PARTNER', season: 2025, segment_type: 'free skating' },
				{ program_id: mislinked, entity: 'skater', slug: 'anna-partner', name: 'Anna PARTNER', season: 2025, segment_type: 'short dance' },
				{ program_id: teams, entity: 'team', slug: 'anna-partner-boris-partner', name: 'Anna PARTNER / Boris PARTNER', season: 2025, segment_type: 'free skating' }
			])
		);
	}));

test("a Piece page groups the Programs using it by Skater or Team, each with its grade, raw text, Wikipedia article and Performances not marked gone", () =>
	rolledBack(async (trx) => {
		const her = await skater(trx, 'Anna PARTNER', 'anna-partner');
		const him = await skater(trx, 'Boris PARTNER', 'boris-partner');
		const pair = await team(trx, her, him, 'Anna PARTNER / Boris PARTNER', 'anna-partner-boris-partner');
		const pirate = await piece(trx, "He's a Pirate", 'hes-a-pirate', {
			composers: ['Klaus Badelt', 'Hans Zimmer'], source: 'Pirates of the Caribbean', qid: 'Q1129221'
		});
		const singles = await performance(trx, { skater_id: her }, { rank: 4 });
		const program = await programOf(trx, singles);
		await performance(trx, { skater_id: her }, { program_id: program, gone: true });
		await trx.insertInto('performance_videos').values({ youtube_id: 'clip', start_seconds: 0, performance_id: singles, origin: 'official' }).execute();
		await music(trx, program, "He's a Pirate by Klaus Badelt; He's a Pirate (reprise)", [[pirate, 'title only'], [pirate, 'credited']]);
		const pairs = await performance(trx, { team_id: pair }, { segment_type: 'free skating' });
		// A corrections alias claim copies Wikipedia's text, so it keeps the article for attribution.
		await music(trx, await programOf(trx, pairs), 'Pirates', [[pirate, 'title only']], 'corrections', { article_title: 'Some Team', revision: '99' });
		await music(trx, await programOf(trx, await performance(trx, { skater_id: him }, { gone: true })), "He's a Pirate", [[pirate, 'identified']]);

		const page = await piecePage(trx, 'hes-a-pirate');

		expect(page?.piece).toEqual({
			title: "He's a Pirate", slug: 'hes-a-pirate', source: 'Pirates of the Caribbean', qid: 'Q1129221', composers: ['Hans Zimmer', 'Klaus Badelt']
		});
		const competition = 'Grand Prix Final';
		expect(page?.owners).toEqual([
			{
				entity: 'skater', slug: 'anna-partner', name: 'Anna PARTNER',
				programs: [{
					id: program, season: 2025, segment_type: 'short program', grade: 'credited',
					raw_text: "He's a Pirate by Klaus Badelt; He's a Pirate (reprise)", origin: 'wikipedia', article_title: 'Some Skater', revision: '1234',
					performances: [{ id: singles, competition, rank: 4, rank_label: null, video: true }]
				}]
			},
			{
				entity: 'team', slug: 'anna-partner-boris-partner', name: 'Anna PARTNER / Boris PARTNER',
				programs: [{
					id: await programOf(trx, pairs), season: 2025, segment_type: 'free skating', grade: 'title only',
					raw_text: 'Pirates', origin: 'corrections', article_title: 'Some Team', revision: '99',
					performances: [{ id: pairs, competition, rank: 1, rank_label: null, video: false }]
				}]
			}
		]);
		expect(await piecePage(trx, 'nothing')).toBeUndefined();
	}));
