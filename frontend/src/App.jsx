import { useEffect, useMemo, useState } from "react";

const API = "/api/v1";

function Badge({ status }) {
  const classes = {
    pending: "bg-slate-700 text-slate-100",
    processing: "bg-amber-600 text-amber-50",
    completed: "bg-emerald-700 text-emerald-50",
    failed: "bg-rose-700 text-rose-50",
  };
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${classes[status] || classes.pending}`}>
      {status}
    </span>
  );
}

function formatInrFromPaise(v) {
  const inr = Number(v || 0) / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(inr);
}

function parseInrToPaise(v) {
  const normalized = String(v || "").replace(/,/g, "").trim();
  if (!normalized) return NaN;
  const amount = Number(normalized);
  if (!Number.isFinite(amount)) return NaN;
  return Math.round(amount * 100);
}

export default function App() {
  const [merchantId, setMerchantId] = useState("1");
  const [balance, setBalance] = useState({ available_balance_paise: 0, held_balance_paise: 0 });
  const [payouts, setPayouts] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [amountInr, setAmountInr] = useState("50.00");
  const [bankAccountId, setBankAccountId] = useState("bank_demo_001");
  const [idempotencyKey, setIdempotencyKey] = useState("demo-key-001");
  const [message, setMessage] = useState("");

  const headers = useMemo(() => ({ "X-Merchant-Id": merchantId }), [merchantId]);

  async function refresh() {
    if (!merchantId) return;
    const [balanceRes, payoutsRes, ledgerRes] = await Promise.all([
      fetch(`${API}/balance`, { headers }),
      fetch(`${API}/payouts`, { headers }),
      fetch(`${API}/ledger?limit=10`, { headers }),
    ]);

    const b = await balanceRes.json();
    const p = await payoutsRes.json();
    const l = await ledgerRes.json();

    if (!balanceRes.ok) throw new Error(b.detail || "Failed to load balance");
    if (!payoutsRes.ok) throw new Error(p.detail || "Failed to load payouts");
    if (!ledgerRes.ok) throw new Error(l.detail || "Failed to load ledger");

    setBalance(b);
    setPayouts(p);
    setLedger(l);
  }

  async function createPayout() {
    setMessage("Creating payout...");
    const amountPaise = parseInrToPaise(amountInr);
    if (!Number.isInteger(amountPaise) || amountPaise <= 0) {
      throw new Error("Enter a valid INR amount greater than 0");
    }

    const res = await fetch(`${API}/payouts`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify({ amount_paise: amountPaise, bank_account_id: bankAccountId }),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail || "Payout failed");
    if (res.status === 200) {
      setMessage("Idempotency replay: existing payout returned");
    } else {
      setMessage("Payout created");
    }
    await refresh();
  }

  useEffect(() => {
    refresh().catch((e) => setMessage(e.message));
    const i = setInterval(() => refresh().catch((e) => setMessage(e.message)), 3000);
    return () => clearInterval(i);
  }, [merchantId]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl p-6">
        <h1 className="text-3xl font-bold">Playto Payout Dashboard</h1>
        <p className="mt-2 text-slate-400">React + Tailwind demo for payout lifecycle, idempotency, and ledger invariants.</p>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <label className="text-xs uppercase tracking-wider text-slate-400">Merchant ID</label>
            <input
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              value={merchantId}
              onChange={(e) => setMerchantId(e.target.value)}
            />
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="text-xs uppercase tracking-wider text-slate-400">Available Balance</div>
            <div className="mt-2 text-2xl font-semibold">{formatInrFromPaise(balance.available_balance_paise)}</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="text-xs uppercase tracking-wider text-slate-400">Held Balance</div>
            <div className="mt-2 text-2xl font-semibold">{formatInrFromPaise(balance.held_balance_paise)}</div>
          </div>
        </div>

        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">
          <h2 className="text-lg font-semibold">Request Payout</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              placeholder="amount_inr (e.g. 600.50)"
              value={amountInr}
              onChange={(e) => setAmountInr(e.target.value)}
            />
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              placeholder="bank_account_id"
              value={bankAccountId}
              onChange={(e) => setBankAccountId(e.target.value)}
            />
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              placeholder="Idempotency-Key"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
            />
            <button onClick={() => createPayout().catch((e) => setMessage(e.message))} className="rounded-lg bg-cyan-600 px-4 py-2 font-semibold hover:bg-cyan-500">
              Submit
            </button>
          </div>
          <div className="mt-2 text-xs text-slate-400">UI takes INR and converts to paise internally before API call.</div>
          <div className="mt-2 text-sm text-cyan-300">{message}</div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-lg font-semibold">Payout History</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="px-2 py-2 text-left">ID</th>
                    <th className="px-2 py-2 text-left">Amount</th>
                    <th className="px-2 py-2 text-left">Status</th>
                    <th className="px-2 py-2 text-left">Attempts</th>
                    <th className="px-2 py-2 text-left">Key</th>
                  </tr>
                </thead>
                <tbody>
                  {payouts.map((p) => (
                    <tr key={p.id} className="border-t border-slate-800">
                      <td className="px-2 py-2">{p.id}</td>
                      <td className="px-2 py-2">{formatInrFromPaise(p.amount_paise)}</td>
                      <td className="px-2 py-2"><Badge status={p.status} /></td>
                      <td className="px-2 py-2">{p.attempts}</td>
                      <td className="px-2 py-2">{p.idempotency_key}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-lg font-semibold">Recent Ledger</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="px-2 py-2 text-left">Type</th>
                    <th className="px-2 py-2 text-left">Kind</th>
                    <th className="px-2 py-2 text-left">Amount</th>
                    <th className="px-2 py-2 text-left">Payout</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.map((e) => (
                    <tr key={e.id} className="border-t border-slate-800">
                      <td className="px-2 py-2">{e.entry_type}</td>
                      <td className="px-2 py-2">{e.kind}</td>
                      <td className="px-2 py-2">{formatInrFromPaise(e.amount_paise)}</td>
                      <td className="px-2 py-2">{e.payout_id || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
