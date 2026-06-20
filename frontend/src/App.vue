<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchHello } from "@/services/api";

const message = ref("loading...");
const name = ref("world");

async function load() {
  message.value = (await fetchHello(name.value)).message;
}

onMounted(load);
</script>

<template>
  <main>
    <h1>develop</h1>
    <p>Vue 3 + Vite + TypeScript &times; FastAPI</p>
    <section>
      <label>
        name:
        <input v-model="name" @keyup.enter="load" />
      </label>
      <button @click="load">送信</button>
    </section>
    <p><strong>API:</strong> {{ message }}</p>
  </main>
</template>
