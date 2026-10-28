-- PROTOTYPE (#39 theme variants), wipe me: seeds the throwaway iceskatesong_prototype database
-- so the real Skater, Team, Performance and Piece pages have something to render.
-- Fictional skaters, real public-domain pieces. Run once on a freshly migrated database.

create function pg_temp.skater(n text, nat text, slug text) returns bigint language sql as $$
	with s as (insert into skaters (name, nation) values (n, nat) returning id),
	_n as (insert into names (entity, entity_id, name, origin) select 'skater', id, n, 'isu' from s),
	_k as (insert into keys (system, value, entity, entity_id) select 'slug', slug, 'skater', id from s)
	select id from s $$;

create function pg_temp.piece(t text, slug text, composer text, qid text) returns bigint language plpgsql as $$
declare p bigint; a bigint;
begin
	insert into pieces (title) values (t) returning id into p;
	insert into keys (system, value, entity, entity_id) values ('slug', slug, 'piece', p);
	if qid is not null then insert into keys (system, value, entity, entity_id) values ('wikidata', qid, 'piece', p); end if;
	insert into names (entity, entity_id, name, origin) values ('piece', p, t, 'wikipedia');
	insert into artists (name) values (composer) returning id into a;
	insert into piece_artists (piece_id, artist_id, origin) values (p, a, 'wikipedia');
	return p;
end $$;

-- A Program's Wikipedia music claim, its occurrences graded in order.
create function pg_temp.music(prog bigint, raw text, pieces bigint[], grades text[]) returns void language plpgsql as $$
declare st bigint; arr bigint;
begin
	insert into music_claims (program_id, origin, raw_text, article_title, revision) values (prog, 'wikipedia', raw, 'Mila Kovač', 1378424980);
	insert into styles (slug) values ('original') on conflict (slug) do update set slug = excluded.slug returning id into st;
	for i in 1 .. coalesce(array_length(pieces, 1), 0) loop
		insert into arrangements (piece_id, style_id) values (pieces[i], st)
			on conflict (piece_id, style_id, performer_id) do update set piece_id = excluded.piece_id returning id into arr;
		insert into music_occurrences (program_id, origin, position, arrangement_id, grade, raw_text) values (prog, 'wikipedia', i - 1, arr, grades[i], raw);
	end loop;
end $$;

-- A Competition with one Segment, and a Performance in it.
create function pg_temp.perf(who_skater bigint, who_team bigint, prog bigint, comp text, city text, d date, disc text, seg text, r int, label text, score numeric, video text)
returns bigint language plpgsql as $$
declare c bigint; s bigint; p bigint;
begin
	select id into c from competitions where name = comp and start_date = d;
	if c is null then
		insert into competitions (name, city, start_date, end_date, level) values (comp, city, d, d + 3, 'senior') returning id into c;
	end if;
	insert into segments (competition_id, discipline, level, segment_type, url) values (c, disc, 'senior', seg, 'https://results.isu.org/') returning id into s;
	insert into performances (segment_id, entry_key, skater_id, team_id, program_id, rank, rank_label, tss, name, nation)
	select s, gen_random_uuid()::text, who_skater, who_team, prog, r, label, score,
		coalesce((select name from skaters where id = who_skater), (select name from teams where id = who_team)), 'CRO'
	returning id into p;
	if video is not null then
		insert into performance_videos (youtube_id, start_seconds, performance_id, origin) values (video, 0, p, 'official');
	end if;
	return p;
end $$;

do $$
declare
	mila bigint := pg_temp.skater('Mila KOVAČ', 'CRO', 'mila-kovac');
	lea bigint := pg_temp.skater('Léa DUMONT', 'FRA', 'lea-dumont');
	noah bigint := pg_temp.skater('Noah BERGSTRÖM', 'SWE', 'noah-bergstrom');
	duo bigint;
	swan bigint := pg_temp.piece('Swan Lake', 'swan-lake', 'Pyotr Ilyich Tchaikovsky', 'Q190200');
	nocturne bigint := pg_temp.piece('Nocturne in C-sharp minor', 'nocturne-in-c-sharp-minor', 'Frédéric Chopin', null);
	bolero bigint := pg_temp.piece('Boléro', 'bolero', 'Maurice Ravel', 'Q193022');
	clair bigint := pg_temp.piece('Clair de lune', 'clair-de-lune', 'Claude Debussy', 'Q211290');
	carmen bigint := pg_temp.piece('Habanera', 'habanera', 'Georges Bizet', null);
	sp23 bigint; fs23 bigint; sp24 bigint; fs24 bigint; sp25 bigint; fs25 bigint; rd bigint; fd bigint;
begin
	insert into teams (name, skater1_id, skater2_id) values ('Léa DUMONT / Noah BERGSTRÖM', lea, noah) returning id into duo;
	insert into names (entity, entity_id, name, origin) values ('team', duo, 'Léa DUMONT / Noah BERGSTRÖM', 'isu');
	insert into keys (system, value, entity, entity_id) values ('slug', 'lea-dumont-noah-bergstrom', 'team', duo);

	insert into programs (skater_id, season, segment_type) values (mila, 2023, 'short program') returning id into sp23;
	insert into programs (skater_id, season, segment_type) values (mila, 2023, 'free skating') returning id into fs23;
	insert into programs (skater_id, season, segment_type) values (mila, 2024, 'short program') returning id into sp24;
	insert into programs (skater_id, season, segment_type) values (mila, 2024, 'free skating') returning id into fs24;
	insert into programs (skater_id, season, segment_type) values (mila, 2025, 'short program') returning id into sp25;
	insert into programs (skater_id, season, segment_type) values (mila, 2025, 'free skating') returning id into fs25;
	insert into programs (team_id, season, segment_type) values (duo, 2025, 'rhythm dance') returning id into rd;
	insert into programs (team_id, season, segment_type) values (duo, 2025, 'free dance') returning id into fd;

	perform pg_temp.music(sp23, 'Habanera from Carmen by Georges Bizet', array[carmen], array['credited']);
	perform pg_temp.music(fs23, 'Swan Lake by Pyotr Ilyich Tchaikovsky', array[swan], array['identified']);
	perform pg_temp.music(sp24, 'Nocturne in C-sharp minor', array[nocturne], array['title only']);
	perform pg_temp.music(fs24, 'Boléro by Maurice Ravel', array[bolero], array['identified']);
	perform pg_temp.music(sp25, 'Clair de lune by Claude Debussy;' || chr(10) || 'Nocturne in C-sharp minor by Frédéric Chopin', array[clair, nocturne], array['identified', 'credited']);
	-- fs25 has no music claim: "Music not known yet".
	perform pg_temp.music(fd, 'Swan Lake by Pyotr Ilyich Tchaikovsky', array[swan], array['identified']);

	perform pg_temp.perf(mila, null, sp23, 'ISU Grand Prix Skate Canada', 'Halifax', '2023-10-27', 'women', 'short program', 4, null, 68.42, null);
	perform pg_temp.perf(mila, null, fs23, 'ISU Grand Prix Skate Canada', 'Halifax', '2023-10-27', 'women', 'free skating', 3, null, 134.10, 'dQw4w9WgXcQ');
	perform pg_temp.perf(mila, null, sp23, 'ISU European Championships', 'Kaunas', '2024-01-10', 'women', 'short program', 7, null, 63.05, null);
	perform pg_temp.perf(mila, null, fs23, 'ISU European Championships', 'Kaunas', '2024-01-10', 'women', 'free skating', null, 'WD', null, null);
	perform pg_temp.perf(mila, null, sp24, 'ISU Grand Prix de France', 'Angers', '2024-11-01', 'women', 'short program', 2, null, 72.81, 'M7lc1UVf-VE');
	perform pg_temp.perf(mila, null, fs24, 'ISU Grand Prix de France', 'Angers', '2024-11-01', 'women', 'free skating', 1, null, 146.37, 'M7lc1UVf-VE');
	perform pg_temp.perf(mila, null, sp24, 'ISU World Championships', 'Boston', '2025-03-26', 'women', 'short program', 5, null, 70.12, null);
	perform pg_temp.perf(mila, null, fs24, 'ISU World Championships', 'Boston', '2025-03-26', 'women', 'free skating', 4, null, 139.88, 'ScMzIvxBSi4');
	perform pg_temp.perf(mila, null, sp25, 'ISU Grand Prix Final', 'Nagoya', '2025-12-04', 'women', 'short program', 2, null, 74.90, 'dQw4w9WgXcQ');
	perform pg_temp.perf(mila, null, fs25, 'ISU Grand Prix Final', 'Nagoya', '2025-12-04', 'women', 'free skating', 3, null, 141.02, null);
	perform pg_temp.perf(null, duo, rd, 'ISU Grand Prix Final', 'Nagoya', '2025-12-04', 'ice dance', 'rhythm dance', 6, null, 74.66, null);
	perform pg_temp.perf(null, duo, fd, 'ISU Grand Prix Final', 'Nagoya', '2025-12-04', 'ice dance', 'free dance', 5, null, 112.30, 'ScMzIvxBSi4');

	insert into youtube_videos (youtube_id, title, channel_id, published_at, duration_seconds, embeddable, made_for_kids, refreshed_at)
	values ('dQw4w9WgXcQ', 'Mila Kovač – Short Program | Grand Prix Final 2025', 'c', now(), 240, true, false, now());
end $$;

update performances set tes = round(tss * 0.54, 2), pcs = round(tss * 0.46, 2), deductions = 0 where tss is not null;
