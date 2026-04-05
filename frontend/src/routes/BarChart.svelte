<script lang="ts">
	import { Chart } from 'chart.js/auto';
	import { themeState } from '$lib/theme.svelte';
	import { Colors } from 'chart.js';

	Chart.register(Colors);

	let { labels, values, title, xLabel, yLabel }: {
		labels: string[];
		values: number[];
		title: string;
		xLabel: string;
		yLabel: string;
	} = $props();

	let canvas: HTMLCanvasElement;
	let chartInstance: Chart | null = null;

	$effect(() => {
		themeState.value;

		const style = getComputedStyle(document.documentElement);
		const chartColors = {
			bar: style.getPropertyValue('--color-primary').trim(),
			text: style.getPropertyValue('--color-base-content').trim(),
			axis: style.getPropertyValue('--color-base-content').trim(),
		};

		chartInstance?.destroy();
		Chart.defaults.color = chartColors.text;
		chartInstance = new Chart(canvas, {
			type: 'bar',
			data: {
				labels,
				datasets: [{ label: title, data: values, backgroundColor: chartColors.bar }]
			},
			options: {
				color: chartColors.text,
				maintainAspectRatio: false,
				scales: {
					x: { ticks: { color: chartColors.axis }, title: { display: true, text: xLabel } },
					y: { ticks: { color: chartColors.axis }, title: { display: true, text: yLabel } }
				},
				plugins: {
					title: { display: true, text: title, color: chartColors.text },
					legend: { display: false }
				}
			}
		});
	});
</script>

<div class="card">
	<div class="canvas-container">
		<canvas bind:this={canvas}></canvas>
	</div>
</div>

<style>
	.canvas-container {
		height: 100%;
		width: 100%;
	}
</style>
