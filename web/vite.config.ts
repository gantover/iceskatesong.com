import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter(),
			// One .env at the repo root, shared with Compose.
			env: { dir: '..' }
		})
	],
	test: {
		expect: { requireAssertions: true },
		environment: 'node',
		globalSetup: ['./vitest.global-setup.ts'],
		include: ['src/**/*.{test,spec}.{js,ts}']
	}
});
