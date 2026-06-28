import { TimeAgoPipe } from './time-ago.pipe';

describe('TimeAgoPipe', () => {
  const pipe = new TimeAgoPipe();

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-06-01T12:30:00Z'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns just now for recent timestamps', () => {
    expect(pipe.transform('2026-06-01T12:29:30Z')).toBe('just now');
  });

  it('returns minutes ago', () => {
    expect(pipe.transform('2026-06-01T12:00:00Z')).toBe('30m ago');
  });

  it('returns hours ago', () => {
    expect(pipe.transform('2026-06-01T08:00:00Z')).toBe('4h ago');
  });

  it('returns days ago', () => {
    expect(pipe.transform('2026-05-28T12:00:00Z')).toBe('4d ago');
  });
});
