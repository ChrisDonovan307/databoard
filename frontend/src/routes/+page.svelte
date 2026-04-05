<script lang="ts">
	import Map from './Map.svelte';
	import BarChart from './BarChart.svelte';

	let { data } = $props();

	// Map interactions
	let selectedName: string | null = $state(null);
	let inst = $derived(
		data.installations.features.find(({ properties }) => properties.name === selectedName) ?? null
	);
</script>

<div class="container grid grid-cols-12 grid-rows-3 gap-4 min-h-0 max-w-full mx-4 my-4">
	<div class="col-span-3 row-span-2">
		<div class="card">
			<div class="card-body">
				<h2 class="card-title">Databoard</h2>
				<p>This is a work in progress to explore and visualize Dataverse installations. It might get more interesting later. UVM needs to be added to this map.</p>
				<div class="card-actions justify-end"></div>
			</div>
		</div>
	</div>

	<div class="col-span-9 row-span-2 flex justify-center">
		<!-- Pass selectedName up from component -->
		<Map {data} bind:selectedName />
	</div>

	<div class="col-span-4">
		<div class="card">
			{#if inst}
				<div class="card-body">
					<h3 class="card-title">{inst?.properties.name}</h3>
					<ul>
						<li>{inst?.properties.country}, {inst?.properties.launch_year}</li>
						<li><strong>Description:</strong> {inst?.properties.description}</li>
						<li>
							<strong>URL:</strong> 
							<a class="inline-link" href={`https://${inst?.properties.hostname}`} target="_blank">
								{inst?.properties.hostname}
							</a>
						</li>
					</ul>
				</div>
			{:else}
				<div class="center-vertical">
					<p>Click an installation on the map to see details.</p>
				</div>
			{/if}
		</div>
	</div>

	<div class="col-span-4">
		<BarChart
			labels={data.countries.map(d => d.country)}
			values={data.countries.map(d => d.count)}
			title="Installations by Country"
			xLabel="Country"
			yLabel="Number of Installations"
		/>
	</div>

	<div class="col-span-4">
		<BarChart
			labels={data.dataverses.map(d => d.installation)}
			values={data.dataverses.map(d => d.count)}
			title="Datasets per Dataverse"
			xLabel="Dataverse"
			yLabel="Number of Datasets"
		/>
	</div>

</div>

<style>
	.container {
		height: calc(100vh - (var(--spacing) * 22));
		width: calc(100vw - (var(--spacing) * 8));
	}
	:global(.card) {
		border-radius: 6px;
		border: var(--border) solid var(--color-base-300);
		width: 100%;
		height: 100%;
		background-color: var(--color-base-200);
		color: var(--color-base-content);
		overflow-y: scroll;

	}
	.center-vertical {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
	}

	.inline-link {
		color: var(--color-secondary);
		cursor: pointer;
	}
	.inline-link:hover {
		text-decoration: underline;
	}
</style>
