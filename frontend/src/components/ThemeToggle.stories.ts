import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ThemeToggle from "./ThemeToggle.vue";

const meta = {
  title: "TX BizFinder/ThemeToggle",
  component: ThemeToggle,
  tags: ["autodocs"],
} satisfies Meta<typeof ThemeToggle>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};