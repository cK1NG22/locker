"use client";

import { useParams } from "next/navigation";
import InvitePage from "@/components/join/InvitePage";

export default function JoinPage() {
  const params = useParams<{ slug: string }>();
  return <InvitePage slug={params.slug} />;
}
