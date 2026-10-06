import Link from "next/link";

export default function Home() {
  return (
    <main>
      <h1>ClientOps Agent</h1>
      <p>Evidence-backed lead decisions with human approval.</p>
      <Link href="/approvals">Open approvals queue</Link>
    </main>
  );
}
