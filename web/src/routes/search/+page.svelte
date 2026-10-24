<script lang="ts">
	let { data } = $props();
</script>

<svelte:head>
	<title>{data.q} · iceskatesong.com</title>
</svelte:head>

{#snippet group(heading: string, kind: 'skater' | 'team', hits: typeof data.hits.skaters)}
	{#if hits.length}
		<h2 class="text-muted-foreground mt-6 mb-1 text-xs tracking-wide uppercase">{heading}</h2>
		<ul class="divide-y rounded-lg border">
			{#each hits as hit (hit.slug)}
				<li><a href="/{kind}/{hit.slug}" class="hover:bg-muted block px-4 py-2">{hit.name}</a></li>
			{/each}
		</ul>
	{/if}
{/snippet}

<main class="mx-auto max-w-3xl px-4 py-6">
	<h1 class="text-xl font-semibold">Search: {data.q}</h1>
	{@render group('Skaters', 'skater', data.hits.skaters)}
	{@render group('Teams', 'team', data.hits.teams)}
	{#if !data.hits.skaters.length && !data.hits.teams.length}
		<p class="text-muted-foreground mt-4">Nothing found.</p>
	{/if}
</main>
