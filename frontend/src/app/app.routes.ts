import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./layout/shell/shell.component').then(m => m.ShellComponent),
    children: [
      { path: '', redirectTo: 'transactions', pathMatch: 'full' },
      { path: 'transactions', loadComponent: () => import('./features/transactions/transaction-list/transaction-list.component').then(m => m.TransactionListComponent) },
      { path: 'alerts',       loadComponent: () => import('./features/alerts/alert-queue/alert-queue.component').then(m => m.AlertQueueComponent) },
      { path: 'cases',        loadComponent: () => import('./features/cases/case-list/case-list.component').then(m => m.CaseListComponent) },
      { path: 'cases/:id',    loadComponent: () => import('./features/cases/case-detail/case-detail.component').then(m => m.CaseDetailComponent) },
      { path: 'watchlist',    loadComponent: () => import('./features/watchlist/watchlist.component').then(m => m.WatchlistComponent) },
      { path: 'metrics',      loadComponent: () => import('./features/metrics/metrics-dashboard/metrics-dashboard.component').then(m => m.MetricsDashboardComponent) },
      { path: 'model-demo',   loadComponent: () => import('./features/model-demo/model-demo.component').then(m => m.ModelDemoComponent) },
    ],
  },
  { path: '**', redirectTo: '' },
];
