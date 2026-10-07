import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { FiExternalLink, FiRadio, FiRefreshCw, FiTrash2, FiX } from "react-icons/fi";

import { deleteTrendReport, getSourcePolicies, getTrendReportTrust, getTrendReports, retrieveTrendReport, updateSourcePolicy } from "../../../services/api/trendReportApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import {
  buildSourceStatusCards,
  getProviderStatusPresentation,
  getSourceStatusPresentation,
} from "../../../utils/trendReportSourceStatus";
import { trustPresentation, trustWarning } from "../../../utils/trendReportTrust";
import { presentTrendMessage, presentTrustRationale } from "../../../utils/trendReportMessage";
import Stage4WorkflowPanel from "./Stage4WorkflowPanel";
import "./TrendReportPanel.css";

const formatDate = (value) => {
  if (!value) return "Không có";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString("vi-VN");
};

function TrendReportPanel({ open, conversationId, onClose }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [trustMode, setTrustMode] = useState("all_evidence");
  const [trustByReport, setTrustByReport] = useState({});
  const [policies, setPolicies] = useState([]);
  const [policyHost, setPolicyHost] = useState("");
  const [policySaving, setPolicySaving] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [deletingReportId, setDeletingReportId] = useState("");

  const refreshTrust = useCallback(async (items, mode = trustMode) => {
    const result = await Promise.all(items.map(async (report) => [report.report_id, await getTrendReportTrust(report.report_id, mode)]));
    setTrustByReport(Object.fromEntries(result));
  }, [trustMode]);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getTrendReports();
      const scoped = conversationId
        ? data.filter((report) => Number(report.conversation_id) === Number(conversationId))
        : data;
      setReports(scoped);
      await Promise.all([refreshTrust(scoped), getSourcePolicies().then(setPolicies)]);
    } catch (loadError) {
      setError(presentTrendMessage(getUserErrorMessage(loadError, "Không thể tải Báo cáo xu hướng.")));
    } finally {
      setLoading(false);
    }
  }, [conversationId, refreshTrust]);

  const changeTrustMode = async (mode) => {
    setTrustMode(mode);
    setError("");
    try { await refreshTrust(reports, mode); } catch (loadError) { setError(presentTrendMessage(getUserErrorMessage(loadError, "Không thể tải Độ tin cậy sản phẩm."))); }
  };

  const savePolicy = async (decision) => {
    const host = policyHost.trim();
    if (!host) return;
    setPolicySaving(true); setError("");
    try {
      await updateSourcePolicy({ host, decision });
      setPolicyHost("");
      const [nextPolicies] = await Promise.all([getSourcePolicies(), refreshTrust(reports)]);
      setPolicies(nextPolicies);
    } catch (policyError) { setError(presentTrendMessage(getUserErrorMessage(policyError, "Không thể cập nhật chính sách nguồn."))); }
    finally { setPolicySaving(false); }
  };


  const runRetrieval = async (event) => {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Hãy nhập chủ đề cần theo dõi trước.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    try {
      const report = await retrieveTrendReport({
        query: trimmedQuery,
        conversation_id: conversationId ? Number(conversationId) : undefined,
      });
      setReports((current) => [
        report,
        ...current.filter((item) => item.report_id !== report.report_id),
      ]);
      await refreshTrust([report]);
      setQuery("");
    } catch (retrieveError) {
      setError(presentTrendMessage(getUserErrorMessage(retrieveError, "Không thể thu thập Báo cáo xu hướng.")));
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteCandidate) return;
    const reportId = deleteCandidate.report_id;
    setDeletingReportId(reportId);
    setError("");
    try {
      await deleteTrendReport(reportId);
      setReports((current) => current.filter((item) => item.report_id !== reportId));
      setTrustByReport((current) => {
        const next = { ...current };
        delete next[reportId];
        return next;
      });
      setDeleteCandidate(null);
    } catch (deleteError) {
      setError(presentTrendMessage(getUserErrorMessage(deleteError, "Không thể xóa Báo cáo xu hướng.")));
    } finally {
      setDeletingReportId("");
    }
  };

  useEffect(() => {
    if (!open) return undefined;
    void Promise.resolve().then(() => loadReports());
    const closeOnEscape = (event) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, loadReports, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="trend-report-panel" role="dialog" aria-modal="true" aria-label="Báo cáo xu hướng">
      <button type="button" className="trend-report-panel__backdrop" onClick={onClose} aria-label="Đóng Báo cáo xu hướng" />
      <aside className="trend-report-panel__drawer">
        <header className="trend-report-panel__header">
          <span><FiRadio /></span>
          <div><h2>Báo cáo xu hướng</h2><p>{conversationId ? "Nguồn cho cuộc trò chuyện hiện tại" : "Nguồn bằng chứng đã lưu"}</p></div>
          <button type="button" onClick={loadReports} disabled={loading} aria-label="Tải lại"><FiRefreshCw className={loading ? "is-spinning" : undefined} /></button>
          <button type="button" onClick={onClose} aria-label="Đóng"><FiX /></button>
        </header>
        <div className="trend-report-panel__content">
          <Stage4WorkflowPanel />
          <p className="trend-report-panel__status-empty">Quy trình: nhập chủ đề cần theo dõi → thu thập → tạo bản ghi xu hướng. Chỉ khi bản ghi có dữ liệu hợp lệ hệ thống mới tạo cảnh báo; từ bằng chứng và Độ tin cậy sản phẩm phù hợp mới có thể tạo góc quảng cáo, brief, chiến dịch và số liệu.</p>
          <form className="trend-report-panel__retrieve" onSubmit={runRetrieval}>
            <label htmlFor="trend-report-query">Theo dõi một chủ đề</label>
            <div>
              <input
                id="trend-report-query"
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ví dụ: xu hướng giày chạy bộ"
                disabled={isSubmitting}
              />
              <button type="submit" disabled={isSubmitting || !query.trim()}>
                {isSubmitting ? "Đang thu thập…" : "Thu thập"}
              </button>
            </div>
          </form>

          <section className="trend-report-panel__trust-controls" aria-label="Điều khiển Độ tin cậy sản phẩm">
            <strong>Độ tin cậy sản phẩm</strong>
            <div role="group" aria-label="Chế độ bằng chứng">
              {["all_evidence", "verified_only"].map((mode) => <button key={mode} type="button" className={trustMode === mode ? "is-active" : ""} onClick={() => changeTrustMode(mode)}>{mode === "verified_only" ? "Chỉ bằng chứng đã xác minh" : "Tất cả bằng chứng"}</button>)}
            </div>
            <small>{trustMode === "verified_only" ? "Chỉ dùng bằng chứng có cơ sở xác minh hợp lệ; backend áp dụng theo chính sách nguồn." : "Tất cả bằng chứng dùng mọi evidence hợp lệ theo đánh giá trust của backend; đây không phải độ tự tin của AI."}</small>
            <div className="trend-report-panel__policy-form"><input value={policyHost} onChange={(event) => setPolicyHost(event.target.value)} placeholder="nguon.example" aria-label="Tên miền nguồn" /><button type="button" disabled={policySaving || !policyHost.trim()} onClick={() => savePolicy("trusted")}>Tin cậy</button><button type="button" disabled={policySaving || !policyHost.trim()} onClick={() => savePolicy("excluded")}>Loại trừ</button></div>
            <small>Nhập tên miền nguồn ở ô trên để cấu hình chính sách nguồn: <strong>Tin cậy</strong> cho phép nguồn được đánh giá trust; <strong>Loại trừ</strong> không dùng nguồn trong trust assessment. Đây không phải ô nhập sản phẩm hoặc chủ đề để tìm xu hướng.</small>
            <small>Chính sách nguồn của bạn: {policies.length ? policies.map((item) => `${item.host} (${item.decision === "trusted" ? "tin cậy" : "loại trừ"})`).join(", ") : "chưa có"}</small>
          </section>

          {loading ? <p className="trend-report-panel__state">Đang tải báo cáo xu hướng…</p> : null}
          {!loading && error ? <p className="trend-report-panel__state is-error">{error}</p> : null}
          {!loading && !error && reports.length === 0 ? <p className="trend-report-panel__state">Chưa có báo cáo xu hướng nào cho phạm vi này.</p> : null}
          {!loading && !error && reports.map((report) => (
            <article className="trend-report-panel__report" key={report.report_id}>
              <header><strong>{report.query}</strong><div className="trend-report-panel__report-actions"><span className={"is-" + getProviderStatusPresentation(report).tone}>{getProviderStatusPresentation(report).label}</span><button type="button" onClick={() => setDeleteCandidate(report)} aria-label={`Xóa báo cáo xu hướng: ${report.query}`} title="Xóa bản ghi"><FiTrash2 /></button></div></header>
              {deleteCandidate?.report_id === report.report_id ? <div className="trend-report-panel__delete-confirm" role="alert"><span>Xóa bản ghi này?</span><div><button type="button" onClick={() => setDeleteCandidate(null)} disabled={deletingReportId === report.report_id}>Hủy</button><button type="button" onClick={confirmDelete} disabled={deletingReportId === report.report_id}>{deletingReportId === report.report_id ? "Đang xóa…" : "Xóa"}</button></div></div> : null}
              <p className="trend-report-panel__time">Thu thập lúc: {formatDate(report.retrieved_at)}</p>
              {buildSourceStatusCards(report).length > 0 ? (
                <section className="trend-report-panel__status-comparison" aria-label="So sánh trạng thái nguồn">
                  <div className="trend-report-panel__section-heading">
                    <strong>Trạng thái nguồn</strong>
                    <small>{buildSourceStatusCards(report).length} nguồn</small>
                  </div>
                  <div className="trend-report-panel__status-grid">
                    {buildSourceStatusCards(report).map((sourceStatus) => (
                      <article
                        className={"trend-report-panel__status-card is-" + sourceStatus.tone}
                        key={sourceStatus.key}
                      >
                        <div className="trend-report-panel__status-card-heading">
                          <div>
                            <strong>{sourceStatus.source}</strong>
                            <small>Nền tảng: {sourceStatus.platform}</small>
                          </div>
                          <span className="trend-report-panel__status-badge">{sourceStatus.label}</span>
                        </div>
                        <small>Trạng thái: {sourceStatus.label} | Bằng chứng: {sourceStatus.evidenceCount}</small>
                        {sourceStatus.message ? <p>{presentTrendMessage(sourceStatus.message)}</p> : null}
                        {sourceStatus.fromCache ? (
                          <small className="trend-report-panel__status-meta">Bộ nhớ đệm: đã dùng lại</small>
                        ) : null}
                        {sourceStatus.deduplicatedEvidenceIds.length > 0 ? (
                          <small className="trend-report-panel__status-meta">
                            Đã loại trùng: {sourceStatus.deduplicatedEvidenceIds.join(", ")}
                          </small>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </section>
              ) : (
                <p className="trend-report-panel__status-empty">
                  Chưa có trạng thái nguồn hoặc bằng chứng có cấu trúc.
                </p>
              )}

              {report.caveat ? <p className="trend-report-panel__caveat">{presentTrendMessage(report.caveat)}</p> : null}
              {trustByReport[report.report_id] ? (() => { const trust = trustByReport[report.report_id]; const warning = trustWarning(trust); return <section className={`trend-report-panel__trust is-${warning.tone}`}><p>{warning.text}</p>{Array.isArray(trust.claims) && trust.claims.length ? trust.claims.map((claim) => { const presentation = trustPresentation(claim); return <article key={claim.claim_id} className={`trend-report-panel__claim is-${presentation.tone}`}><strong>{claim.claim_text}</strong><span>Trạng thái: {presentation.label}</span><small>Hành động: {presentation.actionLabel}{presentation.highRisk ? " · Rủi ro cao" : ""}</small><small>{presentTrustRationale(claim.rationale)}</small></article>; }) : <p className="trend-report-panel__status-empty">Chưa có claim có cấu trúc cho báo cáo này.</p>}</section>; })() : <p className="trend-report-panel__state">Đang tải Độ tin cậy sản phẩm…</p>}
              {report.evidences.map((evidence) => (
                <section className="trend-report-panel__source" key={evidence.evidence_id}>
                  <div><strong>{evidence.title}</strong><small>{evidence.publisher} - <span className={"trend-report-panel__evidence-badge is-" + getSourceStatusPresentation({ status: evidence.status, evidenceCount: 1 }).tone} title={evidence.status}>{getSourceStatusPresentation({ status: evidence.status, evidenceCount: 1 }).label}</span></small></div>
                  <p>{evidence.excerpt}</p><small>Thu thập lúc: {formatDate(evidence.retrieved_at)}</small>
                  <a href={evidence.source_url} target="_blank" rel="noreferrer noopener">Mở nguồn <FiExternalLink /></a>
                </section>
              ))}
            </article>
          ))}
        </div>
      </aside>
    </div>, document.body,
  );
}

export default TrendReportPanel;
