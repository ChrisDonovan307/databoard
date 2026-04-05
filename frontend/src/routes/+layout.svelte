<script lang="ts">
	// import favicon from '$lib/assets/favicon.svg';
	import "../app.css"
	import { base } from '$app/paths';
  import Navbar from './Navbar.svelte'

  // themeState as $state
	import { themeState } from '$lib/theme.svelte';

	let { children } = $props();

	function toggleTheme() {
		themeState.value = themeState.value === 'dim' ? 'emerald' : 'dim';
	}
</script>

<svelte:head>
	<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/7.0.1/css/all.min.css" />
	<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='15' fill='%23555'/><text x='50' y='72' font-size='60' font-family='sans-serif' font-weight='bold' fill='white' text-anchor='middle'>DB</text></svg>">
</svelte:head>

<Navbar />

{@render children()}