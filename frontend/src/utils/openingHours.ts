import type { OpeningPeriod } from "../types";

/**
 * Given trip start_date (ISO string) and 1-based day_number,
 * return the weekday (0=Sun..6=Sat).
 */
export function getWeekday(startDate: string, dayNumber: number): number {
  const parts = startDate.split("-");
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  d.setDate(d.getDate() + dayNumber - 1);
  return d.getDay();
}

/**
 * Short weekday name from day number.
 */
const WEEKDAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
export function getWeekdayName(weekday: number): string {
  return WEEKDAY_NAMES[weekday] || "";
}

/**
 * Check if a place is open on the given weekday.
 */
export function getOpenStatus(
  openingHours: { periods: OpeningPeriod[] } | null | undefined,
  weekday: number
): "open" | "closed" | "unknown" {
  if (!openingHours?.periods?.length) return "unknown";
  const dayPeriods = openingHours.periods.filter((p) => p.day === weekday);
  return dayPeriods.length > 0 ? "open" : "closed";
}

/**
 * Format opening hours for a specific weekday.
 */
export function formatHoursForDay(
  openingHours: { periods: OpeningPeriod[] } | null | undefined,
  weekday: number
): string {
  if (!openingHours?.periods?.length) return "";
  const dayPeriods = openingHours.periods.filter((p) => p.day === weekday);
  if (dayPeriods.length === 0) return "Closed";
  return dayPeriods.map((p) => `${p.open} - ${p.close}`).join(", ");
}
