import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { FiRadio, FiRefreshCw, FiTrash2, FiX } from "react-icons/fi";

import { deleteTrendReport, getSourcePolicies, getTrendReportTrust, getTrendReports, retrieveTrendReport, updateSourcePolicy } from "../../../services/api/trendReportApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import { getProviderStatusPresentation } from "../../../utils/trendReportSourceStatus";
import { trustPresentation, trustWarning } from "../../../utils/trendReportTrust";
import { presentTrendMessage, presentTrustRationale } from "../../../utils/trendReportMessage";
import { formatReportDate, requestReportHistory, requestTopicSearch } from "../../../utils/trendReportView";
import Stage4WorkflowPanel from "./Stage4WorkflowPanel";
import TrendReportResult from "./TrendReportResult";
import "./TrendReportPanel.css";

function TrendReportPanel({ open, conversationId, onClose }) {
  const [reports, setReports] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [retrievalError, setRetrievalError] = useState("");
  const [query, setQuery] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [trustMode, setTrustMode] = useState("all_evidence");
  const [trustByReport, setTrustByReport] = useState({});
  const [trustLoading, setTrustLoading] = useState(false);
  const [trustError, setTrustError] = useState("");
  const [policyError, setPolicyError] = useState("");
  const [trustRevision, setTrustRevision] = useState(0);
  const [policies, setPolicies] = useState([]);
  const [policyHost, setPolicyHost] = useState("");
  const [policySaving, setPolicySaving] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [deletingReportId, setDeletingReportId] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [trustOpen, setTrustOpen] = useState(false);
  const [workflowOpen, setWorkflowOpen] = useState(false);

  const selectedReport = reports.find((report) => report.report_id === selectedReportId) || null;

  const closePanel = useCallback(() => {
    setHistoryOpen(false);
    setTrustOpen(false);
    setWorkflowOpen(false);
    onClose();
  }, [onClose]);

  const loadReports = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const data = await requestReportHistory(getTrendReports);
      const scoped = conversationId
        ? data.filter((report) => Number(report.conversation_id) === Number(conversationId))
        : data;
      setReports(scoped);
      setSelectedReportId((current) => scoped.some((report) => report.report_id === current) ? current : scoped[0]?.report_id ?? null);
    } catch (loadError) {
      setHistoryError(presentTrendMessage(getUserErrorMessage(loadError, "Không thể tải lại lịch sử báo cáo RSS.")));
    } finally {
      setHistoryLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    if (!open) return;
    let active = true;
    getSourcePolicies().then((data) => { if (active) setPolicies(data); })
      .catch((error) => { if (active) setPolicyError(presentTrendMessage(getUserErrorMessage(error, "Không thể tải chính sách nguồn."))); });
    return () => { active = false; };
  }, [open]);

  useEffect(() => {
    if (!open || !selectedReportId) return;
    let active = true;
    Promise.resolve().then(() => { if (active) { setTrustLoading(true); setTrustError(""); } });
    getTrendReportTrust(selectedReportId, trustMode)
      .then((trust) => { if (active) setTrustByReport((current) => ({ ...current, [selectedReportId]: trust })); })
      .catch((error) => { if (active) setTrustError(presentTrendMessage(getUserErrorMessage(error, "Không thể tải Độ tin cậy sản phẩm."))); })
      .finally(() => { if (active) setTrustLoading(false); });
    return () => { active = false; };
  }, [open, selectedReportId, trustMode, trustRevision]);

  const savePolicy = async (decision) => {
    const host = policyHost.trim();
    if (!host) return;
    setPolicySaving(true); setPolicyError("");
    try {
      await updateSourcePolicy({ host, decision });
      setPolicyHost("");
      setPolicies(await getSourcePolicies());
      setTrustRevision((current) => current + 1);
    } catch (error) { setPolicyError(presentTrendMessage(getUserErrorMessage(error, "Không thể cập nhật chính sách nguồn."))); }
    finally { setPolicySaving(false); }
  };


  const runRetrieval = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setRetrievalError("Hãy nhập chủ đề cần tìm trước.");
      return;
    }
    if (trimmedQuery.length > 512) {
      setRetrievalError("Chủ đề tối đa 512 ký tự.");
      return;
    }

    setIsSubmitting(true);
    setRetrievalError("");
    try {
      const report = await requestTopicSearch(retrieveTrendReport, trimmedQuery, conversationId);
      setReports((current) => [
        report,
        ...current.filter((item) => item.report_id !== report.report_id),
      ]);
      setSelectedReportId(report.report_id);
    } catch (retrieveError) {
      setRetrievalError(presentTrendMessage(getUserErrorMessage(retrieveError, "Không thể tìm bài báo RSS.")));
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteCandidate) return;
    const reportId = deleteCandidate.report_id;
    setDeletingReportId(reportId);
    setHistoryError("");
    try {
      await deleteTrendReport(reportId);
      setReports((current) => current.filter((item) => item.report_id !== reportId));
      setSelectedReportId((current) => current === reportId ? reports.find((item) => item.report_id !== reportId)?.report_id ?? null : current);
      setTrustByReport((current) => {
        const next = { ...current };
        delete next[reportId];
        return next;
      });
      setDeleteCandidate(null);
    } catch (deleteError) {
      setHistoryError(presentTrendMessage(getUserErrorMessage(deleteError, "Không thể xóa báo cáo RSS.")));
    } finally {
      setDeletingReportId("");
    }
  };

  useEffect(() => {
    if (!open) return undefined;
    void Promise.resolve().then(() => loadReports());
    const closeOnEscape = (event) => { if (event.key === "Escape") closePanel(); };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, loadReports, closePanel]);

  if (!open) return null;

  return createPortal(
    <div className="trend-report-panel" role="dialog" aria-modal="true" aria-label="Tìm bài báo theo chủ đề (RSS)">
      <button type="button" className="trend-report-panel__backdrop" onClick={closePanel} aria-label="Đóng tìm bài báo theo chủ đề" />
      <aside className="trend-report-panel__drawer">
        <header className="trend-report-panel__header">
          <span><FiRadio /></span>
          <div><h2>Tìm bài báo theo chủ đề (RSS)</h2><p>{conversationId ? "Bài báo cho cuộc trò chuyện hiện tại" : "Bài báo RSS đã lưu"}</p></div>
          <button type="button" onClick={closePanel} aria-label="Đóng"><FiX /></button>
        </header>
        <div className="trend-report-panel__content">
          <p className="trend-report-panel__scope">Tìm trong 2 feed RSS hiện cấu hình của Báo Thanh Niên (Tiêu dùng thông minh và Ẩm thực). Bài báo không chứng minh lượt xem, doanh số, độ viral hay thứ hạng trên mạng xã hội.</p>
          <form className="trend-report-panel__retrieve" onSubmit={runRetrieval}>
            <label htmlFor="trend-report-query">Chủ đề tìm kiếm</label>
            <input id="trend-report-query" type="text" value={query} maxLength={512} onChange={(event) => setQuery(event.target.value)} placeholder="Ví dụ: đồ ăn vặt" disabled={isSubmitting} />
            <small className="trend-report-panel__counter">{query.length}/512 ký tự</small>
            <div className="trend-report-panel__search-actions">
              <button type="submit" disabled={isSubmitting || !query.trim()}>{isSubmitting ? "Đang tìm bài…" : "Tìm bài báo"}</button>
              <button type="button" className="is-secondary" onClick={loadReports} disabled={historyLoading}><FiRefreshCw className={historyLoading ? "is-spinning" : undefined} /> Tải lại lịch sử</button>
            </div>
            {retrievalError ? <p className="trend-report-panel__notice is-error" role="alert">{retrievalError}</p> : null}
          </form>
          {selectedReport ? <TrendReportResult report={selectedReport} /> : <p className="trend-report-panel__state">{historyLoading ? "Đang tải lịch sử báo cáo…" : "Nhập chủ đề để tìm bài báo, hoặc chọn báo cáo trong lịch sử."}</p>}

          <details className="trend-report-panel__section" open={historyOpen} onToggle={(event) => setHistoryOpen(event.currentTarget.open)}>
            <summary><strong>Lịch sử báo cáo</strong><small>{reports.length} báo cáo · chọn để xem lại hoặc xóa</small></summary>
            <div className="trend-report-panel__section-body">
              {historyLoading ? <p>Đang tải lịch sử…</p> : null}
              {historyError ? <p className="trend-report-panel__notice is-error" role="alert">{historyError}</p> : null}
              {!historyLoading && !reports.length ? <p>Chưa có báo cáo RSS nào cho phạm vi này.</p> : null}
              {reports.map((report) => <article className={`trend-report-panel__history-item${selectedReportId === report.report_id ? " is-selected" : ""}`} key={report.report_id}>
                <button type="button" className="trend-report-panel__history-select" onClick={() => setSelectedReportId(report.report_id)}>
                  <strong>{report.query}</strong><small>Thu thập: {formatReportDate(report.retrieved_at)} · {getProviderStatusPresentation(report).label}</small>
                </button>
                <button type="button" className="trend-report-panel__history-delete" onClick={() => setDeleteCandidate(report)} aria-label={`Xóa báo cáo RSS: ${report.query}`} title="Xóa bản ghi"><FiTrash2 /></button>
                {deleteCandidate?.report_id === report.report_id ? <div className="trend-report-panel__delete-confirm" role="alert"><span>Xóa bản ghi này?</span><div><button type="button" onClick={() => setDeleteCandidate(null)} disabled={deletingReportId === report.report_id}>Hủy</button><button type="button" onClick={confirmDelete} disabled={deletingReportId === report.report_id}>{deletingReportId === report.report_id ? "Đang xóa…" : "Xóa"}</button></div></div> : null}
              </article>)}
            </div>
          </details>

          <details className="trend-report-panel__section" open={trustOpen} onToggle={(event) => setTrustOpen(event.currentTarget.open)}>
            <summary><strong>Độ tin cậy sản phẩm</strong><small>Chế độ bằng chứng và chính sách nguồn</small></summary>
            <div className="trend-report-panel__section-body">
              <p>Chính sách nguồn chỉ ảnh hưởng đánh giá Độ tin cậy sản phẩm; không thay đổi danh sách RSS dùng để tìm bài.</p>
              <div className="trend-report-panel__trust-controls" role="group" aria-label="Chế độ bằng chứng">
                <div role="group" aria-label="Chế độ bằng chứng">
                  {["all_evidence", "verified_only"].map((mode) => <button key={mode} type="button" className={trustMode === mode ? "is-active" : ""} onClick={() => setTrustMode(mode)}>{mode === "verified_only" ? "Chỉ bằng chứng đã xác minh" : "Tất cả bằng chứng"}</button>)}
                </div>
                <small>{trustMode === "verified_only" ? "Chỉ dùng bằng chứng có cơ sở xác minh hợp lệ; backend áp dụng theo chính sách nguồn." : "Dùng mọi evidence hợp lệ theo đánh giá trust của backend; đây không phải độ tự tin của AI."}</small>
                <div className="trend-report-panel__policy-form"><input value={policyHost} onChange={(event) => setPolicyHost(event.target.value)} placeholder="nguon.example" aria-label="Tên miền nguồn" /><button type="button" disabled={policySaving || !policyHost.trim()} onClick={() => savePolicy("trusted")}>Tin cậy</button><button type="button" disabled={policySaving || !policyHost.trim()} onClick={() => savePolicy("excluded")}>Loại trừ</button></div>
                <small>Chính sách nguồn của bạn: {policies.length ? policies.map((item) => `${item.host} (${item.decision === "trusted" ? "tin cậy" : "loại trừ"})`).join(", ") : "chưa có"}</small>
              </div>
              {policyError ? <p className="trend-report-panel__notice is-error" role="alert">{policyError}</p> : null}
              {trustError ? <p className="trend-report-panel__notice is-error" role="alert">{trustError}</p> : null}
              {!selectedReport ? <p>Chọn báo cáo để xem Độ tin cậy sản phẩm.</p> : trustLoading ? <p>Đang tải Độ tin cậy sản phẩm…</p> : trustByReport[selectedReport.report_id] ? (() => {
                const trust = trustByReport[selectedReport.report_id];
                const warning = trustWarning(trust);
                return <section className={`trend-report-panel__trust is-${warning.tone}`}><p>{warning.text}</p>{Array.isArray(trust.claims) && trust.claims.length ? trust.claims.map((claim) => {
                  const presentation = trustPresentation(claim);
                  return <article key={claim.claim_id} className={`trend-report-panel__claim is-${presentation.tone}`}><strong>{claim.claim_text}</strong><span>Trạng thái: {presentation.label}</span><small>Hành động: {presentation.actionLabel}{presentation.highRisk ? " · Rủi ro cao" : ""}</small><small>{presentTrustRationale(claim.rationale)}</small></article>;
                }) : <p>Chưa có claim có cấu trúc cho báo cáo này.</p>}</section>;
              })() : <p>Chưa có đánh giá Độ tin cậy sản phẩm cho báo cáo này.</p>}
            </div>
          </details>

          <details className="trend-report-panel__section" open={workflowOpen} onToggle={(event) => setWorkflowOpen(event.currentTarget.open)}>
            <summary><strong>Quy trình chiến dịch — Stage 4</strong><small>Góc quảng cáo, brief, chiến dịch và số liệu do bạn nhập</small></summary>
            <div className="trend-report-panel__section-body">
              <p>Góc quảng cáo và brief là đề xuất của ứng dụng dựa trên bằng chứng và Độ tin cậy sản phẩm; không phải kết luận của bài báo.</p>
              {workflowOpen ? <Stage4WorkflowPanel /> : null}
            </div>
          </details>
        </div>
      </aside>
    </div>, document.body,
  );
}

export default TrendReportPanel;
