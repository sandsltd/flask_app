import stripe

# Set your Stripe API key (use your secret key here)
stripe.api_key = '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'  # Replace with your actual secret key

# The connected account ID to test
connected_account_id = 'acct_1Q5S7IB6DVlKa5p2'  # Replace with the actual connected account ID

# Amount to transfer (in smallest currency unit, e.g., pence for GBP)
amount_to_transfer = 1000  # Example: 10 GBP = 1000 pence

def test_connected_account(connected_account_id, amount):
    try:
        # Attempt to create a transfer to the connected account
        transfer = stripe.Transfer.create(
            amount=amount,
            currency="gbp",
            destination=connected_account_id,
            description="Test transfer to verify connected account",
        )

        # If the transfer is successful, print transfer details
        print(f"Transfer successful! Transfer ID: {transfer.id}")
        print(f"Amount transferred: {transfer.amount / 100} GBP")

    except stripe.error.StripeError as e:
        # Handle Stripe-specific errors
        print(f"Stripe error occurred: {e.user_message}")

    except Exception as e:
        # Handle any other general errors
        print(f"An error occurred: {str(e)}")

# Run the test
test_connected_account(connected_account_id, amount_to_transfer)
