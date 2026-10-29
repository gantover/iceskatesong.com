<script lang="ts">
	import type { Hit, MusicHit, TextHit } from '#lib/server/browse.js';
	import { capitalize, gradeMix, seasonName } from '#lib/format.js';
	import { cn } from '#lib/utils.js';

	let { value = '', large = false }: { value?: string; large?: boolean } = $props();

	// svelte-ignore state_referenced_locally
	let q = $state(value);
	let hits = $state<{ skaters: Hit[]; teams: Hit[]; music: MusicHit[]; text: TextHit[] }>();
	let open = $state(false);
	let controller: AbortController | undefined;
	let form: HTMLFormElement;

	async function lookup() {
		// A slower answer to an older query must not overwrite a newer one.
		controller?.abort();
		const query = q.trim();
		if (!query) {
			hits = undefined;
			return;
		}
		controller = new AbortController();
		try {
			const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
			if (!response.ok) return;
			hits = await response.json();
			open = true;
		} catch (e) {
			if ((e as Error).name !== 'AbortError') throw e;
		}
	}
</script>

{#snippet group(heading: string, kind: 'skater' | 'team', list: Hit[])}
	{#if list.length}
		{@render label(heading)}
		{#each list as hit (hit.slug)}
			<li><a class="hover:bg-muted focus:bg-muted block px-3 py-1.5 outline-none" href="/{kind}/{hit.slug}">{hit.name}</a></li>
		{/each}
	{/if}
{/snippet}

{#snippet label(text: string)}
	<li class="text-muted-foreground px-3 pt-2 pb-1 text-xs tracking-wide uppercase" role="presentation">{text}</li>
{/snippet}

<svelte:document
	onpointerdown={(e) => {
		if (!form.contains(e.target as Node)) open = false;
	}}
/>

<!-- Safari blurs with no relatedTarget before a link click lands: only Tab out closes the list here. -->
<form
	bind:this={form}
	action="/search"
	role="search"
	class="relative w-full"
	onfocusout={(e) => {
		if (e.relatedTarget && !e.currentTarget.contains(e.relatedTarget as Node)) open = false;
	}}
>
	<input
		type="search"
		name="q"
		bind:value={q}
		oninput={lookup}
		onfocus={() => (open = !!hits)}
		onkeydown={(e) => {
			if (e.key === 'Escape') open = false;
		}}
		placeholder="Search a Skater, Team or music…"
		aria-label="Search a Skater, Team or music"
		autocomplete="off"
		class={cn(
			'bg-background focus-visible:ring-ring/50 w-full rounded-lg border px-3 outline-none focus-visible:ring-3',
			large ? 'py-3 text-lg' : 'py-1.5 text-sm'
		)}
	/>
	{#if open && hits}
		<ul class="bg-popover text-popover-foreground absolute inset-x-0 top-full z-20 mt-1 max-h-[70vh] overflow-auto rounded-lg border py-1 text-sm shadow-lg">
			{@render group('Skaters', 'skater', hits.skaters)}
			{@render group('Teams', 'team', hits.teams)}
			{#if hits.music.length}
				{@render label('Music')}
				{#each hits.music as hit (hit.slug)}
					<li>
						<a class="hover:bg-muted focus:bg-muted block px-3 py-1.5 outline-none" href="/piece/{hit.slug}">
							{hit.title}{#if hit.credit}<span class="text-muted-foreground"> · {hit.credit}</span>{/if}
							<span class="text-muted-foreground block text-xs">{gradeMix(hit)}</span>
						</a>
					</li>
				{/each}
			{/if}
			{#if hits.text.length}
				{@render label('In music text, not matched to a Piece')}
				{#each hits.text as hit (hit.program_id)}
					<li>
						<a class="hover:bg-muted focus:bg-muted block px-3 py-1.5 outline-none" href="/{hit.entity}/{hit.slug}/{hit.season}">
							{hit.name}<span class="text-muted-foreground"> · {seasonName(hit.season)} {capitalize(hit.segment_type)}</span>
						</a>
					</li>
				{/each}
			{/if}
			{#if !hits.skaters.length && !hits.teams.length && !hits.music.length && !hits.text.length}
				<li class="text-muted-foreground px-3 py-1.5">Nothing found.</li>
			{/if}
			<li class="text-muted-foreground mt-1 border-t px-3 pt-1.5 text-xs">
				{q.trim().length < 3 ? 'Under 3 letters: names starting with what you typed.' : 'Matches anywhere in a name, typos included.'}
			</li>
		</ul>
	{/if}
</form>
