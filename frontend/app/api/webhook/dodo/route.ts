import { Webhooks } from "@dodopayments/nextjs";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function notifyBackend(eventType: string, clerkId: string, productId?: string) {
    try {
        const response = await fetch(`${API_BASE_URL}/webhook/payment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                event_type: eventType,
                clerk_id: clerkId,
                product_id: productId
            })
        });
        const data = await response.json();
        console.log("Backend webhook response:", data);
        return data;
    } catch (error) {
        console.error("Failed to notify backend:", error);
    }
}

export const POST = Webhooks({
    webhookKey: process.env.DODO_PAYMENTS_WEBHOOK_KEY!,
    onPayload: async (payload) => {
        console.log("Dodo Payments webhook received:", payload.type);
    },
    onPaymentSucceeded: async (payload) => {
        console.log("Payment succeeded:", payload.data.payment_id);
        // Extract clerk_id from metadata (set during checkout)
        const clerkId = (payload.data as any).metadata?.clerk_id;
        const productId = (payload.data as any).product_id;
        if (clerkId) {
            await notifyBackend("payment_succeeded", clerkId, productId);
        }
    },
    onSubscriptionActive: async (payload) => {
        console.log("Subscription activated:", payload.data.subscription_id);
        const clerkId = (payload.data as any).metadata?.clerk_id;
        if (clerkId) {
            await notifyBackend("subscription_active", clerkId);
        }
    },
    onSubscriptionCancelled: async (payload) => {
        console.log("Subscription cancelled:", payload.data.subscription_id);
        const clerkId = (payload.data as any).metadata?.clerk_id;
        if (clerkId) {
            await notifyBackend("subscription_cancelled", clerkId);
        }
    },
});
