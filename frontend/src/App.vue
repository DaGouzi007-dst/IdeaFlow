<template>
  <RouterView />
</template>

<style>
* { box-sizing: border-box; }

body {
  margin: 0;
  background: #f6f7f9;
  color: #1f2328;
  font: 15px/1.6 "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
}

.page {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 20px 64px;
}

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
}

input, select, button, textarea {
  font: inherit;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
}

button { cursor: pointer; background: #1f6feb; border-color: #1f6feb; color: #fff; }
button:disabled { opacity: 0.6; cursor: default; }
button.plain { background: #fff; color: #1f2328; border-color: #d1d5db; }
button.danger { background: #fff; color: #b91c1c; border-color: #fca5a5; }

.error { background: #fee2e2; color: #991b1b; padding: 10px 12px; border-radius: 8px; }
.hint { color: #6b7280; }

.tags { margin: 8px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }
.tags span { background: #eef2ff; color: #3730a3; border-radius: 999px; padding: 1px 10px; font-size: 13px; }

.star { background: none; border: none; color: #9ca3af; font-size: 20px; line-height: 1; padding: 0 4px; }
.star.on { color: #f59e0b; }
</style>
