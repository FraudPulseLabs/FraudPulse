import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'decisionColor', standalone: true })
export class DecisionColorPipe implements PipeTransform {
  transform(decision: string): string {
    switch (decision?.toUpperCase()) {
      case 'ALLOW':  return 'badge-allow';
      case 'REVIEW': return 'badge-review';
      case 'BLOCK':  return 'badge-block';
      default:       return '';
    }
  }
}
