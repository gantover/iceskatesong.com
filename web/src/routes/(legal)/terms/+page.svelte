<script lang="ts">
	import type { PageProps } from './$types';
	let { data }: PageProps = $props();
</script>

<svelte:head><title>Terms · iceskatesong.com</title></svelte:head>

<h1>Terms</h1>
<p>iceskatesong.com is a non-commercial reference for figure skating results, Program music and videos.</p>

<h2>YouTube</h2>
<p>This site uses YouTube API Services. By using this site, including playing videos, you agree to be
	bound by the <a href="https://www.youtube.com/t/terms">YouTube Terms of Service</a>. Review our
	<a href="/privacy">Privacy policy</a> and the
	<a href="https://policies.google.com/privacy">Google Privacy Policy</a> before loading a video.</p>

<h2>Accuracy and availability</h2>
<p>Information is provided without warranty as to accuracy, completeness or availability. Music matches
	and video links can be wrong, and videos may become unavailable. Check the linked original results
	for official information. Nothing here limits rights or liability that cannot lawfully be limited.</p>

<h2>Independent site</h2>
<p>This site is not affiliated with or endorsed by the International Skating Union (ISU), YouTube,
	Google or the Wikimedia Foundation. Names and marks belong to their respective owners. Videos remain
	on YouTube and are subject to their owners' rights.</p>
<p>For data licences and credits, see <a href="/sources">Sources</a>. For corrections, removal requests
	or other questions, contact <a href="mailto:{data.site.email}">{data.site.email}</a>.</p>
