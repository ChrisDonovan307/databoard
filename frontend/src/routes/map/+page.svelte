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
	let canvas: HTMLCanvasElement;
	let chartInstance: Chart | null = null;

	$effect(() => {
		themeState.value; // track

		// Use theme colors so they change with light/dark
		const style = getComputedStyle(document.documentElement);
		const chartColors = {
			bar: style.getPropertyValue('--color-primary').trim(),
			text: style.getPropertyValue('--color-base-content').trim(), // includes legend
			axis: style.getPropertyValue('--color-base-content').trim(),
		};

		chartInstance?.destroy();
		Chart.defaults.color = chartColors.text;
		chartInstance = new Chart(canvas, {
			type: 'bar',
			data: {
				labels: data.dataverses.map(d => d.installation),
				datasets: [{
					label: 'Datasets',
					data: data.dataverses.map(d => d.count),
					backgroundColor: chartColors.bar
				}]
			},
			options: {
				color: chartColors.text,
				scales: {
					x: { 
						ticks: { color: chartColors.axis },
						title: { display: true, text: 'Dataverse' }
					},
					y: { 
						ticks: { color: chartColors.axis },
						title: { display: true, text: 'Number of Datasets' }
					}
				},
				plugins: {
					title: {
						display: true,
						text: "Datasets per Dataverse",
						color: chartColors.text
					},
					legend: {
						display: false
					}
				}
			}
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
					<Popup open = { hoveredName === properties.name } offset={[0, -10]}>
						<div id="popup">
							<h3>{properties.name}</h3>
							<p><span>Established:</span><span>{properties.launch_year}</span></p>
							<p><span>DOI Authority:</span><span>{properties.doi_authority}</span></p>
							<p><span>Metrics API:</span><span>{properties.metrics === true ? 'Yes' : 'No'}</span></p>
						</div>
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
		<!-- Bind canvas to this inside of $effect -->
		<div class="card"><canvas bind:this={canvas}></canvas></div>
	</div>

	<div class="col-span-4">
		<div class="card"></div>
	</div>
</div>

<style>
	.container {
		height: calc(100vh - (var(--spacing) * 22));
		width: calc(100vw - (var(--spacing) * 8));
	}
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
	#popup {
		max-width: 300px;
		h3 {
			font-weight: bold;
		}
		h3, p {
			color: var(--color-gray-900);
		}
		p {
			display: flex;
			justify-content: space-between;
			gap: 1rem;
		}
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
		color: var(--color-secondary);
		cursor: pointer;
	}
	.inline-link:hover {
		text-decoration: underline;
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
