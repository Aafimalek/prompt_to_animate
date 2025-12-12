import { Webhooks } from "@dodopayments/nextjs";

export const POST = Webhooks({
    webhookKey: process.env.DODO_PAYMENTS_WEBHOOK_KEY!,
    onPayload: async (payload) => {
        console.log("Dodo Payments webhook received:", payload.type);
    },
    onPaymentSucceeded: async (payload) => {
        console.log("Payment succeeded:", payload.data.payment_id);
        // TODO: Update user credits/tier in database
    },
    onSubscriptionActive: async (payload) => {
        console.log("Subscription activated:", payload.data.subscription_id);
        // TODO: Update user to Pro tier in database
    },
    onSubscriptionCancelled: async (payload) => {
        console.log("Subscription cancelled:", payload.data.subscription_id);
        // TODO: Downgrade user to Free tier in database
    },
});
