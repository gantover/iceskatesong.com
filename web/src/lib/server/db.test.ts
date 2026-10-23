import { sql } from 'kysely';
import { afterAll, expect, inject, test } from 'vitest';
import { createDb, databaseStatus } from './db.js';

const db = createDb(inject('databaseUrl'));
afterAll(() => db.destroy());

test('databaseStatus reads from the migrated database', async () => {
	expect(await databaseStatus(db)).toMatchObject({ unaccented: 'Kevin' });
});

test('the database is not on the C locale', async () => {
	const { rows } = await sql<{ datcollate: string }>`
		select datcollate from pg_database where datname = current_database()
	`.execute(db);
	expect(rows[0].datcollate).toBe('en_US.utf8');
});

test('f_unaccent works in a generated column', async () => {
	await db.connection().execute(async (conn) => {
		await sql`create temp table skater (name text, search_key text generated always as (f_unaccent(lower(name))) stored)`.execute(conn);
		await sql`insert into skater (name) values ('Kévin AYMOZ'), ('Ёлкин')`.execute(conn);
		const { rows } = await sql<{ search_key: string }>`select search_key from skater`.execute(conn);
		expect(rows.map((r) => r.search_key)).toEqual(['kevin aymoz', 'елкин']);
	});
});
