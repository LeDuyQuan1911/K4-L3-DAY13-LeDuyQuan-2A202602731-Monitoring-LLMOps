# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** (Điền tên)
- **MSSV:** (Điền MSSV)
- **Lớp:** K4-L3A
- **Repository URL:** (Điền URL repo GitHub cá nhân)
- **Commit SHA cuối:** (Điền sau khi commit)
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-<MSSV>`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 0/100 (MISSING correlation_id) | 100/100 | Đạt toàn bộ 4 tiêu chí |
| `validate_dashboard.py` | 6/6 (config sẵn) | 6/6 | Dashboard contract hợp lệ |
| `pytest` | Fail 2 tests | 22/22 passed | Sửa test mock cho generation |
| Số traces hợp lệ | 0 | ≥30 traces | Có root, retriever, generation |
| Số PII leak | Có thể rò rỉ | 0 | PII scrubber chặn trước file writer |
| Latency P95 / TTFT P95 | ~160ms / ~50ms | ~160ms / ~50ms (normal), ~2660ms (rag_slow) | Bình thường dưới SLO 3000ms |
| Retrieval success rate | 100% | 100% | Không có tool_fail trong baseline |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  Middleware `CorrelationIdMiddleware` đọc header `x-request-id` từ client; nếu không có thì sinh format `req-<8-hex>` bằng `uuid.uuid4().hex[:8]`. Gọi `clear_contextvars()` đầu mỗi request để tránh leak giữa các request, rồi `bind_contextvars(correlation_id=...)` để tất cả log trong request đều kèm ID. Trả ngược header `x-request-id` và `x-response-time-ms` trong response.

- **Các metadata được ghi vào structured log:**
  `user_id_hash` (SHA-256 12 ký tự), `session_id`, `feature`, `model`, `env`, `correlation_id`, `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, `error_type`, `payload`.

- **Cách bảo đảm PII được scrub trước khi ghi:**
  Processor `scrub_event` được đặt trong structlog pipeline **trước** `JsonlFileProcessor` (file writer) và `JSONRenderer`. Processor duyệt `payload` dict và `event` string, gọi `scrub_text()` trên mọi string value. `scrub_text()` dùng regex patterns cho email, phone VN, CCCD 12 số, credit card, passport và Vietnamese address keywords, thay bằng `[REDACTED_<TYPE>]`.

- **Cách kiểm chứng kết quả:**
  Chạy `validate_logs.py` đọc `data/logs.jsonl` và kiểm tra:
  1. Có đủ required fields (ts, level, event, correlation_id)
  2. Có ≥2 unique correlation_id
  3. API records có enrichment fields (user_id_hash, session_id, feature, model)
  4. Không phát hiện raw PII bằng regex detectors độc lập

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  Traces gửi tới project Langfuse cá nhân qua `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` riêng. Mỗi trace có `user_id` (hashed), `session_id`, `correlation_id` trong metadata — match với log records.

- **Cấu trúc root/retrieval/generation observations:**
  - Root: `lab-agent-run` (type=agent) — không capture raw input/output
  - Child span: `retriever` (type=span) — ghi doc_count, query_preview
  - Child generation: `fake-llm-generation` (type=generation) — ghi model, usage_details (input/output/total tokens), cost_details, prompt name/version/label

- **Cách nối trace với log:**
  `correlation_id` được bind vào cả structlog context (xuất hiện trong mọi log record) và Langfuse trace metadata. Dùng correlation_id để tìm log line → trace tương ứng.

- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, labels: `baseline`, `production`
- **Version/label candidate:** Version 2, label: `candidate`
- **Trace ID của mỗi version:** (Xem trên Langfuse UI, ghi trace ID cụ thể)
- **Cách promote và rollback `production`:**
  Promote: tạo version mới với cùng template v2 và label `production`. Rollback: tạo version mới với template gốc v1 và label `production`. Langfuse tự chuyển label sang version mới nhất có label đó.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  Streamlit dashboard (`scripts/dashboard.py`) đọc `data/logs.jsonl` theo config `config/dashboard.yaml`:
  1. **Latency** — P50/P95/P99 và TTFT P95, threshold P95 ≤ 3000ms
  2. **Traffic** — count requests, rate per minute, threshold ≥ 1 req/min
  3. **Errors** — error rate %, breakdown by error_type, retrieval success rate, threshold ≤ 2%
  4. **Cost** — total và per-request cost, threshold ≤ $2.5
  5. **Tokens** — input/output token sums, threshold ≤ 50000
  6. **Quality** — mean quality score, threshold ≥ 0.75

- **SLO và lý do chọn:**
  Primary SLO: 99.5% requests có latency ≤ 3000ms trong 28 ngày. Chọn ngưỡng 3s vì fake LLM baseline ~160ms, có margin lớn cho spike; 99.5% đủ nghiêm nhưng cho phép 0.5% error budget cho maintenance/incident.

- **Cách tính error budget:**
  Error budget = 100% - SLO target = 0.5%. Nghĩa là trong 28 ngày, tối đa 0.5% requests được phép vi phạm SLI. Nếu SLI hiện tại = 98%, budget used = 2%, budget remaining = 0.5% - 2% = -1.5% (đã cạn).

- **Ba alert và runbook tương ứng:**
  1. `high_latency_p95` (critical, 5m) — P95 > 3000ms → kiểm tra retrieval/LLM span duration
  2. `elevated_error_rate` (warning, 3m) — error > 2% → lọc error_type, tìm failing span
  3. `cost_budget_exceeded` (warning, 1h) — cost > $2.5/24h → kiểm tra output_tokens spike
  Mỗi alert có runbook chi tiết tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** (Ghi khi chạy challenge chính thức)
- **Triệu chứng từ metrics:** Latency P95 tăng vọt từ ~160ms lên ~2660ms khi `rag_slow` active
- **Log line và correlation ID liên quan:** (Ghi correlation_id cụ thể từ log khi chạy challenge)
- **Trace ID và span gây ảnh hưởng:** (Ghi trace ID từ Langfuse — span `retriever` có duration ~2500ms)
- **Root cause:** Retrieval (vector store) bị slow — `time.sleep(2.5)` khi `STATE["rag_slow"]` active
- **Fix action:** Disable incident `rag_slow` qua API `/incidents/rag_slow/disable`
- **Preventive measure:** Đặt timeout cho retrieval, thêm circuit breaker, monitor retrieval latency riêng biệt

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  Tách `_retrieve_with_span` và `_generate_with_span` thành child observations riêng (thay vì để trong `run()`) để Langfuse waterfall hiển thị rõ thời gian retrieval vs generation — giúp xác định bottleneck ngay lập tức.

- **Một lỗi/blocker đã gặp:**
  Langfuse SDK v4 dùng `usage_details` và `cost_details` thay vì `usage` — starter test mock không có `update_current_generation`, gây test fail.

- **Cách tìm nguyên nhân và xử lý:**
  Dùng `inspect.signature(client.update_current_generation)` để xem đúng parameter names của SDK v4, sửa lại agent code và thêm method vào test mock.

- **Cách hiểu luồng Metrics → Logs → Traces:**
  Metrics (dashboard) cho thấy triệu chứng (latency tăng, error rate tăng) và khoanh vùng thời gian. Logs cho phép lọc request trong khoảng đó và lấy correlation_id cụ thể. Traces cho phép drill-down vào request đó, xem span tree và xác định chính xác component gây chậm/lỗi.

- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  Prompt versioning cho phép A/B testing an toàn; nếu version mới gây regressions (tăng cost/giảm quality), có thể rollback production ngay lập tức. Token/cost monitoring ngăn bill shock. SLO tạo ngôn ngữ chung giữa dev/ops/business về mức chất lượng cam kết.

- **Điều quan trọng nhất đã học:**
  Observability không chỉ là thêm log — cần structured format, correlation ID xuyên suốt, PII protection, và ba tầng metrics/logs/traces phối hợp để thực sự debug production issues.

- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  Challenge chính thức (CP3) chờ Lab Coach release file. Dashboard Streamlit chạy local, chưa deploy. Evidence screenshots cần chụp thủ công từ Langfuse UI.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
