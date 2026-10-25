/** The attributed revision remains accessible even after the live article changes. */
export function wikipediaUrl(title: string, revision: string | null) {
	const params = new URLSearchParams({ title });
	if (revision) params.set('oldid', revision);
	return `https://en.wikipedia.org/w/index.php?${params}`;
}
