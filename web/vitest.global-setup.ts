// Creates a throwaway database in the Compose Postgres, migrates it with Alembic,
// and drops it after the run. Tests read its URL with inject('databaseUrl').
import { execFileSync } from 'node:child_process';
import pg from 'pg';
import { loadEnv } from 'vite';
import type { TestProject } from 'vitest/node';

export default async function setup(project: TestProject) {
	const base = process.env.DATABASE_URL ?? loadEnv('test', '..', '').DATABASE_URL;
	if (!base) throw new Error('DATABASE_URL is not set: copy .env.example to .env');

	const name = `test_${process.pid}_${Date.now()}`;
	const admin = new pg.Client({ connectionString: base });
	await admin.connect();
	await admin.query(`create database ${name}`);

	const url = new URL(base);
	url.pathname = `/${name}`;
	execFileSync('uv', ['run', '--project', '../db', 'alembic', '-c', '../db/alembic.ini', 'upgrade', 'head'], {
		env: { ...process.env, DATABASE_URL: url.href },
		stdio: 'inherit'
	});
	project.provide('databaseUrl', url.href);

	return async () => {
		await admin.query(`drop database ${name} with (force)`);
		await admin.end();
	};
}
