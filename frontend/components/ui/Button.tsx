import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger";

const base =
  "inline-flex items-center justify-center rounded px-4 py-2 text-sm font-medium " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const variants: Record<Variant, string> = {
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  secondary: "border border-gray-300 bg-white text-gray-800 hover:bg-gray-100",
  danger: "border border-red-300 bg-white text-red-600 hover:bg-red-50",
};

// Use on <Link> when a link should look like a button.
export const buttonClass = (variant: Variant = "primary") => `${base} ${variants[variant]}`;

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type={type} {...props} className={`${buttonClass(variant)} ${className}`} />;
}
