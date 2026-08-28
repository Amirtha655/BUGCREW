export function fmtCurrency(n: number | undefined | null, decimals = 0): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "₹0";
  const sign = n < 0 ? "-" : "";
  return (
    sign +
    "₹" +
    Math.abs(n).toLocaleString("en-IN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })
  );
}

/** Signed currency, for gains/losses where the direction matters. */
export function fmtSigned(n: number | undefined | null, decimals = 0): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "₹0";
  return (n >= 0 ? "+" : "") + fmtCurrency(n, decimals);
}

export function fmtPct(n: number | undefined | null, digits = 2): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "0.00%";
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}%`;
}

/** Unsigned percentage, for shares/ratios rather than changes. */
export function fmtPctPlain(n: number | undefined | null, digits = 1): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "0%";
  return `${n.toFixed(digits)}%`;
}

export function fmtNum(n: number | undefined | null, digits = 2): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "0";
  return n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtTime(iso: string | undefined): string {
  if (!iso) return "--:--:--";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "--:--:--";
  return d.toLocaleTimeString("en-GB", { hour12: false });
}

export function fmtClock(iso: string | undefined): string {
  if (!iso) return "--:--";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "--:--";
  return d.toLocaleTimeString("en-GB", { hour12: false, hour: "2-digit", minute: "2-digit" });
}

export function toneClass(tone: string): string {
  return tone;
}

export function pnlTone(n: number): string {
  if (n > 0) return "pos";
  if (n < 0) return "neg";
  return "";
}
