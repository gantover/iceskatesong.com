<script lang="ts">
	import GradeBadge from '#lib/components/GradeBadge.svelte';
	import { capitalize, seasonName } from '#lib/format.js';
	import { wikipediaUrl } from '#lib/wikipedia.js';

	let { data } = $props();
	const piece = $derived(data.piece);
	const programs = $derived(data.owners.flatMap((o) => o.programs));
	const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;
</script>

<svelte:head>
	<title>{piece.title} · iceskatesong.com</title>
</svelte:head>

<main class="mx-auto max-w-4xl px-4 py-6">
	<h1 class="text-2xl font-semibold tracking-tight">{piece.title}</h1>
	<p class="text-muted-foreground text-sm">
		{#if piece.composers.length}By {piece.composers.join(', ')}{/if}
		{#if piece.composers.length && piece.source}·{/if}
		{#if piece.source}From <em>{piece.source}</em>{/if}
		{#if piece.qid}
			· <a href="https://www.wikidata.org/wiki/{piece.qid}" class="hover:underline">Wikidata {piece.qid} ↗</a>
		{/if}
	</p>
	<p class="mt-2 text-sm">
		{data.owners.some((o) => o.entity === 'team')
			? `${data.owners.length} Skaters and Teams`
			: plural(data.owners.length, 'Skater')} ·
		{plural(programs.length, 'Program')}
		<button disabled class="text-muted-foreground ml-3 cursor-not-allowed" title="Available in a future release">Wrong music?</button>
	</p>

	{#each data.owners as owner (`${owner.entity}/${owner.slug}`)}
		<details open={data.owners.length <= 4} class="bg-card my-3 rounded-lg border">
			<summary class="cursor-pointer px-4 py-2.5 font-medium">
				<a href="/{owner.entity}/{owner.slug}" class="hover:underline">{owner.name}</a>
				<span class="text-muted-foreground text-sm font-normal">· {plural(owner.programs.length, 'Program')}</span>
			</summary>
			<ul class="divide-y border-t">
				{#each owner.programs as program (program.id)}
					<li class="px-4 py-2.5">
						<p>
							<a href="/{owner.entity}/{owner.slug}/{program.season}" class="hover:underline"
								>{seasonName(program.season)} · {capitalize(program.segment_type)}</a
							>
							<GradeBadge grade={program.grade} />
						</p>
						{#if program.article_title}
							<a href={wikipediaUrl(program.article_title, program.revision)} title="Music: Wikipedia, {program.article_title}"
								class="text-muted-foreground block text-sm whitespace-pre-line hover:underline">{program.raw_text} ↗</a
							>
						{:else}
							<p class="text-muted-foreground text-sm whitespace-pre-line">{program.raw_text}</p>
						{/if}
						<ul class="mt-1 space-y-0.5 text-sm">
							{#each program.performances as p (p.id)}
								<li class="flex justify-between gap-2">
									<a href="/performance/{p.id}" class="hover:underline">{p.competition}</a>
									<span class="shrink-0 tabular-nums">
										{p.rank_label ?? p.rank ?? '–'} ·
										<span class={p.video ? 'text-primary' : 'text-muted-foreground'}>{p.video ? '▶ video' : 'no video'}</span>
									</span>
								</li>
							{/each}
						</ul>
					</li>
				{/each}
			</ul>
		</details>
	{:else}
		<p class="text-muted-foreground mt-4">No Program on record uses this Piece.</p>
	{/each}

	{#if programs.some((p) => p.article_title)}
		<p class="text-muted-foreground mt-4 text-xs">
			Music: Wikipedia (linked on each music entry) ·
			<a href="https://creativecommons.org/licenses/by-sa/4.0/" class="hover:underline">CC BY-SA 4.0, modified</a>.
		</p>
	{/if}
</main>
