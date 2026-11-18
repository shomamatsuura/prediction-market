import { SignIn } from "@clerk/nextjs";
import { notFound } from "next/navigation";

import { clerkEnabled } from "@/lib/config";

export default function SignInPage() {
  if (!clerkEnabled) notFound();
  return (
    <div className="grid place-items-center py-10">
      <SignIn />
    </div>
  );
}
