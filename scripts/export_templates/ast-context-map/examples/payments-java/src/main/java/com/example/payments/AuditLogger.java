package com.example.payments;

import java.time.Instant;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Writes structured audit lines for payment attempts. Synthetic example data only.
 */
public class AuditLogger {
    private static final Logger LOG = Logger.getLogger(AuditLogger.class.getName());

    public void logAttempt(PaymentRequest request) {
        LOG.log(Level.INFO, "{0} attempt order={1} customer={2} amount={3} {4}",
                new Object[] {Instant.now(), request.getOrderId(), request.getCustomerId(),
                        request.getAmount(), request.getCurrency()});
    }

    public void logResult(PaymentRequest request, PaymentResult result) {
        Level level = result.isApproved() ? Level.INFO : Level.WARNING;
        LOG.log(level, "{0} result order={1} status={2} ref={3} message={4}",
                new Object[] {Instant.now(), request.getOrderId(), result.getStatus(),
                        result.getGatewayReference(), result.getMessage()});
    }

    public void logFailure(PaymentRequest request, Exception e) {
        LOG.log(Level.SEVERE, "payment failure order=" + request.getOrderId(), e);
    }
}
