from company.lifecycle import ProductLifecycle,ProductSignal,ProductState
def test_product_lifecycle():
    p=ProductLifecycle("p"); p.deploy(); p.monitor(); p.ingest(ProductSignal("bug","failure")); assert p.state==ProductState.IMPROVEMENT; assert p.release()==1; assert p.state==ProductState.RELEASED
