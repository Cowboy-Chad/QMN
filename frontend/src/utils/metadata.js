/**
 * Shared utility for formatting metadata fields into display lines.
 * Used by AnalysisRunner.jsx and HistoryPage.jsx.
 */
export function formatMetadataLines(meta) {
  if (!meta) return []
  return [
    meta.title && `Title: ${meta.title}`,
    meta.webpage_url && `Title URL: ${meta.webpage_url}`,
    meta.channel && `Channel: ${meta.channel}`,
    meta.channel_url && `Channel URL: ${meta.channel_url}`,
    meta.view_count != null && `Views: ${meta.view_count.toLocaleString()}`,
    meta.duration_display && `Video Length: ${meta.duration_display}`,
    meta.upload_date_display && `Published: ${meta.upload_date_display}${meta.upload_date_relative ? ` (${meta.upload_date_relative})` : ''}`,
    meta.fabric_pattern && `Fabric Pattern: ${meta.fabric_pattern}`,
    meta.model && `Model: ${meta.model}`,
    meta.processing_time_seconds != null && `Processing Time: ${meta.processing_time_seconds}s`,
    meta.transcript_source && `Transcript Source: ${meta.transcript_source}`,
    meta.input_tokens != null && `Tokens: ${meta.input_tokens} in / ${meta.output_tokens} out (via tiktoken)`,
    meta.estimated_cost != null && `Pattern Cost: $${Number(meta.estimated_cost).toFixed(4)}`,
    meta.pricing_source && `Pricing Source: ${meta.pricing_source}`,
  ].filter(Boolean)
}