import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'FleetMind | AI Chief of Staff for Solo Founders',
  description:
    'Autonomous AI Chief of Staff for solo founders. Monitor competitors, synthesize market signals, automate GitHub/Slack actions, and maintain long-term company memory.',
  icons: {
    icon: [
      {
        url: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="%233B82F6"/><path d="M30 30h40M30 30v40M30 50h30" stroke="white" stroke-width="10" stroke-linecap="round"/><circle cx="60" cy="60" r="8" fill="%2360A5FA"/></svg>',
        type: 'image/svg+xml',
      },
    ],
  },
  openGraph: {
    title: 'FleetMind | AI Chief of Staff for Solo Founders',
    description:
      'Autonomous AI Chief of Staff for solo founders. Monitor competitors, synthesize market signals, automate GitHub/Slack actions, and maintain long-term company memory.',
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
