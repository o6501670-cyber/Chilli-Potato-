import { describe, expect, it } from 'vitest';
import { escapeCsvCell } from './csv.service';

describe('CSV escaping', () => {
  it.each(['=2+2', '+cmd', '-formula', '@SUM(A1:A2)', '  =hidden']) (
    'neutralises spreadsheet formula string %s',
    (value) => expect(escapeCsvCell(value)).toBe(`"'${value}"`),
  );

  it('preserves negative numeric values as numbers', () => {
    expect(escapeCsvCell(-12.5)).toBe('"-12.5"');
  });

  it('escapes embedded quotes and nulls', () => {
    expect(escapeCsvCell('A "quoted" value')).toBe('"A ""quoted"" value"');
    expect(escapeCsvCell(null)).toBe('""');
  });
});
