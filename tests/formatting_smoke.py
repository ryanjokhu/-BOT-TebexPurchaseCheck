from tebextransactioncheck import build_payment_line, product_names_from_payment


def test_product_name_is_primary():
    payment = {
        "txn_id": "tbx-test-123",
        "time": 1760000000,
        "price": "10.00",
        "currency": "USD",
        "status": 1,
        "packages": [{"id": 12345, "name": "VIP Rank"}],
    }

    assert product_names_from_payment(payment) == ["VIP Rank"]
    line = build_payment_line(1, payment)
    assert "**VIP Rank**" in line
    assert "Txn: `tbx-test-123`" in line
