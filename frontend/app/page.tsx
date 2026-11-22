import { redirect } from "next/navigation";

// This page only redirects, so it has nothing to check for instant navigation.
export const instant = false;

export default function Home() {
  redirect("/dashboard");
}