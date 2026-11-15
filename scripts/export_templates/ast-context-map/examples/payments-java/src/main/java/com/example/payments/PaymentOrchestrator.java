package com.example.payments;

import java.io.IOException;

/**
 * Coordinates validation, charging, and auditing of a payment. Synthetic example data only.
 */
public class PaymentOrchestrator {
    private final PaymentGatewayClient gatewayClient;
    private final AuditLogger auditLogger;

    public PaymentOrchestrator(PaymentGatewayClient gatewayClient, AuditLogger auditLogger) {
        this.gatewayClient = gatewayClient;
        this.auditLogger = auditLogger;
    }

    /**
     * Validates the request with the gateway, charges it, and records every step.
     * Never throws for gateway failures; returns an ERROR result instead.
     */
    public PaymentResult processTransaction(PaymentRequest request) {
        auditLogger.logAttempt(request);
        try {
            if (!gatewayClient.validate(request)) {
                PaymentResult declined = PaymentResult.declined(request.getOrderId(), "validation failed");
                auditLogger.logResult(request, declined);
                return declined;
            }
            String reference = gatewayClient.charge(request);
            PaymentResult approved = PaymentResult.approved(request.getOrderId(), reference);
            auditLogger.logResult(request, approved);
            return approved;
        } catch (IOException e) {
            auditLogger.logFailure(request, e);
            return PaymentResult.error(request.getOrderId(), "gateway unavailable");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            auditLogger.logFailure(request, e);
            return PaymentResult.error(request.getOrderId(), "interrupted");
        }
    }
}
