<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import { ModeWatcher, toggleMode } from 'mode-watcher';
	import MoonIcon from '@lucide/svelte/icons/moon';
	import SunIcon from '@lucide/svelte/icons/sun';
	import { page } from '$app/state';
	import { Button } from '#lib/components/ui/button/index.js';
	import SearchBox from '#lib/components/SearchBox.svelte';
	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<!-- Follows the OS until the visitor toggles; the choice is kept in localStorage. -->
<ModeWatcher />
<header class="bg-background sticky top-0 z-10 flex items-center gap-4 border-b px-4 py-2.5">
	<a href="/" class="font-semibold tracking-tight">iceskatesong</a>
	<div class="max-w-md flex-1">
		<!-- The home page has its own, larger box. -->
		{#if page.url.pathname !== '/'}<SearchBox />{/if}
	</div>
	<span class="flex-1"></span>
	<Button onclick={toggleMode} variant="outline" size="icon" aria-label="Toggle dark mode">
		<SunIcon class="scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
		<MoonIcon class="absolute scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
	</Button>
</header>

{@render children()}

<footer class="text-muted-foreground mx-auto mt-8 flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-2 border-t px-4 py-5 text-sm">
	<nav class="flex gap-4" aria-label="Legal">
		<a href="/privacy" class="hover:underline">Privacy</a>
		<a href="/terms" class="hover:underline">Terms</a>
		<a href="/sources" class="hover:underline">Sources</a>
	</nav>
	<a href="mailto:{data.site.email}" class="break-all hover:underline">{data.site.email}</a>
</footer>
