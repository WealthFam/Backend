const p = (n: number) => String(n).padStart(2, '0')

/** Local datetime for <input type="datetime-local"> */
export function localISOString(d: Date = new Date()): string {
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

/** Local YYYY-MM-DD — safe replacement for new Date(y,m,d).toISOString().split('T')[0] */
export function localDateString(year: number, month: number, day: number): string {
    return `${year}-${p(month + 1)}-${p(day)}`
}

/** Today as YYYY-MM-DD in local timezone */
export function todayLocalString(): string {
    const d = new Date()
    return localDateString(d.getFullYear(), d.getMonth(), d.getDate())
}
