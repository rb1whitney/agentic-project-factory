package com.example.payments;

import java.math.BigDecimal;
import java.util.Currency;
import java.util.Objects;

/**
 * Immutable request to charge a payment method. Synthetic example data only.
 */
public final class PaymentRequest {
    private final String orderId;
    private final String customerId;
    private final BigDecimal amount;
    private final Currency currency;
    private final String paymentMethodToken;

    public PaymentRequest(String orderId, String customerId, BigDecimal amount,
                          Currency currency, String paymentMethodToken) {
        this.orderId = Objects.requireNonNull(orderId, "orderId");
        this.customerId = Objects.requireNonNull(customerId, "customerId");
        this.amount = Objects.requireNonNull(amount, "amount");
        this.currency = Objects.requireNonNull(currency, "currency");
        this.paymentMethodToken = Objects.requireNonNull(paymentMethodToken, "paymentMethodToken");
        if (amount.signum() <= 0) {
            throw new IllegalArgumentException("amount must be positive");
        }
    }

    public String getOrderId() { return orderId; }
    public String getCustomerId() { return customerId; }
    public BigDecimal getAmount() { return amount; }
    public Currency getCurrency() { return currency; }
    public String getPaymentMethodToken() { return paymentMethodToken; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof PaymentRequest)) return false;
        PaymentRequest that = (PaymentRequest) o;
        return orderId.equals(that.orderId)
                && customerId.equals(that.customerId)
                && amount.compareTo(that.amount) == 0
                && currency.equals(that.currency)
                && paymentMethodToken.equals(that.paymentMethodToken);
    }

    @Override
    public int hashCode() {
        return Objects.hash(orderId, customerId, amount.stripTrailingZeros(), currency, paymentMethodToken);
    }

    @Override
    public String toString() {
        return "PaymentRequest{orderId=" + orderId + ", customerId=" + customerId
                + ", amount=" + amount + ", currency=" + currency + "}";
    }
}
