<script lang="ts">
	import { onMount } from 'svelte';
	import { initGrid } from './AgGrid.ts';
	import { colorSchemeDarkWarm, colorSchemeLightWarm } from 'ag-grid-community';
	import { themeState } from '$lib/theme.svelte';

	let gridContainer: HTMLElement;
	let { data } = $props();

	console.log(themeState);

	$effect(() => {
	 	initGrid(gridContainer, data.dataverses);
	});
</script>

<main class="m-4">
	<h2>Detail</h2>
	<p>Things that might be interesting:</p>
	<ul>
		<li>Breakdowns by subject, across all and within each</li>
		<li>Trends in publication, citation, and downloads over time, across all and within each</li>
		<li>How are license use, data format, and software availability associated with citation and download counts</li>
	</ul>
	<div bind:this={gridContainer} class="h-125"></div>
</main>

<style>
	ul {
		display: block;
		list-style-type: disc;
		margin-top: 0.5rem;
		margin-bottom: 0.5rem;
		margin-right: 0;
		padding-left: 1.5rem;
	}
</style>