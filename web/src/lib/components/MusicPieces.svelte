<script lang="ts">
	import type { PieceUse } from '#lib/server/browse.js';
	import GradeBadge from './GradeBadge.svelte';

	/** A music line's Pieces in order, each linking to its page with its grade badge after it. */
	let { pieces }: { pieces: PieceUse[] } = $props();
</script>

{#if pieces.length}
	<ul class="flex flex-wrap gap-x-3 gap-y-0.5">
		{#each pieces as piece, i (i)}
			<li><a href="/piece/{piece.slug}" class="hover:underline">{piece.title}</a> <GradeBadge grade={piece.grade} /></li>
		{/each}
	</ul>
{/if}
