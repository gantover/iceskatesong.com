<script lang="ts">
	import type { PerformanceRow } from '#lib/server/browse.js';
	import { dateRange, seasonName, segmentName } from '#lib/format.js';
	import { cn } from '#lib/utils.js';
	import MusicPieces from './MusicPieces.svelte';
	import { wikipediaUrl } from '#lib/wikipedia.js';

	/** Season tabs linking to `{base}/{season}`, and the chosen Season's Competitions, one row per Segment. */
	let {
		base,
		seasons,
		season,
		performances
	}: { base: string; seasons: number[]; season: number | undefined; performances: PerformanceRow[] } = $props();

	// Rows come ordered by Competition: group the consecutive ones.
	const competitions = $derived(
		performances.reduce<PerformanceRow[][]>((groups, row) => {
			if (groups.at(-1)?.[0].competition_id === row.competition_id) groups.at(-1)!.push(row);
			else groups.push([row]);
			return groups;
		}, [])
	);
</script>

<nav class="my-4 flex flex-wrap gap-1" aria-label="Seasons">
	{#each seasons as s (s)}
		<a
			href="{base}/{s}"
			aria-current={s === season ? 'page' : undefined}
			class={cn(
				'rounded-md border px-2.5 py-1 text-sm',
				s === season ? 'bg-foreground text-background border-foreground' : 'hover:bg-muted'
			)}>{seasonName(s)}</a
		>
	{/each}
</nav>

{#each competitions as rows (rows[0].competition_id)}
	<section class="bg-card my-3 rounded-lg border">
		<h2 class="flex flex-wrap justify-between gap-x-4 border-b px-4 py-2.5 font-medium">
			<span>{rows[0].competition}</span>
			<span class="text-muted-foreground text-sm font-normal">{rows[0].city} · {dateRange(rows[0].start_date, rows[0].end_date)}</span>
		</h2>
		<ul class="divide-y">
			{#each rows as p (p.id)}
				<li>
					<div
						class="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 px-4 py-2.5 sm:grid-cols-[14rem_6rem_1fr_6rem]"
					>
						<a href="/performance/{p.id}" class="hover:underline">
							{segmentName(p)}
							{#if p.team}<span class="text-muted-foreground block text-sm">{p.team.name}</span>{/if}
						</a>
						<span class="tabular-nums">
							{#if p.rank_label}{p.rank_label}{:else}<strong>{p.rank ?? '–'}</strong>
								<span class="text-muted-foreground text-sm">{p.tss ?? ''}</span>{/if}
						</span>
						<div class="text-sm">
							<MusicPieces pieces={p.music?.pieces ?? []} />
							{#if p.music?.origin === 'wikipedia' && p.music.article_title}
								<a href={wikipediaUrl(p.music.article_title, p.music.revision)} title="Music: Wikipedia, {p.music.article_title}"
									class="text-muted-foreground whitespace-pre-line hover:underline">{p.music.raw_text} ↗</a>
							{:else}
								<span class="text-muted-foreground whitespace-pre-line">{p.music?.raw_text ?? 'Music not known yet'}</span>
							{/if}
						</div>
						<a href="/performance/{p.id}" class={cn('text-sm hover:underline sm:text-right', p.video ? 'text-primary' : 'text-muted-foreground')}>
							{p.video ? '▶ video' : 'no video'}
					</a>
					</div>
				</li>
			{/each}
		</ul>
	</section>
{:else}
	<p class="text-muted-foreground">No results on record.</p>
{/each}

{#if performances.some((p) => p.music?.origin === 'wikipedia')}
	<p class="text-muted-foreground mt-4 text-xs">
		Music: Wikipedia (linked on each music entry) ·
		<a href="https://creativecommons.org/licenses/by-sa/4.0/" class="hover:underline">CC BY-SA 4.0, modified</a>.
	</p>
{/if}
