<script lang="ts">
	import { Button } from '#lib/components/ui/button/index.js';
	import { cn } from '#lib/utils.js';

	type Video = { youtube_id: string; start_seconds: number | null; origin: string; title: string | null };

	/**
	 * Click-to-load YouTube player: nothing from Google or YouTube loads before the click.
	 * `videos` come in play order; the first one is shown.
	 */
	let { videos }: { videos: Video[] } = $props();

	// Raw: a deep $state proxy would never be === to an entry of `videos`.
	// svelte-ignore state_referenced_locally
	let current = $state.raw(videos[0]);
	let loaded = $state(false);

	const LABELS: Record<string, string> = { official: 'Official ISU video', admin: 'Added by the Admin', submitted: 'Submitted video' };
	const label = (v: Video) => (v.start_seconds === null ? 'Full-segment stream' : LABELS[v.origin]);
</script>

{#snippet empty(heading: string, note: string)}
	<div class="bg-muted flex aspect-video flex-col items-center justify-center gap-1 rounded-lg border border-dashed p-4 text-center">
		<p class="font-medium">{heading}</p>
		<p class="text-muted-foreground text-sm">{note}</p>
	</div>
{/snippet}

{#if !videos.length}
	{@render empty('No video yet', 'Know a YouTube video of this Performance? Submitting one comes soon.')}
{:else if loaded}
	<iframe
		class="aspect-video w-full rounded-lg"
		src="https://www.youtube-nocookie.com/embed/{current.youtube_id}?autoplay=1&start={current.start_seconds ?? 0}"
		title={current.title ?? 'YouTube video'}
		allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
		referrerpolicy="strict-origin-when-cross-origin"
	></iframe>
{:else}
	<button
		type="button"
		onclick={() => (loaded = true)}
		aria-describedby="youtube-privacy"
		class="group flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-lg bg-neutral-900 p-4 text-center text-neutral-100"
	>
		<svg viewBox="0 0 68 48" class="h-12 w-16" aria-hidden="true">
			<rect width="68" height="48" rx="12" class="fill-[#cc0000] group-hover:fill-[#ff0000]" />
			<path d="M27 14 L47 24 L27 34 Z" fill="#fff" />
		</svg>
		<span class="text-sm">{current.title ?? 'Play on YouTube'}</span>
		{#if current.start_seconds === null}
			<span class="text-xs text-neutral-400">Untimed full-segment stream: find this Performance in it yourself.</span>
		{/if}
	</button>
{/if}

{#if videos.length}
	<p id="youtube-privacy" class="text-muted-foreground mt-2 text-xs">
		Plays from YouTube (Google). On click, Google receives your IP address and may store data on your device.
		By playing, you agree to the <a href="https://www.youtube.com/t/terms" class="underline">YouTube Terms</a>
		and acknowledge our <a href="/privacy" class="underline">Privacy policy</a>.
	</p>
{/if}

{#if videos.length > 1}
	<ul class="mt-2 space-y-1 text-sm">
		{#each videos as v, i (i)}
			<li class="flex flex-wrap items-center gap-2">
				<button type="button" onclick={() => (current = v)} class={cn('hover:underline', v === current && 'font-semibold')}
					>{v === current ? '▶' : '·'} {label(v)}</button
				>
				{#if v.start_seconds === null}<span class="bg-muted text-muted-foreground rounded px-1.5 text-xs">untimed, plays last</span>{/if}
			</li>
		{/each}
	</ul>
{/if}

<div class="mt-3 flex flex-wrap gap-2">
	<Button variant="outline" size="sm" disabled title="Coming soon">Wrong video?</Button>
	<Button variant="outline" size="sm" disabled title="Coming soon">Submit another video</Button>
</div>
