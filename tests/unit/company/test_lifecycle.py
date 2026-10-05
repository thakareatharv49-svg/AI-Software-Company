from company.lifecycle import ProductLifecycle, ProductSignal, ProductState


def test_product_lifecycle() -> None:
    product = ProductLifecycle("p")
    product.deploy()
    product.monitor()
    product.ingest(ProductSignal("bug", "failure"))
    assert product.state == ProductState.IMPROVEMENT
    assert product.release() == 1
    assert product.state == ProductState.RELEASED
