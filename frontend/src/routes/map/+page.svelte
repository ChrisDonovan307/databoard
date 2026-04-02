<script lang="ts">
	import { MapLibre, Marker, Popup } from 'svelte-maplibre';
	let { data } = $props();
    let hoveredName: string | null = $state(null);
    $effect(() => {
        console.log(data.installations)
    })
</script>

<div class="container grid grid-cols-12 grid-rows-3 gap-4 min-h-0 max-w-full mx-4 my-4">
    <div class="col-span-3 row-span-2">
        <div class="card">
            <div class="card-body">
                <h2 class="card-title">Card Title</h2>
                <p>A card component has a figure, a body part, and inside body there are title and actions parts</p>
                <div class="card-actions justify-end">
                    <a class="styled-link" href="https://dataverse.harvard.edu/" target="_blank">Harvard Dataverse</a>
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
            style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" >
            {#each data.installations.features as { geometry, properties }}
                <Marker lngLat={geometry.coordinates as [number, number]}>
                    <button
                        class="marker-btn"
                        onmouseenter={() => hoveredName = properties.name}
                        onmouseleave={() => hoveredName = null}
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
        <div class="card"></div>
    </div>

    <div class="col-span-4">
        <div class="card"></div>
    </div>

    <div class="col-span-4">
        <div class="card"></div>
    </div>
</div>

<!-- <div>
	{#each data.installations.features as { geometry, properties }}
		<p><b>{properties.name}</b>:</p>
		<p class="ml-2">lat {geometry.coordinates[1]}, lon {geometry.coordinates[0]}</p>
		<p class="ml-2">Country: {properties.country}</p>
		<p class="ml-2">url: {properties.url}</p>
	{/each}
</div> -->

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
        color: #1f3c22;
        opacity: 0.75;
    }
    .container {
        height: calc(100vh - (var(--spacing) * 22));
        width: calc(100vw - (var(--spacing) * 8));
    }
	:global(.card) {
        border-radius: 6px;
        border: var(--border) solid var(--color-base-200);
        width: 100%;
        height: 100%;
        background-color: var(--color-olive-100);
        color: var(--color-taupe-800);
	}
    .styled-link {
        background-color: var(--color-gray-300);
        border-radius: 5px;
        border: 1px solid black;
        padding: 5px 10px;
        color: var(--color-taupe-800);
    }
</style>
