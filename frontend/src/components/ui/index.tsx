import { useState, useMemo } from "react";
import type { ReactNode } from "react";
import type { Term } from "../../utils/vocab";

/* ---------------- Panel ---------------- */

export function Panel({
  title, sub, actions, children, flush = false,
}: {
  title?: ReactNode; sub?: ReactNode; actions?: ReactNode; children: ReactNode; flush?: boolean;
}) {
  return (
    <section className="panel">
      {(title || actions) && (
        <div className="panel-header">
          <div className="row" style={{ gap: 8, minWidth: 0 }}>
            {typeof title === "string" ? <h3>{title}</h3> : title}
            {sub && <span className="sub">{sub}</span>}
          </div>
          {actions && <div className="row" style={{ gap: 6 }}>{actions}</div>}
        </div>
      )}
      <div className={`panel-body${flush ? " flush" : ""}`}>{children}</div>
    </section>
  );
}

/* ---------------- InfoLabel: plain label + hover explanation ---------------- */

export function InfoLabel({ term, override }: { term: Term; override?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="info-label">
      {override ?? term.label}
      <span
        className="hint"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        aria-label={term.help}
      >
        ?
      </span>
      {open && (
        <span className="tip">
          {term.help}
          {term.technical && <span className="term">Technical term: {term.technical}</span>}
        </span>
      )}
    </span>
  );
}

/* ---------------- Badge ---------------- */

export function Badge({ tone = "gray", children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

/* ---------------- StatTile ---------------- */

export function StatTile({
  term, label, value, delta, deltaTone, note, small,
}: {
  term?: Term; label?: string; value: ReactNode;
  delta?: ReactNode; deltaTone?: string; note?: ReactNode; small?: boolean;
}) {
  return (
    <div className="stat-tile">
      <div className="label">{term ? <InfoLabel term={term} override={label} /> : label}</div>
      <div className={`value${small ? " sm" : ""}`}>{value}</div>
      {delta !== undefined && <div className={`delta ${deltaTone ?? ""}`}>{delta}</div>}
      {note !== undefined && <div className="note">{note}</div>}
    </div>
  );
}

export function StatRow({ cols, children }: { cols: number; children: ReactNode }) {
  return (
    <div className="stat-row" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
      {children}
    </div>
  );
}

/* ---------------- Meter ---------------- */

export function Meter({ pct, tone = "blue" }: { pct: number; tone?: string }) {
  const width = Math.max(0, Math.min(100, pct));
  const color = `var(--${tone === "gray" ? "text-faint" : tone})`;
  return (
    <div className="meter">
      <span style={{ width: `${width}%`, background: color }} />
    </div>
  );
}

/* ---------------- EmptyState ---------------- */

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children}
    </div>
  );
}

/* ---------------- DataTable ---------------- */

export interface Column<T> {
  key: string;
  header: ReactNode;
  align?: "left" | "right" | "center";
  width?: string;
  sortable?: boolean;
  /** Value used for sorting; falls back to the rendered cell when absent. */
  sortValue?: (row: T) => string | number;
  render: (row: T) => ReactNode;
}

export function DataTable<T>({
  columns, rows, rowKey, onRowClick, selectedKey, minWidth, initialSort, emptyTitle, emptyBody,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  selectedKey?: string | null;
  minWidth?: number;
  initialSort?: { key: string; dir: "asc" | "desc" };
  emptyTitle?: string;
  emptyBody?: ReactNode;
}) {
  const [sort, setSort] = useState<{ key: string; dir: "asc" | "desc" } | null>(initialSort ?? null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sortValue) return rows;
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = col.sortValue!(a);
      const bv = col.sortValue!(b);
      if (av === bv) return 0;
      const res = av > bv ? 1 : -1;
      return sort.dir === "asc" ? res : -res;
    });
    return copy;
  }, [rows, sort, columns]);

  const toggle = (key: string) => {
    setSort((prev) =>
      prev?.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "desc" }
    );
  };

  if (rows.length === 0) {
    return <Empty title={emptyTitle ?? "Nothing to show yet"}>{emptyBody}</Empty>;
  }

  return (
    <div className="table-scroll">
      <table className="dt" style={minWidth ? { minWidth } : undefined}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={`${c.align === "right" ? "r" : c.align === "center" ? "c" : ""}${c.sortable ? " sortable" : ""}`}
                style={c.width ? { width: c.width } : undefined}
                onClick={c.sortable ? () => toggle(c.key) : undefined}
              >
                {c.header}
                {c.sortable && sort?.key === c.key && (
                  <span className="arrow">{sort.dir === "asc" ? "▲" : "▼"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => {
            const key = rowKey(row);
            return (
              <tr
                key={key}
                className={`${onRowClick ? "clickable" : ""} ${selectedKey === key ? "selected" : ""}`}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((c) => (
                  <td key={c.key} className={c.align === "right" ? "r" : c.align === "center" ? "c" : ""}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ---------------- Page header ---------------- */

export function PageHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {actions && <div className="row" style={{ gap: 6 }}>{actions}</div>}
    </header>
  );
}
