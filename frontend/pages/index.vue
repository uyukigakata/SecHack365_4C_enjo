<style>
@import url("~/assets/css/style.css");
</style>

<script setup lang="ts">
const isActive = ref(true)
const hasError = ref(false)
const classObject = reactive({
    active: true,
    'text-danger': false
})
</script>


<template>
    <div>
        <PostWritingItem />
        <PostItem />
    </div>
</template>