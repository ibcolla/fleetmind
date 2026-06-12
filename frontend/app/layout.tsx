import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'FleetMind — AI Chief of Staff for Solo Founders',
  description: 'Monitor signals. Reason. Remember. Act. Your AI ops agent that never sleeps.',
  openGraph: {
    title: 'FleetMind',
    description: 'AI Chief of Staff for Solo Founders',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
