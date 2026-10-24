import { DATABASE_URL } from '$app/env/private';
import { Kysely, PostgresDialect } from 'kysely';
import pg from 'pg';
import type { DB } from './db-types.js';

export const createDb = (connectionString: string) =>
	new Kysely<DB>({ dialect: new PostgresDialect({ pool: new pg.Pool({ connectionString }) }) });

// The pool connects lazily, so importing this module needs no database.
export const db = createDb(DATABASE_URL);
