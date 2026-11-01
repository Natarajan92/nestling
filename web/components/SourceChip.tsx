import type { SourceChipData } from "@/lib/api";

/** A small pill naming where a statement comes from; links to the source when it has a URL. */
export default function SourceChip({ source }: { source: SourceChipData }) {
  const label = [source.publisher ?? source.id, source.year, source.page ? `p. ${source.page}` : null]
    .filter(Boolean)
    .join(" · ");
  const cls =
    "inline-flex max-w-full items-center gap-1 rounded-full border border-sage bg-sage/20 px-3 py-1 text-xs text-ink";
  const text = <span className="truncate">📖 {label}</span>;
  return source.url ? (
    <a href={source.url} target="_blank" rel="noopener noreferrer" title={source.title ?? source.id} className={cls}>
      {text}
    </a>
  ) : (
    <span title={source.title ?? source.id} className={cls}>
      {text}
    </span>
  );
}
