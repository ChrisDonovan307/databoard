<script lang="ts">
	import { MapLibre, Marker, Popup } from 'svelte-maplibre';

    // selectedName as bindable, both parent and child can write
	let { data, selectedName = $bindable(null) } = $props();
	let hoveredName: string | null = $state(null);
</script>

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
                <div class="popup">
                    <h3>{properties.name}</h3>
                    <p><span>Established:</span><span>{properties.launch_year}</span></p>
                    <p><span>DOI Authority:</span><span>{properties.doi_authority}</span></p>
                    <p><span>Metrics API:</span><span>{properties.metrics === true ? 'Yes' : 'No'}</span></p>
                </div>
            </Popup>
        </Marker>
    {/each}
</MapLibre>

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
	.popup {
		max-width: 300px;
		h3 {
			font-weight: bold;
			font-size: 1rem;
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
</style>