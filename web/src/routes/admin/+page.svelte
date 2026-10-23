<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { Button } from '#lib/components/ui/button/index.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	type Import = NonNullable<typeof data.last>;
	type Counts = Record<string, { created: number; updated: number }>;

	// Follows a queued or running Import to its end. The import service picks up pending ones within 30 s.
	$effect(() => {
		if (!data.current) return;
		const timer = setInterval(invalidateAll, 3000);
		return () => clearInterval(timer);
	});

	const time = (date: Date | null) =>
		date ? `${date.toLocaleString('en-GB', { timeZone: 'UTC' })} UTC` : '–';
</script>

<svelte:head>
	<title>Admin · iceskatesong.com</title>
</svelte:head>

{#snippet importCard(heading: string, run: Import | undefined)}
	<section class="space-y-2 rounded-lg border p-4">
		<h2 class="font-semibold">{heading}</h2>
		{#if run}
			<dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
				<dt class="text-muted-foreground">Import</dt>
				<dd>#{run.id} <strong>{run.status}</strong></dd>
				<dt class="text-muted-foreground">Queued</dt>
				<dd>{time(run.created_at)}</dd>
				<dt class="text-muted-foreground">Started</dt>
				<dd>{time(run.started_at)}</dd>
				<dt class="text-muted-foreground">Finished</dt>
				<dd>{time(run.finished_at)}</dd>
				<dt class="text-muted-foreground">Problems</dt>
				<dd>{run.problem_count}</dd>
				{#if run.error}
					<dt class="text-muted-foreground">Error</dt>
					<dd class="text-destructive">{run.error}</dd>
				{/if}
			</dl>
			{#if Object.keys(run.counts as Counts).length}
				<table class="text-sm">
					<thead>
						<tr class="text-muted-foreground text-left">
							<th class="pr-6 font-normal">Records</th>
							<th class="pr-6 font-normal">Created</th>
							<th class="font-normal">Updated</th>
						</tr>
					</thead>
					<tbody>
						{#each Object.entries(run.counts as Counts) as [entity, count] (entity)}
							<tr>
								<td class="pr-6">{entity}</td>
								<td class="pr-6 tabular-nums">{count.created}</td>
								<td class="tabular-nums">{count.updated}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		{:else}
			<p class="text-muted-foreground text-sm">None.</p>
		{/if}
	</section>
{/snippet}

<main class="mx-auto max-w-3xl space-y-6 p-6">
	<div class="flex items-center justify-between gap-4">
		<h1 class="text-2xl font-semibold">Admin</h1>
		<form method="POST" action="?/importNow" use:enhance>
			<Button type="submit">Import now</Button>
		</form>
	</div>

	{@render importCard('Current Import', data.current)}
	{@render importCard('Last Import', data.last)}

	{#if data.last}
		<section class="space-y-2">
			<h2 class="font-semibold">Problems of Import #{data.last.id}</h2>
			{#each data.problems as group (group.kind)}
				<details class="rounded-lg border">
					<summary class="cursor-pointer px-4 py-2">{group.kind} ({group.rows.length})</summary>
					<ul class="divide-y border-t text-sm">
						{#each group.rows as row, i (i)}
							<li class="px-4 py-1.5">
								<div class="font-mono break-all">{row.key}</div>
								{#if Object.keys(row.detail ?? {}).length}
									<div class="text-muted-foreground font-mono break-all">{JSON.stringify(row.detail)}</div>
								{/if}
							</li>
						{/each}
					</ul>
				</details>
			{:else}
				<p class="text-muted-foreground text-sm">None.</p>
			{/each}
		</section>
	{/if}
</main>
