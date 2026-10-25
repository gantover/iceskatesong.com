<script lang="ts">
	import type { LayoutProps } from './$types';
	let { children }: LayoutProps = $props();
</script>

<main class="legal mx-auto max-w-3xl px-4 py-8 leading-relaxed">
	{@render children()}
</main>

<style>
	.legal :global(h1) { font-size: 1.875rem; font-weight: 600; letter-spacing: -0.025em; }
	.legal :global(h2) { margin-top: 1.75rem; font-size: 1.25rem; font-weight: 600; }
	.legal :global(p), .legal :global(ul) { margin-top: 0.75rem; }
	.legal :global(ul) { list-style: disc; padding-left: 1.5rem; }
	.legal :global(li + li) { margin-top: 0.5rem; }
	.legal :global(a) { text-decoration: underline; text-underline-offset: 0.15em; overflow-wrap: anywhere; }
</style>
