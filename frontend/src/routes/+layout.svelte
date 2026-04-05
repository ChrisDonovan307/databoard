<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
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
	<link rel="icon" href={favicon} />
	<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/7.0.1/css/all.min.css" />
</svelte:head>

<Navbar />

{@render children()}