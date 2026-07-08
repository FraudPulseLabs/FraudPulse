import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { authGuard, guestGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('auth guards', () => {
  let auth: { resolveSession: jest.Mock };
  let router: { createUrlTree: jest.Mock };

  beforeEach(() => {
    auth = {
      resolveSession: jest.fn(),
    };
    router = {
      createUrlTree: jest.fn((commands: unknown[]) => ({ commands }) as unknown as UrlTree),
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });
  });

  it('authGuard allows authenticated users', async () => {
    auth.resolveSession.mockResolvedValue({ user: { id: '1' } } as never);

    const result = await TestBed.runInInjectionContext(() => authGuard({} as never, [] as never));

    expect(result).toBe(true);
  });

  it('authGuard redirects guests to landing', async () => {
    auth.resolveSession.mockResolvedValue(null);
    const tree = { redirected: true } as unknown as UrlTree;
    router.createUrlTree.mockReturnValue(tree);

    const result = await TestBed.runInInjectionContext(() => authGuard({} as never, [] as never));

    expect(router.createUrlTree).toHaveBeenCalledWith(['/']);
    expect(result).toBe(tree);
  });

  it('guestGuard sends signed-in users to overview', async () => {
    auth.resolveSession.mockResolvedValue({ user: { id: '1' } } as never);
    const tree = { redirected: true } as unknown as UrlTree;
    router.createUrlTree.mockReturnValue(tree);

    const result = await TestBed.runInInjectionContext(() => guestGuard({} as never, [] as never));

    expect(router.createUrlTree).toHaveBeenCalledWith(['/overview']);
    expect(result).toBe(tree);
  });

  it('guestGuard allows anonymous visitors', async () => {
    auth.resolveSession.mockResolvedValue(null);

    const result = await TestBed.runInInjectionContext(() => guestGuard({} as never, [] as never));

    expect(result).toBe(true);
  });
});
