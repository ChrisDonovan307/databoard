<script lang="ts">
	import { Chart } from 'chart.js/auto';
	import { themeState } from '$lib/theme.svelte';
	import { Colors } from 'chart.js';
</script>

<main class="m-4">
	<h2>Detail</h2>
	<p>To do:</p>
	<ul>
		<li>Breakdowns by subject</li>
		<li>Trends over time</li>
	</ul>
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