<script lang="ts">
	import Career from '#lib/components/Career.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.skater.name} · iceskatesong.com</title>
</svelte:head>

<main class="mx-auto max-w-4xl px-4 py-6">
	<h1 class="text-2xl font-semibold tracking-tight">{data.skater.name}</h1>
	<p class="text-muted-foreground text-sm">{data.skater.nation}</p>
	<Career base="/skater/{data.skater.slug}" seasons={data.seasons} season={data.season} performances={data.performances} />
</main>
