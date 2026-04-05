<script lang="ts">
	import { MapLibre, Marker, Popup } from 'svelte-maplibre';
	import { Chart } from 'chart.js/auto';
	import { themeState } from '$lib/theme.svelte';
	import { Colors } from 'chart.js';
	Chart.register(Colors);

	let { data } = $props();

	// Map interactions
	let hoveredName: string | null = $state(null);
	let selectedName: string | null = $state(null);
	let inst = $derived(
		data.installations.features.find(({ properties }) => properties.name === selectedName) ?? null
	);

	// Set up graph
	let chartInstance: Chart | null = null;

	$effect(() => {
		themeState.value; // track 

		requestAnimationFrame(() => {
			const canvas = document.getElementById('chart') as HTMLCanvasElement;
			if (!canvas) return;

			const style = getComputedStyle(document.documentElement);
			const chartColors = {
				bar: style.getPropertyValue('--color-primary').trim(),
				legend: style.getPropertyValue('--color-base-content').trim(),
				axis: style.getPropertyValue('--color-base-content').trim(),
			};

			const countsByInstallation = Object.fromEntries(
				Object.entries(
					data.dataverses.reduce((acc: Record<string, number>, dv) => {
						acc[dv.installation] = (acc[dv.installation] ?? 0) + dv.datasetCount;
						return acc;
					}, {})
				).slice(0, 12)
			);

			console.log(countsByInstallation);

			chartInstance?.destroy();
			chartInstance = new Chart(canvas, {
				type: 'bar',
				data: {
					labels: Object.keys(countsByInstallation),
					datasets: [{
						label: 'Datasets per installation',
						data: Object.values(countsByInstallation),
						backgroundColor: chartColors.bar
					}]
				},
				options: {
					color: chartColors.legend,
					scales: {
						x: { ticks: { color: chartColors.axis } },
						y: { ticks: { color: chartColors.axis } }
					}
				}
			});
		});
	});
</script>

<div class="container grid grid-cols-12 grid-rows-3 gap-4 min-h-0 max-w-full mx-4 my-4">
	<div class="col-span-3 row-span-2">
		<div class="card">
			<div class="card-body">
				<h2 class="card-title">Card Title</h2>
				<p>
					A card component has a figure, a body part, and inside body there are title and actions parts
				</p>
				<div class="card-actions justify-end">
					<a class="styled-link" href="https://dataverse.harvard.edu/" target="_blank">
						Harvard Dataverse
						<i class="fa-solid fa-link"></i>
					</a>
				</div>
			</div>
		</div>
	</div>

	<div class="col-span-9 row-span-2 flex justify-center">
		<MapLibre
			center={[-13.2, 27.2]}
			zoom={1}
			class="map"
			standardControls
			style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
		>
			{#each data.installations.features as { geometry, properties }}
				<Marker lngLat={geometry.coordinates as [number, number]}>
					<button
						class="marker-btn"
						onmouseenter={() => (hoveredName = properties.name)}
						onmouseleave={() => (hoveredName = null)}
						onclick={() => (selectedName = properties.name)}
						title="marker"
					>
						<i class="fa-solid fa-location-pin"></i>
					</button>
					<Popup open={hoveredName === properties.name} offset={[0, -10]}>
						<div class="text-lg text-black">{properties.name}</div>
					</Popup>
				</Marker>
			{/each}
		</MapLibre>
	</div>

	<div class="col-span-4">
		<div class="card">
			{#if inst}
				<div class="card-body">
					<h2 class="card-title">{inst?.properties.name}</h2>
					<ul>
						<li>{inst?.properties.country}, {inst?.properties.launch_year}</li>
						<li><strong>Description:</strong> {inst?.properties.description}</li>
						<li>
							<strong>URL:</strong>
							<a class="inline-link" href={inst?.properties.hostname}>{inst?.properties.hostname}</a
							>
						</li>
					</ul>
				</div>
			{/if}
		</div>
	</div>

	<div class="col-span-4">
		<div class="card"><canvas id="chart"></canvas></div>
	</div>

	<div class="col-span-4">
		<div class="card"></div>
	</div>
</div>

<style>
	:global(.map) {
		height: 100%;
		width: 100%;
		border-radius: 6px;
	}
	.marker-btn {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 1.5rem;
		padding: 0;
	}
	i {
		color: var(--color-green-950);
		opacity: 0.75;
	}
	.container {
		height: calc(100vh - (var(--spacing) * 22));
		width: calc(100vw - (var(--spacing) * 8));
	}
	:global(.card) {
		border-radius: 6px;
		border: var(--border) solid var(--color-base-100);
		width: 100%;
		height: 100%;
		background-color: var(--color-base-300);
		color: var(--color-base-content);
		overflow-y: scroll;
	}
	.inline-link {
		color: var(--color-taupe-800);
		cursor: pointer;
	}
	.inline-link:hover {
		color: var(--color-green-700);
	}
	.styled-link {
		background-color: var(--color-gray-300);
		border-radius: 5px;
		border: 1px solid black;
		padding: 5px 10px;
		color: var(--color-taupe-800);
	}
	.styled-link:hover {
		background-color: var(--color-taupe-500);
	}
</style>
