<script lang="ts">
	import { capitalize, gradeMix, seasonName } from '#lib/format.js';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.q} · iceskatesong.com</title>
</svelte:head>

{#snippet group(heading: string, kind: 'skater' | 'team', hits: typeof data.hits.skaters)}
	{#if hits.length}
		{@render label(heading)}
		<ul class="divide-y rounded-lg border">
			{#each hits as hit (hit.slug)}
				<li><a href="/{kind}/{hit.slug}" class="hover:bg-muted block px-4 py-2">{hit.name}</a></li>
			{/each}
		</ul>
	{/if}
{/snippet}

{#snippet label(text: string)}
	<h2 class="text-muted-foreground mt-6 mb-1 text-xs tracking-wide uppercase">{text}</h2>
{/snippet}

<main class="mx-auto max-w-3xl px-4 py-6">
	<h1 class="text-xl font-semibold">Search: {data.q}</h1>
	{@render group('Skaters', 'skater', data.hits.skaters)}
	{@render group('Teams', 'team', data.hits.teams)}
	{#if data.hits.music.length}
		{@render label('Music')}
		<ul class="divide-y rounded-lg border">
			{#each data.hits.music as hit (hit.slug)}
				<li>
					<a href="/piece/{hit.slug}" class="hover:bg-muted block px-4 py-2">
						{hit.title}{#if hit.credit}<span class="text-muted-foreground"> · {hit.credit}</span>{/if}
						<span class="text-muted-foreground block text-sm">{gradeMix(hit)}</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
	{#if data.hits.text.length}
		{@render label('In music text, not matched to a Piece')}
		<ul class="divide-y rounded-lg border">
			{#each data.hits.text as hit (hit.program_id)}
				<li>
					<a href="/{hit.entity}/{hit.slug}/{hit.season}" class="hover:bg-muted block px-4 py-2">
						{hit.name}<span class="text-muted-foreground"> · {seasonName(hit.season)} {capitalize(hit.segment_type)}</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
	{#if !data.hits.skaters.length && !data.hits.teams.length && !data.hits.music.length && !data.hits.text.length}
		<p class="text-muted-foreground mt-4">Nothing found.</p>
	{/if}
</main>
