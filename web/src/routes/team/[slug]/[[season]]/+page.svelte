<script lang="ts">
	import Career from '#lib/components/Career.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.team.name} · iceskatesong.com</title>
</svelte:head>

<main class="mx-auto max-w-4xl px-4 py-6">
	<h1 class="text-2xl font-semibold tracking-tight">
		{#each data.skaters as skater, i (skater.slug)}
			{#if i}<span class="text-muted-foreground mx-1">/</span>{/if}<a href="/skater/{skater.slug}" class="hover:underline">{skater.name}</a>
		{/each}
	</h1>
	<Career base="/team/{data.team.slug}" seasons={data.seasons} season={data.season} performances={data.performances} />
</main>
