"""
性能基准测试：同步阻塞 vs 非阻塞 效率对比
"""
import threading
import time
from opentdx.client.standardClient import StandardClient
from opentdx.const import MARKET, PERIOD


def bench_single_request(client, label, rounds=10):
    """单线程顺序请求延迟"""
    times_ms = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        client.get_count(MARKET.SZ)
        elapsed = (time.perf_counter() - t0) * 1000
        times_ms.append(elapsed)

    avg = sum(times_ms) / len(times_ms)
    print(f"  [{label}] 单线程顺序请求 {rounds} 次: "
          f"avg={avg:.1f}ms, min={min(times_ms):.1f}ms, max={max(times_ms):.1f}ms")
    return avg


def bench_concurrent(client, label, n_threads=10, req_per_thread=5):
    """多线程并发请求吞吐量"""
    errors = []
    latencies_ms = []

    def worker(tid):
        for _ in range(req_per_thread):
            t0 = time.perf_counter()
            try:
                client.get_count(MARKET.SZ)
                elapsed = (time.perf_counter() - t0) * 1000
                latencies_ms.append(elapsed)
            except Exception as e:
                errors.append((tid, str(e)))

    t0 = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time_ms = (time.perf_counter() - t0) * 1000

    total_requests = n_threads * req_per_thread
    rps = total_requests / (total_time_ms / 1000)

    print(f"  [{label}] {n_threads}线程 x {req_per_thread}请求 = {total_requests}次: "
          f"总耗时={total_time_ms:.0f}ms, RPS={rps:.1f}, "
          f"avg延迟={sum(latencies_ms)/len(latencies_ms):.1f}ms, "
          f"max延迟={max(latencies_ms):.1f}ms")
    if errors:
        print(f"    errors: {errors}")
    return rps


def main():
    print("=" * 65)
    print("  Socket 同步 vs 非阻塞 性能对比")
    print("=" * 65)

    # 同步客户端
    print("\n--- 同步阻塞模式 (nonblocking=False) ---")
    sync = StandardClient(multithread=True, heartbeat=False, nonblocking=False)
    sync.connect().login()

    bench_single_request(sync, "sync")

    # 非阻塞客户端
    print("\n--- 非阻塞模式 (nonblocking=True) ---")
    async_client = StandardClient(multithread=True, heartbeat=False, nonblocking=True)
    async_client.connect().login()

    bench_single_request(async_client, "async")

    # ========= 并发对比 =========
    print("\n--- 并发测试 (10线程 x 5请求 = 50次) ---")
    rps_sync = bench_concurrent(sync, "sync", n_threads=10, req_per_thread=5)
    rps_async = bench_concurrent(async_client, "async", n_threads=10, req_per_thread=5)

    speedup = rps_async / rps_sync if rps_sync > 0 else float('inf')
    print(f"\n  >>> 吞吐提升: {speedup:.1f}x ({rps_sync:.1f} -> {rps_async:.1f} RPS)")

    # 高并发
    print("\n--- 高并发测试 (20线程 x 5请求 = 100次) ---")
    rps_sync2 = bench_concurrent(sync, "sync", n_threads=20, req_per_thread=5)
    rps_async2 = bench_concurrent(async_client, "async", n_threads=20, req_per_thread=5)

    speedup2 = rps_async2 / rps_sync2 if rps_sync2 > 0 else float('inf')
    print(f"\n  >>> 吞吐提升: {speedup2:.1f}x ({rps_sync2:.1f} -> {rps_async2:.1f} RPS)")

    sync.disconnect()
    async_client.disconnect()

    print("\n" + "=" * 65)
    print("  测试完成")
    print("=" * 65)


if __name__ == '__main__':
    main()
