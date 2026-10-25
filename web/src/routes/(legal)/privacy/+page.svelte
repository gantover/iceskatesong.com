<script lang="ts">
	import type { PageProps } from './$types';
	let { data }: PageProps = $props();
</script>

<svelte:head><title>Privacy · iceskatesong.com</title></svelte:head>

<h1>Privacy</h1>
<p>iceskatesong.com is a non-commercial figure skating and music reference run by {data.site.operator},
	the data controller, in Belgium. For privacy questions or to exercise your rights, email
	<a href="mailto:{data.site.email}">{data.site.email}</a>.</p>

<h2>Visiting the site</h2>
<p>We do not use analytics, advertising trackers or third-party fonts. The public pages set no cookies.
	The light or dark appearance preference is stored in your browser's local storage; you can remove it
	by clearing this site's browser data.</p>
<p>Cloudflare delivers and protects the site. It processes connection information, including IP addresses,
	request details and security signals, to route traffic and prevent abuse. The legal basis is our
	legitimate interest in providing a reliable, secure service (GDPR Article 6(1)(f)). Cloudflare may
	process data outside the European Economic Area using the safeguards described in its
	<a href="https://www.cloudflare.com/cloudflare-customer-dpa/">data processing agreement</a> and
	<a href="https://www.cloudflare.com/privacypolicy/">Privacy Policy</a>.</p>
<p>Our application does not deliberately log visitor IP addresses. Operational and error logs are rotated,
	with a maximum of three 10 MB files per service. Cloudflare's own security and connection data follow
	the retention described in its Privacy Policy. The Admin's Cloudflare Access login uses necessary
	authentication cookies on <code>/admin</code>; it is not used to track public visitors.</p>

<h2>YouTube videos</h2>
<p>This site uses YouTube API Services to find official videos and display their titles. We do not ask
	for your YouTube account or use YouTube sign-in. Public video metadata is refreshed or removed within
	30 days.</p>
<p>No YouTube or Google resource loads until you choose to play a video. Clicking the video placeholder
	loads a player from <code>youtube-nocookie.com</code>. Google then receives your IP address, browser
	information and the referring site, and may store or access information on your device. This happens
	on your consent to load that video. Read the
	<a href="https://policies.google.com/privacy">Google Privacy Policy</a> and
	<a href="https://www.youtube.com/t/terms">YouTube Terms of Service</a> before playing.</p>
<p>Consent applies to the selected player, not future page visits. To stop further player requests, leave
	or reload the page. To remove data already stored by Google, use your browser's site-data controls
	and Google's privacy controls; leaving the page does not undo earlier processing.</p>

<h2>If you are a Skater listed here</h2>
<p>We reuse public sporting facts from ISU results: names, competition nationality, ISU identifiers,
	partners, Seasons, results and scores. Wikidata supplies alternative names and links; English Wikipedia
	supplies Program music. Official YouTube videos may be linked to Performances. See
	<a href="/sources">Sources</a> for attribution. We do not collect dates of birth or height as profile
	fields or show them.</p>
<p>The legal basis is our legitimate interest in a public reference connecting figure skating Performances
	and music (GDPR Article 6(1)(f)). We limit records to public competition facts needed for that purpose,
	including for junior Skaters. We keep these historical records while they serve that reference purpose,
	and review them when you raise an objection or ask for a correction or removal.</p>
<p>You can object to the processing or ask for correction, restriction or erasure by emailing
	<a href="mailto:{data.site.email}">{data.site.email}</a>. Include the page link and the issue; you do
	not need to publish personal information in a form. We consider your circumstances, including concerns
	about minors, and respond within one month unless a lawful extension is needed. Removed information
	may remain in protected backups for up to 30 days.</p>

<h2>Contact and your rights</h2>
<p>If you email us, we use your address and message to respond and handle your request, based on our
	legitimate interest in providing support or our legal obligations where applicable. We keep that
	correspondence only as needed to resolve the request and meet applicable legal obligations.</p>
<p>Depending on the processing, you have rights of access, rectification, erasure, restriction, objection
	and data portability, and may withdraw consent without affecting earlier lawful processing. Contact
	<a href="mailto:{data.site.email}">{data.site.email}</a>. You can also complain to the
	<a href="https://www.autoriteprotectiondonnees.be/citoyen/agir/introduire-une-plainte">Belgian Data Protection Authority (APD/GBA)</a>
	or your local supervisory authority.</p>
