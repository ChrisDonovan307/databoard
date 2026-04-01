<script lang="ts">
	import { MapLibre, Marker, Popup } from 'svelte-maplibre';
	let { data } = $props();
    let hoveredName: string | null = $state(null);
    $effect(() => {
        console.log(data.installations)
    })
</script>

<h2>Map</h2>

<div class="flex justify-center">
    <MapLibre
        center={[-43, 32]}
        zoom={2}
        class="map"
        standardControls
        style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    >
	    {#each data.installations.features as { geometry, properties }}
            <Marker lngLat={geometry.coordinates as [number, number]}>
                <button
                    class="marker-btn"
                    onmouseenter={() => hoveredName = properties.name}
                    onmouseleave={() => hoveredName = null}
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

<div>
	{#each data.installations.features as { geometry, properties }}
		<p><b>{properties.name}</b>:</p>
		<p class="ml-2">lat {geometry.coordinates[1]}, lon {geometry.coordinates[0]}</p>
		<p class="ml-2">Country: {properties.country}</p>
		<p class="ml-2">url: {properties.url}</p>
	{/each}
</div>

<style>
	:global(.map) {
		height: 500px;
		width: 75%;
	}
	.marker-btn {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 1.5rem;
		padding: 0;
	}
    i {
        color: #000;
        opacity: 0.75;
    }
</style>
