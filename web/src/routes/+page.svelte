<script lang="ts">
	import SearchBox from '#lib/components/SearchBox.svelte';

	const EXAMPLES = ['Kévin Aymoz', 'Kaori Sakamoto', 'Yuzuru Hanyu', 'Papadakis', "He's a Pirate"];
</script>

<svelte:head>
	<title>iceskatesong.com: who skated to what</title>
</svelte:head>

<main class="mx-auto max-w-xl px-4 pt-16 pb-10 text-center sm:pt-24">
	<h1 class="text-3xl font-semibold tracking-tight">Who skated to what</h1>
	<p class="text-muted-foreground mt-2">Results and videos of ISU figure skating Performances since 2004–05.</p>
	<div class="mt-8 text-left"><SearchBox large /></div>
	<p class="text-muted-foreground mt-3 text-sm">
		Try
		{#each EXAMPLES as example (example)}
			<a href="/search?q={encodeURIComponent(example)}" class="hover:bg-muted ml-1 inline-block rounded-full border px-2.5 py-0.5"
				>{example}</a
			>
		{/each}
	</p>
</main>
