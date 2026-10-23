import { createLocalJWKSet, exportJWK, generateKeyPair, SignJWT } from 'jose';
import { expect, test } from 'vitest';
import { accessGuard } from './access.js';

const issuer = 'https://team.cloudflareaccess.com';
const audience = 'app-aud';
const signer = await generateKeyPair('RS256');
const stranger = await generateKeyPair('RS256');
const keySet = createLocalJWKSet({ keys: [{ ...(await exportJWK(signer.publicKey)), kid: 'k1', alg: 'RS256' }] });

const token = (key = signer.privateKey, aud = audience, iss = issuer) =>
	new SignJWT({ email: 'owner@example.com' })
		.setProtectedHeader({ alg: 'RS256', kid: 'k1' })
		.setIssuer(iss)
		.setAudience(aud)
		.setIssuedAt()
		.setExpirationTime('5m')
		.sign(key);

const guard = accessGuard({ keySet, issuer, audience });

async function status(path: string, jwt?: string, routeId: string | null = null, check = guard) {
	const request = new Request(`http://localhost${path}`, {
		headers: jwt ? { 'cf-access-jwt-assertion': jwt } : {}
	});
	const event = { request, url: new URL(request.url), route: { id: routeId } } as never;
	const response = await check({ event, resolve: async () => new Response('ok') });
	return response.status;
}

test('a valid Access JWT reaches /admin', async () => {
	expect(await status('/admin', await token())).toBe(200);
});

test('a JWT for another application gets 403', async () => {
	expect(await status('/admin', await token(signer.privateKey, 'other-aud'))).toBe(403);
});

test('a JWT from another Access team gets 403', async () => {
	expect(await status('/admin', await token(signer.privateKey, audience, 'https://other.cloudflareaccess.com'))).toBe(403);
});

test('a JWT signed by another key gets 403', async () => {
	expect(await status('/admin', await token(stranger.privateKey))).toBe(403);
});

test('a request without the header gets 403, on /admin and anything under it', async () => {
	expect(await status('/admin')).toBe(403);
	expect(await status('/admin/anything')).toBe(403);
	expect(await status('/admin/__data.json')).toBe(403);
});

test('an encoded path that routes to /admin gets 403', async () => {
	expect(await status('/%61dmin', undefined, '/admin')).toBe(403);
});

test('without Access configured, /admin fails closed', async () => {
	const unset = accessGuard({ keySet, issuer: undefined, audience: undefined });
	expect(await status('/admin', await token(), '/admin', unset)).toBe(403);
});

test('public pages need no JWT', async () => {
	expect(await status('/', undefined, '/')).toBe(200);
	expect(await status('/administrator')).toBe(200);
});
