<script lang="ts">
	let { data } = $props();
</script>

<main class="mx-auto max-w-2xl p-6">
	<h1 class="text-2xl font-semibold">iceskatesong.com</h1>
	<p class="text-muted-foreground mt-2">
		Postgres {data.status.version}: f_unaccent('Kévin') = {data.status.unaccented}
	</p>
</main>
