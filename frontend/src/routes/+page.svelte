<script lang="ts">
    let { data } = $props();
</script>

<div class="m-4">
    <p>This is the site</p>
    <button class="btn btn-primary">This is a button</button>
    <button class="btn btn-secondary">This is a button</button>

    <h2 class="mt-2">Data from Flask:</h2>
    {#each data.items as item}
        <p>{item.id}: {item.name}</p>
    {/each}
</div>
