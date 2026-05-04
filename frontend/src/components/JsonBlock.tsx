type JsonBlockProps = {
  value: unknown
}

export default function JsonBlock({ value }: JsonBlockProps) {
  return <pre className="json-block">{JSON.stringify(value, null, 2)}</pre>
}
