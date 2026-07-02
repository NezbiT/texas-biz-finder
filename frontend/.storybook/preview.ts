import type { Preview } from "@storybook/vue3-vite";
import "../src/style.css";

const preview: Preview = {
  decorators: [
    () => ({
      template: '<div class="dark min-h-[12rem] bg-brand-navy p-6 text-slate-100"><story /></div>',
    }),
  ],
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      test: "todo",
    },
    layout: "fullscreen",
  },
};

export default preview;