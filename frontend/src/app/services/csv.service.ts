import { Injectable } from '@angular/core';

export function escapeCsvCell(cell: unknown): string {
  if (cell === null || cell === undefined) return '""';
  let value = String(cell);
  if (typeof cell === 'string' && /^\s*[=+\-@]/.test(value)) {
    value = `'${value}`;
  }
  return `"${value.replace(/"/g, '""')}"`;
}

@Injectable({
  providedIn: 'root'
})
export class CsvService {
  exportToCsv(filename: string, headers: string[], rows: unknown[][]): void {
    // Create CSV content with UTF-8 BOM so Excel opens it correctly
    let csvContent = "\uFEFF" + headers.map(escapeCsvCell).join(",") + "\n";
    
    if (rows && rows.length) {
    
    rows.forEach(row => {
      const rowData = row.map(escapeCsvCell);
      csvContent += rowData.join(",") + "\n";
    });
    }
    
    // Download Blob
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}
