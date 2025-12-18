import type { Metadata } from "next";
import { Geist, Geist_Mono, Nabla } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });
const nabla = Nabla({
  subsets: ["latin"],
  variable: "--font-nabla",
  weight: "400",
  display: "swap",
});

// Comprehensive SEO metadata
export const metadata: Metadata = {
  // Basic metadata
  title: {
    default: "Manimancer - AI Animation Generator | Create Educational Videos & Visualizations",
    template: "%s | Manimancer"
  },
  description: "Create stunning educational animations and visualizations with AI. Generate 2D/3D math animations, science explainers, algorithm visualizations, and teaching content in seconds. Powered by Manim - the same engine used by 3Blue1Brown.",

  // Keywords for SEO - targeting animation and educational content searches
  keywords: [
    // Primary keywords
    "AI animation generator",
    "educational animation",
    "math visualization",
    "educational video maker",
    "animated explainer",

    // Educational content keywords
    "educational content creator",
    "teaching animations",
    "learning visualization",
    "educational video generator",
    "e-learning animation",
    "STEM visualization",
    "science animation",
    "physics animation",
    "chemistry visualization",

    // Math-specific keywords
    "math animation",
    "mathematical visualization",
    "3Blue1Brown style",
    "calculus animation",
    "geometry visualization",
    "algebra animation",
    "graph visualization",

    // Algorithm and CS keywords
    "algorithm visualization",
    "data structure animation",
    "sorting algorithm animation",
    "programming visualization",
    "code animation",

    // Technology keywords
    "Manim",
    "AI video generation",
    "text to animation",
    "prompt to video",
    "automated animation",

    // General animation keywords
    "2D animation",
    "motion graphics",
    "explainer video",
    "animated tutorial",
    "video content creator"
  ],

  // Authors and creator
  authors: [{ name: "Manimancer Team", url: "https://www.manimancer.fun" }],
  creator: "Manimancer",
  publisher: "Manimancer",

  // Robots directives
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },

  // Canonical URL
  metadataBase: new URL("https://www.manimancer.fun"),
  alternates: {
    canonical: "/",
  },

  // Open Graph metadata - enhanced
  openGraph: {
    title: "Manimancer - AI Animation Generator for Educational Content",
    description: "Create stunning educational animations and visualizations with AI. Generate math animations, science explainers, algorithm visualizations, and teaching content like 3Blue1Brown in seconds.",
    url: "https://www.manimancer.fun",
    siteName: "Manimancer",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Manimancer - AI-powered animation generator for educational content",
        type: "image/png",
      },
    ],
    locale: "en_US",
    type: "website",
  },

  // Twitter Card metadata - enhanced
  twitter: {
    card: "summary_large_image",
    title: "Manimancer - AI Animation Generator for Educational Content",
    description: "Create stunning educational animations like 3Blue1Brown. Generate math visualizations, science explainers & algorithm animations with AI.",
    images: ["/og-image.png"],
    creator: "@aafimalek2032",
    site: "@manimancer",
  },

  // Additional metadata
  category: "Technology",
  classification: "Educational Technology",

  // Verification (add your actual verification codes here)
  verification: {
    // google: "your-google-verification-code",
    // yandex: "your-yandex-verification-code",
    // bing: "your-bing-verification-code",
  },

  // App-specific metadata
  applicationName: "Manimancer",
  referrer: "origin-when-cross-origin",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },

  // Icons
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/icon.png", type: "image/png" },
    ],
    apple: [
      { url: "/icon.png" },
    ],
  },
};

// JSON-LD Structured Data for rich snippets
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    // WebSite schema
    {
      "@type": "WebSite",
      "@id": "https://www.manimancer.fun/#website",
      "url": "https://www.manimancer.fun",
      "name": "Manimancer",
      "description": "AI-powered animation generator for educational content",
      "publisher": {
        "@id": "https://www.manimancer.fun/#organization"
      },
      "potentialAction": {
        "@type": "SearchAction",
        "target": {
          "@type": "EntryPoint",
          "urlTemplate": "https://www.manimancer.fun/?q={search_term_string}"
        },
        "query-input": "required name=search_term_string"
      }
    },
    // Organization schema
    {
      "@type": "Organization",
      "@id": "https://www.manimancer.fun/#organization",
      "name": "Manimancer",
      "url": "https://www.manimancer.fun",
      "logo": {
        "@type": "ImageObject",
        "url": "https://www.manimancer.fun/icon.png",
        "width": 512,
        "height": 512
      },
      "sameAs": [
        "https://twitter.com/aafimalek2032",
        "https://github.com/Aafimalek"
      ]
    },
    // SoftwareApplication schema
    {
      "@type": "SoftwareApplication",
      "name": "Manimancer",
      "applicationCategory": "EducationalApplication",
      "operatingSystem": "Web",
      "description": "AI-powered animation generator that creates educational visualizations, math animations, and explainer videos from text prompts.",
      "url": "https://www.manimancer.fun",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD",
        "description": "Free tier with 5 videos per month"
      },
      "featureList": [
        "AI-powered animation generation",
        "Math and science visualizations",
        "Algorithm visualizations",
        "Educational explainer videos",
        "3Blue1Brown style animations",
        "Up to 4K resolution output",
        "Text-to-animation conversion"
      ],
      "screenshot": "https://www.manimancer.fun/og-image.png"
    },
    // WebPage schema
    {
      "@type": "WebPage",
      "@id": "https://www.manimancer.fun/#webpage",
      "url": "https://www.manimancer.fun",
      "name": "Manimancer - AI Animation Generator for Educational Content",
      "description": "Create stunning educational animations and visualizations with AI. Generate math animations, science explainers, and algorithm visualizations in seconds.",
      "isPartOf": {
        "@id": "https://www.manimancer.fun/#website"
      },
      "about": {
        "@id": "https://www.manimancer.fun/#organization"
      },
      "primaryImageOfPage": {
        "@type": "ImageObject",
        "url": "https://www.manimancer.fun/og-image.png"
      }
    },
    // FAQPage schema for common questions
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is Manimancer?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Manimancer is an AI-powered tool that generates educational animations and visualizations from text prompts. It uses the same Manim engine that powers 3Blue1Brown's famous math videos."
          }
        },
        {
          "@type": "Question",
          "name": "Can I create math animations like 3Blue1Brown?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes! Manimancer uses the Manim library, the same tool used by 3Blue1Brown. Simply describe what you want to visualize, and our AI generates the animation code and renders it for you."
          }
        },
        {
          "@type": "Question",
          "name": "What types of educational content can I create?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "You can create math visualizations, algorithm animations, physics simulations, chemistry diagrams, data structure explanations, and any other educational content that benefits from visual representation."
          }
        },
        {
          "@type": "Question",
          "name": "Is Manimancer free to use?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes! Manimancer offers a free tier with 5 videos per month at 720p resolution. Premium plans are available for higher quality outputs and more videos."
          }
        }
      ]
    }
  ]
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
        <head>
          {/* Google AdSense verification */}
          <meta name="google-adsense-account" content="ca-pub-3724900084324676" />

          {/* JSON-LD Structured Data */}
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
          />
        </head>
        <body className={`${geistSans.variable} ${geistMono.variable} ${nabla.variable} font-sans antialiased bg-background text-foreground`}>
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem
            disableTransitionOnChange
          >
            {children}
            <Analytics />
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
