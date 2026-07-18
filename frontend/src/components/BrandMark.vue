<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import AppLogo from "./AppLogo.vue";

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    /** In-app route (`/…`), hash (`#…`), or omit for static. */
    to?: string;
    size?: "sm" | "md" | "lg";
    titleTag?: "h1" | "p";
  }>(),
  { size: "md", titleTag: "p" },
);

const wrapper = computed(() => {
  if (!props.to) return { tag: "div" as const, bind: {} };
  if (props.to.startsWith("/") && !props.to.startsWith("//")) {
    return { tag: RouterLink, bind: { to: props.to } };
  }
  return { tag: "a" as const, bind: { href: props.to } };
});

const interactiveClass =
  "rounded-lg outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-teal";
</script>

<template>
  <component
    :is="wrapper.tag"
    v-bind="wrapper.bind"
    class="flex min-w-0 items-center gap-3"
    :class="to ? interactiveClass : ''"
  >
    <AppLogo :size="size" class="shrink-0" />
    <div class="min-w-0">
      <p
        v-if="subtitle"
        class="truncate text-[0.6rem] font-semibold uppercase tracking-[0.2em] accent-text sm:text-[0.65rem]"
      >
        {{ subtitle }}
      </p>
      <component
        :is="titleTag"
        class="truncate font-display font-bold tracking-tight text-brand-navy dark:text-white"
        :class="
          titleTag === 'h1'
            ? size === 'sm'
              ? 'text-xl'
              : 'text-2xl'
            : size === 'sm'
              ? 'text-lg'
              : 'text-lg sm:text-xl'
        "
      >
        {{ title }}
      </component>
    </div>
  </component>
</template>
