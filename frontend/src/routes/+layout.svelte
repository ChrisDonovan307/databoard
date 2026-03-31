<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import "../app.css"
	import { onMount } from 'svelte';

	let { children } = $props();
	let theme = $state('dim');

	onMount(() => {
		const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		theme = prefersDark ? 'dim' : 'emerald';
		document.documentElement.setAttribute('data-theme', theme);
	});

	function toggleTheme() {
		theme = theme === 'dim' ? 'emerald' : 'dim';
		document.documentElement.setAttribute('data-theme', theme);
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="navbar bg-base-100 shadow-sm">
  <div class="flex-1">
    <a href="/" class="btn btn-ghost text-xl">Databoard</a>
  </div>
	<div class="flex gap-1">
		🌙<input type="checkbox" class="toggle" onclick={toggleTheme}/>☀️
	</div>
  <div class="flex-none">
    <ul class="menu menu-horizontal px-1">
      <li><a>Link</a></li>
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