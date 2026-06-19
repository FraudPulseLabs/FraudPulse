import { NgModule } from '@angular/core';
import { LucideAngularModule } from 'lucide-angular';
import { lucideIcons } from './app-icons';

/** Import in standalone components that use `<lucide-icon>`. */
@NgModule({
  imports: [LucideAngularModule.pick(lucideIcons)],
  exports: [LucideAngularModule],
})
export class FpIconsModule {}
