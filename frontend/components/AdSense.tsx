'use client';

import { useEffect } from 'react';

interface AdSenseProps {
    userTier: string;
    basicCredits?: number;
}

/**
 * AdSense component that only loads Google Ads for free-tier users.
 * Users with basic credits or Pro subscription won't see ads.
 */
export function AdSense({ userTier, basicCredits = 0 }: AdSenseProps) {
    // Don't show ads to paying users (Pro or users with basic credits)
    const shouldShowAds = userTier === 'free' && basicCredits === 0;

    useEffect(() => {
        if (!shouldShowAds) return;

        // Check if script is already loaded
        if (document.querySelector('script[src*="pagead2.googlesyndication.com"]')) {
            return;
        }

        // Dynamically load AdSense script only for free users
        const script = document.createElement('script');
        script.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3724900084324676';
        script.async = true;
        script.crossOrigin = 'anonymous';
        document.head.appendChild(script);

        return () => {
            // Cleanup on unmount (optional, but good practice)
            // Note: We don't remove the script as it may cause issues
        };
    }, [shouldShowAds]);

    // Don't render anything for paying users
    if (!shouldShowAds) {
        return null;
    }

    // Return an ad container for auto ads - Google will automatically place ads
    return (
        <>
            {/* Optional: Add specific ad slots here if you want manual ad placement */}
            {/* For now, using Auto ads which Google places automatically */}
        </>
    );
}

/**
 * Banner Ad component for specific ad placement (optional)
 * Use this if you want to place ads in specific locations
 */
export function AdBanner({ userTier, basicCredits = 0, slot }: AdSenseProps & { slot?: string }) {
    const shouldShowAds = userTier === 'free' && basicCredits === 0;

    useEffect(() => {
        if (!shouldShowAds) return;

        try {
            // Push ad to adsbygoogle queue
            ((window as unknown as { adsbygoogle: unknown[] }).adsbygoogle = (window as unknown as { adsbygoogle: unknown[] }).adsbygoogle || []).push({});
        } catch (error) {
            console.error('AdSense error:', error);
        }
    }, [shouldShowAds]);

    if (!shouldShowAds) {
        return null;
    }

    return (
        <div className="ad-container my-4 flex justify-center">
            <ins
                className="adsbygoogle"
                style={{ display: 'block' }}
                data-ad-client="ca-pub-3724900084324676"
                data-ad-slot={slot || 'auto'}
                data-ad-format="auto"
                data-full-width-responsive="true"
            />
        </div>
    );
}
