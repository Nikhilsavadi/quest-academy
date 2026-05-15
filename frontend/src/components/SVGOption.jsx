import DOMPurify from 'dompurify'

export default function SVGOption({ svg }) {
  const clean = DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true } })
  return (
    <div
      className="flex items-center justify-center w-20 h-20 [&_svg]:w-full [&_svg]:h-full"
      dangerouslySetInnerHTML={{ __html: clean }}
    />
  )
}
