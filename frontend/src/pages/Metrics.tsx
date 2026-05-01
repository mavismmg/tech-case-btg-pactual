import { useState } from "react";

import { metricsApi } from "../api/resources";
import { Panel, Stat } from "../components/Panel";
import { Badge, Notice } from "../components/Status";
import { errorMessage, useAsync } from "../hooks";
import { formatCurrency, formatOperation } from "../utils/formatters";

export function MetricsPage() {
  const metrics = useAsync(() => metricsApi.loans(), []);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  async function exportCsv() {
    setExporting(true);
    setExportError(null);

    try {
      const csv = await metricsApi.exportLoansCsv();
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = "metricas-emprestimos.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(errorMessage(err, "load"));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="page">
      {metrics.error ? <Notice tone="error">{metrics.error}</Notice> : null}
      {exportError ? <Notice tone="error">{exportError}</Notice> : null}
      <div className="stats-grid">
        <Stat label="Total" value={metrics.data?.total_loans ?? 0} />
        <Stat label="Ativos" value={metrics.data?.active_loans ?? 0} />
        <Stat label="Atrasados" value={metrics.data?.overdue_loans ?? 0} />
        <Stat label="Devolvidos" value={metrics.data?.returned_loans ?? 0} />
        <Stat label="Multas" value={formatCurrency(metrics.data?.total_fine_value)} />
      </div>
      <Panel
        title="Eventos registrados"
        actions={
          <button type="button" onClick={exportCsv} disabled={exporting}>
            {exporting ? "Exportando..." : "Exportar CSV"}
          </button>
        }
      >
        {metrics.loading ? <span className="muted">Carregando eventos...</span> : null}
        {Object.keys(metrics.data?.events_by_operation ?? {}).length ? (
          <div className="event-list">
            {Object.entries(metrics.data?.events_by_operation ?? {}).map(([operation, total]) => (
              <div key={operation}>
                <Badge>{formatOperation(operation)}</Badge>
                <strong>{total}</strong>
              </div>
            ))}
          </div>
        ) : (
          !metrics.loading && <span className="muted">Nenhum evento registrado ainda.</span>
        )}
      </Panel>
    </div>
  );
}
