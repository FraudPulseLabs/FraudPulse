import { DecisionColorPipe } from './decision-color.pipe';

describe('DecisionColorPipe', () => {
  const pipe = new DecisionColorPipe();

  it('maps known decisions to badge classes', () => {
    expect(pipe.transform('ALLOW')).toBe('badge-allow');
    expect(pipe.transform('review')).toBe('badge-review');
    expect(pipe.transform('BLOCK')).toBe('badge-block');
  });

  it('returns empty string for unknown decisions', () => {
    expect(pipe.transform('UNKNOWN')).toBe('');
  });
});
