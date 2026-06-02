# Payment Retry Policy

The billing service retries failed card payments after one hour, one day, and
three days. Each retry records the attempt number and the gateway response.

Retries stop when the customer updates payment details or when the retry limit
is reached. After the final failure, the subscription enters grace period.
