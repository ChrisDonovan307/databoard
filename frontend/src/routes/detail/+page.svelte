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

<main class="container grid grid-cols-12 grid-rows-2 gap-4 min-h-0 max-w-full mx-4 my-4">
	<div class="col-span-3 row-span-1">
		<div class="card">
			<div class="card-body">
				<h2 class="card-title">More Things</h2>
				<div>
					<p>Things that might be interesting:</p>
					<ul>
						<li>Breakdowns by subject, across all and within each</li>
						<li>Trends in publication, citation, and downloads over time, across all and within each</li>
						<li>How are license use, data format, and software availability associated with citation and download counts</li>
					</ul>
				</div>
				<div class="card-actions justify-end"></div>
			</div>
		</div>
	</div>

	<div class="col-span-9 row-span-2">
		<div class="card">
			<div class="card-body p-0">
				<div bind:this={gridContainer} class="h-full"></div>
			</div>
		</div>
	</div>

	<div class="col-span-3 row-span-1">
		<div class="card">
			<div class="card-body">
				<h2 class="card-title">Even More Things</h2>
				<div>
				</div>
				<div class="card-actions justify-end"></div>
			</div>
		</div>
	</div>
</main>

<style>
	.container {
		height: calc(100vh - (var(--spacing) * 22));
		width: calc(100vw - (var(--spacing) * 8));
	}
	ul {
		display: block;
		list-style-type: disc;
		margin-top: 0.5rem;
		margin-bottom: 0.5rem;
		margin-right: 0;
		padding-left: 1.5rem;
	}
	:global(.card) {
		border-radius: 10px;
		border: var(--border) solid var(--color-base-300);
		width: 100%;
		height: 100%;
		background-color: var(--color-base-200);
		color: var(--color-base-content);
		overflow-y: scroll;
	}
</style>