/** A Season by its start year: 2025 → "2025–26". */
export const seasonName = (season: number) => `${season}–${String(season + 1).slice(2)}`;

export const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** "Junior Pairs free skating, qualifying group a": the Segment, as the ISU names it. */
export const segmentName = (p: { discipline: string; level: string; segment_type: string; round: string }) =>
	capitalize([p.level === 'junior' ? 'junior' : '', p.discipline, p.segment_type].filter(Boolean).join(' ')) +
	(p.round ? `, ${p.round}` : '');

/** "4–7 Dec 2025": a Competition's dateRange, given as yyyy-mm-dd. */
export function dateRange(start: string, end: string) {
	const day = (d: string, options: Intl.DateTimeFormatOptions) =>
		new Date(`${d}T00:00:00Z`).toLocaleDateString('en-GB', { timeZone: 'UTC', ...options });
	return start === end ? day(end, { dateStyle: 'medium' }) : `${day(start, { day: 'numeric' })}–${day(end, { dateStyle: 'medium' })}`;
}
