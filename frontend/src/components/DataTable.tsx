import type { ReactNode } from 'react'

type Column<T> = {
  key: string
  header: string
  render: (row: T) => ReactNode
}

type DataTableProps<T> = {
  rows: T[]
  columns: Column<T>[]
}

export default function DataTable<T>({ rows, columns }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="muted">No data.</p>
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
