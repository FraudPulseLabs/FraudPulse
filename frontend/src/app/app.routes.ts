import { Routes } from '@angular/router';
import { adminGuard, authGuard, guestGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    canMatch: [guestGuard],
    loadComponent: () =>
      import('./features/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(m => m.LoginComponent),
  },

  // Public demo dashboard — no authentication. Model Validation is fully usable
  // by guests; the Live Pipeline Demo gates its actions behind sign-in itself.
  {
    path: 'demo',
    loadComponent: () =>
      import('./layout/demo-shell/demo-shell.component').then(m => m.DemoShellComponent),
    children: [
      { path: '', redirectTo: 'model-validation', pathMatch: 'full' },
      { path: 'model-validation', loadComponent: () => import('./features/model-demo/model-demo.component').then(m => m.ModelDemoComponent) },
      { path: 'live-pipeline',    loadComponent: () => import('./features/live-demo/live-demo.component').then(m => m.LiveDemoComponent) },
    ],
  },

  {
    path: '',
    canMatch: [authGuard],
    loadComponent: () =>
      import('./layout/shell/shell.component').then(m => m.ShellComponent),
    children: [
      { path: '', redirectTo: 'overview', pathMatch: 'full' },
      { path: 'overview',    loadComponent: () => import('./features/overview/overview.component').then(m => m.OverviewComponent) },
      { path: 'transactions', loadComponent: () => import('./features/transactions/transaction-list/transaction-list.component').then(m => m.TransactionListComponent) },
      { path: 'alerts',       loadComponent: () => import('./features/alerts/alert-queue/alert-queue.component').then(m => m.AlertQueueComponent) },
      { path: 'cases',        loadComponent: () => import('./features/cases/case-list/case-list.component').then(m => m.CaseListComponent) },
      { path: 'cases/:id',    loadComponent: () => import('./features/cases/case-detail/case-detail.component').then(m => m.CaseDetailComponent) },
      { path: 'watchlist',    loadComponent: () => import('./features/watchlist/watchlist.component').then(m => m.WatchlistComponent) },
      // Demos are also reachable from inside the authenticated app for analysts.
      { path: 'model-demo',   loadComponent: () => import('./features/model-demo/model-demo.component').then(m => m.ModelDemoComponent) },
      { path: 'live-demo',    loadComponent: () => import('./features/live-demo/live-demo.component').then(m => m.LiveDemoComponent) },
      { path: 'access',       canActivate: [adminGuard], loadComponent: () => import('./features/access/access-requests.component').then(m => m.AccessRequestsComponent) },
    ],
  },
  { path: '**', redirectTo: '' },
];
