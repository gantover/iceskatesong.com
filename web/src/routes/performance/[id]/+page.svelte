<script lang="ts">
	import VideoSlot from '#lib/components/VideoSlot.svelte';
	import { dateRange, seasonName, segmentName } from '#lib/format.js';

	let { data } = $props();
	const p = $derived(data.performance);
</script>

<svelte:head>
	<title>{p.name} · {p.competition} · iceskatesong.com</title>
</svelte:head>

<main class="mx-auto max-w-5xl px-4 py-6">
	<nav class="text-muted-foreground text-sm" aria-label="Breadcrumb">
		<a href="/" class="hover:underline">Search</a> ›
		<a href="/{p.entity}/{p.slug}/{p.season}" class="hover:underline">{p.name} {seasonName(p.season)}</a> › Performance
	</nav>
	<h1 class="mt-1 text-2xl font-semibold tracking-tight">{p.name}</h1>
	<p class="text-muted-foreground">{p.competition} · {segmentName(p)}</p>

	<div class="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
		<div>
			<!-- A new Performance starts a new slot: back to its first video, not yet loaded. -->
			{#key p.id}<VideoSlot videos={data.videos} />{/key}
		</div>
		<aside class="space-y-4">
			<section class="bg-card rounded-lg border p-4">
				<h2 class="text-muted-foreground text-xs tracking-wide uppercase">Result</h2>
				<p class="mt-1 text-2xl tabular-nums">
					{#if p.rank_label}{p.rank_label}{:else}{p.rank ?? '–'}
						<span class="text-muted-foreground text-base">{p.tss ?? ''}</span>{/if}
				</p>
				{#if p.tss}
					<dl class="mt-2 grid grid-cols-[max-content_1fr] gap-x-4 text-sm tabular-nums">
						<dt class="text-muted-foreground">Technical</dt>
						<dd>{p.tes}</dd>
						<dt class="text-muted-foreground">Components</dt>
						<dd>{p.pcs}</dd>
						{#if p.deductions && Number(p.deductions)}
							<dt class="text-muted-foreground">Deductions</dt>
							<dd>{p.deductions}</dd>
						{/if}
					</dl>
				{/if}
				<p class="text-muted-foreground mt-2 text-sm">{p.city} · {dateRange(p.start_date, p.end_date)}</p>
				<a href={p.url} target="_blank" rel="noopener noreferrer" class="text-primary mt-1 inline-block text-sm hover:underline"
					>ISU result page ↗</a
				>
			</section>
			{#if data.sameProgram.length}
				<section class="bg-card rounded-lg border p-4">
					<h2 class="text-muted-foreground text-xs tracking-wide uppercase">Same Program, other Competitions</h2>
					<ul class="mt-1 space-y-1 text-sm">
						{#each data.sameProgram as other (other.id)}
							<li class="flex justify-between gap-2">
								<a href="/performance/{other.id}" class="hover:underline">{other.competition}</a>
								<span class="text-muted-foreground shrink-0 tabular-nums"
									>{other.rank_label ?? other.rank ?? '–'}{other.video ? ' · ▶' : ''}</span
								>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
		</aside>
	</div>
</main>
