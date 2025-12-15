import type { Metadata } from "next";
import { Geist, Geist_Mono, Nabla } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });
const nabla = Nabla({
  subsets: ["latin"],
  variable: "--font-nabla",
  weight: "400",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Manimancer",
  description: "Generate 2D animations from text prompts using AI",
  metadataBase: new URL("https://www.manimancer.fun"),
  openGraph: {
    title: "Manimancer",
    description: "Generate 2D animations from text prompts using AI",
    url: "https://www.manimancer.fun",
    siteName: "Manimancer",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Manimancer - AI-powered 2D animation generator",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Manimancer",
    description: "Generate 2D animations from text prompts using AI",
    images: ["/og-image.png"],
  },
};

import { ThemeProvider } from "@/components/ThemeProvider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className={`${geistSans.variable} ${geistMono.variable} ${nabla.variable} font-sans antialiased bg-background text-foreground`}>
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem
            disableTransitionOnChange
          >
            {children}
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
