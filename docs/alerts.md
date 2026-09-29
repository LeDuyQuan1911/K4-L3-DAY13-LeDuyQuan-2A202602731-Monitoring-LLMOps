# Alert Runbooks

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: high_latency_p95
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack
- SLI/SLO liên quan: P95 latency ≤ 3000ms (primary SLO: 99.5% requests < 3000ms in 28d)
- Điều kiện và thời gian duy trì: latency_p95 > 3000ms liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng trải nghiệm phản hồi chậm, có thể timeout; giảm chất lượng dịch vụ
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra dashboard panel Latency để xác nhận P95 > 3000ms
  2. Lọc logs theo khoảng thời gian bất thường, tìm request có latency_ms cao nhất
  3. Mở trace của request đó, so sánh duration retrieval vs generation span
- Mitigation tạm thời: Nếu retrieval chậm, restart vector store hoặc tăng timeout; nếu LLM chậm, giảm max_tokens hoặc chuyển model nhẹ hơn
- Owner: on-call-sre

## Alert 2

- Tên: elevated_error_rate
- Severity: warning
- Duration: 3m
- Kênh thông báo: Slack
- SLI/SLO liên quan: Error rate ≤ 2% (guardrail: error_rate_pct_max = 2)
- Điều kiện và thời gian duy trì: error_rate_pct > 2% liên tục trong 3 phút
- Ảnh hưởng tới người dùng: Một phần người dùng nhận HTTP 500; request thất bại không có câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra dashboard panel Errors: error_rate_pct và error_type breakdown
  2. Lọc logs theo event=request_failed, tìm error_type phổ biến nhất
  3. Mở trace của request lỗi, xác định span nào raise exception
- Mitigation tạm thời: Nếu tool_fail (Vector store timeout), kiểm tra kết nối vector DB; nếu dependency ngoài, bật circuit breaker hoặc fallback
- Owner: on-call-sre

## Alert 3

- Tên: cost_budget_exceeded
- Severity: warning
- Duration: 1h
- Kênh thông báo: Slack
- SLI/SLO liên quan: Daily cost ≤ $2.5 (guardrail: daily_cost_usd_max = 2.5)
- Điều kiện và thời gian duy trì: total_cost_usd > $2.5 trong rolling window 24h
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp, nhưng chi phí vận hành tăng đột biến; có thể dẫn tới throttle hoặc shutdown nếu không xử lý
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra dashboard panel Cost: sum_by_minute tăng đột biến ở thời điểm nào
  2. Lọc logs theo response_sent, sắp xếp theo cost_usd giảm dần; tìm request có cost cao bất thường
  3. Mở trace, kiểm tra tokens_in/tokens_out của generation span — so sánh với baseline
- Mitigation tạm thời: Giảm output_tokens limit; kiểm tra xem cost_spike incident có đang active không; nếu có, disable incident
- Owner: platform-lead
