import { DATABASE_URL } from '$app/env/private';
import { Kysely, PostgresDialect, sql } from 'kysely';
import pg from 'pg';
import type { DB } from './db-types';

export const createDb = (connectionString: string) =>
	new Kysely<DB>({ dialect: new PostgresDialect({ pool: new pg.Pool({ connectionString }) }) });

// The pool connects lazily, so importing this module needs no database.
export const db = createDb(DATABASE_URL);

/** One row proving the database is up and migrated: f_unaccent comes from the first migration. */
export async function databaseStatus(db: Kysely<DB>) {
	const { rows } = await sql<{ version: string; unaccented: string }>`
		select current_setting('server_version') as version, f_unaccent('Kévin') as unaccented
	`.execute(db);
	return rows[0];
}
