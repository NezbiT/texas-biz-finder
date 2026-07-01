<template>
  <div class="page-particles" aria-hidden="true">
    <span
      v-for="n in 10"
      :key="n"
      class="particle"
      :style="{ '--i': n, '--x': `${(n * 17) % 100}%`, '--y': `${(n * 23) % 100}%` }"
    />
  </div>
</template>