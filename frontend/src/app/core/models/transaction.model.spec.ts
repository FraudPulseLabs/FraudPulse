import { mapBackendDecisionToUi } from './transaction.model';

describe('transaction.model', () => {
  it('maps backend decisions to UI labels', () => {
    expect(mapBackendDecisionToUi('APPROVE')).toBe('ALLOW');
    expect(mapBackendDecisionToUi('APPROVE_WITH_REVIEW')).toBe('REVIEW');
    expect(mapBackendDecisionToUi('DECLINE')).toBe('BLOCK');
    expect(mapBackendDecisionToUi(null)).toBe('ALLOW');
  });
});
