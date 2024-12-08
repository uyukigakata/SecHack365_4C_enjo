<script setup lang="ts">
type Post = {
    uri: string;
    author: {
        handle: string;
        displayName: string;
        avatar: string;
    };
    record: {
        $type: string;
        createdAt: string;
        text: string;
    };
    replyCount: number;
    repostCount: number;
    likeCount: number;
    quoteCount: number;
    indexedAt: string;
};

type Feed = [
    {
        post: Post;
    }
];

type Response = {
    feed: Feed,
    cursor: string
};

// import timeline.json


const res: Response = await $fetch('/timeline.json', {});
const feeds = ref(res.feed.map((f) => f.post));

</script>

<template>
    <div class="max-w-xl mx-auto mt-4">
        <div v-for="post in feeds" :key="post.uri" class="bg-white p-4 rounded-lg shadow mb-4">
            <div class="flex items-center mb-4">
                <img :src="post.author.avatar" alt="Avatar" class="w-12 h-12 rounded-full mr-4">
                <div>
                    <h2 class="font-bold">{{ post.author.displayName }}</h2>
                    <p class="text-gray-600">@{{ post.author.handle }}</p>
                </div>
            </div>
            <p class="mb-4">{{ post.record.text }}</p>
            <div class="flex justify-between text-gray-600">
                <span>{{ post.indexedAt }}</span>
                <div class="flex space-x-4">
                    <button class="hover:text-blue-500">Like</button>
                    <button class="hover:text-blue-500">Comment</button>
                    <button class="hover:text-blue-500">Share</button>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* Add any additional styling here */
</style>