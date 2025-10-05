// This nested layout simply passes its children through to the root layout,
// ensuring that the main Header and Footer are applied.
export default function ProductsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>;
}
