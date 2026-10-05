from company.distributed import DistributedExecutor,Worker,WorkResult
def test_distributed_round_robin_and_retry():
    ex=DistributedExecutor((Worker("w1"),Worker("w2")))
    assert ex.execute(ex.submit("a"),lambda x:x.upper()).value=="A"
    assert ex.execute(ex.submit("b"),lambda x:x.upper()).worker_id=="w2"
    attempts={"n":0}
    def flaky(x):
        attempts["n"]+=1
        if attempts["n"]==1: raise RuntimeError("temporary")
        return x
    assert ex.execute_with_retry(ex.submit("ok"),flaky).success
def test_no_ready_worker():
    ex=DistributedExecutor((Worker("w",status="offline"),))
    try: ex.execute(ex.submit("x"),lambda x:x)
    except RuntimeError: pass
    else: assert False
