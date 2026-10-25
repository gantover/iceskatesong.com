import { sql, type Kysely, type RawBuilder } from 'kysely';
import type { DB } from './db-types.js';

export type Hit = { slug: string; name: string };

// Public pages show only Import data, which changes when the Admin runs an Import.
export const PUBLIC_CACHE = { 'cache-control': 'public, max-age=300' };

/**
 * Skaters and Teams whose name or alias matches, accents and case ignored: from 3 characters a substring
 * or a close spelling, below that the start of a word.
 */
export async function search(db: Kysely<DB>, query: string) {
	const q = query.trim().slice(0, 100);
	if (!q) return { skaters: [], teams: [] };
	const { rows } = await sql<Hit & { entity: 'skater' | 'team' }>`
		with q as (select q, replace(replace(replace(q, '\\', '\\\\'), '%', '\\%'), '_', '\\_') as esc
			from f_unaccent(lower(${q})) as q),
		hit as (
			-- One row per record: its best-matching name. Substring matches rank above close spellings.
			select entity, entity_id,
				max((search_key like '%' || esc || '%')::int) as substring,
				max(word_similarity(q, search_key)) as similarity
			from names, q
			where entity in ('skater', 'team')
				and case when length(q) >= 3 then search_key like '%' || esc || '%' or q <% search_key
					else search_key like esc || '%' or search_key like '% ' || esc || '%' end
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
	return {
		skaters: rows.filter((r) => r.entity === 'skater').map(({ slug, name }) => ({ slug, name })),
		teams: rows.filter((r) => r.entity === 'team').map(({ slug, name }) => ({ slug, name }))
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
const slugOf = (entity: 'skater' | 'team', id: string) =>
	sql<string>`(select min(value) from keys k where k.system = 'slug' and k.entity = ${entity} and k.entity_id = ${sql.ref(id)})`;

async function idBySlug(db: Kysely<DB>, entity: 'skater' | 'team', slug: string) {
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
	/** The Team that skated it, when it is a Team's Performance. */
	team: Hit | null;
};

/** Performances not marked gone, newest Season and Competition first, Segments in skating order. */
async function performanceRows(db: Kysely<DB>, where: RawBuilder<boolean>) {
	const { rows } = await sql<PerformanceRow>`
		select p.id, pr.season, c.id as competition_id, c.name as competition, c.city,
			c.start_date::text, c.end_date::text, s.discipline, s.level, s.segment_type, s.round,
			p.rank, p.rank_label, p.tss,
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
			p.rank, p.rank_label, p.tss, p.tes, p.pcs, p.deductions, p.start_number,
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

/** The Season tabs of a career, newest first, and the rows of the one in the URL (else the newest); undefined for a Season not in it. */
export function pickSeason(rows: PerformanceRow[], param: string | undefined) {
	const seasons = [...new Set(rows.map((r) => r.season))];
	const season = param === undefined ? seasons[0] : Number(param);
	if (param !== undefined && !seasons.includes(season)) return undefined;
	return { seasons, season, performances: rows.filter((r) => r.season === season) };
}
