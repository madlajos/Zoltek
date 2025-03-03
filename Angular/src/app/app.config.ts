import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

import { routes } from './app.routes';

import { LightboxModule } from 'ngx-lightbox';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { FormsModule } from '@angular/forms';
import { MatCommonModule } from '@angular/material/core';

import { SharedService } from './shared.service';
import { MessageService } from './message.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(),
    provideAnimations(),
    importProvidersFrom(
      MatCommonModule,
      LightboxModule,
      MatProgressBarModule,
      MatSidenavModule,
      MatExpansionModule,
      MatButtonModule,
      MatIconModule,
      FormsModule
    ),
    SharedService,
    MessageService,
  ]
};