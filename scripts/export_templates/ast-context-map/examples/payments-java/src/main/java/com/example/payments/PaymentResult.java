package com.example.payments;

import java.time.Instant;
import java.util.Objects;

/**
 * Outcome of a charge attempt. Synthetic example data only.
 */
public final class PaymentResult {
    public enum Status { APPROVED, DECLINED, ERROR }

    private final String orderId;
    private final Status status;
    private final String gatewayReference;
    private final String message;
    private final Instant processedAt;

    private PaymentResult(String orderId, Status status, String gatewayReference,
                          String message, Instant processedAt) {
        this.orderId = Objects.requireNonNull(orderId, "orderId");
        this.status = Objects.requireNonNull(status, "status");
        this.gatewayReference = gatewayReference;
        this.message = message;
        this.processedAt = Objects.requireNonNull(processedAt, "processedAt");
    }

    public static PaymentResult approved(String orderId, String gatewayReference) {
        return new PaymentResult(orderId, Status.APPROVED, gatewayReference, "approved", Instant.now());
    }

    public static PaymentResult declined(String orderId, String reason) {
        return new PaymentResult(orderId, Status.DECLINED, null, reason, Instant.now());
    }

    public static PaymentResult error(String orderId, String reason) {
        return new PaymentResult(orderId, Status.ERROR, null, reason, Instant.now());
    }

    public boolean isApproved() { return status == Status.APPROVED; }
    public String getOrderId() { return orderId; }
    public Status getStatus() { return status; }
    public String getGatewayReference() { return gatewayReference; }
    public String getMessage() { return message; }
    public Instant getProcessedAt() { return processedAt; }
}
