import type { Meta, StoryObj } from "@storybook/vue3-vite";
import AppLogo from "./AppLogo.vue";

const meta = {
  title: "TX BizFinder/AppLogo",
  component: AppLogo,
  tags: ["autodocs"],
  argTypes: {
    size: { control: "select", options: ["sm", "md", "lg"] },
  },
} satisfies Meta<typeof AppLogo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Small: Story = {
  args: { size: "sm" },
};

export const Medium: Story = {
  args: { size: "md" },
};

export const Large: Story = {
  args: { size: "lg" },
};