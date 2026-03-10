const p = (n: number) => String(n).padStart(2, '0')

/** Local datetime for <input type="datetime-local"> */
export function localISOString(d: Date = new Date()): string {
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

/** Local YYYY-MM-DD — safe replacement for new Date(y,m,d).toISOString().split('T')[0] */
export function localDateString(year: number, month: number, day: number): string {
    // Normalization: new Date(year, month, day) handles overflows/underflows (e.g. day 0 is last day of prev month)
    const d = new Date(year, month, day)
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/** Today as YYYY-MM-DD in local timezone */
export function todayLocalString(): string {
    const d = new Date()
    return localDateString(d.getFullYear(), d.getMonth(), d.getDate())
}
