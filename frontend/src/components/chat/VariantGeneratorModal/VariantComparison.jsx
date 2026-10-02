const CRITERIA = [
  ["Mức thu hút", "Mức độ thu hút"],
  ["CTA", "Chất lượng CTA"],
  ["Khả năng chuyển đổi", "Khả năng chuyển đổi"],
  ["Phù hợp nền tảng", "Phù hợp nền tảng quảng cáo"],
  ["Độ dài", "Độ dài"],
];

const scoreFor = (evaluation, criterionName) =>
  evaluation?.criteria?.find((item) => item.name === criterionName)?.score ?? "—";

function VariantComparison({
  variants,
  evaluations,
  onEvaluateAll,
  onSaveBest,
  saving,
}) {
  if (variants.length < 2) return null;

  const complete = variants.every((item) => evaluations[item.label]);
  const recommended = complete
    ? [...variants].sort(
        (left, right) =>
          evaluations[right.label].overall_score -
          evaluations[left.label].overall_score,
      )[0]
    : null;

  return (
    <section className="variant-comparison">
      <div className="variant-comparison__heading">
        <div>
          <h3>So sánh phiên bản</h3>
          <p>Điểm số là đề xuất của AI, không phải kết quả quảng cáo thực tế.</p>
        </div>
        {!complete && (
          <button type="button" onClick={onEvaluateAll}>
            Đánh giá các bản đã chọn
          </button>
        )}
      </div>

      {complete && (
        <>
          <div className="variant-comparison__table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tiêu chí</th>
                  {variants.map((variant) => (
                    <th key={variant.label}>Bản {variant.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>Điểm tổng</th>
                  {variants.map((variant) => (
                    <td key={variant.label}>
                      <strong>{evaluations[variant.label].overall_score}</strong>
                    </td>
                  ))}
                </tr>
                {CRITERIA.map(([label, name]) => (
                  <tr key={name}>
                    <th>{label}</th>
                    {variants.map((variant) => (
                      <td key={variant.label}>
                        {scoreFor(evaluations[variant.label], name)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="variant-comparison__recommendation">
            <p>
              AI đề xuất <strong>Phiên bản {recommended.label}</strong> vì có
              điểm tổng cao nhất trong các bản được chọn.
            </p>
            <button
              type="button"
              onClick={() => onSaveBest(recommended)}
              disabled={saving}
            >
              Lưu phiên bản tốt nhất
            </button>
          </div>
        </>
      )}
    </section>
  );
}

export default VariantComparison;
