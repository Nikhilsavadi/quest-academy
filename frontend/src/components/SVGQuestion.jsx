import DOMPurify from 'dompurify'

export default function SVGQuestion({ svg }) {
  if (!svg) return null
  const clean = DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true } })
  return (
    <div
      className="my-3 flex justify-center [&_svg]:max-w-full [&_svg]:h-auto"
      dangerouslySetInnerHTML={{ __html: clean }}
    />
  )
}
