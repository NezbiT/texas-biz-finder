import type { Meta, StoryObj } from "@storybook/vue3-vite";
import LocaleToggle from "./LocaleToggle.vue";

const meta = {
  title: "TX BizFinder/LocaleToggle",
  component: LocaleToggle,
  tags: ["autodocs"],
} satisfies Meta<typeof LocaleToggle>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};