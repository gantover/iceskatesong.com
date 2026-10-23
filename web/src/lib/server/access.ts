import type { Handle } from '@sveltejs/kit/hooks';
import { jwtVerify, type JWTVerifyGetKey } from 'jose';

const ADMIN = /^\/admin(\/|$)/;

/**
 * Lets an `/admin` request through only with a `Cf-Access-Jwt-Assertion` signed by the Access team's keys
 * for this application. Fails closed: no header, a bad token or missing config all get 403.
 */
export const accessGuard =
	(config: { keySet: JWTVerifyGetKey; issuer?: string; audience?: string }): Handle =>
	async ({ event, resolve }) => {
		// The route id also catches encoded paths (`/%61dmin`) that SvelteKit decodes before routing.
		const admin = ADMIN.test(event.url.pathname) || ADMIN.test(event.route.id ?? '');
		if (admin && !(await verified(event.request, config))) return new Response('Forbidden', { status: 403 });
		return resolve(event);
	};

async function verified(request: Request, { keySet, issuer, audience }: Parameters<typeof accessGuard>[0]) {
	const token = request.headers.get('cf-access-jwt-assertion');
	// jose skips the aud and iss checks when they are undefined, so missing config must refuse here.
	if (!token || !issuer || !audience) return false;
	try {
		await jwtVerify(token, keySet, { issuer, audience });
		return true;
	} catch {
		return false;
	}
}
