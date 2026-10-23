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
	},
	CF_ACCESS_TEAM_DOMAIN: {
		description: 'Cloudflare Access team domain, e.g. https://<team>.cloudflareaccess.com. Unset: /admin answers 403',
		schema: (value) => value || undefined
	},
	CF_ACCESS_AUD: {
		description: "The Access application's Audience (AUD) tag. Unset: /admin answers 403",
		schema: (value) => value || undefined
	},
	ADMIN_DEV_BYPASS: {
		description: "'true' skips the Access check on /admin, under `pnpm dev` only",
		schema: (value) => value === 'true'
	}
});
