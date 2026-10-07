import { useEffect, useState } from "react";

import {
  createBriefFromAngle,
  createCampaignFromBrief,
  createCampaignMetricSnapshot,
  getCampaignMetricSnapshots,
  getInsightCampaignOverview,
} from "../../../services/api/trendReportApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import { actionPresentation, metricEntries, snapshotTone } from "../../../utils/stage4Workflow";
import { presentTrendMessage } from "../../../utils/trendReportMessage";

const date = (value) => value ? new Date(value).toLocaleString("vi-VN") : "Chưa có";
const statusLabel = (value) => ({ success: "Thành công", empty: "Không có dữ liệu", error: "Lỗi", new: "Mới", active: "Đang hoạt động", resolved: "Đã xử lý", draft: "Bản nháp" }[String(value || "").toLowerCase()] || value || "Chưa rõ");
const severityLabel = (value) => ({ low: "Thấp", medium: "Trung bình", high: "Cao", critical: "Nghiêm trọng" }[String(value || "").toLowerCase()] || value || "Chưa rõ");
const angleTypeLabel = (value) => ({ evidence_led: "Dựa trên bằng chứng" }[String(value || "").toLowerCase()] || value || "Góc quảng cáo");

function Stage4WorkflowPanel() {
  const [data, setData] = useState(null);
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pending, setPending] = useState({});
  const [payloads, setPayloads] = useState({});

  const load = async () => {
    setLoading(true); setError("");
    try { setData(await getInsightCampaignOverview()); }
    catch (err) { setError(presentTrendMessage(getUserErrorMessage(err, "Không thể tải quy trình xu hướng."))); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    void Promise.resolve().then(() => load());
  }, []);
  const run = async (key, work) => {
    if (pending[key]) return;
    setPending((value) => ({ ...value, [key]: true })); setError("");
    try { await work(); await load(); }
    catch (err) { setError(presentTrendMessage(getUserErrorMessage(err, "Thao tác bị từ chối bởi dữ liệu nguồn hoặc Độ tin cậy sản phẩm."))); }
    finally { setPending((value) => ({ ...value, [key]: false })); }
  };
  const loadMetrics = async (campaignId) => {
    const key = `metrics-${campaignId}`;
    await run(key, async () => {
      const items = await getCampaignMetricSnapshots(campaignId);
      setMetrics((current) => ({ ...current, [campaignId]: items }));
    });
  };
  const recordMetric = async (campaignId) => {
    const key = `record-${campaignId}`;
    let parsed;
    try { parsed = JSON.parse(payloads[campaignId] || ""); } catch { setError("Dữ liệu chỉ số phải là JSON hợp lệ do bạn cung cấp."); return; }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || !Object.keys(parsed).length) { setError("Hãy nhập ít nhất một chỉ số thực tế."); return; }
    await run(key, async () => {
      const snapshot = await createCampaignMetricSnapshot(campaignId, parsed);
      setMetrics((current) => ({ ...current, [campaignId]: [...(current[campaignId] || []), snapshot] }));
      setPayloads((current) => ({ ...current, [campaignId]: "" }));
    });
  };
  if (loading) return <p className="trend-workflow__state">Đang tải quy trình xu hướng…</p>;
  if (error) return <p className="trend-workflow__state is-error">{error}</p>;
  const overview = data || {};
  return <section className="trend-workflow" aria-label="Quy trình xu hướng">
    <header><strong>Quy trình xu hướng</strong><button type="button" onClick={load}>Tải lại</button></header>
    <p className="trend-workflow__path">Theo dõi → Bản ghi → Cảnh báo → Góc quảng cáo → Brief → Chiến dịch → Chỉ số</p>
    <div className="trend-workflow__grid">
      <section><h3>Chủ đề theo dõi</h3>{overview.monitors?.length ? overview.monitors.map((item) => <article key={item.monitor_key}><strong>{item.query}</strong><small>{item.enabled ? "Đang bật" : "Đã tắt"} · mỗi {item.cadence_minutes} phút · {item.timezone}</small><small>Lần chạy tiếp theo: {date(item.next_run_at)}</small></article>) : <p>Chưa có chủ đề theo dõi.</p>}</section>
      <section><h3>Bản ghi xu hướng</h3>{overview.snapshots?.length ? overview.snapshots.map((item, index) => <article className={`is-${snapshotTone(item.status)}`} key={`${item.monitor_id}-${index}`}><strong>{statusLabel(item.status)}</strong><small>{date(item.captured_at)} · {item.provider || "Nguồn chưa nêu"}</small>{item.error_message ? <small>{presentTrendMessage(item.error_message)}</small> : null}{Object.entries(item.payload || {}).map(([key, value]) => <small key={key}>{key}: {String(value)}</small>)}</article>) : <p>Chưa có bản ghi xu hướng.</p>}</section>
      <section><h3>Cảnh báo</h3>{overview.alerts?.length ? overview.alerts.map((item, index) => <article key={`${item.title}-${index}`}><strong>{severityLabel(item.severity)} · {statusLabel(item.status)}</strong><span>{item.title}</span><small>{presentTrendMessage(item.message)}</small>{item.resolved_at ? <small>Đã xử lý lúc: {date(item.resolved_at)}</small> : null}</article>) : <p>Chưa có cảnh báo.</p>}</section>
    </div>
    <section className="trend-workflow__list"><h3>Góc quảng cáo</h3>{overview.angles?.length ? overview.angles.map((item) => { const trust = actionPresentation(item.trust_action); return <article key={item.id}><strong>{angleTypeLabel(item.angle_type)} · {item.title}</strong><small>{item.wording}</small><small>{item.rationale}</small><span className={`trend-workflow__trust is-${trust.tone}`}>{trust.label}</span><button type="button" disabled={!trust.canCreate || pending[`brief-${item.id}`]} onClick={() => run(`brief-${item.id}`, () => createBriefFromAngle(item.id))}>{pending[`brief-${item.id}`] ? "Đang tạo…" : "Tạo brief"}</button></article>; }) : <p>Chưa có góc quảng cáo.</p>}</section>
    <section className="trend-workflow__list"><h3>Brief quảng cáo</h3>{overview.briefs?.length ? overview.briefs.map((item) => <article key={item.id}><strong>{item.title}</strong><small>{item.core_message}</small><small>{item.copy_direction}</small><button type="button" disabled={pending[`campaign-${item.id}`]} onClick={() => run(`campaign-${item.id}`, () => createCampaignFromBrief(item.id))}>{pending[`campaign-${item.id}`] ? "Đang tạo…" : "Tạo chiến dịch"}</button></article>) : <p>Chưa có brief quảng cáo.</p>}</section>
    <section className="trend-workflow__list"><h3>Chiến dịch & số liệu</h3>{overview.campaigns?.length ? overview.campaigns.map((item) => <article key={item.id}><strong>{item.name} · {statusLabel(item.status)}</strong><small>Dựa trên: Xu hướng → Góc quảng cáo → Brief</small><button type="button" disabled={pending[`metrics-${item.id}`]} onClick={() => loadMetrics(item.id)}>Xem bản ghi</button>{metrics[item.id]?.length ? metrics[item.id].map((snapshot) => <div className="trend-workflow__metric" key={snapshot.id}><small>Ghi nhận lúc: {date(snapshot.captured_at)}</small>{metricEntries(snapshot.metric_payload).map(([key, value]) => <small key={key}>{key}: {String(value)}</small>)}</div>) : null}<textarea value={payloads[item.id] || ""} onChange={(event) => setPayloads((current) => ({ ...current, [item.id]: event.target.value }))} placeholder={'Ghi nhận số liệu, ví dụ: {"clicks": 12}'} /><button type="button" disabled={pending[`record-${item.id}`] || !payloads[item.id]?.trim()} onClick={() => recordMetric(item.id)}>{pending[`record-${item.id}`] ? "Đang lưu…" : "Lưu bản ghi số liệu"}</button></article>) : <p>Chưa có chiến dịch từ quy trình xu hướng.</p>}</section>
  </section>;
}

export default Stage4WorkflowPanel;
