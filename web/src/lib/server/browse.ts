import { sql, type Kysely, type RawBuilder } from 'kysely';
import type { DB } from './db-types.js';

export type Hit = { slug: string; name: string };

// Public pages show only Import data, which changes when the Admin runs an Import.
export const PUBLIC_CACHE = { 'cache-control': 'public, max-age=300' };

export type Grade = 'identified' | 'credited' | 'title only';

/** A Piece found by a music search, with how many Programs use it and how well each link is backed. */
export type MusicHit = {
	slug: string;
	title: string;
	/** Its Source, else its composers. */
	credit: string | null;
	programs: number;
	grades: Partial<Record<Grade, number>>;
};

/** A Program whose music text matches a search though none of its Pieces does. */
export type TextHit = Hit & { program_id: string; entity: 'skater' | 'team'; season: number; segment_type: string };

// Best first.
const GRADES = sql.lit('{identified,credited,title only}');

// The query as a search_key (q) and as a LIKE pattern (esc).
const searchQ = (q: string) => sql`q as (select q, replace(replace(replace(q, '\\', '\\\\'), '%', '\\%'), '_', '\\_') as esc
	from f_unaccent(lower(${q})) as q)`;

// From 3 characters a substring or a close spelling, below that the start of a word.
// Chosen here rather than in a SQL case, so Postgres plans only the branch that applies.
const matches = (key: string, query: string) =>
	[...query].length >= 3
		? sql`(${sql.ref(key)} like '%' || esc || '%' or q <% ${sql.ref(key)})`
		: sql`(${sql.ref(key)} like esc || '%' or ${sql.ref(key)} like '% ' || esc || '%')`;

/**
 * Skaters and Teams whose name or alias matches, and Pieces whose title, alias, Artist or Source matches,
 * accents and case ignored: from 3 characters a substring or a close spelling, below that the start of a word.
 * How search, the Piece page and music lines behave, and why: docs/search.md.
 */
export async function search(db: Kysely<DB>, query: string) {
	const q = query.trim().slice(0, 100);
	if (!q) return { skaters: [], teams: [], music: [], text: [] };
	// The matching Pieces as hit(piece_id, substring, similarity).
	const pieceHits = sql`
		named as (
			select 'piece' as entity, id, search_key from pieces, q where ${matches('search_key', q)}
			union all select 'artist', id, search_key from artists, q where ${matches('search_key', q)}
			union all select 'source', id, search_key from sources, q where ${matches('search_key', q)}
			union all select entity, entity_id, search_key from names, q
				where entity in ('piece', 'artist', 'source') and ${matches('search_key', q)}
		),
		hit as (
			-- An Artist or Source finds its Pieces. One row per Piece: its best-matching name.
			select piece_id, max((search_key like '%' || esc || '%')::int) as substring, max(word_similarity(q, search_key)) as similarity
			from (
				select id as piece_id, search_key from named where entity = 'piece'
				union all select pa.piece_id, named.search_key from named join piece_artists pa on pa.artist_id = named.id where entity = 'artist'
				union all select a.piece_id, named.search_key from named join arrangements a on a.performer_id = named.id where entity = 'artist'
				union all select p.id, named.search_key from named join pieces p on p.source_id = named.id where entity = 'source'
			) found, q
			group by piece_id
		)`;
	// The recall guarantee: music text that names what was searched, on Programs none of whose Pieces matched.
	// The tsvector expression is the one migration 0007 indexes.
	const textHits = sql<TextHit>`
		with ${searchQ(q)}, ${pieceHits}
		select m.program_id, case when pr.team_id is null then 'skater' else 'team' end as entity,
			coalesce(s.name, t.name) as name, coalesce(${slugOf('skater', 's.id')}, ${slugOf('team', 't.id')}) as slug,
			pr.season, pr.segment_type
		from music_claims m
		join programs pr on pr.id = m.program_id
		left join skaters s on s.id = pr.skater_id
		left join teams t on t.id = pr.team_id
		where to_tsvector('english', m.raw_text) @@ websearch_to_tsquery('english', ${q})
			and m.origin = ${topClaim('m.program_id')}
			and exists (select from performances p where p.program_id = m.program_id and not p.gone)
			and not exists (select from ${currentMusic} u join hit using (piece_id) where u.program_id = m.program_id)
		order by ts_rank(to_tsvector('english', m.raw_text), websearch_to_tsquery('english', ${q})) desc, pr.season desc, m.program_id
		limit 8
	`.execute(db);
	const musicHits = sql<MusicHit>`
		with ${searchQ(q)}, ${pieceHits},
		used as (
			-- One grade per Program and Piece: its best.
			select u.piece_id, u.program_id, min(array_position(${GRADES}::text[], u.grade)) as best
			from ${currentMusic} u join hit using (piece_id)
			group by u.piece_id, u.program_id
		),
		graded as (
			select piece_id, sum(n)::int as programs, json_object_agg((${GRADES}::text[])[best], n) as grades
			from (select piece_id, best, count(*)::int as n from used group by piece_id, best) g
			group by piece_id
		),
		shown as (
			-- Ranked before the per-Piece lookups, so those run for 8 rows, not every hit.
			select p.id, p.title, p.source_id, hit.substring, hit.similarity,
				coalesce(graded.programs, 0) as programs, coalesce(graded.grades, '{}') as grades
			from hit
			join pieces p on p.id = hit.piece_id
			left join graded using (piece_id)
			order by substring desc, similarity desc, programs desc, p.title
			limit 8
		)
		select ${slugOf('piece', 'shown.id')} as slug, shown.title,
			coalesce(s.name, (select string_agg(distinct a.name, ', ') from piece_artists pa join artists a on a.id = pa.artist_id
				where pa.piece_id = shown.id)) as credit,
			shown.programs, shown.grades
		from shown
		left join sources s on s.id = shown.source_id
		order by substring desc, similarity desc, programs desc, shown.title
	`.execute(db);
	const ownerHits = sql<Hit & { entity: 'skater' | 'team' }>`
		with ${searchQ(q)},
		hit as (
			-- One row per record: its best-matching name. Substring matches rank above close spellings.
			select entity, entity_id,
				max((search_key like '%' || esc || '%')::int) as substring,
				max(word_similarity(q, search_key)) as similarity
			from names, q
			where entity in ('skater', 'team') and ${matches('search_key', q)}
			group by entity, entity_id
		)
		select entity, name, slug from (
			select hit.entity, coalesce(s.name, t.name) as name,
				coalesce(${slugOf('skater', 's.id')}, ${slugOf('team', 't.id')}) as slug,
				row_number() over (partition by hit.entity order by substring desc, similarity desc, coalesce(s.name, t.name)) as n
			from hit
			left join skaters s on hit.entity = 'skater' and s.id = hit.entity_id
			left join teams t on hit.entity = 'team' and t.id = hit.entity_id
		) ranked
		where n <= 8
		order by n
	`.execute(db);
	const [{ rows: text }, { rows: music }, { rows }] = await Promise.all([textHits, musicHits, ownerHits]);
	return {
		skaters: rows.filter((r) => r.entity === 'skater').map(({ slug, name }) => ({ slug, name })),
		teams: rows.filter((r) => r.entity === 'team').map(({ slug, name }) => ({ slug, name })),
		music,
		text
	};
}

const ORIGINS = ['official', 'admin', 'submitted'];

/**
 * A Performance's videos in play order: clips and timed streams, then untimed streams, each in origin order.
 * Geo-blocked videos stay in: the page is the same for every visitor, and YouTube tells a blocked one.
 */
export function playOrder<V extends { start_seconds: number | null; origin: string }>(videos: V[]) {
	const rank = (v: V) => (v.start_seconds === null ? ORIGINS.length : 0) + ORIGINS.indexOf(v.origin);
	return videos.toSorted((a, b) => rank(a) - rank(b));
}

// A Season's Segments in skating order.
const SEGMENT_ORDER = sql.lit(
	'{compulsory dance,original dance,short program,short dance,rhythm dance,free skating,free dance}'
);

// Merges (R2) can leave a record with several slugs: link the same one every time.
const slugOf = (entity: 'skater' | 'team' | 'piece', id: string) =>
	sql<string>`(select min(value) from keys k where k.system = 'slug' and k.entity = ${entity} and k.entity_id = ${sql.ref(id)})`;

/** A music line: the Pieces of one music claim in order, each with its grade. */
export type PieceUse = { slug: string; title: string; grade: Grade };

export type MusicClaim = {
	raw_text: string;
	origin: string;
	article_title: string | null;
	revision: string | null;
	pieces: PieceUse[];
};

// A Program's music is its highest-precedence claim (ADR 0002).
// Its own alias, so a caller's `m.program_id` still names the caller's row.
const topClaim = (program: string) => sql`(select top.origin from music_claims top where top.program_id = ${sql.ref(program)}
	order by array_position('{admin,corrections,submitted,wikipedia,isu}'::text[], top.origin) limit 1)`;

const musicOf = (program: string) => sql<MusicClaim | null>`(
	select json_build_object('raw_text', m.raw_text, 'origin', m.origin,
		'article_title', m.article_title, 'revision', m.revision::text,
		'pieces', (select coalesce(json_agg(json_build_object('slug', ${slugOf('piece', 'a.piece_id')}, 'title', pc.title, 'grade', o.grade)
				order by o.position), '[]')
			from music_occurrences o join arrangements a on a.id = o.arrangement_id join pieces pc on pc.id = a.piece_id
			where o.program_id = m.program_id and o.origin = m.origin))
	from music_claims m where m.program_id = ${sql.ref(program)} and m.origin = ${topClaim(program)}
)`;

/** Each Program's Pieces from its winning claim, for Programs with a Performance not marked gone. */
const currentMusic = sql`(
	select o.program_id, o.origin, o.position, o.grade, o.raw_text, a.piece_id
	from music_occurrences o join arrangements a on a.id = o.arrangement_id
	where o.origin = ${topClaim('o.program_id')}
		and exists (select from performances p where p.program_id = o.program_id and not p.gone)
)`;

async function idBySlug(db: Kysely<DB>, entity: 'skater' | 'team' | 'piece', slug: string) {
	const row = await db
		.selectFrom('keys')
		.select('entity_id')
		.where('system', '=', 'slug')
		.where('entity', '=', entity)
		.where('value', '=', slug)
		.executeTakeFirst();
	return row?.entity_id;
}

export type PerformanceRow = {
	id: string;
	season: number;
	competition_id: string;
	competition: string;
	city: string;
	start_date: string;
	end_date: string;
	discipline: string;
	level: string;
	segment_type: string;
	round: string;
	rank: number | null;
	rank_label: string | null;
	tss: string | null;
	video: boolean;
	music: MusicClaim | null;
	/** The Team that skated it, when it is a Team's Performance. */
	team: Hit | null;
};

/** Performances not marked gone, newest Season and Competition first, Segments in skating order. */
async function performanceRows(db: Kysely<DB>, where: RawBuilder<boolean>) {
	const { rows } = await sql<PerformanceRow>`
		select p.id, pr.season, c.id as competition_id, c.name as competition, c.city,
			c.start_date::text, c.end_date::text, s.discipline, s.level, s.segment_type, s.round,
			p.rank, p.rank_label, p.tss, ${musicOf('pr.id')} as music,
			exists (select from performance_videos v where v.performance_id = p.id and v.status = 'active') as video,
			case when t.id is not null then json_build_object('slug', ${slugOf('team', 't.id')}, 'name', t.name) end as team
		from performances p
		join programs pr on pr.id = p.program_id
		join segments s on s.id = p.segment_id
		join competitions c on c.id = s.competition_id
		left join teams t on t.id = p.team_id
		where not p.gone and (${where})
		order by pr.season desc, c.start_date desc, c.id, array_position(${SEGMENT_ORDER}::text[], s.segment_type), s.round, p.id
	`.execute(db);
	return rows;
}

/** A Skater and their Performances, their Teams' included; undefined for an unknown slug. */
export async function skaterPage(db: Kysely<DB>, slug: string) {
	const id = await idBySlug(db, 'skater', slug);
	if (!id) return undefined;
	const skater = await db
		.selectFrom('skaters')
		.select(['name', 'nation', slugOf('skater', 'skaters.id').as('slug')])
		.where('id', '=', id)
		.executeTakeFirstOrThrow();
	const performances = await performanceRows(
		db,
		sql`p.skater_id = ${id} or p.team_id in (select id from teams where ${id} in (skater1_id, skater2_id))`
	);
	return { skater, performances };
}

/** A Team, its two Skaters and its Performances; undefined for an unknown slug. */
export async function teamPage(db: Kysely<DB>, slug: string) {
	const id = await idBySlug(db, 'team', slug);
	if (!id) return undefined;
	const team = await db
		.selectFrom('teams')
		.select(['name', 'skater1_id', 'skater2_id', slugOf('team', 'teams.id').as('slug')])
		.where('id', '=', id)
		.executeTakeFirstOrThrow();
	const skaters = await db
		.selectFrom('skaters')
		.select(['name', slugOf('skater', 'skaters.id').as('slug')])
		.where('id', 'in', [team.skater1_id, team.skater2_id])
		.orderBy(sql`id = ${team.skater1_id}`, 'desc')
		.execute();
	return { team: { name: team.name, slug: team.slug }, skaters, performances: await performanceRows(db, sql`p.team_id = ${id}`) };
}

/**
 * A Performance not marked gone, with its active videos in play order, and the other Performances
 * of its Program; undefined when there is none.
 */
export async function performancePage(db: Kysely<DB>, id: string) {
	const { rows } = await sql<
		Omit<PerformanceRow, 'video' | 'team'> & {
			program_id: string;
			tes: string | null;
			pcs: string | null;
			deductions: string | null;
			start_number: number | null;
			url: string;
			entity: 'skater' | 'team';
			name: string;
			slug: string;
		}
	>`
		select p.id, pr.season, p.program_id, c.id as competition_id, c.name as competition, c.city,
			c.start_date::text, c.end_date::text, s.discipline, s.level, s.segment_type, s.round, s.url,
			p.rank, p.rank_label, p.tss, p.tes, p.pcs, p.deductions, p.start_number, ${musicOf('pr.id')} as music,
			case when p.team_id is null then 'skater' else 'team' end as entity,
			coalesce(sk.name, t.name) as name,
			coalesce(${slugOf('skater', 'sk.id')}, ${slugOf('team', 't.id')}) as slug
		from performances p
		join programs pr on pr.id = p.program_id
		join segments s on s.id = p.segment_id
		join competitions c on c.id = s.competition_id
		left join skaters sk on sk.id = p.skater_id
		left join teams t on t.id = p.team_id
		where p.id = ${id} and not p.gone
	`.execute(db);
	const performance = rows[0];
	if (!performance) return undefined;
	const videos = await db
		.selectFrom('performance_videos as v')
		.leftJoin('youtube_videos as y', 'y.youtube_id', 'v.youtube_id')
		.select(['v.youtube_id', 'v.start_seconds', 'v.origin', 'y.title'])
		.where('v.performance_id', '=', id)
		.where('v.status', '=', 'active')
		.orderBy('v.id')
		.execute();
	const sameProgram = await performanceRows(db, sql`p.program_id = ${performance.program_id} and p.id <> ${id}`);
	return { performance, videos: playOrder(videos), sameProgram };
}

export type PieceProgram = {
	id: string;
	season: number;
	segment_type: string;
	/** The best grade among the Program's entries naming the Piece. */
	grade: Grade;
	/** Those entries' raw text. */
	raw_text: string;
	origin: string;
	article_title: string | null;
	revision: string | null;
	performances: { id: string; competition: string; rank: number | null; rank_label: string | null; video: boolean }[];
};

/**
 * A Piece and the Programs using it, grouped by Skater or Team, newest Season first, each with its
 * Performances not marked gone; undefined for an unknown slug.
 */
export async function piecePage(db: Kysely<DB>, slug: string) {
	const id = await idBySlug(db, 'piece', slug);
	if (!id) return undefined;
	const { rows: pieces } = await sql<{ title: string; slug: string; source: string | null; qid: string | null; composers: string[] }>`
		select p.title, ${slugOf('piece', 'p.id')} as slug, s.name as source,
			(select value from keys k where k.system = 'wikidata' and k.entity = 'piece' and k.entity_id = p.id) as qid,
			array(select distinct a.name from piece_artists pa join artists a on a.id = pa.artist_id where pa.piece_id = p.id order by a.name) as composers
		from pieces p left join sources s on s.id = p.source_id
		where p.id = ${id}
	`.execute(db);
	const { rows } = await sql<PieceProgram & Hit & { entity: 'skater' | 'team' }>`
		select pr.id, pr.season, pr.segment_type,
			case when pr.team_id is null then 'skater' else 'team' end as entity,
			coalesce(s.name, t.name) as name, coalesce(${slugOf('skater', 's.id')}, ${slugOf('team', 't.id')}) as slug,
			(${GRADES}::text[])[min(array_position(${GRADES}::text[], u.grade))] as grade,
			string_agg(distinct u.raw_text, E'\n') as raw_text,
			m.origin, m.article_title, m.revision::text as revision,
			(select json_agg(json_build_object('id', p.id::text, 'competition', c.name, 'rank', p.rank, 'rank_label', p.rank_label,
					'video', exists (select from performance_videos v where v.performance_id = p.id and v.status = 'active'))
				order by c.start_date, p.id)
			from performances p join segments sg on sg.id = p.segment_id join competitions c on c.id = sg.competition_id
			where p.program_id = pr.id and not p.gone) as performances
		from ${currentMusic} u
		join programs pr on pr.id = u.program_id
		join music_claims m on m.program_id = u.program_id and m.origin = u.origin
		left join skaters s on s.id = pr.skater_id
		left join teams t on t.id = pr.team_id
		where u.piece_id = ${id}
		group by pr.id, m.program_id, m.origin, s.id, t.id
		order by pr.season desc, name, array_position(${SEGMENT_ORDER}::text[], pr.segment_type)
	`.execute(db);
	const owners = new Map<string, Hit & { entity: 'skater' | 'team'; programs: PieceProgram[] }>();
	for (const { entity, slug, name, ...program } of rows) {
		const key = `${entity}/${slug}`;
		if (!owners.has(key)) owners.set(key, { entity, slug, name, programs: [] });
		owners.get(key)!.programs.push(program);
	}
	return { piece: pieces[0], owners: [...owners.values()] };
}

/** The Season tabs of a career, newest first, and the rows of the one in the URL (else the newest); undefined for a Season not in it. */
export function pickSeason(rows: PerformanceRow[], param: string | undefined) {
	const seasons = [...new Set(rows.map((r) => r.season))];
	const season = param === undefined ? seasons[0] : Number(param);
	if (param !== undefined && !seasons.includes(season)) return undefined;
	return { seasons, season, performances: rows.filter((r) => r.season === season) };
}
