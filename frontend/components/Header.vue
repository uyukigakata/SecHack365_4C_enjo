<template>
    <header class="bg-white shadow-md p-4 flex items-center justify-between mb-1">
        <div class="flex items-center space-x-4">
            <h1 class="text-2xl font-bold">えんじょっぷ</h1>
        </div>
        <div class="flex items-center space-x-4">
            <button class="text-gray-600">ホーム</button>
            <button class="text-gray-600">ユーザーページ</button>
            <img src="https://www.gravatar.com/avatar/?d=mp" alt="User Avatar" class="h-8 w-8 rounded-full" />
        </div>
    </header>
</template>

<script>
export default {
    name: 'Header',
};
</script>

<style scoped></style>