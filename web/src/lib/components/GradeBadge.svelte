<script lang="ts">
	import type { Grade } from '#lib/server/browse.js';
	import { cn } from '#lib/utils.js';

	let { grade }: { grade: Grade } = $props();

	const EXPLAIN: Record<Grade, string> = {
		identified: 'Identified: linked to this Piece by an external ID (Wikidata)',
		credited: 'Credited: the music text names its composer or Source',
		'title only': 'Title only: matched on the title alone, so it may be another Piece of that name'
	};
</script>

<span
	title={EXPLAIN[grade]}
	class={cn(
		'inline-block rounded-full border px-1.5 py-px align-middle text-[0.7rem] leading-tight whitespace-nowrap',
		grade === 'identified' && 'border-primary text-primary',
		grade === 'title only' && 'text-muted-foreground border-dashed'
	)}>{grade}</span
>
