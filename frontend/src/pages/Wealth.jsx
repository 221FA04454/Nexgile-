import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, money, Status } from "../components/ui";

export default function Wealth() {
  const { data, loading, error, reload } = useApi(() => api.accounts(), []);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Accounts</div>
          <h1>Household wealth</h1>
          <p>Custodied positions plus cash reserve. Real estate and mortgage are off-book for net-worth only.</p>
        </div>
        <div className="metric-sm num">{money(data.total_market_value)}</div>
      </div>
      <div className="grid g-2">
        {data.accounts.map((a) => (
          <Card key={a.id} title={a.type.replace("_", " ")}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, margin: 0, fontSize: 22 }}>{a.name}</h2>
                <div className="faint">
                  {a.masked} · {a.owner} · {a.provider}
                </div>
              </div>
              <Status value={a.status} />
            </div>
            <div className="metric num" style={{ marginTop: 12 }}>
              {money(a.market_value)}
            </div>
            <div className="grid g-3" style={{ marginTop: 12 }}>
              <div>
                <div className="faint">Cash</div>
                <strong className="num">{money(a.cash)}</strong>
              </div>
              <div>
                <div className="faint">Cost basis</div>
                <strong className="num">{money(a.cost_basis)}</strong>
              </div>
              <div>
                <div className="faint">Unrealized</div>
                <strong className="num" style={{ color: a.unrealized >= 0 ? "var(--up)" : "var(--down)" }}>
                  {money(a.unrealized)}
                </strong>
              </div>
            </div>
            <p className="faint" style={{ marginTop: 10 }}>
              Tax status {a.tax_status} · as of {a.as_of} · source {a.source} · v{a.version}
            </p>
          </Card>
        ))}
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Balance sheet (illustrative)">
          <div className="grid g-3">
            <div>
              <div className="faint">Invested + cash</div>
              <div className="metric-sm num">{money(data.total_market_value)}</div>
            </div>
            <div>
              <div className="faint">Residence (external)</div>
              <div className="metric-sm num">{money(data.balance_sheet?.other_assets)}</div>
            </div>
            <div>
              <div className="faint">Mortgage (external)</div>
              <div className="metric-sm num">{money(data.balance_sheet?.liabilities)}</div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
