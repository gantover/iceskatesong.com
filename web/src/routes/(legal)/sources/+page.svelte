<script lang="ts">
	import type { PageProps } from './$types';
	let { data }: PageProps = $props();
</script>

<svelte:head><title>Sources · iceskatesong.com</title></svelte:head>

<h1>Sources</h1>

<h2>International Skating Union</h2>
<p>Competition facts, entrants and results come from the
	<a href="https://results.isu.org/">ISU results service</a> and its
	<a href="https://www.isuresults.com/">results archive</a>. Performance pages link the exact result
	page used. The ISU is the official authority for these results; this site is independent.</p>

<h2>English Wikipedia</h2>
<p>Raw Program music text comes from program tables written by
	<a href="https://en.wikipedia.org/">English Wikipedia</a> contributors. Each Wikipedia-sourced music
	line links its article, whose history identifies its contributors. On a Skater page, the article
	credits are collected in one line.</p>
<p>Wikipedia music text: <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>,
	modified. We extract music cells, remove table formatting and references, and associate the text with
	our Programs. The Wikipedia-derived text and our adaptations remain available under that licence;
	this does not assert a licence over ISU results or YouTube videos.</p>

<h2>Wikidata</h2>
<p>External identifiers, article links and alternative names come from
	<a href="https://www.wikidata.org/">Wikidata</a>. Its structured data is released under
	<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>. Thanks to its contributors.</p>

<h2>YouTube</h2>
<p>Videos are hosted by <a href="https://www.youtube.com/">YouTube</a>; metadata comes through YouTube
	API Services. Players load only when you click. Video rights remain with their respective owners.
	See <a href="/privacy">Privacy</a> and <a href="/terms">Terms</a> for the player notices.</p>

<h2>Corrections and removal</h2>
<p>To report incorrect music, results or video assignments, request removal, or raise a rights concern,
	email <a href="mailto:{data.site.email}">{data.site.email}</a> with the page link and a short
	explanation. {data.site.operator} reviews these requests.</p>
