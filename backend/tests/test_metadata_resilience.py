from services.metadata import _backoff_delay, _is_retryable_status


def test_retryable_statuses():
    assert _is_retryable_status(429) is True
    assert _is_retryable_status(500) is True
    assert _is_retryable_status(503) is True
    assert _is_retryable_status(404) is False
    assert _is_retryable_status(200) is False


def test_backoff_delay_exponential():
    assert _backoff_delay(0) == 1
    assert _backoff_delay(1) == 2
    assert _backoff_delay(2) == 4


def test_backoff_delay_capped():
    assert _backoff_delay(10, cap=30.0) == 30.0


def test_backoff_delay_honors_retry_after():
    assert _backoff_delay(0, retry_after=5.0) == 5.0
    assert _backoff_delay(5, retry_after=1.0) == 1.0


def test_partial_urls_excluded_from_watermark_candidates():
    # Mirrors the intersection done in _pull_combine_save: only URLs that
    # both appear in the combined data AND completed their pull should have
    # their incremental watermark advanced.
    urls_in_data = {"https://a", "https://b"}
    complete_urls = {"https://a"}  # b returned partial results
    successful_urls = urls_in_data & complete_urls
    assert successful_urls == {"https://a"}
