<script lang="ts">
	import { base } from '$app/paths';

    // themeState as $state
	import { themeState } from '$lib/theme.svelte';

	function toggleTheme() {
		themeState.value = themeState.value === 'dim' ? 'emerald' : 'dim';
	}
</script>

<div class="navbar bg-(--color-base-300) shadow-sm min-h-0 h-14">
  <div class="flex-1">
    <a href="/databoard" class="btn btn-ghost text-xl">Databoard</a>
    <ul class="menu menu-horizontal px-1">
      <li><a href="/databoard/detail">Detail</a></li>
    </ul>
  </div>

  <label class="flex cursor-pointer gap-2">
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round">
      <circle cx="12" cy="12" r="5" />
      <path
        d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
    </svg>
    <input type="checkbox" value="synthwave" class="toggle theme-controller" onclick={toggleTheme} />
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
    </svg>
  </label>
</div>
