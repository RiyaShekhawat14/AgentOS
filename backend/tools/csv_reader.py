import csv
import statistics
from collections import Counter
from pathlib import Path

from backend.tools.base import Tool, ToolContext, ToolError

MAX_ROWS = 100_000
AGGREGATES = ("sum", "mean", "count", "min", "max")


def _num(value):
    if value is None:
        return None
    text = str(value).strip()
    for junk in (",", "₹", "$", "%"):
        text = text.replace(junk, "")
    try:
        return float(text) if text else None
    except ValueError:
        return None


def _load(ctx: ToolContext, name):
    if not name:
        raise ToolError("Give the CSV file name in 'file'.")
    path = ctx.data_dir / Path(str(name)).name  # basename only: no path tricks
    if path.suffix.lower() != ".csv" or not path.is_file():
        available = sorted(p.name for p in ctx.data_dir.glob("*.csv")) if ctx.data_dir.is_dir() else []
        raise ToolError(f"File '{name}' not found. Available CSV files: {available or 'none'}")
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = [row for _, row in zip(range(MAX_ROWS), reader)]
        fields = reader.fieldnames or []
    if not rows:
        raise ToolError("The CSV file has no data rows.")
    return fields, rows


def _column(fields, name):
    if not name:
        raise ToolError("Give a column name in 'column'.")
    for f in fields:
        if f == name or f.strip().lower() == str(name).strip().lower():
            return f
    raise ToolError(f"Column '{name}' not found. Columns are: {fields}")


def _numeric_values(rows, col):
    values = [_num(r.get(col)) for r in rows]
    return [v for v in values if v is not None]


def _describe(fields, rows):
    columns = []
    for col in fields:
        raw = [r.get(col) for r in rows if str(r.get(col) or "").strip()]
        nums = _numeric_values(rows, col)
        info = {"name": col, "non_empty": len(raw)}
        if raw and len(nums) / len(raw) >= 0.8:
            info.update(type="number", min=min(nums), max=max(nums),
                        mean=round(statistics.fmean(nums), 4), sum=round(sum(nums), 4))
        else:
            top = Counter(raw).most_common(3)
            info.update(type="text", unique=len(set(raw)), top_values=[v for v, _ in top])
        columns.append(info)
    return {"rows": len(rows), "columns": columns}


def _head(fields, rows, args):
    try:
        n = int(args.get("n") or 5)
    except ValueError:
        raise ToolError("'n' must be a number.")
    return {"columns": fields, "rows": rows[:max(1, min(n, 20))]}


def _aggregate(fields, rows, args):
    agg = str(args.get("agg") or "sum").lower()
    if agg not in AGGREGATES:
        raise ToolError(f"'agg' must be one of: {', '.join(AGGREGATES)}.")
    group_by = _column(fields, args["group_by"]) if args.get("group_by") else None
    column = _column(fields, args.get("column")) if (agg != "count" or args.get("column")) else None
    groups = {}
    for r in rows:
        key = r.get(group_by) if group_by else "all"
        if agg == "count":
            groups.setdefault(key, []).append(1)
        else:
            v = _num(r.get(column))
            if v is not None:
                groups.setdefault(key, []).append(v)
    if not groups:
        raise ToolError(f"Column '{column}' has no numeric values.")
    fn = {"sum": sum, "mean": statistics.fmean, "count": len, "min": min, "max": max}[agg]
    result = sorted(((k, fn(v)) for k, v in groups.items()), key=lambda kv: kv[1], reverse=True)
    return {"agg": agg, "column": column, "group_by": group_by, "total_groups": len(result),
            "groups": [{"group": k, "value": round(v, 4)} for k, v in result[:20]]}


def _anomalies(fields, rows, args):
    col = _column(fields, args.get("column"))
    pairs = [(i, _num(r.get(col))) for i, r in enumerate(rows)]
    pairs = [(i, v) for i, v in pairs if v is not None]
    if len(pairs) < 4:
        raise ToolError("Need at least 4 numeric values to look for anomalies.")
    q1, _, q3 = statistics.quantiles([v for _, v in pairs], n=4)
    low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    found = [{"row": i + 2, "value": v, "data": rows[i]} for i, v in pairs if v < low or v > high]
    return {"column": col, "normal_range": [round(low, 4), round(high, 4)],
            "anomaly_count": len(found), "anomalies": found[:10]}


def run(args: dict, ctx: ToolContext):
    fields, rows = _load(ctx, args.get("file"))
    action = str(args.get("action") or "describe").lower()
    if action == "describe":
        return _describe(fields, rows)
    if action == "head":
        return _head(fields, rows, args)
    if action == "aggregate":
        return _aggregate(fields, rows, args)
    if action == "anomalies":
        return _anomalies(fields, rows, args)
    raise ToolError("'action' must be one of: describe, head, aggregate, anomalies.")


TOOL = Tool(
    name="csv_reader",
    description="Read and analyse an uploaded CSV file: columns, sample rows, totals by group, outliers.",
    args={
        "file": "CSV file name, for example Sales.csv",
        "action": "describe | head | aggregate | anomalies (default describe)",
        "column": "column to use (aggregate, anomalies)",
        "group_by": "optional column to group by (aggregate)",
        "agg": "sum | mean | count | min | max (aggregate, default sum)",
        "n": "number of rows for head (default 5)",
    },
    run=run,
)
