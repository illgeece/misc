import React from 'react';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DM Helper - AI Dungeon Master Companion',
  description: 'An intelligent assistant for Dungeon Masters with AI-powered chat, character creation, and knowledge management.',
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#dc2626',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full bg-gray-50`}>
        <div id="root" className="min-h-full">
          {children}
        </div>
      </body>
    </html>
  );
} 