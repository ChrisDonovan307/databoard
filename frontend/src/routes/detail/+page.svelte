<script lang="ts">
	import { onMount } from 'svelte';
	import { initGrid } from './AgGrid';
	let gridContainer: HTMLElement;

	onMount(() => {
		initGrid(gridContainer);
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
	<div id="detailgrid" bind:this={gridContainer} style="height: 400px;"></div>
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