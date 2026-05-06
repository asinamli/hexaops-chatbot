# paralel istk atmak içn test scripti

"""
AYNI USER İLE TEST 

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


URL = "http://127.0.0.1:8000/api/chat"

TOTAL_REQUESTS = 11
MAX_WORKERS = 5

PAYLOAD = {
    "message": "merhaba",
    "user_id": "load_test_user_1",
    "conversation_id": "load_test_conv_1"
}


def send_request(index: int) -> dict:
    start_time = time.time()

    try:
        response = requests.post(URL, json=PAYLOAD, timeout=90)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "index": index,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "worker_pid": response.headers.get("X-Worker-Pid"),
            "request_id": response.headers.get("X-Request-Id"),
            "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
            "response_text": response.text
        }

    except requests.exceptions.RequestException as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "index": index,
            "status_code": "REQUEST_ERROR",
            "duration_ms": duration_ms,
            "worker_pid": None,
            "request_id": None,
            "rate_limit_remaining": None,
            "response_text": str(e)
        }


def main():
    results = []

    print(f"Toplam istek sayısı: {TOTAL_REQUESTS}")
    print(f"Aynı anda çalışan thread sayısı: {MAX_WORKERS}")
    print("Yük testi başlıyor...\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(send_request, i) for i in range(1, TOTAL_REQUESTS + 1)]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            print(
                f"[istek={result['index']}] "
                f"status={result['status_code']} "
                f"duration_ms={result['duration_ms']} "
                f"worker_pid={result['worker_pid']} "
                f"remaining={result['rate_limit_remaining']}"
            )

    print("\n--- Özet ---")

    success_count = sum(1 for r in results if r["status_code"] == 200)
    rate_limited_count = sum(1 for r in results if r["status_code"] == 429)
    error_count = sum(1 for r in results if r["status_code"] == "REQUEST_ERROR")

    durations = [r["duration_ms"] for r in results if isinstance(r["duration_ms"], (int, float))]
    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0

    worker_pids = sorted({r["worker_pid"] for r in results if r["worker_pid"]})

    print(f"Başarılı istek sayısı: {success_count}")
    print(f"Rate limit'e takılan istek sayısı: {rate_limited_count}")
    print(f"Request error sayısı: {error_count}")
    print(f"Ortalama süre (ms): {avg_duration}")
    print(f"Cevap veren worker pid'ler: {worker_pids}")


if __name__ == "__main__":
    main()
    

"""



"""

# FARKLI USERLARLA TEST
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


URL = "http://127.0.0.1:8000/api/chat"

TOTAL_REQUESTS = 12
MAX_WORKERS = 6

# test modu:
# "same_user"  -> aynı kullanıcıyla test, rate limiting davranışını görmek için
# "different_users" -> farklı kullanıcılarla test, gerçek concurrency davranışını daha temiz görmek için
TEST_MODE = "different_users"


def build_payload(index: int) -> dict:
    if TEST_MODE == "same_user":
        return {
            "message": "merhaba",
            "user_id": "load_test_same_user",
            "conversation_id": "load_test_same_conv"
        }

    return {
        "message": "merhaba",
        "user_id": f"load_user_{index}",
        "conversation_id": f"load_conv_{index}"
    }


def send_request(index: int) -> dict:
    payload = build_payload(index)
    start_time = time.time()

    try:
        response = requests.post(URL, json=payload, timeout=90)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "index": index,
            "user_id": payload["user_id"],
            "conversation_id": payload["conversation_id"],
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "worker_pid": response.headers.get("X-Worker-Pid"),
            "request_id": response.headers.get("X-Request-Id"),
            "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
            "response_time_header": response.headers.get("X-Response-Time-Ms"),
            "response_text": response.text
        }

    except requests.exceptions.RequestException as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "index": index,
            "user_id": payload["user_id"],
            "conversation_id": payload["conversation_id"],
            "status_code": "REQUEST_ERROR",
            "duration_ms": duration_ms,
            "worker_pid": None,
            "request_id": None,
            "rate_limit_remaining": None,
            "response_time_header": None,
            "response_text": str(e)
        }


def print_summary(results: list[dict]) -> None:
    success_count = sum(1 for r in results if r["status_code"] == 200)
    rate_limited_count = sum(1 for r in results if r["status_code"] == 429)
    error_count = sum(1 for r in results if r["status_code"] == "REQUEST_ERROR")

    durations = [r["duration_ms"] for r in results if isinstance(r["duration_ms"], (int, float))]
    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
    min_duration = round(min(durations), 2) if durations else 0
    max_duration = round(max(durations), 2) if durations else 0

    worker_pids = sorted({r["worker_pid"] for r in results if r["worker_pid"]})
    status_groups = {}

    for result in results:
        status = result["status_code"]
        status_groups[status] = status_groups.get(status, 0) + 1

    print("\n--- Özet ---")
    print(f"Test modu: {TEST_MODE}")
    print(f"Başarılı istek sayısı: {success_count}")
    print(f"Rate limit'e takılan istek sayısı: {rate_limited_count}")
    print(f"Request error sayısı: {error_count}")
    print(f"Minimum süre (ms): {min_duration}")
    print(f"Maksimum süre (ms): {max_duration}")
    print(f"Ortalama süre (ms): {avg_duration}")
    print(f"Cevap veren worker pid'ler: {worker_pids}")
    print(f"Status dağılımı: {status_groups}")


def main():
    results = []

    print(f"Test modu: {TEST_MODE}")
    print(f"Toplam istek sayısı: {TOTAL_REQUESTS}")
    print(f"Aynı anda çalışan thread sayısı: {MAX_WORKERS}")
    print("Yük testi başlıyor...\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(send_request, i) for i in range(1, TOTAL_REQUESTS + 1)]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            print(
                f"[istek={result['index']}] "
                f"user={result['user_id']} "
                f"status={result['status_code']} "
                f"duration_ms={result['duration_ms']} "
                f"worker_pid={result['worker_pid']} "
                f"remaining={result['rate_limit_remaining']}"
            )

    print_summary(results)


if __name__ == "__main__":
    main()"""



# daha ağır test senaryosu
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


URL = "http://127.0.0.1:8000/api/chat"

# burada test senaryosunu kolayca değiştiriyoruz
TOTAL_REQUESTS = 50
MAX_WORKERS = 20

# "same_user" -> rate limiting davranışını görmek için
# "different_users" -> gerçek concurrency davranışını daha temiz görmek için
TEST_MODE = "different_users"

# sonuçları json dosyasına da yazsın mı
SAVE_RESULTS_TO_FILE = True
RESULTS_FILE_NAME = "load_test_results.json"


def build_payload(index: int) -> dict:
    if TEST_MODE == "same_user":
        return {
            "message": "merhaba",
            "user_id": "load_test_same_user",
            "conversation_id": "load_test_same_conv"
        }

    return {
        "message": "Ankara hava durumu nasıl",
        "user_id": f"load_user_{index}",
        "conversation_id": f"load_conv_{index}"
    }


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0

    sorted_values = sorted(values)
    k = math.ceil((p / 100) * len(sorted_values)) - 1
    k = max(0, min(k, len(sorted_values) - 1))
    return round(sorted_values[k], 2)


def send_request(index: int) -> dict:
    payload = build_payload(index)
    start_time = time.time()

    try:
        response = requests.post(URL, json=payload, timeout=90)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "index": index,
            "user_id": payload["user_id"],
            "conversation_id": payload["conversation_id"],
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "worker_pid": response.headers.get("X-Worker-Pid"),
            "request_id": response.headers.get("X-Request-Id"),
            "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
            "response_time_header": response.headers.get("X-Response-Time-Ms"),
            "response_text": response.text,
            "llm_required": response.headers.get("X-LLM-Concurrency-Required"),
            "llm_concurrency_current": response.headers.get("X-LLM-Concurrency-Current"),
            "llm_concurrency_remaining": response.headers.get("X-LLM-Concurrency-Remaining"),
        }

    except requests.exceptions.RequestException as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "index": index,
            "user_id": payload["user_id"],
            "conversation_id": payload["conversation_id"],
            "status_code": "REQUEST_ERROR",
            "duration_ms": duration_ms,
            "worker_pid": None,
            "request_id": None,
            "rate_limit_remaining": None,
            "response_time_header": None,
            "response_text": str(e)
        }


def save_results(results: list[dict]) -> None:
    if not SAVE_RESULTS_TO_FILE:
        return

    with open(RESULTS_FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def print_summary(results: list[dict], total_test_duration_ms: float) -> None:
    success_count = sum(1 for r in results if r["status_code"] == 200)
    rate_limited_count = sum(1 for r in results if r["status_code"] == 429)
    busy_count = sum(1 for r in results if r["status_code"] == 503)
    error_count = sum(1 for r in results if r["status_code"] == "REQUEST_ERROR")

    durations = [r["duration_ms"] for r in results if isinstance(r["duration_ms"], (int, float))]
    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
    min_duration = round(min(durations), 2) if durations else 0
    max_duration = round(max(durations), 2) if durations else 0
    p50 = percentile(durations, 50)
    p95 = percentile(durations, 95)

    worker_pids = sorted({r["worker_pid"] for r in results if r["worker_pid"]})
    status_groups = {}

    for result in results:
        status = result["status_code"]
        status_groups[status] = status_groups.get(status, 0) + 1

    print("\n--- Özet ---")
    print(f"Test modu: {TEST_MODE}")
    print(f"Toplam test süresi (ms): {total_test_duration_ms}")
    print(f"Başarılı istek sayısı: {success_count}")
    print(f"Rate limit'e takılan istek sayısı: {rate_limited_count}")
    print(f"LLM yoğunluğu nedeniyle reddedilen istek sayısı: {busy_count}")
    print(f"Request error sayısı: {error_count}")
    print(f"Minimum süre (ms): {min_duration}")
    print(f"Maksimum süre (ms): {max_duration}")
    print(f"Ortalama süre (ms): {avg_duration}")
    print(f"P50 süre (ms): {p50}")
    print(f"P95 süre (ms): {p95}")
    print(f"Cevap veren worker pid'ler: {worker_pids}")
    print(f"Status dağılımı: {status_groups}")

    if SAVE_RESULTS_TO_FILE:
        print(f"Sonuçlar dosyaya yazıldı: {RESULTS_FILE_NAME}")


def main():
    results = []

    print(f"Test modu: {TEST_MODE}")
    print(f"Toplam istek sayısı: {TOTAL_REQUESTS}")
    print(f"Aynı anda çalışan thread sayısı: {MAX_WORKERS}")
    print("Yük testi başlıyor...\n")

    test_start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(send_request, i) for i in range(1, TOTAL_REQUESTS + 1)]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            print(
    f"[istek={result['index']}] "
    f"user={result['user_id']} "
    f"status={result['status_code']} "
    f"duration_ms={result['duration_ms']} "
    f"worker_pid={result['worker_pid']} "
    f"llm_required={result.get('llm_required')} "
    f"llm_concurrency_current={result.get('llm_concurrency_current')} "
    f"llm_concurrency_remaining={result.get('llm_concurrency_remaining')}"
)
    total_test_duration_ms = round((time.time() - test_start) * 1000, 2)

    save_results(results)
    print_summary(results, total_test_duration_ms)


if __name__ == "__main__":
    main()