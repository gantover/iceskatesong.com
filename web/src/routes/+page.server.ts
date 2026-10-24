import { PUBLIC_CACHE } from '#lib/server/browse.js';

export const load = ({ setHeaders }) => setHeaders(PUBLIC_CACHE);
