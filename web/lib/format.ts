export const dateLabel = (value: string | null) => value ? new Date(value.length === 10 ? `${value}T12:00:00` : value).toLocaleDateString("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric"
}) : "";

export const inr = (value: number | null | undefined) => value == null ? "Not listed — ask the studio" : new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0
}).format(value);

export const safeLink = (value: string | null | undefined) => {
  try {
    const u = new URL(value ?? "");
    return ["https:", "http:"].includes(u.protocol) ? u.href : undefined;
  } catch {
    return undefined;
  }
};
