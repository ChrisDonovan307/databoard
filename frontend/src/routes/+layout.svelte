<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import "../app.css"
	import { base } from '$app/paths';

	import { themeState } from '$lib/theme.svelte';

	let { children } = $props();

	function toggleTheme() {
		themeState.value = themeState.value === 'dim' ? 'emerald' : 'dim';
		document.documentElement.setAttribute('data-theme', themeState.value);
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/7.0.1/css/all.min.css" />
</svelte:head>

<div class="navbar bg-base-100 shadow-sm min-h-0 h-14">
  <div class="flex-1">
    <a href="{base}/" class="btn btn-ghost text-xl">Databoard</a>
  </div>
	<div class="flex gap-1">
		🌙<input type="checkbox" class="toggle" onclick={toggleTheme}/>☀️
	</div>
  <div class="flex-none">
    <ul class="menu menu-horizontal px-1">
      <li><a href="/databoard/map">Map</a></li>
      <li>
        <details>
          <summary>Parent</summary>
          <ul class="bg-base-100 rounded-t-none p-2">
            <li><a>Link 1</a></li>
            <li><a>Link 2</a></li>
          </ul>
        </details>
      </li>
    </ul>
  </div>
</div>

{@render children()}