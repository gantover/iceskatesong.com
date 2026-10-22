\pset pager off
\timing off
create extension if not exists pg_trgm;
create extension if not exists unaccent;

-- 2. unaccent volatility and coverage
select proname, provolatile, pg_get_function_identity_arguments(oid) from pg_proc where proname = 'unaccent';
select unaccent('Ёлкин') ru_yo, unaccent('Ribič Ñandú Søren Weiß Æon Łukasz Gabriella Papadakis Guillaume Cizeron Kévin Aymoz') latin;
select normalize('ﾊﾆｭｳ ﾕﾂﾞﾙ', NFKC) halfwidth_kana, normalize('ＨＡＮＹＵ', NFKC) fullwidth_latin, unaccent('はにゅう') = unaccent('ハニュウ') hira_eq_kata;
select lower('ПЛЮЩЕНКО ЁЛКИН') ru_lower, lower('KÉVIN ÇA') lat_lower;

-- immutable wrapper (unaccent() is STABLE, so it cannot go in an index or generated column directly)
create or replace function f_unaccent(text) returns text
  language sql immutable parallel safe strict
  return public.unaccent('public.unaccent'::regdictionary, $1);

-- 4. FTS tokenisation of JA / RU
select to_tsvector('simple', '羽生結弦のフリー') ja_simple;
select alias, token from ts_debug('simple', '羽生結弦 のフリー');
select to_tsvector('russian', 'Плющенко катался под музыку') ru;
select cfgname from pg_ts_config order by 1;

-- synthetic data: ~50k people names, ~30k pieces with Wikipedia-sized text
drop table if exists person, piece;
create table person (id int generated always as identity primary key, name text not null,
  search_key text generated always as (f_unaccent(lower(name))) stored);
create table piece (id int generated always as identity primary key, title text not null, body text not null,
  search_key text generated always as (f_unaccent(lower(title))) stored,
  body_tsv tsvector generated always as (to_tsvector('english', f_unaccent(body))) stored);

with syl as (select array['ka','ri','to','na','me','lo','vic','ski','sen','ber','zé','ov','ić','an','el','mar','yu','ha','shi','ro','dmi','ser','gei','ña','ø'] s)
insert into person(name)
select initcap(s[1+floor(random()*25)::int] || s[1+floor(random()*25)::int] || s[1+floor(random()*25)::int]) || ' ' ||
       initcap(s[1+floor(random()*25)::int] || s[1+floor(random()*25)::int] || s[1+floor(random()*25)::int] || s[1+floor(random()*25)::int])
from syl, generate_series(1, 49000);
insert into person(name) values ('Yuzuru Hanyu'),('羽生結弦'),('はにゅう ゆづる'),('Evgeni Plushenko'),('Евгений Плющенко'),('Shoma Uno'),('宇野昌磨'),('Kévin Aymoz'),('Guillaume Cizeron'),('Kaori Sakamoto'),('坂本花織');
insert into person(name) select '羽生' || chr(19968 + floor(random()*20000)::int) || chr(19968 + floor(random()*20000)::int) from generate_series(1,50);
insert into person(name) select chr(19968 + floor(random()*20000)::int) || chr(19968 + floor(random()*20000)::int) || chr(19968 + floor(random()*20000)::int) || chr(19968 + floor(random()*20000)::int) from generate_series(1,1000);

with w as (select regexp_split_to_array('the opera ballet suite symphony concerto film score song aria overture waltz tango march nocturne pirates caribbean swan lake phantom night dream love moon river fire dance theme composed premiered orchestra piano violin cello recorded album single soundtrack musical act scene movement major minor allegro adagio composer performed version arrangement cover remix', ' ') a)
insert into piece(title, body)
select initcap(w.a[1+floor(random()*array_length(w.a,1))::int] || ' ' || w.a[1+floor(random()*array_length(w.a,1))::int] || ' ' || w.a[1+floor(random()*array_length(w.a,1))::int]),
       -- i*0 makes the aggregate inner-level, so each row gets its own random words
       (select string_agg(w.a[1+floor(random()*array_length(w.a,1) + i*0)::int], ' ') from generate_series(1, 250 + g*0) i)
from w, generate_series(1, 30000) g;
insert into piece(title, body) values ('He''s a Pirate', 'He''s a Pirate is an instrumental piece composed by Klaus Badelt and Hans Zimmer for the 2003 film Pirates of the Caribbean: The Curse of the Black Pearl.');

create index person_trgm on person using gin (search_key gin_trgm_ops);
create index person_trgm_gist on person using gist (search_key gist_trgm_ops);
create index piece_trgm on piece using gin (search_key gin_trgm_ops);
create index piece_fts on piece using gin (body_tsv);
analyze person; analyze piece;

select count(*) persons from person; select count(*) pieces from piece;
select pg_size_pretty(pg_relation_size('person_trgm')) person_gin, pg_size_pretty(pg_relation_size('person_trgm_gist')) person_gist,
       pg_size_pretty(pg_relation_size('piece_fts')) piece_fts, pg_size_pretty(pg_total_relation_size('piece')) piece_total;

\echo '--- a. as-you-type substring, accent-insensitive: "aymo"'
explain (analyze, costs off, summary on) select name from person where search_key like '%' || f_unaccent(lower('aymo')) || '%' limit 20;
\echo '--- a2. accented query against accented data: "kévin" and "kevin"'
select name from person where search_key like '%' || f_unaccent(lower('kévin')) || '%';
select name from person where search_key like '%' || f_unaccent(lower('kevin aym')) || '%';
\echo '--- b. typo: "plushchenko" (ISU spelling) vs stored "Plushenko"; "cizeronn"'
explain (analyze, costs off, summary on) select name, word_similarity('plushchenko', search_key) from person where 'plushchenko' <% search_key order by 'plushchenko' <<-> search_key limit 10;
select name, round(word_similarity('plushchenko', search_key)::numeric,2) ws from person where 'plushchenko' <% search_key order by ws desc limit 5;
select name, round(word_similarity('cizeronn', search_key)::numeric,2) ws from person where 'cizeronn' <% search_key order by ws desc limit 5;
select name, round(word_similarity('hanyu yuzru', search_key)::numeric,2) ws from person where 'hanyu yuzru' <% search_key order by ws desc limit 5;
\echo '--- c. JA 2-char substring "羽生" (no full trigram in pattern)'
explain (analyze, costs off, summary on) select name from person where search_key like '%羽生%';
select count(*) from person where search_key like '%羽生%';
\echo '--- d. JA 1-char "羽"'
explain (analyze, costs off, summary on) select name from person where search_key like '%羽%';
\echo '--- e. JA 3-char "羽生結"'
explain (analyze, costs off, summary on) select name from person where search_key like '%羽生結%';
\echo '--- e2. JA anchored prefix 2-char "宇野"'
explain (analyze, costs off, summary on) select name from person where search_key like '宇野%';
\echo '--- e3. JA forced seq scan for 2-char, worst case'
set enable_bitmapscan = off; set enable_indexscan = off;
explain (analyze, costs off, summary on) select name from person where search_key like '%羽生%';
reset enable_bitmapscan; reset enable_indexscan;
\echo '--- e4. Cyrillic substring + typo'
select name from person where search_key like '%плющ%';
select name, round(word_similarity('плющенка', search_key)::numeric,2) from person where 'плющенка' <% search_key;
\echo '--- f. FTS on long music text'
explain (analyze, costs off, summary on) select id, title, ts_rank(body_tsv, q) r from piece, websearch_to_tsquery('english', 'pirates caribbean zimmer') q where body_tsv @@ q order by r desc limit 10;
select title from piece, websearch_to_tsquery('english', 'pirates caribbean zimmer') q where body_tsv @@ q;
\echo '--- f2. FTS prefix as-you-type on long text: "zimm:*"'
explain (analyze, costs off, summary on) select id from piece where body_tsv @@ to_tsquery('english', 'zimm:*') limit 10;
\echo '--- f3. common-word FTS (many matches, ranking all)'
explain (analyze, costs off, summary on) select id, ts_rank(body_tsv, q) r from piece, websearch_to_tsquery('english', 'opera ballet') q where body_tsv @@ q order by r desc limit 10;
\echo '--- g. title typo search "swan lak" / "pirat"'
explain (analyze, costs off, summary on) select title from piece where search_key like '%pirat%' or 'pirat' <% search_key limit 10;

\echo '=== GIN only (gist dropped)'
drop index person_trgm_gist; analyze person;
explain (analyze, costs off, summary on) select name from person where search_key like '%aymo%' limit 20;
explain (analyze, costs off, summary on) select name from person where 'plushchenko' <% search_key order by word_similarity('plushchenko', search_key) desc limit 10;
explain (analyze, costs off, summary on) select name from person where search_key like '%羽生%';
\echo '--- 3 letters, many hits'
explain (analyze, costs off, summary on) select name from person where search_key like '%kar%' order by word_similarity('kar', search_key) desc limit 10;
\echo '--- 2 letters (no full trigram)'
explain (analyze, costs off, summary on) select name from person where search_key like '%ka%' order by word_similarity('ka', search_key) desc limit 10;
\echo '--- hiragana -> katakana fold'
select translate('はにゅう ゆづる', (select string_agg(chr(c),'') from generate_series(x'3041'::int, x'3096'::int) c), (select string_agg(chr(c+96),'') from generate_series(x'3041'::int, x'3096'::int) c)) = 'ハニュウ ユヅル' as kana_fold_ok;
