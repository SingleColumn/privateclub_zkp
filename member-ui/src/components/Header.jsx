export default function Header({ title, subtitle, helpLink }) {
  return (
    <header className="mb-10">
      <h1 className="text-2xl font-semibold text-white tracking-tight">{title}</h1>
      {subtitle ? <p className="mt-1.5 text-gray-400 text-sm">{subtitle}</p> : null}
      {helpLink && (
        <a
          href={helpLink}
          className="mt-3 inline-block text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          How this works
        </a>
      )}
    </header>
  )
}
