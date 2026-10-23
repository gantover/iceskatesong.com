import { dev } from '$app/env';
import { ADMIN_DEV_BYPASS, CF_ACCESS_AUD, CF_ACCESS_TEAM_DOMAIN } from '$app/env/private';
import type { Handle } from '@sveltejs/kit/hooks';
import { createRemoteJWKSet } from 'jose';
import { accessGuard } from '#lib/server/access.js';

// jose fetches the certs on first use and caches them, refetching when a token names an unknown key.
const keySet = createRemoteJWKSet(new URL('/cdn-cgi/access/certs', CF_ACCESS_TEAM_DOMAIN ?? 'https://unset.invalid'));

export const handle: Handle =
	dev && ADMIN_DEV_BYPASS
		? ({ event, resolve }) => resolve(event)
		: accessGuard({ keySet, issuer: CF_ACCESS_TEAM_DOMAIN, audience: CF_ACCESS_AUD });
