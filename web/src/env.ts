import { building } from '$app/env';
import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	DATABASE_URL: {
		description: 'Postgres connection URL',
		// The Docker build has no database; the running app must have one.
		schema: (value) => {
			if (!value && !building) throw new Error('DATABASE_URL is not set');
			return value ?? '';
		}
	}
});
