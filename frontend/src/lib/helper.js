import { DROUGHT_CATEGORY } from "@/static/config";

export const findCategory = (category) =>
  DROUGHT_CATEGORY.find((c) => c.value === category);
