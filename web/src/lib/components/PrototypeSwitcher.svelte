<script lang="ts">
	// PROTOTYPE (#39), throwaway: cycles the theme variants in prototype-themes.css.
	// The layout keeps this mounted, so the variant survives links that drop ?variant=; it is written back for reloads.
	import { afterNavigate, replaceState } from '$app/navigation';
	import { page } from '$app/state';

	const VARIANTS = [
		{ key: '0', name: 'Current (shadcn neutral)' },
		{ key: 'a', name: 'Pit wall' },
		{ key: 'b', name: 'Rink' },
		{ key: 'c', name: 'Programme notes' },
		{ key: 'd', name: 'Scoreboard' }
	];

	let current = $state('a');
	const index = $derived(VARIANTS.findIndex((v) => v.key === current));

	$effect(() => {
		if (current === '0') delete document.documentElement.dataset.variant;
		else document.documentElement.dataset.variant = current;
	});

	function writeUrl() {
		const url = new URL(page.url.href);
		url.searchParams.set('variant', current);
		// shortcut: replaceState is deprecated in Kit 3, but the suggested shallow goto hung the tab here; fine for a throwaway.
		replaceState(url, page.state);
	}

	afterNavigate(() => {
		const asked = page.url.searchParams.get('variant');
		if (VARIANTS.some((v) => v.key === asked)) current = asked!;
		else writeUrl();
	});

	function step(by: number) {
		current = VARIANTS[(index + by + VARIANTS.length) % VARIANTS.length].key;
		writeUrl();
	}

	function onkeydown(e: KeyboardEvent) {
		const el = e.target as HTMLElement;
		if (e.altKey || e.ctrlKey || e.metaKey || el.closest('input, textarea, select, [contenteditable]')) return;
		if (e.key === 'ArrowLeft') step(-1);
		if (e.key === 'ArrowRight') step(1);
	}
</script>

<svelte:window {onkeydown} />

<div
	class="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-1 rounded-full bg-black px-1.5 py-1 font-[system-ui] text-sm text-white shadow-lg ring-2 ring-fuchsia-500"
>
	<button class="rounded-full px-2.5 py-1 hover:bg-white/15" onclick={() => step(-1)} aria-label="Previous variant">←</button>
	<span class="min-w-48 text-center">{current.toUpperCase()} ({VARIANTS[index].name})</span>
	<button class="rounded-full px-2.5 py-1 hover:bg-white/15" onclick={() => step(1)} aria-label="Next variant">→</button>
</div>
