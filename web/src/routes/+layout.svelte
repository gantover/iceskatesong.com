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

	let { children }: LayoutProps = $props();
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
