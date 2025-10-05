// This nested layout simply passes its children through to the root layout.
// It does not need to add any extra HTML tags.

export default function MainLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>;
}
