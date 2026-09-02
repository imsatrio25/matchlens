import './globals.css';

export const metadata = { title: 'The Style Galaxy', description: 'Interactive map of every playing style in the Premier League' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
