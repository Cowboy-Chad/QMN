/**
 * Heuristic: detect whether text contains markdown formatting.
 * Checks for multiple distinct markdown patterns to avoid false
 * positives on plain text that happens to contain *, -, etc.
 */
export function isMarkdown(text) {
  if (!text || typeof text !== 'string') return false

  let score = 0

  // Strong signals — unlikely in plain text
  if (/^#{1,6}\s/m.test(text)) score += 3          // ATX headings
  if (/```[\s\S]*?```/.test(text)) score += 3      // code blocks
  if (/^\s*\|[^\n]+\|\s*$/m.test(text)) score += 3 // table rows
  if (/^>\s/m.test(text)) score += 2               // blockquotes
  if (/^[-*]{3,}\s*$/m.test(text)) score += 2      // horizontal rules
  if (/\[([^\]]*)\]\(([^)]+)\)/.test(text)) score += 2  // links
  if (/!\[([^\]]*)\]\(([^)]+)\)/.test(text)) score += 2 // images

  // Weaker signals — could appear in plain text
  if (/^\s*[-*+]\s/m.test(text)) score += 1        // unordered lists
  if (/^\s*\d+\.\s/m.test(text)) score += 1        // ordered lists
  if (/(\*\*|__)(.*?)\1/.test(text)) score += 1    // bold
  if (/(\*|_)(.*?)\1/.test(text)) score += 1       // italic
  if (/`[^`]+`/.test(text)) score += 1             // inline code

  return score >= 3
}