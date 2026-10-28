from auth.throttle import FailureThrottle


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(max_failures=3, window=60, max_keys=100):
    clock = FakeClock()
    return FailureThrottle(max_failures, window, max_keys=max_keys, clock=clock), clock


def test_attempts_are_allowed_below_the_limit():
    throttle, _ = make()
    throttle.record_failure("alice")
    throttle.record_failure("alice")
    assert throttle.retry_after("alice") == 0


def test_attempts_are_blocked_at_the_limit_with_a_wait_time():
    throttle, clock = make()
    for _ in range(3):
        throttle.record_failure("alice")
        clock.now += 10
    assert throttle.retry_after("alice") == 30


def test_the_block_ends_when_the_oldest_failure_leaves_the_window():
    throttle, clock = make()
    for _ in range(3):
        throttle.record_failure("alice")
    clock.now += 60
    assert throttle.retry_after("alice") == 0


def test_reset_clears_the_counter():
    throttle, _ = make()
    for _ in range(3):
        throttle.record_failure("alice")
    throttle.reset("alice")
    assert throttle.retry_after("alice") == 0


def test_keys_are_counted_independently():
    throttle, _ = make()
    for _ in range(3):
        throttle.record_failure("alice")
    assert throttle.retry_after("alice") > 0
    assert throttle.retry_after("bob") == 0


def test_the_table_never_grows_past_its_cap():
    throttle, _ = make(max_keys=50)
    for number in range(500):
        throttle.record_failure("user-" + str(number))
    assert len(throttle) <= 50


def test_expired_keys_are_dropped_to_make_room():
    throttle, clock = make(max_keys=5, window=60)
    for number in range(5):
        throttle.record_failure("old-" + str(number))
    clock.now += 61
    throttle.record_failure("new")
    assert len(throttle) == 1
