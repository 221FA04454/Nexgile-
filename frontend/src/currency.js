export const DEFAULT_CURRENCY = "INR";
export const DEFAULT_CURRENCY_SYMBOL = "₹";
export const DEFAULT_LOCALE = "en-IN";

const inrFormatters = new Map();

function formatter(digits) {
  const key = String(digits);
  if (!inrFormatters.has(key)) {
    inrFormatters.set(
      key,
      new Intl.NumberFormat(DEFAULT_LOCALE, {
        style: "currency",
        currency: DEFAULT_CURRENCY,
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      })
    );
  }
  return inrFormatters.get(key);
}

export function formatINR(value, digits = 0) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return formatter(digits).format(Number(value));
}

export function formatINRCompact(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e7) return `₹${(n / 1e7).toFixed(1)} Cr`;
  if (abs >= 1e5) return `₹${(n / 1e5).toFixed(1)} L`;
  return formatINR(n);
}

export const currencyMeta = {
  currency: DEFAULT_CURRENCY,
  currency_symbol: DEFAULT_CURRENCY_SYMBOL,
  locale: DEFAULT_LOCALE,
};
