package com.example.payments;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Thin HTTP client for an external payment gateway. Synthetic example data only;
 * the base URL uses a reserved documentation domain.
 */
public class PaymentGatewayClient {
    private static final String BASE_URL = "https://gateway.example.com/v1";
    private final HttpClient http;

    public PaymentGatewayClient() {
        this(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build());
    }

    PaymentGatewayClient(HttpClient http) {
        this.http = http;
    }

    /** Returns true when the gateway accepts the payment method token for this amount. */
    public boolean validate(PaymentRequest request) throws IOException, InterruptedException {
        String body = "{\"token\":\"" + request.getPaymentMethodToken() + "\","
                + "\"amount\":\"" + request.getAmount() + "\","
                + "\"currency\":\"" + request.getCurrency() + "\"}";
        HttpResponse<String> response = send("/validate", body);
        return response.statusCode() == 200 && response.body().contains("\"valid\":true");
    }

    /** Charges the payment method and returns the gateway reference id. */
    public String charge(PaymentRequest request) throws IOException, InterruptedException {
        String body = "{\"token\":\"" + request.getPaymentMethodToken() + "\","
                + "\"order\":\"" + request.getOrderId() + "\","
                + "\"amount\":\"" + request.getAmount() + "\","
                + "\"currency\":\"" + request.getCurrency() + "\"}";
        HttpResponse<String> response = send("/charge", body);
        if (response.statusCode() != 200) {
            throw new IOException("gateway returned " + response.statusCode());
        }
        return extract(response.body(), "reference");
    }

    private HttpResponse<String> send(String path, String json) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(URI.create(BASE_URL + path))
                .timeout(Duration.ofSeconds(10))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();
        return http.send(request, HttpResponse.BodyHandlers.ofString());
    }

    private static String extract(String json, String field) {
        String marker = "\"" + field + "\":\"";
        int start = json.indexOf(marker);
        if (start < 0) {
            throw new IllegalStateException("missing field " + field);
        }
        start += marker.length();
        int end = json.indexOf('"', start);
        return json.substring(start, end);
    }
}
