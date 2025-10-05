// This nested layout simply passes its children through to the root layout,
// ensuring that the main Header and Footer are applied to all legal pages.
export default function LegalLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>;
}
