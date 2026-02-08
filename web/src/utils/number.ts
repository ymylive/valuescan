export const parseIntSafe = (value: string, fallback: number): number => {
  const next = Number.parseInt(value, 10);
  return Number.isFinite(next) ? next : fallback;
};

export const parseFloatSafe = (value: string, fallback: number): number => {
  const next = Number.parseFloat(value);
  return Number.isFinite(next) ? next : fallback;
};
