import { databaseStatus, db } from '#lib/server/db.js';

export const load = async () => ({ status: await databaseStatus(db) });
