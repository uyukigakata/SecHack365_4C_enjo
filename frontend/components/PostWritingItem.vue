<template>
    <div class="max-w-xl mx-auto p-4 bg-white rounded-lg shadow-md">
        <textarea v-model="postContent"
            class="w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" rows="4"
            placeholder="What's happening?"></textarea>
        <div class="flex justify-between items-center mt-2">
            <span class="text-sm text-gray-500">{{ remainingCharacters }} characters left</span>
            <button @click="submitPost" :disabled="isDisabled"
                class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50">
                Tweet
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">

const postContent = ref('');
const maxCharacters = 280;

const remainingCharacters = computed(() => {
    return maxCharacters - postContent.value.length;
});

const isDisabled = computed(() => {
    return postContent.value.length === 0 || postContent.value.length > maxCharacters;
});

const submitPost = () => {
    // Handle post submission logic here
    console.log('Post submitted:', postContent.value);
    postContent.value = '';
};
</script>

<style scoped>
/* Add any additional styles here */
</style>